import os
import logging
import psutil
from threading import Lock

logger = logging.getLogger("DTPS.Worker")


class WorkerMonitor:

    def __init__(self, processes: int):
        if processes < 1:
            raise ValueError("Processes minimal 1.")

        self.processes = processes
        self.active_tasks = 0
        self.lock = Lock()
        self._cpu_metric_available = True
        self._memory_metric_available = True

        self._get_cpu_percent()

    def _get_cpu_percent(self) -> float:
        if not self._cpu_metric_available:
            return 0.0

        try:
            return psutil.cpu_percent(interval=None)
        except (PermissionError, psutil.AccessDenied) as error:
            self._cpu_metric_available = False
            logger.warning(
                "Metrik CPU tidak dapat dibaca; menggunakan 0.0%%: %s", error
            )
            return 0.0

    def _get_total_memory_mb(self) -> int:
        if not self._memory_metric_available:
            return 0

        try:
            memory = psutil.virtual_memory()
        except (PermissionError, psutil.AccessDenied) as error:
            self._memory_metric_available = False
            logger.warning(
                "Metrik memori tidak dapat dibaca; menggunakan 0 MB: %s", error
            )
            return 0

        return int(memory.total / (1024 * 1024))

    def set_active_tasks(self, count: int):
        with self.lock:
            self.active_tasks = max(0, count)

    def get_metrics(self) -> dict:
        with self.lock:
            active_tasks = self.active_tasks

        return {
            "cpu_percent": self._get_cpu_percent(),
            "total_memory_mb": self._get_total_memory_mb(),
            "available_slots": max(0, 1 - active_tasks),
            "active_tasks": active_tasks,
            "cpu_cores": self.processes,
            "hostname": os.environ.get(
                "COMPUTERNAME", os.environ.get("HOSTNAME", "UNKNOWN")
            ),
        }
