import json, time
from pathlib import Path
from benchmark.distributed import run_distributed
from visualization.charts import plot_execution_times

def run_scalability(inputs, worker_counts=(1,2,4,6,9), processes_per_worker=1, port=54400,
                    output_dir="results/raw", chunk_words=2000):
    records=[run_distributed(inputs,count,port=port+i,processes_per_worker=processes_per_worker,
                             output_dir=output_dir,chunk_words=chunk_words)
             for i,count in enumerate(worker_counts)]
    for item in records: item["experiment"]=f'{item["workers"]} workers'
    target=Path(output_dir); target.mkdir(parents=True,exist_ok=True)
    stamp=time.strftime("%Y%m%d-%H%M%S")
    raw=target/f"scalability-{stamp}.json"
    raw.write_text(json.dumps({"mode":"single_host_process_simulation","records":records},indent=2),encoding="utf-8")
    plot=Path(output_dir).parent/"charts"/f"scalability-{stamp}.png"
    plot_execution_times(records,plot)
    return {"records":records,"raw":str(raw),"chart":str(plot)}
