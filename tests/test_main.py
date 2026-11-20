import pytest

from master.main import MasterApplication


def test_master_application_initialization():
    app = MasterApplication()

    assert app.worker_manager is not None
    assert app.task_queue is not None
    assert app.aggregator is not None
    assert app.scheduler is not None
    assert app.fault_tolerance is not None
    assert app.server is not None


def test_custom_server_configuration():
    app = MasterApplication(host="127.0.0.1", port=6000)

    assert app.server.host == "127.0.0.1"
    assert app.server.port == 6000


def test_invalid_heartbeat_timeout():
    with pytest.raises(ValueError):
        MasterApplication(heartbeat_timeout=0)


def test_invalid_heartbeat_check_interval():
    with pytest.raises(ValueError):
        MasterApplication(heartbeat_check_interval=0)


def test_master_initial_state():
    app = MasterApplication()

    assert app.stop_event.is_set() is False
    assert app.monitor_thread is None


def test_scheduler_uses_master_worker_manager():
    app = MasterApplication()

    assert app.scheduler.worker_manager is app.worker_manager


def test_fault_tolerance_uses_master_components():
    app = MasterApplication()

    assert app.fault_tolerance.worker_manager is app.worker_manager

    assert app.fault_tolerance.task_queue is app.task_queue
