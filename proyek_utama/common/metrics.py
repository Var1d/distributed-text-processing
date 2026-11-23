import csv
import hashlib
import os

FIELDS = ["label", "dataset_id", "bigrams", "mode", "units", "total_cores", "docs", "mb", "exec_time_s",
          "throughput_docs_s", "throughput_mb_s", "retries", "avg_recovery_s",
          "avg_cpu_pct", "avg_mem_pct", "imbalance", "failed_tasks", "static_failovers"]


def dataset_id(files):
    """Stable content fingerprint; calculate outside the timed processing interval."""
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(os.path.basename(path).encode("utf-8"))
        digest.update(b"\0")
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(block)
        digest.update(b"\0")
    return digest.hexdigest()[:16]

def append_summary(row, path="results/summary.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})
