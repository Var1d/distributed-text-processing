"""State simulation of task requeue; this is not a physical network failure measurement."""
import json,time
from pathlib import Path
from common.models import Task
from master.task_queue import TaskQueue

def simulate_recovery(output="results/raw/fault-recovery.json"):
    queue=TaskQueue(); task=Task("fault-demo","demo.txt","uji pemulihan",max_attempts=3)
    queue.add_task(task); queue.get_next_task("worker-simulasi"); started=time.perf_counter()
    outcome=queue.fail_task(task.task_id,"worker-simulasi","simulasi worker terputus",retry=True,attempt=task.attempt)
    result={"mode":"state_simulation","outcome":outcome,
            "recovery_time_seconds":time.perf_counter()-started,
            "task":queue.get_task_info(task.task_id)}
    path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2),encoding="utf-8")
    result["raw_result"]=str(path)
    return result
