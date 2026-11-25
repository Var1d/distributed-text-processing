"""MASTER: task decomposition, distribusi dinamis, deteksi kegagalan, agregasi hasil.
Contoh: python master.py --data data/corpus --chunk 10 --min-workers 9 --label dist_9w
Mode: --balancing dynamic (pull-based, default) | static (pembagian tetap, tanpa work stealing)
"""
import argparse, glob, json, os, socket, threading, time, uuid
import math
from collections import deque, Counter
from common.protocol import send_msg, recv_msg
from common.textproc import new_result, merge_into, from_wire, counter_digest
from common.metrics import append_summary, dataset_id

class Master:
    def __init__(self, a):
        self.a = a
        self.lock = threading.RLock()
        self.files = sorted(glob.glob(os.path.join(a.data, "*.txt")))
        if not self.files:
            raise SystemExit(f"Tidak ada .txt di {a.data}")
        self.total_bytes = sum(os.path.getsize(f) for f in self.files)
        self.dataset_id = dataset_id(self.files)
        self.tasks = {}
        for i in range(0, len(self.files), a.chunk):          # TASK DECOMPOSITION
            tid = len(self.tasks)
            self.tasks[tid] = {"files": self.files[i:i + a.chunk], "state": "pending",
                               "attempts": 0, "fail_time": None, "lease_id": None, "owner": None}
        self.pending = deque(self.tasks)
        self.queues = {}
        self.workers = {}
        self.started = False
        self.started_event = threading.Event()
        self.t0 = self.t_end = None
        self.done = self.failed = 0
        self.result = new_result()
        self.recoveries, self.detect_lat, self.retries = [], [], 0
        self.static_failovers = 0
        self.finished = threading.Event()

    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    # ---------- koneksi ----------
    def serve(self):
        srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server = srv
        srv.bind((self.a.host, self.a.port)); srv.listen(64)
        self.log(f"Master listen {self.a.host}:{self.a.port} | {len(self.files)} file, "
                 f"{len(self.tasks)} task | mode={self.a.balancing} | menunggu {self.a.min_workers} worker")
        threading.Thread(target=self.monitor, daemon=True).start()
        threading.Thread(target=self.accept_loop, daemon=True).start()
        if not self.started_event.wait(self.a.startup_timeout):
            self.log(f"Timeout: tidak mencapai {self.a.min_workers} worker dalam {self.a.startup_timeout}s")
            srv.close()
            raise SystemExit(2)
        self.finished.wait()
        time.sleep(2)            # beri waktu worker menerima 'shutdown', termasuk lintas jaringan
        srv.close()
        self.report()

    def accept_loop(self):
        while not self.finished.is_set():
            try:
                conn, _ = self.server.accept()
            except OSError:
                return
            threading.Thread(target=self.handle, args=(conn,), daemon=True).start()

    def handle(self, conn):
        w = None
        initial_msg = None
        try:
            initial_msg = recv_msg(conn)
            if not isinstance(initial_msg, dict) or not isinstance(initial_msg.get("type"), str):
                raise ValueError("pesan awal tidak valid")
            if initial_msg["type"] == "register":
                w = self.register(initial_msg, conn)
                while True:
                    m = recv_msg(conn)
                    if m["type"] == "get_task":
                        send_msg(conn, self.next_task(w))
                    elif m["type"] == "result":
                        accepted = self.on_result(w, m)
                        send_msg(conn, {"type": "ack" if accepted else "stale_result"})
            elif initial_msg["type"] == "hb_hello":
                self.heartbeat_loop(conn, initial_msg["worker_id"])
        except Exception as exc:
            if w is not None and not w["finished"]:
                self.mark_dead(w, "koneksi putus")
            elif (w is None and isinstance(initial_msg, dict)
                  and initial_msg.get("type") == "register"):
                self.log(f"Registrasi worker gagal: {type(exc).__name__}: {exc}")
        finally:
            conn.close()

    def register(self, msg, conn):
        if not isinstance(msg.get("host"), str) or not isinstance(msg.get("cores"), int) or msg["cores"] < 1:
            raise ValueError("metadata worker tidak valid")
        with self.lock:
            wid = f"w{len(self.workers) + 1}"
            w = {"id": wid, "idx": len(self.workers), "host": msg["host"], "cores": msg["cores"],
                 "last_seen": time.time(), "alive": True, "finished": False, "inflight": {},
                 "tasks": 0, "docs": 0, "busy": 0.0, "cpu": [], "mem": []}
            self.workers[wid] = w
            if self.started and self.a.balancing == "static":
                self.queues.setdefault(w["idx"], deque())
                while self.pending:
                    self.queues[w["idx"]].append(self.pending.popleft())
            self.log(f"Worker {wid} terdaftar: {msg['host']} ({msg['cores']} core)")
            if not self.started and len(self.workers) >= self.a.min_workers:
                self.start()
        send_msg(conn, {"type": "registered", "worker_id": wid})
        return w

    def start(self):
        self.started, self.t0 = True, time.perf_counter()
        if self.a.balancing == "static":      # pembagian awal round-robin, tanpa stealing
            self.queues = {i: deque() for i in range(self.a.min_workers)}
            for n, tid in enumerate(list(self.pending)):
                self.queues[n % self.a.min_workers].append(tid)
            self.pending.clear()
        self.log("Semua worker siap -> pemrosesan DIMULAI")
        self.started_event.set()

    def heartbeat_loop(self, conn, wid):
        while True:
            m = recv_msg(conn)
            if not isinstance(m, dict) or m.get("type") != "hb":
                raise ValueError("heartbeat tidak valid")
            with self.lock:
                w = self.workers.get(wid)
                if w and w["alive"]:
                    w["last_seen"] = time.time()
                    if isinstance(m.get("cpu"), (int, float)):
                        w["cpu"].append(m["cpu"])
                    if isinstance(m.get("mem"), (int, float)):
                        w["mem"].append(m["mem"])

    # ---------- penjadwalan (dynamic load balancing: worker menarik task) ----------
    def next_task(self, w):
        with self.lock:
            if not self.started or not w["alive"]:
                return {"type": "wait"}
            tid = None
            if self.a.balancing == "static":
                q = self.queues.get(w["idx"])
                if q: tid = q.popleft()
            elif self.pending:
                tid = self.pending.popleft()
            if tid is None:
                if self.done + self.failed >= len(self.tasks):
                    w["finished"] = True
                    return {"type": "shutdown"}
                return {"type": "wait"}
            t = self.tasks[tid]; t["state"] = "running"; t["attempts"] += 1
            t["lease_id"] = uuid.uuid4().hex; t["owner"] = w["id"]
            lease_id = t["lease_id"]
            w["inflight"][tid] = {"time": time.time(), "lease_id": lease_id}
            files = t["files"]
        docs = []
        for f in files:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                docs.append((os.path.basename(f), fh.read()))
        with self.lock:
            current = self.tasks[tid]
            if current["state"] != "running" or current["owner"] != w["id"] or current["lease_id"] != lease_id:
                return {"type": "wait"}
        return {"type": "task", "task_id": tid, "lease_id": lease_id,
                "docs": docs, "bigrams": self.a.bigrams}

    def on_result(self, w, m):
        with self.lock:
            tid = m.get("task_id")
            if tid not in self.tasks:
                return False
            t = self.tasks[tid]
            if (t["state"] != "running" or t["owner"] != w["id"]
                    or t["lease_id"] != m.get("lease_id")):
                self.log(f"Hasil task {tid} ditolak: lease usang dari {w['id']}")
                return False
            result = m.get("result")
            numeric = ("docs", "chars", "tokens", "sentences", "ttr_sum")
            if (not isinstance(result, dict) or not all(k in result for k in numeric)
                    or not isinstance(result.get("uni"), dict) or not isinstance(result.get("bi"), dict)
                    or any(type(result[k]) is not int or result[k] < 0 for k in numeric[:4])
                    or not isinstance(result.get("ttr_sum"), (int, float))
                    or not math.isfinite(result["ttr_sum"])
                    or not isinstance(m.get("elapsed"), (int, float)) or not math.isfinite(m["elapsed"])
                    or m["elapsed"] < 0
                    or result.get("docs") != len(t["files"])
                    or any(type(v) is not int or v < 0 for v in result["uni"].values())
                    or any(type(v) is not int or v < 0 for v in result["bi"].values())):
                raise ValueError("hasil task tidak valid")
            w["inflight"].pop(tid, None)
            t["state"] = "done"; self.done += 1
            t["owner"] = None; t["lease_id"] = None
            w["tasks"] += 1; w["docs"] += m["result"]["docs"]; w["busy"] += m["elapsed"]
            merge_into(self.result, from_wire(m["result"]))
            if t["fail_time"]:                   # task ini pernah di-requeue
                rec = time.time() - t["fail_time"]
                self.recoveries.append(rec)
                self.log(f"Task {tid} pulih oleh {w['id']} | recovery time {rec:.2f}s")
            self.log(f"Task {tid} selesai oleh {w['id']} ({self.done}/{len(self.tasks)})")
            self.check_finish()
            return True

    # ---------- fault tolerance ----------
    def monitor(self):
        while True:
            time.sleep(1)
            now = time.time()
            with self.lock:
                for w in list(self.workers.values()):
                    if w["alive"] and not w["finished"] and now - w["last_seen"] > self.a.timeout:
                        self.mark_dead(w, f"heartbeat timeout >{self.a.timeout}s")

    def mark_dead(self, w, reason):
        with self.lock:
            if not w["alive"]:
                return
            w["alive"] = False
            now = time.time()
            self.detect_lat.append(now - w["last_seen"])
            self.log(f"!! Worker {w['id']} GAGAL ({reason}); requeue {len(w['inflight'])} task")
            lost = list(w["inflight"]) + list(self.queues.get(w["idx"], []))
            if w["idx"] in self.queues: self.queues[w["idx"]].clear()
            w["inflight"].clear()
            for tid in lost:
                t = self.tasks[tid]
                if t["state"] == "done": continue
                was_running = t["state"] == "running"
                t["owner"] = None; t["lease_id"] = None
                if t["attempts"] >= self.a.max_attempts:
                    t["state"] = "failed"; self.failed += 1
                else:
                    t["state"] = "pending"
                    if was_running:
                        t["fail_time"] = now
                        self.retries += 1
                    if self.a.balancing == "static":
                        candidates = [x for x in self.workers.values()
                                      if x["alive"] and x["id"] != w["id"] and not x["finished"]]
                        if candidates:
                            target = min(candidates, key=lambda x: (len(self.queues.setdefault(x["idx"], deque())), x["tasks"]))
                            self.queues[target["idx"]].append(tid)
                            if was_running: self.static_failovers += 1
                        else:
                            self.pending.appendleft(tid)
                    else:
                        self.pending.appendleft(tid)
            self.check_finish()

    def check_finish(self):
        if self.started and self.done + self.failed >= len(self.tasks) and not self.finished.is_set():
            self.t_end = time.perf_counter(); self.finished.set()

    # ---------- laporan ----------
    def report(self):
        T = max(self.t_end - self.t0, 1e-9)
        ws = list(self.workers.values())
        used_ws = [w for w in ws if w["tasks"] > 0]
        busy = [w["busy"] for w in used_ws] or [0]
        avg = lambda xs: sum(xs) / len(xs) if xs else 0.0
        cpu_samples = [v for w in used_ws for v in w["cpu"] if isinstance(v, (int, float))]
        mem_samples = [v for w in used_ws for v in w["mem"] if isinstance(v, (int, float))]
        cpu = avg(cpu_samples) if cpu_samples else None
        mem = avg(mem_samples) if mem_samples else None
        mb = self.total_bytes / 1e6
        row = {"label": self.a.label, "dataset_id": self.dataset_id, "bigrams": int(self.a.bigrams),
               "mode": f"dist_{self.a.balancing}", "units": len(used_ws),
               "total_cores": sum(w["cores"] for w in used_ws), "docs": self.result["docs"], "mb": round(mb, 3),
               "exec_time_s": round(T, 6), "throughput_docs_s": round(self.result["docs"] / T, 2),
               "throughput_mb_s": round(mb / T, 3), "retries": self.retries,
               "avg_recovery_s": round(avg(self.recoveries), 3),
               "avg_cpu_pct": round(cpu, 1) if cpu is not None else None,
               "avg_mem_pct": round(mem, 1) if mem is not None else None,
               "imbalance": round(max(busy) / avg(busy), 3) if avg(busy) else 0,
               "failed_tasks": self.failed, "static_failovers": self.static_failovers}
        append_summary(row, os.path.join(self.a.out, "summary.csv"))
        r = self.result
        detail = {**row, "failed_tasks": self.failed, "detect_latency_s": self.detect_lat,
                  "per_worker": {w["id"]: {"host": w["host"], "cores": w["cores"], "tasks": w["tasks"],
                                           "docs": w["docs"], "busy_s": round(w["busy"], 2),
                                           "alive": w["alive"]} for w in ws},
                  "chars": r["chars"], "tokens": r["tokens"], "sentences": r["sentences"],
                  "avg_ttr": r["ttr_sum"] / max(r["docs"], 1),
                  "uni_digest": counter_digest(r["uni"]), "bi_digest": counter_digest(r["bi"]),
                  "top20_words": r["uni"].most_common(20), "top10_bigrams": r["bi"].most_common(10)}
        with open(os.path.join(self.a.out, f"{self.a.label}.json"), "w") as f:
            json.dump(detail, f, indent=2)
        self.log("=== RINGKASAN ===\n" + json.dumps(row, indent=2))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/corpus")
    p.add_argument("--host", default="0.0.0.0"); p.add_argument("--port", type=int, default=5000)
    p.add_argument("--chunk", type=int, default=10, help="jumlah dokumen per task")
    p.add_argument("--min-workers", type=int, default=9)
    p.add_argument("--balancing", choices=["dynamic", "static"], default="dynamic")
    p.add_argument("--timeout", type=float, default=6, help="detik tanpa heartbeat = worker dianggap mati")
    p.add_argument("--startup-timeout", type=float, default=120, help="batas tunggu worker pertama")
    p.add_argument("--max-attempts", type=int, default=3)
    p.add_argument("--bigrams", action="store_true", help="tambah beban: hitung bigram")
    p.add_argument("--label", default="run"); p.add_argument("--out", default="results")
    a = p.parse_args()
    if a.chunk < 1 or a.min_workers < 1 or a.max_attempts < 1 or a.timeout <= 0 or a.startup_timeout <= 0:
        p.error("chunk, min-workers, max-attempts harus >= 1; timeout harus > 0")
    os.makedirs(a.out, exist_ok=True)
    Master(a).serve()
