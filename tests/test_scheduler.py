import pytest

from common.models import WorkerInfo

from master.worker_manager import WorkerManager
from master.scheduler import Scheduler


def create_worker(worker_id, cpu_cores, cpu_percent, active_tasks, available_slots):
    return WorkerInfo(
        worker_id=worker_id,
        hostname=f"PC-{worker_id}",
        cpu_cores=cpu_cores,
        total_memory_mb=8192,
        cpu_percent=cpu_percent,
        active_tasks=active_tasks,
        available_slots=available_slots,
    )


def create_scheduler():
    manager = WorkerManager()
    scheduler = Scheduler(manager)

    return manager, scheduler


def test_calculate_load_score():
    manager, scheduler = create_scheduler()

    worker = create_worker(
        "WORKER-01", cpu_cores=8, cpu_percent=40, active_tasks=2, available_slots=6
    )

    score = scheduler.calculate_load_score(worker)

    assert score == pytest.approx(32.5)


def test_select_lowest_load_worker():
    manager, scheduler = create_scheduler()

    manager.register_worker(create_worker("WORKER-01", 8, 80, 5, 3))

    manager.register_worker(create_worker("WORKER-02", 4, 20, 1, 3))

    manager.register_worker(create_worker("WORKER-03", 2, 60, 0, 2))
    
    selected = scheduler.select_worker()

    assert selected.worker_id == "WORKER-02"


def test_offline_worker_not_selected():
    manager, scheduler = create_scheduler()

    manager.register_worker(create_worker("WORKER-01", 4, 10, 0, 2))

    manager.register_worker(create_worker("WORKER-02", 4, 40, 1, 2))

    manager.mark_offline("WORKER-01")

    selected = scheduler.select_worker()

    assert selected.worker_id == "WORKER-02"


def test_worker_without_slots_not_selected():
    manager, scheduler = create_scheduler()

    manager.register_worker(create_worker("WORKER-01", 4, 10, 4, 0))

    manager.register_worker(create_worker("WORKER-02", 4, 40, 1, 2))

    selected = scheduler.select_worker()

    assert selected.worker_id == "WORKER-02"


def test_no_available_worker():
    manager, scheduler = create_scheduler()

    selected = scheduler.select_worker()

    assert selected is None


def test_get_worker_scores_sorted():
    manager, scheduler = create_scheduler()

    manager.register_worker(create_worker("WORKER-01", 8, 80, 5, 3))

    manager.register_worker(create_worker("WORKER-02", 4, 20, 1, 3))

    manager.register_worker(create_worker("WORKER-03", 2, 40, 0, 2))

    scores = scheduler.get_worker_scores()

    values = [item["load_score"] for item in scores]

    assert values == sorted(values)


def test_equal_score_prefers_more_available_slots():
    manager, scheduler = create_scheduler()

    manager.register_worker(create_worker("WORKER-01", 4, 50, 0, 2))

    manager.register_worker(create_worker("WORKER-02", 4, 50, 0, 3))

    selected = scheduler.select_worker()

    assert selected.worker_id == "WORKER-02"


def test_invalid_weights():
    manager = WorkerManager()

    with pytest.raises(ValueError):
        Scheduler(manager, cpu_weight=0.5, task_weight=0.3, slot_weight=0.5)


def test_negative_weights():
    manager = WorkerManager()

    with pytest.raises(ValueError):
        Scheduler(manager, cpu_weight=-0.1, task_weight=0.6, slot_weight=0.5)


def test_custom_weights():
    manager = WorkerManager()

    scheduler = Scheduler(manager, cpu_weight=0.6, task_weight=0.2, slot_weight=0.2)

    assert scheduler.cpu_weight == 0.6
    assert scheduler.task_weight == 0.2
    assert scheduler.slot_weight == 0.2



def test_dynamic_scheduler_turns_toward_less_served_worker():
    manager = WorkerManager()
    scheduler = Scheduler(manager, strategy="dynamic")
    manager.register_worker(create_worker("WORKER-01", 4, 10, 0, 1))
    manager.register_worker(create_worker("WORKER-02", 4, 10, 0, 1))
    scheduler.record_assignment("WORKER-01")
    scheduler.record_assignment("WORKER-01")
    assert scheduler.select_worker().worker_id == "WORKER-02"
