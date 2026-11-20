import socket
import threading
import time
import logging

from common.models import Task
from common.protocol import send_message, recv_message

from worker.monitor import WorkerMonitor
from worker.processor import process_task

logger = logging.getLogger("DTPS.Worker")


class WorkerClient:

    def __init__(
        self,
        master_host: str,
        master_port: int,
        worker_id: str,
        processes: int = 1,
        heartbeat_interval: float = 5.0,
    ):
        self.master_host = master_host
        self.master_port = master_port
        self.worker_id = worker_id
        self.processes = processes
        self.heartbeat_interval = heartbeat_interval

        self.monitor = WorkerMonitor(processes)

        self.stop_event = threading.Event()
        self.heartbeat_stop = threading.Event()

        self.socket = None
        self.heartbeat_thread = None

    def connect(self):
        self.socket = socket.create_connection(
            (self.master_host, self.master_port), timeout=10
        )

        self.socket.settimeout(60)

        logger.info("Terhubung ke Master %s:%s", self.master_host, self.master_port)

    def register(self):
        metrics = self.monitor.get_metrics()

        message = {
            "type": "REGISTER",
            "worker_id": self.worker_id,
            "hostname": metrics["hostname"],
            "cpu_cores": metrics["cpu_cores"],
            "total_memory_mb": metrics["total_memory_mb"],
            "cpu_percent": metrics["cpu_percent"],
            "available_slots": metrics["available_slots"],
            "active_tasks": metrics["active_tasks"],
        }

        send_message(self.socket, message)
        response = recv_message(self.socket)

        if response is None:
            raise ConnectionError("Master tidak memberikan respons.")

        if response.get("type") == "ERROR":
            # Mencoba membersihkan registrasi lama ketika reconnect.
            send_message(
                self.socket, {"type": "DISCONNECT", "worker_id": self.worker_id}
            )

            recv_message(self.socket)

            send_message(self.socket, message)
            response = recv_message(self.socket)

        if response is None or response.get("type") != "REGISTERED":
            raise ConnectionError(f"Registrasi Worker gagal: {response}")

        logger.info("Worker %s berhasil terdaftar.", self.worker_id)

    def send_heartbeat(self):
        while not self.heartbeat_stop.wait(self.heartbeat_interval):
            try:
                metrics = self.monitor.get_metrics()

                with socket.create_connection(
                    (self.master_host, self.master_port), timeout=5
                ) as heartbeat_socket:

                    heartbeat_socket.settimeout(5)

                    send_message(
                        heartbeat_socket,
                        {
                            "type": "HEARTBEAT",
                            "worker_id": self.worker_id,
                            "cpu_percent": metrics["cpu_percent"],
                            "available_slots": metrics["available_slots"],
                            "active_tasks": metrics["active_tasks"],
                        },
                    )

                    response = recv_message(heartbeat_socket)

                    if response is None or response.get("type") == "ERROR":
                        logger.warning("Heartbeat tidak diterima: %s", response)

            except (OSError, ConnectionError) as error:
                logger.warning("Heartbeat gagal: %s", error)

    def start_heartbeat(self):
        self.heartbeat_stop.clear()

        self.heartbeat_thread = threading.Thread(
            target=self.send_heartbeat, daemon=True
        )

        self.heartbeat_thread.start()

    def request_task(self):
        send_message(self.socket, {"type": "REQUEST_TASK", "worker_id": self.worker_id})

        return recv_message(self.socket)

    def work_loop(self):
        logger.info("Worker mulai mencari Task.")

        while not self.stop_event.is_set():

            response = self.request_task()

            if response is None:
                raise ConnectionError("Koneksi Master terputus.")

            response_type = response.get("type")

            if response_type == "SHUTDOWN":
                logger.info("Master memberi sinyal shutdown; Worker selesai.")
                self.stop_event.set()
                return

            if response_type == "NO_TASK":
                time.sleep(0.1)
                continue

            if response_type == "ERROR":
                logger.warning("Permintaan Task ditolak: %s", response.get("message"))
                time.sleep(0.1)
                continue

            if response_type != "TASK":
                logger.warning("Respons tidak dikenal: %s", response)
                time.sleep(1)
                continue

            task = Task.from_dict(response["task"])

            logger.info("Mengerjakan Task %s (attempt %s)", task.task_id, task.attempt)

            self.monitor.set_active_tasks(1)

            result = process_task(
                task=task, worker_id=self.worker_id, processes=self.processes
            )

            self.monitor.set_active_tasks(0)

            send_message(
                self.socket, {"type": "SUBMIT_RESULT", "result": result.to_dict()}
            )

            result_response = recv_message(self.socket)

            if result_response is None:
                raise ConnectionError("Koneksi terputus ketika mengirim hasil.")

            logger.info(
                "Respons hasil Task %s: %s", task.task_id, result_response.get("type")
            )

    def disconnect(self):
        self.heartbeat_stop.set()

        if self.heartbeat_thread is not None and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=3)

        if self.socket is not None:
            try:
                send_message(
                    self.socket, {"type": "DISCONNECT", "worker_id": self.worker_id}
                )

                recv_message(self.socket)

            except (OSError, ConnectionError):
                pass

            try:
                self.socket.close()
            except OSError:
                pass

            self.socket = None

    def run(self):
        try:
            while not self.stop_event.is_set():
                try:
                    self.connect()
                    self.register()
                    self.start_heartbeat()
                    self.work_loop()
                except KeyboardInterrupt:
                    logger.info("Worker menerima perintah berhenti.")
                    break
                except (OSError, ConnectionError) as error:
                    logger.warning("Koneksi Master terputus (%s); mencoba menyambung kembali.", error)
                    self.heartbeat_stop.set()
                    if self.heartbeat_thread is not None and self.heartbeat_thread.is_alive():
                        self.heartbeat_thread.join(timeout=3)
                    if self.socket is not None:
                        try:
                            self.socket.close()
                        except OSError:
                            pass
                        self.socket = None
                    self.stop_event.wait(2.0)
        finally:
            self.stop_event.set()
            self.disconnect()
            logger.info("Worker dihentikan.")
