import argparse
import logging
import threading
import json
import time

from pathlib import Path
from uuid import uuid4

from common.models import Task

from master.worker_manager import WorkerManager
from master.task_queue import TaskQueue
from master.scheduler import Scheduler
from master.aggregator import Aggregator
from master.fault_tolerance import FaultTolerance
from master.server import MasterServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("DTPS.Master")


class MasterApplication:
    """
    Aplikasi utama Distributed Text Processing System.

    Fitur:
    - Master-Worker architecture
    - Task decomposition
    - Dynamic task scheduling
    - Worker heartbeat monitoring
    - Fault tolerance
    - Result aggregation
    - Automatic batch shutdown
    """

    def __init__(
        self,
        host="0.0.0.0",
        port=5000,
        heartbeat_timeout=15.0,
        heartbeat_check_interval=5.0,
        auto_stop=False,
        idle_shutdown_seconds=5.0,
        scheduling="dynamic",
        result_file="results/raw/summary.json",
        min_workers=1,
    ):
        if heartbeat_check_interval <= 0:
            raise ValueError("Heartbeat interval harus lebih dari 0.")

        if idle_shutdown_seconds <= 0:
            raise ValueError("Idle shutdown harus lebih dari 0.")

        self.worker_manager = WorkerManager()
        self.task_queue = TaskQueue()
        self.aggregator = Aggregator()

        self.scheduler = Scheduler(self.worker_manager, strategy=scheduling)

        self.fault_tolerance = FaultTolerance(
            self.worker_manager,
            self.task_queue,
            heartbeat_timeout,
        )

        self.server = MasterServer(
            worker_manager=self.worker_manager,
            task_queue=self.task_queue,
            aggregator=self.aggregator,
            host=host,
            port=port,
            scheduler=self.scheduler,
            min_workers=min_workers,
        )

        self.heartbeat_check_interval = heartbeat_check_interval
        self.auto_stop = auto_stop
        self.idle_shutdown_seconds = idle_shutdown_seconds

        self.expected_task_count = 0
        self.result_file = Path(result_file)

        self.stop_event = threading.Event()
        self.monitor_thread = None

    def add_document(
        self,
        document_id: str,
        text: str,
        chunk_words: int = 2000,
    ) -> int:
        """Membagi dokumen menjadi beberapa Task."""

        if chunk_words < 1:
            raise ValueError("Chunk words minimal 1.")

        words = text.split()
        task_count = 0

        for start in range(0, len(words), chunk_words):
            chunk = " ".join(words[start : start + chunk_words])

            task = Task(
                task_id=f"TASK-{uuid4().hex[:12]}",
                document_id=document_id,
                content=chunk,
            )

            if self.task_queue.add_task(task):
                task_count += 1

        self.expected_task_count += task_count

        logger.info(
            "Dokumen %s dibagi menjadi %s Task.",
            document_id,
            task_count,
        )

        return task_count

    def load_input_files(
        self,
        file_paths: list[str],
        chunk_words: int = 2000,
    ):
        """Membaca dokumen input dan memasukkannya ke antrean."""

        for file_path in file_paths:
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"File tidak ditemukan: {path}")

            if not path.is_file():
                raise ValueError(f"Path bukan file: {path}")

            text = path.read_text(encoding="utf-8")

            self.add_document(
                document_id=path.name,
                text=text,
                chunk_words=chunk_words,
            )

        logger.info(
            "Total Task dalam antrean: %s",
            self.task_queue.pending_count(),
        )

    def monitor_workers(self):
        """
        Memantau Worker dan memeriksa penyelesaian Task.

        Dalam batch mode, Master otomatis berhenti setelah seluruh
        Task berhasil diproses dan waktu tunggu terpenuhi.
        """

        logger.info("Heartbeat monitor dimulai.")

        completion_detected_at = None

        while not self.stop_event.wait(self.heartbeat_check_interval):
            failed_workers = self.fault_tolerance.check_worker_health()

            for worker in failed_workers:
                logger.warning(
                    "Worker %s OFFLINE. Requeued: %s",
                    worker["worker_id"],
                    worker["recovered_tasks"],
                )

            if not self.auto_stop:
                continue

            if self.expected_task_count == 0:
                continue

            summary = self.aggregator.get_summary()
            completed_tasks = summary.get("total_tasks", 0)

            registered_workers = self.worker_manager.get_all_workers()

            all_tasks_completed = completed_tasks >= self.expected_task_count

            if all_tasks_completed and registered_workers:
                if completion_detected_at is None:
                    completion_detected_at = time.monotonic()

                    logger.info(
                        "Seluruh %s Task berhasil diproses.",
                        self.expected_task_count,
                    )

                elapsed = time.monotonic() - completion_detected_at

                if elapsed >= self.idle_shutdown_seconds:
                    logger.info("Batch selesai; memberi sinyal shutdown ke Worker.")
                    self.server.request_shutdown()
                    shutdown_deadline = time.monotonic() + 3.0
                    while time.monotonic() < shutdown_deadline:
                        online = [
                            worker for worker in self.worker_manager.get_all_workers()
                            if worker.status != "OFFLINE"
                        ]
                        if not online:
                            break
                        self.stop_event.wait(0.1)
                    self.server.stop()
                    return

            else:
                completion_detected_at = None

    def save_results(self):
        """Menyimpan ringkasan hasil pemrosesan."""

        self.result_file.parent.mkdir(parents=True, exist_ok=True)
        summary = self.aggregator.get_summary()
        output_file = self.result_file

        with output_file.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                summary,
                file,
                indent=4,
                ensure_ascii=False,
            )

        logger.info("Hasil tersimpan di %s", output_file)
        logger.info("Ringkasan: %s", summary)

    def run(self):
        """Menjalankan aplikasi Master."""

        logger.info("Memulai DTPS Master.")
        logger.info(
            "Server: %s:%s",
            self.server.host,
            self.server.port,
        )

        if self.auto_stop:
            logger.info(
                "Mode: BATCH (auto-stop aktif, jeda %.1f detik).",
                self.idle_shutdown_seconds,
            )
        else:
            logger.info("Mode: SERVER (berhenti manual dengan Ctrl+C).")

        self.monitor_thread = threading.Thread(
            target=self.monitor_workers,
            daemon=True,
        )

        self.monitor_thread.start()

        try:
            self.server.serve_forever()

        except KeyboardInterrupt:
            logger.info("Master dihentikan oleh pengguna.")

        finally:
            self.stop()

    def stop(self):
        """Menghentikan seluruh komponen Master."""

        self.stop_event.set()

        self.server.stop()

        if (
            self.monitor_thread is not None
            and self.monitor_thread.is_alive()
            and threading.current_thread() != self.monitor_thread
        ):
            self.monitor_thread.join(timeout=3)

        self.save_results()

        logger.info("Master shutdown selesai.")


def main():
    parser = argparse.ArgumentParser(
        description="Distributed Text Processing System - Master"
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5000,
    )

    parser.add_argument(
        "--input",
        nargs="*",
        default=[],
    )

    parser.add_argument(
        "--chunk-words",
        type=int,
        default=2000,
    )

    parser.add_argument(
        "--heartbeat-timeout",
        type=float,
        default=15.0,
    )

    parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=5.0,
    )

    parser.add_argument(
        "--min-workers",
        type=int,
        default=1,
        help="Tahan task sampai jumlah Worker ini terdaftar (untuk demo multi-Worker).",
    )

    parser.add_argument(
        "--result-file",
        default="results/raw/summary.json",
        help="Path file JSON untuk ringkasan hasil.",
    )

    parser.add_argument(
        "--scheduling",
        choices=("dynamic", "static"),
        default="dynamic",
        help="Strategi pemilihan worker untuk eksperimen.",
    )

    parser.add_argument(
        "--auto-stop",
        action="store_true",
        help="Menghentikan Master otomatis setelah semua Task selesai.",
    )

    parser.add_argument(
        "--idle-shutdown-seconds",
        type=float,
        default=5.0,
        help="Waktu tunggu sebelum batch mode menghentikan Master.",
    )

    args = parser.parse_args()

    app = MasterApplication(
        host=args.host,
        port=args.port,
        heartbeat_timeout=args.heartbeat_timeout,
        heartbeat_check_interval=args.heartbeat_interval,
        auto_stop=args.auto_stop,
        idle_shutdown_seconds=args.idle_shutdown_seconds,
        scheduling=args.scheduling,
        result_file=args.result_file,
        min_workers=args.min_workers,
    )

    if args.input:
        app.load_input_files(
            args.input,
            chunk_words=args.chunk_words,
        )
    else:
        logger.warning("Tidak ada input dokumen. " "Master akan berjalan tanpa Task.")

    app.run()


if __name__ == "__main__":
    main()
