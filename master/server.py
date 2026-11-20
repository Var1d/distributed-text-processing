import socket
import threading

from common.models import WorkerInfo, TaskResult
from common.protocol import send_message, recv_message

from master.worker_manager import WorkerManager, OFFLINE
from master.task_queue import TaskQueue, REQUEUED, FAILED
from master.aggregator import Aggregator
from master.scheduler import Scheduler
from master.fault_tolerance import FaultTolerance


class MasterServer:
    """
    TCP Server untuk komunikasi antara Master dan Workers.

    Mendukung:
    - REGISTER
    - HEARTBEAT
    - REQUEST_TASK
    - SUBMIT_RESULT
    - DISCONNECT

    Juga mendukung:
    - Dynamic task scheduling
    - Validasi attempt task
    - Pemulihan task saat Worker terputus
    """

    def __init__(
        self,
        worker_manager: WorkerManager,
        task_queue: TaskQueue,
        aggregator: Aggregator,
        host: str = "0.0.0.0",
        port: int = 5000,
        scheduler: Scheduler = None,
        min_workers: int = 1,
    ):
        if not (0 < port < 65536):
            raise ValueError("Port harus berada antara 1 dan 65535.")

        self.worker_manager = worker_manager
        self.task_queue = task_queue
        self.aggregator = aggregator
        if min_workers < 1:
            raise ValueError("min_workers harus minimal 1.")
        self.scheduler = scheduler
        self.min_workers = min_workers
        self.shutdown_requested = threading.Event()

        self.host = host
        self.port = port

        self.server_socket = None
        self.running = threading.Event()

        self.assignment_lock = threading.Lock()
        self.client_threads = []

        self.fault_tolerance = FaultTolerance(
            self.worker_manager,
            self.task_queue,
        )

    def process_message(self, message: dict) -> dict:
        """Memproses satu pesan dari Worker."""

        if not isinstance(message, dict):
            return {
                "type": "ERROR",
                "message": "Format pesan harus berupa dictionary.",
            }

        message_type = message.get("type")

        try:
            handlers = {
                "REGISTER": self._handle_register,
                "HEARTBEAT": self._handle_heartbeat,
                "REQUEST_TASK": self._handle_request_task,
                "SUBMIT_RESULT": self._handle_submit_result,
                "DISCONNECT": self._handle_disconnect,
            }

            handler = handlers.get(message_type)

            if handler is None:
                return {
                    "type": "ERROR",
                    "message": "Jenis pesan tidak dikenal.",
                }

            return handler(message)

        except (ValueError, TypeError, KeyError) as error:
            return {
                "type": "ERROR",
                "message": str(error),
            }

    def _handle_register(self, message: dict) -> dict:
        """Mendaftarkan Worker ke Master."""

        worker_id = message.get("worker_id")

        if not worker_id:
            raise ValueError("Worker ID wajib diisi.")

        existing_worker = self.worker_manager.get_worker(worker_id)

        # Worker yang sebelumnya offline boleh mendaftar kembali.
        if existing_worker is not None:
            if existing_worker.status == OFFLINE:
                self.worker_manager.remove_worker(worker_id)
            else:
                return {
                    "type": "ERROR",
                    "message": "Worker sudah terdaftar.",
                }

        worker = WorkerInfo(
            worker_id=worker_id,
            hostname=message.get("hostname", "UNKNOWN"),
            cpu_cores=message.get("cpu_cores", 1),
            total_memory_mb=message.get("total_memory_mb", 0),
            cpu_percent=message.get("cpu_percent", 0.0),
            available_slots=message.get("available_slots", 1),
            active_tasks=message.get("active_tasks", 0),
        )

        registered = self.worker_manager.register_worker(worker)

        if not registered:
            return {
                "type": "ERROR",
                "message": "Worker gagal didaftarkan.",
            }

        print(f"[MASTER] Worker terdaftar: {worker_id}")

        return {
            "type": "REGISTERED",
            "worker_id": worker_id,
            "message": "Worker berhasil terdaftar.",
        }

    def _handle_heartbeat(self, message: dict) -> dict:
        """Memperbarui kondisi dan kapasitas Worker."""

        worker_id = message.get("worker_id")

        if not worker_id:
            raise ValueError("Worker ID wajib diisi.")

        worker = self.worker_manager.get_worker(worker_id)

        if worker is None or worker.status == OFFLINE:
            return {
                "type": "ERROR",
                "message": "Worker belum terdaftar atau sedang offline.",
            }

        updated = self.worker_manager.update_heartbeat(
            worker_id=worker_id,
            cpu_percent=message.get("cpu_percent", 0.0),
            available_slots=message.get("available_slots", 0),
            active_tasks=message.get("active_tasks", 0),
        )

        if not updated:
            return {
                "type": "ERROR",
                "message": "Data heartbeat tidak valid.",
            }

        return {
            "type": "HEARTBEAT_ACK",
            "worker_id": worker_id,
        }

    def _handle_request_task(self, message: dict) -> dict:
        """Memberikan task kepada Worker yang meminta pekerjaan."""

        worker_id = message.get("worker_id")

        if not worker_id:
            raise ValueError("Worker ID wajib diisi.")

        worker = self.worker_manager.get_worker(worker_id)

        if worker is None or worker.status == OFFLINE:
            return {
                "type": "ERROR",
                "message": "Worker belum terdaftar atau sedang offline.",
            }

        if self.shutdown_requested.is_set():
            return {"type": "SHUTDOWN", "message": "Batch telah selesai."}

        online_count = sum(w.status != OFFLINE for w in self.worker_manager.get_all_workers())
        if online_count < self.min_workers:
            return {
                "type": "NO_TASK",
                "message": f"Menunggu Worker ({online_count}/{self.min_workers} terdaftar).",
            }

        with self.assignment_lock:
            # Pastikan Worker masih memiliki kapasitas.
            capacity = worker.available_slots + worker.active_tasks

            running_count = len(self.task_queue.get_running_tasks_by_worker(worker_id))

            if worker.available_slots <= 0 or running_count >= capacity:
                return {
                    "type": "NO_TASK",
                    "message": "Kapasitas Worker sedang penuh.",
                }

            # Dynamic scheduling:
            # Worker dengan beban terendah diprioritaskan.
            if self.scheduler is not None:
                selected_worker = self.scheduler.select_worker()

                if selected_worker is None:
                    return {
                        "type": "NO_TASK",
                        "message": "Belum ada Worker yang tersedia.",
                    }

                if selected_worker.worker_id != worker_id:
                    return {
                        "type": "NO_TASK",
                        "message": "Task sedang diprioritaskan untuk Worker lain.",
                    }

            task = self.task_queue.get_next_task(worker_id)
            if task is not None:
                self.worker_manager.adjust_active_tasks(worker_id, 1)
                if self.scheduler is not None:
                    self.scheduler.record_assignment(worker_id)

        if task is None:
            return {
                "type": "NO_TASK",
                "message": "Belum ada Task yang tersedia.",
            }

        print(
            f"[MASTER] Task {task.task_id} diberikan kepada {worker_id} "
            f"(attempt {task.attempt})."
        )

        return {
            "type": "TASK",
            "task": task.to_dict(),
        }

    def _handle_submit_result(self, message: dict) -> dict:
        """Menerima hasil pemrosesan task dari Worker."""

        result_data = message.get("result")

        if not isinstance(result_data, dict):
            raise ValueError("Data result tidak valid.")

        result = TaskResult.from_dict(result_data)

        if not result.task_id or not result.worker_id:
            raise ValueError("Task ID dan Worker ID wajib diisi.")

        # Task gagal diproses oleh Worker.
        if not result.success:
            failure_status = self.task_queue.fail_task(
                task_id=result.task_id,
                worker_id=result.worker_id,
                error=result.error or "Task gagal diproses.",
                retry=True,
                attempt=result.attempt,
            )

            if failure_status not in (REQUEUED, FAILED):
                return {
                    "type": "ERROR",
                    "message": (
                        "Kegagalan Task tidak dapat dicatat: " f"{failure_status}"
                    ),
                }

            self.worker_manager.adjust_active_tasks(result.worker_id, -1)

            print(
                f"[MASTER] Task {result.task_id} gagal pada "
                f"attempt {result.attempt}. Status: {failure_status}"
            )

            return {
                "type": "RESULT_RECORDED",
                "task_id": result.task_id,
                "status": failure_status,
                "message": "Kegagalan Task berhasil dicatat.",
            }

        # Task berhasil: validasi ID, Worker, status, dan attempt.
        completed = self.task_queue.complete_task(
            task_id=result.task_id,
            worker_id=result.worker_id,
            attempt=result.attempt,
        )

        if not completed:
            return {
                "type": "ERROR",
                "message": (
                    "Task tidak cocok, attempt tidak valid, "
                    "belum berjalan, atau sudah selesai."
                ),
            }

        self.worker_manager.adjust_active_tasks(result.worker_id, -1)
        added = self.aggregator.add_result(result)

        if not added:
            return {
                "type": "ERROR",
                "message": "Hasil tidak dapat ditambahkan ke Aggregator.",
            }

        print(
            f"[MASTER] Task {result.task_id} selesai oleh "
            f"{result.worker_id} dalam {result.processing_time:.4f} detik."
        )

        return {
            "type": "RESULT_ACCEPTED",
            "task_id": result.task_id,
            "message": "Hasil berhasil diterima.",
        }

    def _recover_worker(self, worker_id: str) -> dict:
        """Menandai Worker offline dan memulihkan task miliknya."""

        worker = self.worker_manager.get_worker(worker_id)

        if worker is None or worker.status == OFFLINE:
            return {
                "requeued": [],
                "failed": [],
            }

        self.worker_manager.mark_offline(worker_id)

        recovery = self.fault_tolerance.recover_worker_tasks(worker_id)

        print(
            f"[MASTER] Worker {worker_id} offline. "
            f"Task dikembalikan: {recovery['requeued']}, "
            f"task gagal permanen: {recovery['failed']}."
        )

        return recovery

    def _handle_disconnect(self, message: dict) -> dict:
        """Menangani Worker yang meminta disconnect secara normal."""

        worker_id = message.get("worker_id")

        if not worker_id:
            raise ValueError("Worker ID wajib diisi.")

        worker = self.worker_manager.get_worker(worker_id)

        if worker is None:
            return {
                "type": "ERROR",
                "message": "Worker tidak ditemukan.",
            }

        recovery = self._recover_worker(worker_id)

        return {
            "type": "DISCONNECT_ACK",
            "worker_id": worker_id,
            "recovered_tasks": recovery["requeued"],
            "failed_tasks": recovery["failed"],
        }

    def handle_client(self, client_socket):
        """Melayani pesan dari satu koneksi Worker."""

        registered_worker_id = None

        try:
            with client_socket:
                while self.running.is_set():
                    message = recv_message(client_socket)

                    if message is None:
                        break

                    response = self.process_message(message)

                    send_message(client_socket, response)

                    if message.get("type") == "REGISTER":
                        if response.get("type") == "REGISTERED":
                            registered_worker_id = message.get("worker_id")

                    elif message.get("type") == "DISCONNECT":
                        registered_worker_id = None

        except (ConnectionError, OSError):
            pass

        finally:
            # Hanya koneksi yang melakukan REGISTER yang dapat
            # menyebabkan Worker dianggap terputus saat socket tertutup.
            # Koneksi heartbeat terpisah tidak akan memicu recovery.
            if registered_worker_id is not None:
                self._recover_worker(registered_worker_id)

    def serve_forever(self):
        """Menjalankan TCP Server dan menerima koneksi Worker."""

        self.server_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        self.server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(20)
        self.server_socket.settimeout(1.0)

        self.running.set()

        print(f"[MASTER] Server berjalan di {self.host}:{self.port}")

        try:
            while self.running.is_set():
                try:
                    client_socket, address = self.server_socket.accept()

                except socket.timeout:
                    continue

                except OSError:
                    if self.running.is_set():
                        raise
                    break

                print(f"[MASTER] Koneksi dari {address}")

                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,),
                    daemon=True,
                )

                thread.start()
                self.client_threads.append(thread)

        finally:
            self.stop()

    def request_shutdown(self):
        """Minta Worker mengakhiri loop secara graceful setelah batch selesai."""
        self.shutdown_requested.set()

    def stop(self):
        """Menghentikan TCP Server."""

        self.running.clear()

        if self.server_socket is not None:
            try:
                self.server_socket.close()
            except OSError:
                pass

            self.server_socket = None

        print("[MASTER] Server dihentikan.")
