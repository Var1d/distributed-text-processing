import os
import psutil
from threading import Lock


class WorkerMonitor:

    def __init__(self, processes: int):
        if processes < 1:
            raise ValueError("Processes minimal 1.")

        self.processes = processes
        self.active_tasks = 0
        self.lock = Lock()

        psutil.cpu_percent(interval=None)

    def set_active_tasks(self, count: int):
        with self.lock:
            self.active_tasks = max(0, count)

    def get_metrics(self) -> dict:
        with self.lock:
            active_tasks = self.active_tasks

        memory = psutil.virtual_memory()

        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "total_memory_mb": int(memory.total / (1024 * 1024)),
            "available_slots": max(0, 1 - active_tasks),
            "active_tasks": active_tasks,
            "cpu_cores": self.processes,
            "hostname": os.environ.get(
                "COMPUTERNAME", os.environ.get("HOSTNAME", "UNKNOWN")
            ),
        }
