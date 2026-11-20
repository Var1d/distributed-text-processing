"""Perbandingan scheduling dinamis dan statis pada jaringan TCP lokal."""
import json,time
from pathlib import Path
from benchmark.distributed import run_distributed
from visualization.charts import plot_execution_times

def compare(inputs, workers=2, processes_per_worker=1, port=54331, output_dir="results/raw",
            chunk_words=2000):
    static=run_distributed(inputs,workers,port=port,processes_per_worker=processes_per_worker,
                           output_dir=output_dir,scheduling="static",chunk_words=chunk_words)
    dynamic=run_distributed(inputs,workers,port=port+1,processes_per_worker=processes_per_worker,
                            output_dir=output_dir,scheduling="dynamic",chunk_words=chunk_words)
    static["experiment"]="static"; dynamic["experiment"]="dynamic"
    result={"mode":"single_host_process_simulation","static":static,"dynamic":dynamic,
            "interpretation":"Bandingkan waktu aktual; noise OS dan jaringan memengaruhi hasil."}
    target=Path(output_dir);target.mkdir(parents=True,exist_ok=True)
    stamp=time.strftime("%Y%m%d-%H%M%S")
    raw=target/f"load-balancing-{stamp}.json"
    raw.write_text(json.dumps(result,indent=2),encoding="utf-8")
    chart=Path(output_dir).parent/"charts"/f"load-balancing-{stamp}.png"
    plot_execution_times([static,dynamic],chart)
    result.update({"raw":str(raw),"chart":str(chart)})
    return result
