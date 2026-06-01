# Durable Scan Worker

Milestone 3 introduces a separate Postgres-backed scan worker.

## Local

Terminal 1:

```bash
make backend
```

Terminal 2:

```bash
SCAN_WORKER_CONCURRENCY=2 make worker
```

Create jobs from `/admin/onboarding`; review progress/results/logs in `/admin/scans`.

## Production / Droplet

`docker-compose.backend-full.yml` now runs two services from the same backend image:

- `backend` — FastAPI web service on port 80
- `scan-worker` — `python -m apps.backend.app.workers.scan_worker`

Both services use the same `.env` and therefore the same `DATABASE_URL` / Supabase Postgres.

Recommended worker env vars:

```env
SCAN_WORKER_CONCURRENCY=2
SCAN_WORKER_POLL_INTERVAL_SECONDS=5
SCAN_TASK_LEASE_SECONDS=900
SCAN_TASK_HEARTBEAT_SECONDS=60
```

Apply `docs/sql/scan_jobs_initial_schema.sql` in Supabase before using production workers if app startup has not already created the tables.

## Restart safety

Tasks are claimed with leases. If a worker dies, another worker can reclaim queued/retrying tasks, or running tasks after `locked_until` expires.

## Current limitation

The v1 task runner wraps the existing agentic onboarding crawler and persists final candidates/logs to Postgres. Temporary crawler files may still be used as execution cache, but reviewable job state and candidates are stored durably in `scan_jobs`, `scan_tasks`, `scan_results`, and `scan_logs`.
