import argparse
import logging
import threading

from master.worker_manager import WorkerManager
from master.task_queue import TaskQueue
from master.scheduler import Scheduler
from master.aggregator import Aggregator
from master.fault_tolerance import FaultTolerance
from master.server import MasterServer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("DTPS.Master")


class MasterApplication:
    """
    Aplikasi utama Master DTPS.

    Menginisialisasi seluruh komponen Master,
    menjalankan TCP Server, dan memantau kesehatan Worker.
    """

    def __init__(
        self,
        host="0.0.0.0",
        port=5000,
        heartbeat_timeout=15.0,
        heartbeat_check_interval=5.0,
    ):
        if heartbeat_check_interval <= 0:
            raise ValueError("Heartbeat check interval harus lebih dari 0.")

        # Komponen utama
        self.worker_manager = WorkerManager()
        self.task_queue = TaskQueue()
        self.aggregator = Aggregator()

        # Komponen pengaturan pekerjaan
        self.scheduler = Scheduler(self.worker_manager)

        # Komponen pemulihan kegagalan
        self.fault_tolerance = FaultTolerance(
            worker_manager=self.worker_manager,
            task_queue=self.task_queue,
            heartbeat_timeout=heartbeat_timeout,
        )

        # TCP Server
        self.server = MasterServer(
            worker_manager=self.worker_manager,
            task_queue=self.task_queue,
            aggregator=self.aggregator,
            host=host,
            port=port,
        )

        self.heartbeat_check_interval = heartbeat_check_interval

        self.stop_event = threading.Event()
        self.monitor_thread = None

    def monitor_workers(self):
        """
        Memeriksa heartbeat Worker secara berkala.
        """

        logger.info("Heartbeat monitor dimulai.")

        while not self.stop_event.wait(self.heartbeat_check_interval):
            failed_workers = self.fault_tolerance.check_worker_health()

            for worker in failed_workers:
                logger.warning(
                    "Worker %s OFFLINE. " "Task dikembalikan: %s",
                    worker["worker_id"],
                    worker["recovered_tasks"],
                )

    def run(self):
        """
        Menjalankan aplikasi Master.
        """

        logger.info("Memulai Distributed Text Processing System.")
        logger.info("Konfigurasi server: %s:%s", self.server.host, self.server.port)

        self.monitor_thread = threading.Thread(
            target=self.monitor_workers, daemon=True, name="HeartbeatMonitor"
        )

        self.monitor_thread.start()

        try:
            self.server.serve_forever()

        except KeyboardInterrupt:
            logger.info("Master menerima perintah penghentian.")

        finally:
            self.stop()

    def stop(self):
        """
        Menghentikan seluruh komponen Master.
        """

        self.stop_event.set()
        self.server.stop()

        if self.monitor_thread is not None and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=3)

        logger.info("Aplikasi Master dihentikan.")


def main():
    parser = argparse.ArgumentParser(
        description="Distributed Text Processing System - Master"
    )

    parser.add_argument(
        "--host", default="0.0.0.0", help="Alamat IP untuk server Master."
    )

    parser.add_argument("--port", type=int, default=5000, help="Port TCP server.")

    parser.add_argument(
        "--heartbeat-timeout",
        type=float,
        default=15.0,
        help="Batas waktu heartbeat Worker dalam detik.",
    )

    parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=5.0,
        help="Interval pemeriksaan heartbeat dalam detik.",
    )

    args = parser.parse_args()

    application = MasterApplication(
        host=args.host,
        port=args.port,
        heartbeat_timeout=args.heartbeat_timeout,
        heartbeat_check_interval=args.heartbeat_interval,
    )

    application.run()


if __name__ == "__main__":
    main()
