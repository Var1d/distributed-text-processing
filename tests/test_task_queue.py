from common.models import Task
from master.task_queue import TaskQueue, PENDING, RUNNING, COMPLETED, FAILED, REQUEUED


def create_task(task_id="TASK-0001", max_attempts=3):
    return Task(
        task_id=task_id,
        document_id="DOC-001",
        content="Contoh teks untuk diproses",
        max_attempts=max_attempts,
    )


def test_add_task():
    queue = TaskQueue()

    task = create_task()

    assert queue.add_task(task) is True
    assert queue.get_task_info(task.task_id)["status"] == PENDING


def test_duplicate_task():
    queue = TaskQueue()

    task = create_task()

    assert queue.add_task(task) is True
    assert queue.add_task(task) is False


def test_get_next_task():
    queue = TaskQueue()

    task = create_task()
    queue.add_task(task)

    assigned = queue.get_next_task("WORKER-01")

    assert assigned.task_id == task.task_id

    info = queue.get_task_info(task.task_id)

    assert info["status"] == RUNNING
    assert info["worker_id"] == "WORKER-01"


def test_complete_task():
    queue = TaskQueue()

    task = create_task()
    queue.add_task(task)

    queue.get_next_task("WORKER-01")

    result = queue.complete_task(task.task_id, "WORKER-01")

    assert result is True

    info = queue.get_task_info(task.task_id)

    assert info["status"] == COMPLETED


def test_wrong_worker_cannot_complete():
    queue = TaskQueue()

    task = create_task()
    queue.add_task(task)

    queue.get_next_task("WORKER-01")

    result = queue.complete_task(task.task_id, "WORKER-02")

    assert result is False


def test_failed_task_requeued():
    queue = TaskQueue()

    task = create_task()
    queue.add_task(task)

    queue.get_next_task("WORKER-01")

    status = queue.fail_task(task.task_id, "WORKER-01", "Worker mengalami error")

    assert status == REQUEUED

    info = queue.get_task_info(task.task_id)

    assert info["status"] == REQUEUED
    assert info["attempt"] == 2


def test_retry_limit():
    queue = TaskQueue()

    task = create_task(max_attempts=2)
    queue.add_task(task)

    queue.get_next_task("WORKER-01")

    first = queue.fail_task(task.task_id, "WORKER-01", "Percobaan pertama gagal")

    assert first == REQUEUED

    queue.get_next_task("WORKER-02")

    second = queue.fail_task(task.task_id, "WORKER-02", "Percobaan kedua gagal")

    assert second == FAILED


def test_empty_queue():
    queue = TaskQueue()

    assert queue.get_next_task("WORKER-01") is None


def test_task_counts():
    queue = TaskQueue()

    task1 = create_task("TASK-0001")
    task2 = create_task("TASK-0002")

    queue.add_task(task1)
    queue.add_task(task2)

    queue.get_next_task("WORKER-01")

    queue.complete_task("TASK-0001", "WORKER-01")

    counts = queue.get_counts()

    assert counts["TOTAL"] == 2
    assert counts[COMPLETED] == 1
    assert counts[PENDING] == 1
