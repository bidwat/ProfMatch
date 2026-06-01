# DigitalOcean Migration Runbook

Goal: move Professor Match away from the current Vercel + Render Free shape toward DigitalOcean App Platform for more predictable production hosting.

## Current baseline from handoff

- Authoritative repo: `/home/drl/pi-agent/profmatch-clean-git`
- Branch: `main`
- Remote: `git@github.com:bidwat/ProfMatch.git`
- Current frontend: Vercel (`https://prof-match-chi.vercel.app`)
- Current backend: Render Free (`https://profmatch-backend.onrender.com`)
- Current production DB: Supabase Postgres, preferably through Session Pooler

## Prepared in this repo

- `apps/backend/Dockerfile` — FastAPI Docker image, already compatible with a platform `PORT` env var.
- `apps/frontend/Dockerfile` — Next.js Docker image, now uses `${PORT:-3000}`.
- `docker-compose.digitalocean.yml` — local container smoke test for a DigitalOcean-like frontend/backend setup.
- `.do/app.yaml` — starter DigitalOcean App Platform spec with placeholders for final hostnames/secrets.

## Recommended target architecture

Option A — lowest migration risk:

```txt
Frontend: DigitalOcean App Platform Next.js service
Backend: DigitalOcean App Platform FastAPI service
Database: existing Supabase Postgres Session Pooler
```

Option B — more consolidated:

```txt
Frontend: DigitalOcean App Platform Next.js service
Backend: DigitalOcean App Platform FastAPI service
Database: DigitalOcean Managed Postgres dev/prod database
```

Option A avoids an immediate database move. Option B reduces provider sprawl but requires a DB import and backup plan.

## Local smoke test

From the authoritative repo:

```bash
cd /home/drl/pi-agent/profmatch-clean-git
docker compose -f docker-compose.digitalocean.yml build
ALLOWED_ORIGINS=http://localhost:3000 \
BACKEND_URL=http://backend:8000 \
docker compose -f docker-compose.digitalocean.yml up
```

Then in another terminal:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/stats
open http://localhost:3000
```

To test against Supabase/Postgres instead of the image SQLite fallback:

```bash
DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/DB?sslmode=require' \
ALLOWED_ORIGINS=http://localhost:3000 \
BACKEND_URL=http://backend:8000 \
docker compose -f docker-compose.digitalocean.yml up --build
```


## Avoiding DigitalOcean serverless autodetect

If the Create App UI detects this repository as **Functions / Serverless**, do not finalize that resource. Use the checked-in App Spec instead, or delete the detected Function resource and manually add Dockerfile-backed Web Services. The required resources are:

```txt
backend:  service, source_dir=/, dockerfile_path=apps/backend/Dockerfile, http_port=8000, routes=/api and /health
frontend: service, source_dir=/, dockerfile_path=apps/frontend/Dockerfile, http_port=3000, route=/
```

The App Spec path is `.do/app.yaml`; it is the preferred source of truth for DigitalOcean because it bypasses framework/serverless autodetection.

## DigitalOcean App Platform setup

1. Push the `main` branch to GitHub.
2. In DigitalOcean, create a new App Platform app from `bidwat/ProfMatch`, branch `main`.
3. Add backend service:
   - Source directory: `/`
   - Dockerfile path: `apps/backend/Dockerfile`
   - HTTP port: `8000`
   - Routes: `/api` and `/health`
   - Health check path: `/health`
4. Add frontend service:
   - Source directory: `/`
   - Dockerfile path: `apps/frontend/Dockerfile`
   - HTTP port: `3000`
   - Route: `/`
5. Set backend environment variables:
   - `DATABASE_URL` = Supabase pooler URL or DigitalOcean Postgres URL. Mark secret.
   - `ALLOWED_ORIGINS` = final frontend URL.
   - `RATE_LIMIT_PER_MINUTE=300`
   - `LOG_LEVEL=INFO`
   - `OPENROUTER_API_KEY` only if optional reranking/onboarding requires it.
   - `OPENROUTER_MODEL=inclusionai/ring-2.6-1t:free`
   - `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
6. Set frontend environment variables:
   - `BACKEND_URL` = final app URL when using the `/api` backend route on the same App Platform app, or final backend service URL if you expose backend separately.
7. Deploy backend first and verify `/health`.
8. Deploy frontend and verify API calls through the frontend.
9. After final hostnames are known, update `ALLOWED_ORIGINS` and `BACKEND_URL`, then redeploy. With the provided `.do/app.yaml`, both can usually be the same app hostname because backend owns `/api` and frontend owns `/`.

## Using `.do/app.yaml`

Before using `doctl apps create --spec .do/app.yaml`, replace:

- `REPLACE_WITH_DO_POSTGRES_OR_SUPABASE_POOLER_URL`
- `REPLACE_WITH_FRONTEND_HOSTNAME`
- `REPLACE_WITH_APP_HOSTNAME`

Then run:

```bash
doctl apps create --spec .do/app.yaml
```

Or create the app in the UI and export the generated spec:

```bash
doctl apps list
doctl apps spec get APP_ID > .do/app.generated.yaml
```

Do not commit generated specs if they include real hostnames, project refs, or secret values that should remain private.

## Database migration if moving from Supabase to DigitalOcean Postgres

If staying on Supabase, skip this section.

If creating a new DigitalOcean Postgres database, import data from the SQLite seed or current local source using:

```bash
DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/DB?sslmode=require' \
RESET_POSTGRES=true \
PYTHONPATH=. \
python scripts/migrate_sqlite_to_postgres.py
```

Then smoke test:

```bash
curl https://BACKEND_HOST/health
curl https://BACKEND_HOST/api/stats
curl 'https://BACKEND_HOST/api/professors?limit=3'
```

## Production hardening to do with or after the hosting move

From the handoff, these remain important before inviting real users:

- Verify production cookie settings, especially `secure=True` for HTTPS.
- Move agentic onboarding job state off local container filesystem into Postgres/object storage.
- Replace base64 profile-photo JSON storage with object storage such as Supabase Storage or DigitalOcean Spaces.
- Add Alembic migrations instead of relying only on `SQLModel.metadata.create_all`.
- Replace in-memory rate limiting with provider/Redis/Upstash/Cloudflare-backed rate limits.
- Add monitoring, backup, and rollback notes.

## Render retirement checklist

Only after DigitalOcean smoke tests pass:

1. Disable Render auto-deploys.
2. Keep Render available for one rollback window.
3. Update Vercel `BACKEND_URL` only if Vercel remains the frontend.
4. Update docs and secrets inventory to remove Render as the default backend target.
5. Delete or pause Render after the rollback window.


## Droplet production backend checks

The current production backend runs on a DigitalOcean Droplet, not App Platform.

Required Droplet env:

```env
APP_ENV=production
DATABASE_URL=postgresql+psycopg://USER:URL_ENCODED_PASSWORD@HOST:5432/postgres?sslmode=require
ALLOWED_ORIGINS=http://137.184.16.45,https://prof-match-chi.vercel.app,http://localhost:3000
```

`APP_ENV=production` intentionally refuses SQLite fallback. If `DATABASE_URL` or Supabase Postgres component variables are missing, backend startup must fail rather than silently using local SQLite.

Production health checks:

```bash
# health endpoints: /health, /api/health, /api/health/db, /api/stats
```

Production DB verification on the Droplet:

```bash
cd /opt/profmatch
docker compose -f docker-compose.backend-full.yml exec backend python scripts/check_production_db.py
```

Expected baseline corpus at time of migration:

```txt
professors=1039
publications=4358
```

GitHub Actions auto-deploy uses repository secrets:

```txt
DROPLET_HOST=137.184.16.45
DROPLET_SSH_KEY=<private SSH key authorized on the Droplet>
```

These are GitHub repository secrets used only by the deploy workflow. They are not application runtime environment variables and are not stored in the Droplet `.env` file.

## Supabase backup/export

Before risky schema/data changes, export Supabase Postgres from a trusted machine with `pg_dump` using the Supabase pooler/direct connection details:

```bash
pg_dump "$DATABASE_URL" --format=custom --file=profmatch-supabase-$(date +%Y%m%d-%H%M%S).dump
```

For a plain SQL export:

```bash
pg_dump "$DATABASE_URL" --file=profmatch-supabase-$(date +%Y%m%d-%H%M%S).sql
```

Store backups outside the repo. Do not commit dumps because they can contain user data.
