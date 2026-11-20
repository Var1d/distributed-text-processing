import argparse
import logging
import multiprocessing
import os
import socket
import uuid

from worker.client import WorkerClient


def main():

    parser = argparse.ArgumentParser(
        description="Distributed Text Processing System - Worker"
    )

    parser.add_argument(
        "--master-host", required=True, help="Alamat IP komputer Master."
    )

    parser.add_argument("--port", type=int, default=5000)

    parser.add_argument("--worker-id", default=None)

    parser.add_argument("--processes", type=int, default=os.cpu_count() or 1)

    parser.add_argument("--heartbeat-interval", type=float, default=5.0)

    args = parser.parse_args()

    worker_id = args.worker_id or (f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}")

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )

    client = WorkerClient(
        master_host=args.master_host,
        master_port=args.port,
        worker_id=worker_id,
        processes=args.processes,
        heartbeat_interval=args.heartbeat_interval,
    )

    client.run()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
