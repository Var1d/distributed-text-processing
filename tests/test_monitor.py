from unittest.mock import patch

from worker.monitor import WorkerMonitor


def test_cpu_permission_error_does_not_prevent_worker_start(caplog):
    with patch(
        "worker.monitor.psutil.cpu_percent",
        side_effect=PermissionError("permission denied"),
    ):
        monitor = WorkerMonitor(processes=1)
        metrics = monitor.get_metrics()

    assert metrics["cpu_percent"] == 0.0
    assert "Metrik CPU tidak dapat dibaca" in caplog.text


def test_memory_permission_error_does_not_prevent_metrics():
    monitor = WorkerMonitor(processes=1)

    with patch(
        "worker.monitor.psutil.virtual_memory",
        side_effect=PermissionError("permission denied"),
    ):
        metrics = monitor.get_metrics()

    assert metrics["total_memory_mb"] == 0
