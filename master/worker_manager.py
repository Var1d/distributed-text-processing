from threading import Lock
from typing import Optional
from copy import deepcopy
import time

from common.models import WorkerInfo

IDLE = "IDLE"
BUSY = "BUSY"
OFFLINE = "OFFLINE"


class WorkerManager:
    """
    Mengelola informasi dan kondisi seluruh Worker.

    Fitur:
    - Registrasi Worker.
    - Monitoring CPU dan RAM.
    - Memperbarui heartbeat.
    - Memantau kapasitas Worker.
    - Mengambil daftar Worker yang tersedia.
    - Menandai Worker offline.
    """

    def __init__(self):
        self.workers: dict[str, WorkerInfo] = {}
        self.lock = Lock()

    def register_worker(self, worker: WorkerInfo) -> bool:
        """
        Mendaftarkan Worker baru.

        Worker dengan ID yang sudah terdaftar
        tidak boleh didaftarkan kembali melalui fungsi ini.
        """

        if not worker.worker_id:
            raise ValueError("Worker ID tidak boleh kosong.")

        if worker.cpu_cores < 1:
            raise ValueError("CPU Core minimal harus 1.")

        if worker.total_memory_mb < 0:
            raise ValueError("Total memory tidak boleh negatif.")

        if worker.available_slots < 0:
            raise ValueError("Available slots tidak boleh negatif.")

        with self.lock:
            if worker.worker_id in self.workers:
                return False

            new_worker = deepcopy(worker)

            new_worker.last_heartbeat = time.time()

            if new_worker.available_slots > 0:
                new_worker.status = IDLE
            else:
                new_worker.status = BUSY

            self.workers[worker.worker_id] = new_worker

            return True

    def update_heartbeat(
        self,
        worker_id: str,
        cpu_percent: float,
        available_slots: int,
        active_tasks: int,
    ) -> bool:
        """
        Memperbarui kondisi Worker ketika heartbeat diterima.

        Informasi yang diperbarui:
        - CPU usage.
        - Available slots.
        - Active tasks.
        - Last heartbeat.
        - Worker status.
        """

        if not 0 <= cpu_percent <= 100:
            raise ValueError("CPU usage harus berada antara 0-100.")

        if available_slots < 0:
            raise ValueError("Available slots tidak boleh negatif.")

        if active_tasks < 0:
            raise ValueError("Active tasks tidak boleh negatif.")

        with self.lock:
            worker = self.workers.get(worker_id)

            if worker is None:
                return False

            worker.cpu_percent = cpu_percent
            worker.available_slots = available_slots
            worker.active_tasks = active_tasks
            worker.last_heartbeat = time.time()

            if available_slots > 0:
                worker.status = IDLE
            else:
                worker.status = BUSY

            return True

    def adjust_active_tasks(self, worker_id: str, delta: int) -> bool:
        """Memperbarui task aktif segera saat assignment/hasil terjadi."""
        if delta not in (-1, 1):
            raise ValueError("delta hanya boleh -1 atau 1.")
        with self.lock:
            worker = self.workers.get(worker_id)
            if worker is None or worker.status == OFFLINE:
                return False
            worker.active_tasks = max(0, worker.active_tasks + delta)
            worker.available_slots = max(0, 1 - worker.active_tasks)
            worker.status = IDLE if worker.available_slots else BUSY
            return True

    def mark_offline(self, worker_id: str) -> bool:
        """
        Menandai Worker sebagai offline.
        """

        with self.lock:
            worker = self.workers.get(worker_id)

            if worker is None:
                return False

            worker.status = OFFLINE
            worker.available_slots = 0

            return True

    def get_worker(self, worker_id: str) -> Optional[WorkerInfo]:
        """
        Mengambil informasi satu Worker.
        """

        with self.lock:
            worker = self.workers.get(worker_id)

            if worker is None:
                return None

            return deepcopy(worker)

    def get_available_workers(self) -> list[WorkerInfo]:
        """
        Mengambil Worker yang masih memiliki slot tersedia.
        """

        with self.lock:
            return [
                deepcopy(worker)
                for worker in self.workers.values()
                if worker.status != OFFLINE and worker.available_slots > 0
            ]

    def get_all_workers(self) -> list[WorkerInfo]:
        """
        Mengambil informasi seluruh Worker.
        """

        with self.lock:
            return [deepcopy(worker) for worker in self.workers.values()]

    def get_worker_counts(self) -> dict:
        """
        Menghitung jumlah Worker berdasarkan status.
        """

        with self.lock:
            counts = {IDLE: 0, BUSY: 0, OFFLINE: 0, "TOTAL": len(self.workers)}

            for worker in self.workers.values():
                counts[worker.status] += 1

            return counts

    def get_worker_count(self) -> int:
        """
        Mengambil jumlah seluruh Worker yang terdaftar.
        """

        with self.lock:
            return len(self.workers)

    def remove_worker(self, worker_id: str) -> bool:
        """
        Menghapus Worker dari daftar Master.

        Penghapusan hanya dilakukan ketika memang diperlukan.
        Untuk pemulihan task, Worker sebaiknya ditandai OFFLINE
        terlebih dahulu, bukan langsung dihapus.
        """

        with self.lock:
            if worker_id not in self.workers:
                return False

            del self.workers[worker_id]

            return True
