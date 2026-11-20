
from queue import Queue, Empty
from threading import Lock
from typing import Optional

from common.models import Task


# Status task
PENDING = "PENDING"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
REQUEUED = "REQUEUED"


class TaskQueue:
    """
    Mengelola antrean pekerjaan pada Master.

    Fitur:
    - Menambahkan task.
    - Mengambil task untuk Worker.
    - Memperbarui status task.
    - Menangani kegagalan dan retry.
    - Memvalidasi Worker dan attempt.
    - Mengambil informasi status task.
    """

    def __init__(self):
        self.queue = Queue()
        self.tasks = {}
        self.lock = Lock()

    def add_task(self, task: Task) -> bool:
        """Menambahkan task baru ke antrean."""

        with self.lock:
            if task.task_id in self.tasks:
                return False

            self.tasks[task.task_id] = {
                "task": task,
                "status": PENDING,
                "worker_id": None,
                "error": None,
            }

            self.queue.put(task.task_id)

            return True

    def get_next_task(self, worker_id: str) -> Optional[Task]:
        """Mengambil task berikutnya untuk Worker."""

        with self.lock:
            while True:
                try:
                    task_id = self.queue.get_nowait()
                except Empty:
                    return None

                record = self.tasks.get(task_id)

                if record is None:
                    continue

                if record["status"] not in (PENDING, REQUEUED):
                    continue

                record["status"] = RUNNING
                record["worker_id"] = worker_id
                record["error"] = None

                return record["task"]

    def complete_task(
        self,
        task_id: str,
        worker_id: str,
        attempt: Optional[int] = None
    ) -> bool:
        """
        Menandai task berhasil diselesaikan.

        Hanya Worker yang ditugaskan dan attempt yang
        sesuai yang boleh menyelesaikan task.
        """

        with self.lock:
            record = self.tasks.get(task_id)

            if record is None:
                return False

            if record["status"] != RUNNING:
                return False

            if record["worker_id"] != worker_id:
                return False

            if (
                attempt is not None
                and record["task"].attempt != attempt
            ):
                return False

            record["status"] = COMPLETED
            record["worker_id"] = None
            record["error"] = None

            return True

    def fail_task(
        self,
        task_id: str,
        worker_id: str,
        error: str,
        retry: bool = True,
        attempt: Optional[int] = None
    ) -> str:
        """
        Menangani task yang gagal.

        Jika masih memiliki kesempatan retry,
        task dimasukkan kembali ke antrean.

        Mengembalikan:
        REQUEUED       : task berhasil dimasukkan kembali.
        FAILED         : batas percobaan sudah habis.
        NOT_FOUND      : task tidak ditemukan.
        INVALID_STATE  : status task tidak sesuai.
        INVALID_WORKER : Worker tidak sesuai.
        INVALID_ATTEMPT: nomor percobaan tidak sesuai.
        """

        with self.lock:
            record = self.tasks.get(task_id)

            if record is None:
                return "NOT_FOUND"

            if record["status"] != RUNNING:
                return "INVALID_STATE"

            if record["worker_id"] != worker_id:
                return "INVALID_WORKER"

            task = record["task"]

            if (
                attempt is not None
                and task.attempt != attempt
            ):
                return "INVALID_ATTEMPT"

            record["worker_id"] = None
            record["error"] = error

            if retry and task.attempt < task.max_attempts:
                task.attempt += 1

                record["status"] = REQUEUED
                self.queue.put(task_id)

                return REQUEUED

            record["status"] = FAILED

            return FAILED

    def get_task_info(self, task_id: str) -> Optional[dict]:
        """Mengambil informasi satu task."""

        with self.lock:
            record = self.tasks.get(task_id)

            if record is None:
                return None

            return {
                "task_id": task_id,
                "status": record["status"],
                "worker_id": record["worker_id"],
                "attempt": record["task"].attempt,
                "max_attempts": record["task"].max_attempts,
                "error": record["error"],
            }

    def get_all_tasks(self) -> list[dict]:
        """Mengambil informasi seluruh task."""

        with self.lock:
            return [
                {
                    "task_id": task_id,
                    "status": record["status"],
                    "worker_id": record["worker_id"],
                    "attempt": record["task"].attempt,
                    "max_attempts": record["task"].max_attempts,
                    "error": record["error"],
                }
                for task_id, record in self.tasks.items()
            ]

    def get_counts(self) -> dict:
        """Menghitung jumlah task berdasarkan status."""

        with self.lock:
            counts = {
                PENDING: 0,
                RUNNING: 0,
                COMPLETED: 0,
                FAILED: 0,
                REQUEUED: 0,
                "TOTAL": len(self.tasks),
            }

            for record in self.tasks.values():
                counts[record["status"]] += 1

            return counts

    def pending_count(self) -> int:
        """Menghitung jumlah item dalam antrean."""

        with self.lock:
            return self.queue.qsize()

    def is_empty(self) -> bool:
        """Memeriksa apakah antrean kosong."""

        return self.pending_count() == 0

    def get_running_tasks_by_worker(self, worker_id: str) -> list:
        """Mengambil ID seluruh task yang sedang dikerjakan Worker."""

        with self.lock:
            return [
                task_id
                for task_id, record in self.tasks.items()
                if (
                    record["status"] == RUNNING
                    and record["worker_id"] == worker_id
                )
            ]
