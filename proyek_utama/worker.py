"""Worker: ambil task master, proses lokal dengan multiprocessing, kirim hasil."""
import argparse
import multiprocessing as mp
import os
import socket
import threading
import time

from common.protocol import send_msg, recv_msg
from common.textproc import process_batch, new_result, merge_into, to_wire
from common.metrics import ResourceSampler


def connect_with_retry(host, port, retries, retry_delay):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            sock = socket.create_connection((host, port), timeout=5)
            # Do not let the short startup timeout interrupt a large task later.
            sock.settimeout(None)
            return sock
        except OSError as exc:
            last_error = exc
            if attempt == retries:
                break
            delay = min(retry_delay * (2 ** (attempt - 1)), 10.0)
            print(f"Koneksi ke master {host}:{port} gagal ({attempt}/{retries}): {exc}; "
                  f"coba lagi dalam {delay:g} dtk", flush=True)
            time.sleep(delay)
    raise ConnectionError(
        f"Tidak dapat terhubung ke master {host}:{port} setelah {retries} percobaan. "
        "Periksa IP, jaringan yang sama, master yang sedang berjalan, dan firewall."
    ) from last_error


def heartbeat(host, port, wid, interval, stop):
    sampler = ResourceSampler()
    sock = None
    try:
        sock = socket.create_connection((host, port), timeout=10)
        send_msg(sock, {"type": "hb_hello", "worker_id": wid})
        while not stop.is_set():
            cpu, mem = sampler.sample()
            send_msg(sock, {"type": "hb", "cpu": cpu, "mem": mem})
            if stop.wait(interval):
                break
    except OSError as exc:
        print(f"[{wid}] heartbeat berhenti: {exc}", flush=True)
    finally:
        if sock:
            sock.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--master", required=True)
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--cores", type=int, default=min(os.cpu_count() or 1, 4))
    p.add_argument("--slow", type=float, default=1.0)
    p.add_argument("--crash-after", type=int, default=0)
    p.add_argument("--hb-interval", type=float, default=1.0)
    p.add_argument("--connect-retries", type=int, default=10,
                   help="jumlah percobaan koneksi awal ke master")
    p.add_argument("--retry-delay", type=float, default=1.0,
                   help="jeda awal antarpercobaan koneksi (detik; eksponensial, maksimum 10)")
    a = p.parse_args()
    if (a.cores < 1 or a.slow < 1 or a.hb_interval <= 0 or not 1 <= a.port <= 65535
            or a.connect_retries < 1 or a.retry_delay <= 0):
        p.error("cores >= 1, slow >= 1, heartbeat/retry-delay > 0, retries >= 1, dan port 1..65535 diperlukan")

    try:
        pool = mp.Pool(a.cores)
    except (OSError, FileNotFoundError) as exc:
        raise SystemExit(
            "Worker tidak dapat memulai multiprocessing.Pool pada perangkat ini. "
            "Gunakan Linux/Windows/Android Termux; iSH pada iPhone tidak mendukung kebutuhan ini."
        ) from exc
    sock = None
    stop_hb = threading.Event()
    hb_thread = None
    try:
        sock = connect_with_retry(a.master, a.port, a.connect_retries, a.retry_delay)
        send_msg(sock, {"type": "register", "host": socket.gethostname(), "cores": a.cores})
        registration = recv_msg(sock)
        if registration.get("type") != "registered":
            raise ConnectionError("master menolak registrasi worker")
        wid = registration["worker_id"]
        print(f"[{wid}] terdaftar, {a.cores} core", flush=True)
        hb_thread = threading.Thread(target=heartbeat,
                                     args=(a.master, a.port, wid, a.hb_interval, stop_hb), daemon=True)
        hb_thread.start()
        received = 0
        while True:
            send_msg(sock, {"type": "get_task"})
            msg = recv_msg(sock)
            if msg.get("type") == "wait":
                time.sleep(0.2)
                continue
            if msg.get("type") == "shutdown":
                print(f"[{wid}] selesai", flush=True)
                break
            if msg.get("type") != "task" or not isinstance(msg.get("lease_id"), str):
                raise ValueError("respons task dari master tidak valid")

            received += 1
            if a.crash_after and received > a.crash_after:
                print(f"[{wid}] SIMULASI CRASH saat memproses task {msg['task_id']}", flush=True)
                pool.terminate()
                os._exit(1)

            started = time.perf_counter()
            docs = msg["docs"]
            slices = [part for part in (docs[i::a.cores] for i in range(a.cores)) if part]
            acc = new_result()
            for part in pool.map(process_batch, [(batch, msg["bigrams"]) for batch in slices]):
                merge_into(acc, part)
            elapsed = time.perf_counter() - started
            if a.slow > 1:
                time.sleep(elapsed * (a.slow - 1))
                elapsed *= a.slow
            send_msg(sock, {"type": "result", "task_id": msg["task_id"],
                            "lease_id": msg["lease_id"], "elapsed": elapsed,
                            "result": to_wire(acc)})
            recv_msg(sock)  # ack or stale_result; both mean the master accepted the message frame
    finally:
        stop_hb.set()
        if sock:
            sock.close()
        if hb_thread:
            hb_thread.join(timeout=2)
        pool.close()
        pool.join()


if __name__ == "__main__":
    main()
