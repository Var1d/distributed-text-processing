"""Baseline: sequential (1 proses) dan local parallel (multiprocessing satu komputer).
python baseline.py --mode sequential --label seq
python baseline.py --mode local --procs 4 --label local_4
"""
import argparse, glob, json, multiprocessing as mp, os, time
from common.textproc import process_batch, new_result, merge_into, counter_digest
from common.metrics import append_summary, dataset_id, ResourceSampler

def load_batch(files):
    out = []
    for f in files:
        with open(f, encoding="utf-8", errors="ignore") as fh:
            out.append((os.path.basename(f), fh.read()))
    return out

def batches(files, chunk):
    for i in range(0, len(files), chunk):
        yield load_batch(files[i:i + chunk])

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/corpus"); p.add_argument("--mode", choices=["sequential", "local"], required=True)
    p.add_argument("--procs", type=int, default=min(os.cpu_count() or 1, 8)); p.add_argument("--chunk", type=int, default=10)
    p.add_argument("--bigrams", action="store_true"); p.add_argument("--label", default=None)
    a = p.parse_args()
    files = sorted(glob.glob(os.path.join(a.data, "*.txt")))
    if not files:
        p.error(f"Tidak ada .txt di {a.data}")
    if a.procs < 1 or a.chunk < 1:
        p.error("--procs dan --chunk harus >= 1")
    corpus_id = dataset_id(files)
    t = time.perf_counter()
    sampler = ResourceSampler()
    sampler.sample()  # prime CPU counter before timing the run
    mb = sum(os.path.getsize(f) for f in files) / 1e6
    if a.mode == "sequential":
        acc = new_result()
        for batch in batches(files, a.chunk):
            merge_into(acc, process_batch((batch, a.bigrams)))
        units = 1
    else:
        acc = new_result()
        with mp.Pool(a.procs) as pool:
            jobs = ((batch, a.bigrams) for batch in batches(files, a.chunk))
            for r in pool.imap_unordered(process_batch, jobs, chunksize=1): merge_into(acc, r)
        units = a.procs
    T = time.perf_counter() - t
    cpu_pct, mem_pct = sampler.sample()
    print(f"{a.mode} units={units}: {T:.2f}s, {acc['docs']} docs, {acc['tokens']} tokens")
    append_summary({"label": a.label or f"{a.mode}_{units}", "dataset_id": corpus_id,
                    "bigrams": int(a.bigrams), "mode": a.mode, "units": units,
                    "total_cores": units, "docs": acc["docs"], "mb": round(mb, 3), "exec_time_s": round(T, 6),
                    "throughput_docs_s": round(acc["docs"] / T, 2), "throughput_mb_s": round(mb / T, 3),
                    "avg_cpu_pct": round(cpu_pct, 1) if cpu_pct is not None else None,
                    "avg_mem_pct": round(mem_pct, 1) if mem_pct is not None else None,
                    "failed_tasks": 0})
    # keluaran rinci (dipakai verify.py untuk membandingkan dengan hasil distributed)
    os.makedirs("results", exist_ok=True)
    with open(f"results/{a.label or a.mode + '_' + str(units)}.json", "w") as f:
        json.dump({"dataset_id": corpus_id, "bigrams": a.bigrams,
                   "docs": acc["docs"], "chars": acc["chars"], "tokens": acc["tokens"],
                   "sentences": acc["sentences"], "avg_ttr": acc["ttr_sum"] / max(acc["docs"], 1),
                   "uni_digest": counter_digest(acc["uni"]), "bi_digest": counter_digest(acc["bi"]),
                   "top20_words": acc["uni"].most_common(20)}, f, indent=2)
