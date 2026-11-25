"""Ringkas ulangan dengan median per dataset, opsi bigram, mode, dan unit."""
import csv
import statistics
import sys
from collections import defaultdict


def numeric(rows, field):
    values = []
    for row in rows:
        try:
            value = float(row[field])
        except (KeyError, TypeError, ValueError):
            continue
        values.append(value)
    return statistics.median(values) if values else None


def fmt(value, digits=3):
    return f"{value:.{digits}f}" if value is not None else "—"


def main(path="results/summary.csv"):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"Tidak ada hasil di {path}")

    workloads = defaultdict(list)
    for row in rows:
        key = (row.get("dataset_id", ""), row.get("bigrams", "0"))
        workloads[key].append(row)

    print("| workload | mode | unit | n | median waktu (s) | speedup | efficiency | docs/s | CPU % | mem % | recovery (s) | retries | failed |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for (data_id, bigrams), items in sorted(workloads.items()):
        configs = defaultdict(list)
        for row in items:
            configs[(row.get("mode", ""), row.get("units", ""))].append(row)
        seq_rows = [row for row in items if row.get("mode") == "sequential"]
        baseline = numeric(seq_rows, "exec_time_s")
        for (mode, units), samples in sorted(configs.items()):
            t = numeric(samples, "exec_time_s")
            speedup = baseline / t if baseline is not None and t else None
            try:
                efficiency = speedup / int(units) if speedup is not None else None
            except (TypeError, ValueError, ZeroDivisionError):
                efficiency = None
            workload = f"{data_id or 'legacy'} / bigrams={bigrams} / {samples[0].get('docs', '?')} docs"
            retries = numeric(samples, "retries")
            failed = numeric(samples, "failed_tasks")
            print(f"| {workload} | {mode} | {units} | {len(samples)} | {fmt(t)} | {fmt(speedup, 2)} | "
                  f"{fmt(efficiency, 2)} | {fmt(numeric(samples, 'throughput_docs_s'), 2)} | "
                  f"{fmt(numeric(samples, 'avg_cpu_pct'), 1)} | {fmt(numeric(samples, 'avg_mem_pct'), 1)} | "
                  f"{fmt(numeric(samples, 'avg_recovery_s'), 3)} | "
                  f"{fmt(retries, 1)} | {fmt(failed, 1)} |")
        if baseline is None:
            print(f"\nWorkload {data_id or 'legacy'} tidak memiliki baseline sequential; speedup tidak dihitung.\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/summary.csv")
