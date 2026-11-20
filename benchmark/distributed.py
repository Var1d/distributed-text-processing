"""Runner distributed TCP lokal; proses worker lokal bukan komputer fisik terpisah."""
import json, os, subprocess, sys, time
from pathlib import Path
from benchmark.metrics import calculate_metrics
from benchmark.resource_monitor import ResourceMonitor
from benchmark.sequential import run_sequential

def _documents(inputs):
    paths=[]
    for raw in inputs:
        p=Path(raw)
        paths.extend(sorted(p.glob("*.txt")) if p.is_dir() else [p])
    return [(p.name,p.read_text(encoding="utf-8")) for p in paths]

def run_distributed(inputs, workers=1, master_host="127.0.0.1", port=54321,
                    processes_per_worker=1, output_dir="results/raw", scheduling="dynamic",
                    startup_timeout=20, chunk_words=2000, verbose=False):
    if workers<1 or processes_per_worker<1: raise ValueError("Jumlah worker dan proses harus positif.")
    docs=_documents(inputs)
    if not docs: raise ValueError("Input tidak berisi file teks.")
    baseline=run_sequential(docs)
    output=Path(output_dir); output.mkdir(parents=True,exist_ok=True)
    root=Path.cwd()
    run_summary=output/f"summary-{os.getpid()}-{port}.json"
    master_cmd=[sys.executable,"-m","master.main","--host","0.0.0.0","--port",str(port),
                "--input",*map(str,inputs),"--auto-stop","--scheduling",scheduling,
                "--min-workers",str(workers),"--chunk-words",str(chunk_words),
                "--heartbeat-interval","0.2","--idle-shutdown-seconds","0.4",
                "--result-file",str(run_summary)]
    child_output=None if verbose else subprocess.DEVNULL
    master=subprocess.Popen(master_cmd,cwd=root,stdout=child_output,stderr=child_output)
    children=[]
    try:
        deadline=time.monotonic()+startup_timeout
        while time.monotonic()<deadline:
            if master.poll() is not None: raise RuntimeError("Master berhenti sebelum worker dimulai.")
            try:
                import socket
                with socket.create_connection((master_host,port),timeout=.2): break
            except OSError: time.sleep(.1)
        else: raise TimeoutError("Master tidak siap menerima koneksi.")
        for i in range(workers):
            children.append(subprocess.Popen([sys.executable,"-m","worker.main","--master-host",master_host,
                "--port",str(port),"--worker-id",f"benchmark-{os.getpid()}-{i}",
                "--processes",str(processes_per_worker)],cwd=root,stdout=child_output,stderr=child_output))
        with ResourceMonitor() as monitor:
            started=time.perf_counter()
            try: master.wait(timeout=3600)
            except subprocess.TimeoutExpired as exc: raise TimeoutError("Benchmark melebihi satu jam.") from exc
            elapsed=time.perf_counter()-started
        if master.returncode: raise RuntimeError(f"Master gagal dengan kode {master.returncode}")
        summary=json.loads(run_summary.read_text(encoding="utf-8-sig"))
        p=workers*processes_per_worker
        record={"experiment":"distributed_simulation","workers":workers,"processes_per_worker":processes_per_worker,
                "parallelism_assumption":p,"scheduling":scheduling,"documents":len(docs),
                "bytes":sum(len(t.encode("utf-8")) for _,t in docs),"total_words":summary["total_words"],
                "total_tasks":summary["total_tasks"],
                "tasks_by_worker":summary.get("tasks_by_worker",{}),
                "workers_used":len(summary.get("tasks_by_worker",{})),
                "mode":"single_host_process_simulation",
                **calculate_metrics(elapsed,len(docs),baseline["execution_time_seconds"],p,
                                   monitor.cpu_percent,monitor.peak_rss_mb)}
        stamp=time.strftime("%Y%m%d-%H%M%S")
        raw=output/f"distributed-{workers}w-{scheduling}-{stamp}.json"
        raw.write_text(json.dumps(record,indent=2),encoding="utf-8")
        record["raw_result"]=str(raw)
        print(json.dumps(record,indent=2))
        return record
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: child.kill()
        if master.poll() is None:
            master.terminate()
            try: master.wait(timeout=5)
            except subprocess.TimeoutExpired: master.kill()
