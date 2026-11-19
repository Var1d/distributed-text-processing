import pytest

from common.models import Task, WorkerInfo
from master.task_queue import TaskQueue
from master.worker_manager import WorkerManager, OFFLINE
from master.fault_tolerance import FaultTolerance


def create_worker(worker_id):
    return WorkerInfo(
        worker_id=worker_id,
        hostname="TEST-PC",
        cpu_cores=4,
        total_memory_mb=8192,
        available_slots=4,
    )


def create_task(task_id, attempt=1, max_attempts=3):
    return Task(
        task_id=task_id,
        document_id="DOC-001",
        content="Contoh teks untuk diproses.",
        attempt=attempt,
        max_attempts=max_attempts,
    )


def create_system():
    manager = WorkerManager()
    task_queue = TaskQueue()

    fault_tolerance = FaultTolerance(manager, task_queue, heartbeat_timeout=15)

    return manager, task_queue, fault_tolerance


def test_invalid_heartbeat_timeout():
    manager = WorkerManager()
    task_queue = TaskQueue()

    with pytest.raises(ValueError):
        FaultTolerance(manager, task_queue, heartbeat_timeout=0)


def test_healthy_worker_not_marked_offline():
    manager, task_queue, fault = create_system()

    manager.register_worker(create_worker("WORKER-01"))

    worker = manager.get_worker("WORKER-01")

    failed = fault.check_worker_health(current_time=worker.last_heartbeat + 10)

    assert failed == []
    assert manager.get_worker("WORKER-01").status != OFFLINE


def test_unresponsive_worker_marked_offline():
    manager, task_queue, fault = create_system()

    manager.register_worker(create_worker("WORKER-01"))

    worker = manager.get_worker("WORKER-01")

    failed = fault.check_worker_health(current_time=worker.last_heartbeat + 20)

    assert len(failed) == 1
    assert failed[0]["worker_id"] == "WORKER-01"
    assert manager.get_worker("WORKER-01").status == OFFLINE


def test_running_task_requeued_after_worker_failure():
    manager, task_queue, fault = create_system()

    manager.register_worker(create_worker("WORKER-01"))

    task_queue.add_task(create_task("TASK-01"))

    task_queue.get_next_task("WORKER-01")

    recovery = fault.recover_worker_tasks("WORKER-01")

    assert recovery["requeued"] == ["TASK-01"]
    assert task_queue.get_task_info("TASK-01")["status"] == "REQUEUED"


def test_multiple_running_tasks_recovered():
    manager, task_queue, fault = create_system()

    manager.register_worker(create_worker("WORKER-01"))

    for i in range(3):
        task_queue.add_task(create_task(f"TASK-{i + 1:02d}"))

    for i in range(3):
        task_queue.get_next_task("WORKER-01")

    recovery = fault.recover_worker_tasks("WORKER-01")

    assert len(recovery["requeued"]) == 3
    assert recovery["total_tasks"] == 3


def test_task_exceeding_max_attempts_becomes_failed():
    manager, task_queue, fault = create_system()

    manager.register_worker(create_worker("WORKER-01"))

    task_queue.add_task(create_task("TASK-01", attempt=3, max_attempts=3))

    task_queue.get_next_task("WORKER-01")

    recovery = fault.recover_worker_tasks("WORKER-01")

    assert recovery["failed"] == ["TASK-01"]
    assert task_queue.get_task_info("TASK-01")["status"] == "FAILED"


def test_already_offline_worker_is_not_checked_again():
    manager, task_queue, fault = create_system()

    manager.register_worker(create_worker("WORKER-01"))
    manager.mark_offline("WORKER-01")

    worker = manager.get_worker("WORKER-01")

    failed = fault.check_worker_health(current_time=worker.last_heartbeat + 100)

    assert failed == []


def test_worker_failure_recovers_task_automatically():
    manager, task_queue, fault = create_system()

    manager.register_worker(create_worker("WORKER-01"))

    task_queue.add_task(create_task("TASK-01"))
    task_queue.get_next_task("WORKER-01")

    worker = manager.get_worker("WORKER-01")

    failed = fault.check_worker_health(current_time=worker.last_heartbeat + 20)

    assert len(failed) == 1
    assert failed[0]["recovered_tasks"] == ["TASK-01"]

    task_info = task_queue.get_task_info("TASK-01")

    assert task_info["status"] == "REQUEUED"
