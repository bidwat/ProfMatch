from __future__ import annotations

import asyncio
import os
import signal
import socket
from uuid import uuid4

from apps.backend.app.db import get_db
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
                claimed_task_id = self.claim_one()
                if not claimed_task_id:
                    break
                task = asyncio.create_task(self.run_one(claimed_task_id))
                self.active.add(task)
            if self.active:
                done, _ = await asyncio.wait(self.active, timeout=self.poll_interval, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        task.result()
                    except Exception as exc:
                        print(f"scan worker task crashed: {exc}", flush=True)
            else:
                await asyncio.sleep(self.poll_interval)
        print("scan worker stopping; waiting for active tasks", flush=True)
        if self.active:
            await asyncio.wait(self.active, timeout=10)

    def claim_one(self) -> int | None:
        task = ScanJobService(get_db()).claim_next_scan_task(self.worker_id, self.lease_seconds)
        return task.id if task else None

    async def run_one(self, task_id: int) -> None:
        heartbeat = asyncio.create_task(self.heartbeat_loop(task_id))
        try:
            db = get_db()
            scan_task = ScanJobService(db).get_scan_task(task_id)
            if scan_task:
                await run_department_scan_task(scan_task, db, self.worker_id)
        finally:
            heartbeat.cancel()
            try:
                await heartbeat
            except asyncio.CancelledError:
                pass

    async def heartbeat_loop(self, task_id: int) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_seconds)
            ScanJobService(get_db()).heartbeat_task(task_id, self.worker_id, self.lease_seconds)


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
