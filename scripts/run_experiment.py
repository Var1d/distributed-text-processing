import argparse
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psutil
from benchmark.sequential import run_sequential
from benchmark.local_parallel import run_local_parallel
from benchmark.metrics import calculate_metrics
from visualization.charts import plot_execution_times
from benchmark.resource_monitor import ResourceMonitor


def load_documents(paths):
    return [(p.name, p.read_text(encoding="utf-8")) for raw in paths
            for p in sorted(Path(raw).glob("*.txt"))] if paths else []


def run(paths, processes, output_dir):
    docs = load_documents(paths)
    if not docs:
        raise ValueError("Tidak ada file .txt pada input.")
    with ResourceMonitor() as seq_monitor:
        seq = run_sequential(docs)
    with ResourceMonitor() as parallel_monitor:
        par = run_local_parallel(docs, processes)
    if [r["word_frequency"] for r in seq["results"]] != [r["word_frequency"] for r in par["results"]]:
        raise RuntimeError("Hasil sequential dan parallel berbeda.")
    metrics = []
    for name, item, p, monitor in (("sequential", seq, 1, seq_monitor),
                                    ("local_parallel", par, processes, parallel_monitor)):
        metrics.append({"experiment": name, "documents": len(docs), "bytes": item["bytes"],
                        **calculate_metrics(item["execution_time_seconds"], len(docs),
                          seq["execution_time_seconds"], p, monitor.cpu_percent, monitor.peak_rss_mb)})
    out = Path(output_dir)
    raw_dir, metric_dir, chart_dir = out / "raw", out / "metrics", out / "charts"
    for directory in (raw_dir, metric_dir, chart_dir):
        directory.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    payload = {"environment": {"mode": "single-host", "physical_workers": 0,
                               "cpu_sample_note": "null berarti durasi terlalu singkat untuk mendapat sampel"},
               "records": metrics}
    raw = raw_dir / f"experiment-{stamp}.json"
    metric_file = metric_dir / f"experiment-{stamp}.json"
    raw.write_text(json.dumps({**payload,
                               "documents": [name for name, _ in docs],
                               "document_count": len(docs),
                               "input_bytes": sum(len(text.encode("utf-8")) for _, text in docs)}, indent=2),
                   encoding="utf-8")
    metric_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    chart = plot_execution_times(metrics, chart_dir / f"experiment-{stamp}.png")
    print(json.dumps({"raw": str(raw), "metrics": str(metric_file), "chart": chart,
                      "records": metrics}, indent=2))
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark sequential dan multiprocessing lokal.")
    parser.add_argument("--input", nargs="+", default=["data/sample"])
    parser.add_argument("--processes", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--output", default="results")
    args = parser.parse_args()
    run(args.input, args.processes, args.output)
