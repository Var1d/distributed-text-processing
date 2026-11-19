from threading import Lock

from master.worker_manager import WorkerManager, OFFLINE


class Scheduler:
    """
    Dynamic Task Scheduler.

    Memilih Worker berdasarkan:
    - CPU utilization.
    - Active tasks dibandingkan CPU cores.
    - Available slots dibandingkan CPU cores.

    Worker dengan load score terendah mendapatkan prioritas.
    """

    def __init__(
        self,
        worker_manager: WorkerManager,
        cpu_weight: float = 0.5,
        task_weight: float = 0.3,
        slot_weight: float = 0.2,
    ):
        weights = [cpu_weight, task_weight, slot_weight]

        if any(weight < 0 for weight in weights):
            raise ValueError("Bobot tidak boleh negatif.")

        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("Total bobot harus sama dengan 1.")

        self.worker_manager = worker_manager

        self.cpu_weight = cpu_weight
        self.task_weight = task_weight
        self.slot_weight = slot_weight

        self.lock = Lock()

    def calculate_load_score(self, worker) -> float:
        """
        Menghitung skor beban satu Worker.

        Semakin rendah skor, semakin ringan bebannya.
        """

        if worker.cpu_cores < 1:
            raise ValueError("Worker harus memiliki minimal 1 CPU core.")

        cpu_load = min(max(worker.cpu_percent, 0), 100)

        task_load = min(worker.active_tasks / worker.cpu_cores, 1.0) * 100

        slot_pressure = (1 - min(worker.available_slots / worker.cpu_cores, 1.0)) * 100

        score = (
            self.cpu_weight * cpu_load
            + self.task_weight * task_load
            + self.slot_weight * slot_pressure
        )

        return score

    def get_worker_scores(self) -> list[dict]:
        """
        Mengambil skor seluruh Worker yang tersedia.

        Hasil diurutkan dari skor terendah.
        """

        workers = self.worker_manager.get_all_workers()

        scores = []

        for worker in workers:

            if worker.status == OFFLINE:
                continue

            if worker.available_slots <= 0:
                continue

            score = self.calculate_load_score(worker)

            scores.append(
                {
                    "worker_id": worker.worker_id,
                    "cpu_cores": worker.cpu_cores,
                    "cpu_percent": worker.cpu_percent,
                    "active_tasks": worker.active_tasks,
                    "available_slots": worker.available_slots,
                    "load_score": score,
                }
            )

        scores.sort(
            key=lambda item: (
                item["load_score"],
                -item["available_slots"],
                -item["cpu_cores"],
                item["worker_id"],
            )
        )

        return scores

    def select_worker(self):
        """
        Memilih Worker terbaik berdasarkan load score.

        Mengembalikan WorkerInfo jika tersedia.
        Mengembalikan None jika tidak ada Worker yang siap.
        """

        with self.lock:

            scores = self.get_worker_scores()

            if not scores:
                return None

            selected_id = scores[0]["worker_id"]

            return self.worker_manager.get_worker(selected_id)
