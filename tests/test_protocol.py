import socket

from common.models import Task, WorkerInfo, TaskResult
from common.protocol import send_message, recv_message


def test_task_serialization():
    task = Task(
        task_id="TASK-0001", document_id="DOC-001", content="Belajar komputasi paralel"
    )

    restored = Task.from_dict(task.to_dict())

    assert restored.task_id == task.task_id
    assert restored.content == task.content


def test_worker_serialization():
    worker = WorkerInfo(
        worker_id="WORKER-01", hostname="PC-01", cpu_cores=4, total_memory_mb=8192
    )

    restored = WorkerInfo.from_dict(worker.to_dict())

    assert restored.worker_id == worker.worker_id
    assert restored.cpu_cores == 4


def test_result_serialization():
    result = TaskResult(
        task_id="TASK-0001",
        worker_id="WORKER-01",
        success=True,
        result={"total_words": 10},
    )

    restored = TaskResult.from_dict(result.to_dict())

    assert restored.success is True
    assert restored.result["total_words"] == 10


def test_tcp_message():
    sender, receiver = socket.socketpair()

    try:
        message = {"type": "HEARTBEAT", "worker_id": "WORKER-01"}

        send_message(sender, message)
        received = recv_message(receiver)

        assert received == message

    finally:
        sender.close()
        receiver.close()


def test_multiple_tcp_messages():
    sender, receiver = socket.socketpair()

    try:
        messages = [
            {"type": "REGISTER", "worker_id": "WORKER-01"},
            {"type": "HEARTBEAT", "worker_id": "WORKER-01"},
            {"type": "REQUEST_TASK", "worker_id": "WORKER-01"},
        ]

        for message in messages:
            send_message(sender, message)

        for expected in messages:
            received = recv_message(receiver)
            assert received == expected

    finally:
        sender.close()
        receiver.close()
