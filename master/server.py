import socket
import threading

from common.models import WorkerInfo, TaskResult
from common.protocol import send_message, recv_message

from master.worker_manager import WorkerManager, OFFLINE
from master.task_queue import TaskQueue
from master.aggregator import Aggregator


class MasterServer:
    """
    TCP Server untuk komunikasi antara Master dan Workers.

    Mendukung:
    - REGISTER
    - HEARTBEAT
    - REQUEST_TASK
    - SUBMIT_RESULT
    - DISCONNECT
    """

    def __init__(
        self,
        worker_manager: WorkerManager,
        task_queue: TaskQueue,
        aggregator: Aggregator,
        host: str = "0.0.0.0",
        port: int = 5000,
    ):
        if not (0 < port < 65536):
            raise ValueError("Port harus berada antara 1 dan 65535.")

        self.worker_manager = worker_manager
        self.task_queue = task_queue
        self.aggregator = aggregator

        self.host = host
        self.port = port

        self.server_socket = None
        self.running = threading.Event()
        self.assignment_lock = threading.Lock()
        self.client_threads = []

    def process_message(self, message: dict) -> dict:
        """
        Memproses satu pesan dari Worker dan menghasilkan respons.
        """

        if not isinstance(message, dict):
            return {"type": "ERROR", "message": "Format pesan harus berupa dictionary."}

        message_type = message.get("type")

        try:
            if message_type == "REGISTER":
                return self._handle_register(message)

            if message_type == "HEARTBEAT":
                return self._handle_heartbeat(message)

            if message_type == "REQUEST_TASK":
                return self._handle_request_task(message)

            if message_type == "SUBMIT_RESULT":
                return self._handle_submit_result(message)

            if message_type == "DISCONNECT":
                return self._handle_disconnect(message)

            return {"type": "ERROR", "message": "Jenis pesan tidak dikenal."}

        except (ValueError, TypeError, KeyError) as error:
            return {"type": "ERROR", "message": str(error)}

    def _handle_register(self, message: dict) -> dict:
        worker_id = message.get("worker_id")

        if not worker_id:
            raise ValueError("Worker ID wajib diisi.")

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
                "message": "Worker sudah terdaftar atau data tidak valid.",
            }

        return {
            "type": "REGISTERED",
            "worker_id": worker_id,
            "message": "Worker berhasil terdaftar.",
        }

    def _handle_heartbeat(self, message: dict) -> dict:
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
            return {"type": "ERROR", "message": "Data heartbeat tidak valid."}

        return {"type": "HEARTBEAT_ACK", "worker_id": worker_id}

    def _handle_request_task(self, message: dict) -> dict:
        worker_id = message.get("worker_id")

        if not worker_id:
            raise ValueError("Worker ID wajib diisi.")

        worker = self.worker_manager.get_worker(worker_id)

        if worker is None or worker.status == OFFLINE:
            return {
                "type": "ERROR",
                "message": "Worker belum terdaftar atau sedang offline.",
            }

        with self.assignment_lock:
            # Kapasitas maksimum berasal dari laporan heartbeat terakhir.
            capacity = worker.available_slots + worker.active_tasks

            running_count = len(self.task_queue.get_running_tasks_by_worker(worker_id))

            if running_count >= capacity:
                return {"type": "NO_TASK", "message": "Kapasitas Worker sedang penuh."}

            task = self.task_queue.get_next_task(worker_id)

        if task is None:
            return {"type": "NO_TASK", "message": "Belum ada Task yang tersedia."}

        return {"type": "TASK", "task": task.to_dict()}

    def _handle_submit_result(self, message: dict) -> dict:
        result_data = message.get("result")

        if not isinstance(result_data, dict):
            raise ValueError("Data result tidak valid.")

        result = TaskResult.from_dict(result_data)

        if not result.success:
            failed = self.task_queue.fail_task(
                task_id=result.task_id,
                worker_id=result.worker_id,
                error=result.error or "Task gagal diproses.",
                retry=True,
            )

            if not failed:
                return {
                    "type": "ERROR",
                    "message": "Task gagal dilaporkan atau tidak cocok.",
                }

            return {
                "type": "RESULT_RECORDED",
                "task_id": result.task_id,
                "message": "Kegagalan Task berhasil dicatat.",
            }

        completed = self.task_queue.complete_task(
            task_id=result.task_id, worker_id=result.worker_id
        )

        if not completed:
            return {
                "type": "ERROR",
                "message": "Task tidak cocok, belum berjalan, atau sudah selesai.",
            }

        added = self.aggregator.add_result(result)

        if not added:
            return {
                "type": "ERROR",
                "message": "Hasil tidak dapat ditambahkan ke Aggregator.",
            }

        return {
            "type": "RESULT_ACCEPTED",
            "task_id": result.task_id,
            "message": "Hasil berhasil diterima.",
        }

    def _handle_disconnect(self, message: dict) -> dict:
        worker_id = message.get("worker_id")

        if not worker_id:
            raise ValueError("Worker ID wajib diisi.")

        worker = self.worker_manager.get_worker(worker_id)

        if worker is None:
            return {"type": "ERROR", "message": "Worker tidak ditemukan."}

        self.worker_manager.mark_offline(worker_id)

        from master.fault_tolerance import FaultTolerance

        fault_tolerance = FaultTolerance(self.worker_manager, self.task_queue)

        recovery = fault_tolerance.recover_worker_tasks(worker_id)

        return {
            "type": "DISCONNECT_ACK",
            "worker_id": worker_id,
            "recovered_tasks": recovery["requeued"],
            "failed_tasks": recovery["failed"],
        }

    def handle_client(self, client_socket):
        """
        Melayani pesan dari satu koneksi Worker.
        """

        try:
            with client_socket:
                while self.running.is_set():
                    message = recv_message(client_socket)

                    if message is None:
                        break

                    response = self.process_message(message)
                    send_message(client_socket, response)

        except (ConnectionError, OSError):
            pass

    def serve_forever(self):
        """
        Menjalankan TCP Server dan menerima koneksi Worker.
        """

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(20)
        self.server_socket.settimeout(1.0)

        self.running.set()

        print(f"[MASTER] Server berjalan di " f"{self.host}:{self.port}")

        try:
            while self.running.is_set():
                try:
                    client_socket, address = self.server_socket.accept()
                except socket.timeout:
                    continue

                print(f"[MASTER] Koneksi dari {address}")

                thread = threading.Thread(
                    target=self.handle_client, args=(client_socket,), daemon=True
                )

                thread.start()
                self.client_threads.append(thread)

        finally:
            self.stop()

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
