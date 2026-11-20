import pytest
from benchmark.metrics import calculate_metrics
from benchmark.local_parallel import run_local_parallel
from benchmark.sequential import run_sequential
from master.scheduler import Scheduler
from master.worker_manager import WorkerManager
from common.models import WorkerInfo

def test_metrics_formulas():
    result=calculate_metrics(2,10,sequential_seconds=8,parallelism=4)
    assert result["speedup"] == 4
    assert result["efficiency"] == 1
    assert result["throughput_units_per_second"] == 5

def test_sequential_and_local_parallel_are_identical():
    docs=[("a.txt","Python python sistem."),("b.txt","Sistem paralel.")]
    assert [x["word_frequency"] for x in run_sequential(docs)["results"]] == [
        x["word_frequency"] for x in run_local_parallel(docs,2)["results"]]

def test_static_scheduler_round_robin():
    manager=WorkerManager()
    for name in ("A","B"):
        manager.register_worker(WorkerInfo(name,name,1,1024,available_slots=1))
    scheduler=Scheduler(manager,strategy="static")
    selected = []
    for _ in range(4):
        worker = scheduler.select_worker()
        selected.append(worker.worker_id)
        scheduler.record_assignment(worker.worker_id)
    assert selected == ["A","B","A","B"]

def test_invalid_metrics():
    with pytest.raises(ValueError):
        calculate_metrics(0,1)
