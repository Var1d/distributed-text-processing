import time

from master.worker_manager import WorkerManager, OFFLINE
from master.task_queue import TaskQueue


class FaultTolerance:
    """
    Menangani kegagalan Worker dan pemulihan Task.

    Mekanisme:
    - Memeriksa heartbeat Worker.
    - Mendeteksi Worker yang tidak merespons.
    - Menandai Worker sebagai OFFLINE.
    - Mengembalikan Task yang terbengkalai ke antrean.
    """

    def __init__(
        self,
        worker_manager: WorkerManager,
        task_queue: TaskQueue,
        heartbeat_timeout: float = 15.0,
    ):
        if heartbeat_timeout <= 0:
            raise ValueError("Heartbeat timeout harus lebih dari 0.")

        self.worker_manager = worker_manager
        self.task_queue = task_queue
        self.heartbeat_timeout = heartbeat_timeout

    def check_worker_health(self, current_time=None) -> list:
        """
        Memeriksa seluruh Worker dan mendeteksi timeout.

        current_time disediakan agar pengujian dapat
        menggunakan waktu simulasi.
        """

        if current_time is None:
            current_time = time.time()

        failed_workers = []

        workers = self.worker_manager.get_all_workers()

        for worker in workers:
            if worker.status == OFFLINE:
                continue

            elapsed = current_time - worker.last_heartbeat

            if elapsed > self.heartbeat_timeout:
                self.worker_manager.mark_offline(worker.worker_id)

                recovery = self.recover_worker_tasks(worker.worker_id)

                failed_workers.append(
                    {
                        "worker_id": worker.worker_id,
                        "elapsed": elapsed,
                        "recovered_tasks": recovery["requeued"],
                        "failed_tasks": recovery["failed"],
                    }
                )

        return failed_workers

    def recover_worker_tasks(self, worker_id: str) -> dict:
        """
        Mengembalikan Task yang masih RUNNING pada Worker
        yang gagal ke antrean untuk dicoba ulang.
        """

        task_ids = self.task_queue.get_running_tasks_by_worker(worker_id)

        requeued = []
        failed = []

        for task_id in task_ids:
            success = self.task_queue.fail_task(
                task_id=task_id,
                worker_id=worker_id,
                error="Worker gagal atau kehilangan koneksi.",
                retry=True,
            )

            if success:
                task_info = self.task_queue.get_task_info(task_id)

                if task_info["status"] == "REQUEUED":
                    requeued.append(task_id)
                else:
                    failed.append(task_id)

        return {
            "worker_id": worker_id,
            "total_tasks": len(task_ids),
            "requeued": requeued,
            "failed": failed,
        }
