import pytest

from common.models import WorkerInfo

from master.worker_manager import WorkerManager, IDLE, BUSY, OFFLINE


def create_worker(worker_id="WORKER-01", cpu_cores=4, available_slots=2):
    return WorkerInfo(
        worker_id=worker_id,
        hostname="PC-TEST",
        cpu_cores=cpu_cores,
        total_memory_mb=8192,
        cpu_percent=20.0,
        available_slots=available_slots,
        active_tasks=0,
    )


def test_register_worker():
    manager = WorkerManager()

    worker = create_worker()

    result = manager.register_worker(worker)

    assert result is True
    assert manager.get_worker_count() == 1


def test_duplicate_registration():
    manager = WorkerManager()

    worker = create_worker()

    assert manager.register_worker(worker) is True
    assert manager.register_worker(worker) is False


def test_worker_initial_status():
    manager = WorkerManager()

    worker = create_worker(available_slots=2)

    manager.register_worker(worker)

    registered = manager.get_worker("WORKER-01")

    assert registered.status == IDLE


def test_busy_worker_status():
    manager = WorkerManager()

    worker = create_worker(available_slots=0)

    manager.register_worker(worker)

    registered = manager.get_worker("WORKER-01")

    assert registered.status == BUSY


def test_update_heartbeat():
    manager = WorkerManager()

    manager.register_worker(create_worker())

    result = manager.update_heartbeat(
        worker_id="WORKER-01", cpu_percent=75.0, available_slots=1, active_tasks=3
    )

    assert result is True

    worker = manager.get_worker("WORKER-01")

    assert worker.cpu_percent == 75.0
    assert worker.available_slots == 1
    assert worker.active_tasks == 3
    assert worker.status == IDLE


def test_update_unknown_worker():
    manager = WorkerManager()

    result = manager.update_heartbeat(
        worker_id="UNKNOWN", cpu_percent=20, available_slots=1, active_tasks=0
    )

    assert result is False


def test_invalid_cpu_usage():
    manager = WorkerManager()

    manager.register_worker(create_worker())

    with pytest.raises(ValueError):
        manager.update_heartbeat(
            worker_id="WORKER-01", cpu_percent=120, available_slots=1, active_tasks=0
        )


def test_available_workers():
    manager = WorkerManager()

    manager.register_worker(create_worker("WORKER-01", available_slots=2))

    manager.register_worker(create_worker("WORKER-02", available_slots=0))

    manager.register_worker(create_worker("WORKER-03", available_slots=1))

    available = manager.get_available_workers()

    ids = [worker.worker_id for worker in available]

    assert "WORKER-01" in ids
    assert "WORKER-03" in ids
    assert "WORKER-02" not in ids


def test_mark_worker_offline():
    manager = WorkerManager()

    manager.register_worker(create_worker())

    result = manager.mark_offline("WORKER-01")

    assert result is True

    worker = manager.get_worker("WORKER-01")

    assert worker.status == OFFLINE
    assert worker.available_slots == 0


def test_offline_worker_not_available():
    manager = WorkerManager()

    manager.register_worker(create_worker())

    manager.mark_offline("WORKER-01")

    assert manager.get_available_workers() == []


def test_worker_counts():
    manager = WorkerManager()

    manager.register_worker(create_worker("WORKER-01", available_slots=2))

    manager.register_worker(create_worker("WORKER-02", available_slots=0))

    manager.register_worker(create_worker("WORKER-03", available_slots=1))

    manager.mark_offline("WORKER-03")

    counts = manager.get_worker_counts()

    assert counts["TOTAL"] == 3
    assert counts[IDLE] == 1
    assert counts[BUSY] == 1
    assert counts[OFFLINE] == 1


def test_worker_data_is_protected():
    manager = WorkerManager()

    manager.register_worker(create_worker())

    external_worker = manager.get_worker("WORKER-01")

    external_worker.cpu_percent = 99.0

    internal_worker = manager.get_worker("WORKER-01")

    assert internal_worker.cpu_percent == 20.0


def test_remove_worker():
    manager = WorkerManager()

    manager.register_worker(create_worker())

    result = manager.remove_worker("WORKER-01")

    assert result is True
    assert manager.get_worker_count() == 0
    assert manager.get_worker("WORKER-01") is None
