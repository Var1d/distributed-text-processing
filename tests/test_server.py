import pytest

from common.models import Task, WorkerInfo, TaskResult

from master.server import MasterServer
from master.worker_manager import WorkerManager
from master.task_queue import TaskQueue
from master.aggregator import Aggregator


def create_server():
    worker_manager = WorkerManager()
    task_queue = TaskQueue()
    aggregator = Aggregator()

    server = MasterServer(
        worker_manager=worker_manager, task_queue=task_queue, aggregator=aggregator
    )

    return server, worker_manager, task_queue, aggregator


def create_worker_message(worker_id="WORKER-01"):
    return {
        "type": "REGISTER",
        "worker_id": worker_id,
        "hostname": "TEST-PC",
        "cpu_cores": 4,
        "total_memory_mb": 8192,
        "cpu_percent": 10.0,
        "available_slots": 4,
        "active_tasks": 0,
    }


def create_task():
    return Task(
        task_id="TASK-01",
        document_id="DOC-001",
        content="Python adalah bahasa pemrograman.",
    )


def test_invalid_port():
    manager = WorkerManager()
    queue = TaskQueue()
    aggregator = Aggregator()

    with pytest.raises(ValueError):
        MasterServer(manager, queue, aggregator, port=70000)


def test_unknown_message_type():
    server, _, _, _ = create_server()

    response = server.process_message({"type": "UNKNOWN"})

    assert response["type"] == "ERROR"


def test_register_worker():
    server, manager, _, _ = create_server()

    response = server.process_message(create_worker_message())

    assert response["type"] == "REGISTERED"
    assert manager.get_worker("WORKER-01") is not None


def test_register_duplicate_worker():
    server, _, _, _ = create_server()

    server.process_message(create_worker_message())

    response = server.process_message(create_worker_message())

    assert response["type"] == "ERROR"


def test_worker_heartbeat():
    server, manager, _, _ = create_server()

    server.process_message(create_worker_message())

    response = server.process_message(
        {
            "type": "HEARTBEAT",
            "worker_id": "WORKER-01",
            "cpu_percent": 30.0,
            "available_slots": 3,
            "active_tasks": 1,
        }
    )

    assert response["type"] == "HEARTBEAT_ACK"

    worker = manager.get_worker("WORKER-01")

    assert worker.cpu_percent == 30.0
    assert worker.available_slots == 3
    assert worker.active_tasks == 1


def test_request_task():
    server, _, queue, _ = create_server()

    server.process_message(create_worker_message())
    queue.add_task(create_task())

    response = server.process_message(
        {"type": "REQUEST_TASK", "worker_id": "WORKER-01"}
    )

    assert response["type"] == "TASK"
    assert response["task"]["task_id"] == "TASK-01"


def test_request_task_when_queue_empty():
    server, _, _, _ = create_server()

    server.process_message(create_worker_message())

    response = server.process_message(
        {"type": "REQUEST_TASK", "worker_id": "WORKER-01"}
    )

    assert response["type"] == "NO_TASK"


def test_submit_successful_result():
    server, _, queue, aggregator = create_server()

    server.process_message(create_worker_message())
    queue.add_task(create_task())

    server.process_message({"type": "REQUEST_TASK", "worker_id": "WORKER-01"})

    result = TaskResult(
        task_id="TASK-01",
        worker_id="WORKER-01",
        success=True,
        result={"document_id": "DOC-001", "word_frequency": {"python": 1, "bahasa": 1}},
        error=None,
        processing_time=0.5,
    )

    response = server.process_message(
        {"type": "SUBMIT_RESULT", "result": result.to_dict()}
    )

    assert response["type"] == "RESULT_ACCEPTED"
    assert aggregator.get_result_count() == 1


def test_disconnect_recovers_running_task():
    server, manager, queue, _ = create_server()

    server.process_message(create_worker_message())
    queue.add_task(create_task())

    server.process_message({"type": "REQUEST_TASK", "worker_id": "WORKER-01"})

    response = server.process_message({"type": "DISCONNECT", "worker_id": "WORKER-01"})

    assert response["type"] == "DISCONNECT_ACK"
    assert response["recovered_tasks"] == ["TASK-01"]
    assert manager.get_worker("WORKER-01").status == "OFFLINE"
    assert queue.get_task_info("TASK-01")["status"] == "REQUEUED"



def test_min_workers_barrier_holds_tasks_until_target_registered():
    manager = WorkerManager()
    queue = TaskQueue()
    server = MasterServer(manager, queue, Aggregator(), min_workers=2)
    server.process_message(create_worker_message("WORKER-01"))
    queue.add_task(create_task())

    waiting = server.process_message({"type": "REQUEST_TASK", "worker_id": "WORKER-01"})
    assert waiting["type"] == "NO_TASK"
    assert queue.get_task_info("TASK-01")["status"] == "PENDING"

    second = create_worker_message("WORKER-02")
    server.process_message(second)
    assigned = server.process_message({"type": "REQUEST_TASK", "worker_id": "WORKER-01"})
    assert assigned["type"] == "TASK"


def test_master_sends_shutdown_after_batch():
    server, _, _, _ = create_server()
    server.process_message(create_worker_message())
    server.request_shutdown()

    response = server.process_message({"type": "REQUEST_TASK", "worker_id": "WORKER-01"})
    assert response["type"] == "SHUTDOWN"


def test_assignment_updates_worker_load_immediately():
    server, manager, queue, _ = create_server()
    server.process_message(create_worker_message())
    queue.add_task(create_task())
    server.process_message({"type": "REQUEST_TASK", "worker_id": "WORKER-01"})

    assigned = manager.get_worker("WORKER-01")
    assert assigned.active_tasks == 1
    assert assigned.available_slots == 0

    result = TaskResult(task_id="TASK-01", worker_id="WORKER-01", success=True,
                        result={"document_id": "DOC-001", "word_frequency": {"python": 1}},
                        attempt=1)
    response = server.process_message({"type": "SUBMIT_RESULT", "result": result.to_dict()})
    assert response["type"] == "RESULT_ACCEPTED"
    completed = manager.get_worker("WORKER-01")
    assert completed.active_tasks == 0
    assert completed.available_slots == 1
