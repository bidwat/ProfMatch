from __future__ import annotations

import asyncio
import os
import signal
import socket
from uuid import uuid4

from sqlmodel import Session

from apps.backend.app.db import engine
from apps.backend.app.services.scan_job_service import ScanJobService
from apps.backend.app.services.scan_task_runner import run_department_scan_task


class ScanWorker:
    def __init__(self) -> None:
        self.worker_id = f"{socket.gethostname()}-{os.getpid()}-{uuid4().hex[:8]}"
        self.concurrency = int(os.getenv("SCAN_WORKER_CONCURRENCY", "2"))
        self.poll_interval = int(os.getenv("SCAN_WORKER_POLL_INTERVAL_SECONDS", "5"))
        self.lease_seconds = int(os.getenv("SCAN_TASK_LEASE_SECONDS", "900"))
        self.heartbeat_seconds = int(os.getenv("SCAN_TASK_HEARTBEAT_SECONDS", "60"))
        self.stop_event = asyncio.Event()
        self.active: set[asyncio.Task] = set()

    def request_stop(self) -> None:
        self.stop_event.set()

    async def run(self) -> None:
        print(f"scan worker {self.worker_id} starting with concurrency={self.concurrency}", flush=True)
        while not self.stop_event.is_set():
            self.active = {task for task in self.active if not task.done()}
            while len(self.active) < self.concurrency and not self.stop_event.is_set():
                claimed = self.claim_one()
                if not claimed:
                    break
                task = asyncio.create_task(self.run_one(claimed))
                self.active.add(task)
            if self.active:
                done, _ = await asyncio.wait(self.active, timeout=self.poll_interval, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
            else:
                await asyncio.sleep(self.poll_interval)
        print("scan worker stopping; waiting for active tasks", flush=True)
        if self.active:
            await asyncio.wait(self.active, timeout=10)

    def claim_one(self):
        with Session(engine) as session:
            return ScanJobService(session).claim_next_scan_task(self.worker_id, self.lease_seconds)

    async def run_one(self, scan_task) -> None:
        heartbeat = asyncio.create_task(self.heartbeat_loop(scan_task.id))
        try:
            with Session(engine) as session:
                await run_department_scan_task(scan_task, session, self.worker_id)
        finally:
            heartbeat.cancel()
            try:
                await heartbeat
            except asyncio.CancelledError:
                pass

    async def heartbeat_loop(self, task_id: int) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_seconds)
            with Session(engine) as session:
                ScanJobService(session).heartbeat_task(task_id, self.worker_id, self.lease_seconds)


async def main() -> None:
    worker = ScanWorker()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, worker.request_stop)
        except NotImplementedError:
            pass
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
