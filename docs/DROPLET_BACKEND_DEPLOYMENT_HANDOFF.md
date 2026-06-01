# Professor Match — Droplet Backend Deployment Handoff

_Last updated: 2026-06-01_

This handoff records the production backend migration work performed from the historical/WIP repo context. The authoritative deployment repo is still:

```txt
/home/drl/pi-agent/profmatch-clean-git
```

GitHub repo:

```txt
bidwat/ProfMatch
```

Production branch:

```txt
main
```

## Outcome

The backend was moved off Render Free and deployed to a DigitalOcean Droplet.

Current backend URL:

```txt
http://137.184.16.45
```

The Vercel frontend should use:

```env
BACKEND_URL=http://137.184.16.45
```

## Deployment architecture

```txt
Vercel frontend
  -> BACKEND_URL=http://137.184.16.45
DigitalOcean Droplet backend
  -> Docker Compose full backend image
Supabase Postgres
  -> production database via DATABASE_URL / Supabase pooler
```

The backend runs on the Droplet at:

```txt
/opt/profmatch
```

Runtime env file on Droplet:

```txt
/opt/profmatch/.env
```

Do not commit this env file.

## Git changes made in clean repo

The following deployment/production-hardening work was committed and pushed to `main` in `/home/drl/pi-agent/profmatch-clean-git`:

```txt
3f37641 Add lightweight backend droplet deployment
dcf3ec7 Use full backend droplet deployment
fd6438b Handle droplet backend container replacement
e7c037f Add production backend health and DB guardrails
d637a1f Document droplet production verification
99a47bf Include scripts in full backend image
2b2903c Fix production DB table checks
f27b48d Record droplet backend QA verification
```

Key files added/changed:

```txt
.github/workflows/deploy-droplet-backend.yml
.dockerignore
apps/backend/Dockerfile
apps/backend/Dockerfile.runtime
apps/backend/requirements.runtime.txt
docker-compose.backend-only.yml
docker-compose.backend-full.yml
scripts/check_production_db.py
apps/backend/app/db/__init__.py
apps/backend/app/api/stats.py
.env.example
docs/deployment/DIGITALOCEAN_MIGRATION.md
docs/qa-reports/latest.md
```

## Current production compose path

The production backend deploy now uses:

```txt
docker-compose.backend-full.yml
```

This uses the original full backend image:

```txt
apps/backend/Dockerfile
```

So the production backend includes:

- FastAPI app
- Supabase/Postgres support
- SQLite local fallback when not in production
- Playwright
- Patchright
- Crawl4AI
- admin/onboarding scraper workflow dependencies

A lightweight backend-only compose/image also exists, but it is not the active production workflow.

## Production guardrails added

`APP_ENV=production` now prevents accidental SQLite fallback.

Production startup fails if:

- `DATABASE_URL` is missing and Supabase DB component vars are missing.
- SQLite would be selected while `APP_ENV=production`.

The app can still use SQLite locally when not in production.

## Health endpoints

Live checks passed for:

```txt
/health
/api/health
/api/health/db
/api/stats
```

Expected examples:

```bash
curl http://137.184.16.45/health
curl http://137.184.16.45/api/health
curl http://137.184.16.45/api/health/db
curl http://137.184.16.45/api/stats
```

## Database verification

Added:

```txt
scripts/check_production_db.py
```

Run on Droplet:

```bash
cd /opt/profmatch
docker compose -f docker-compose.backend-full.yml exec backend python scripts/check_production_db.py
```

Verified result at time of handoff:

```txt
PASS: production DB is Postgres and baseline data is present
professors=1036 publications=4347
```

The count differs from older docs that mentioned `1039` / `4358`; the live Supabase count observed during verification is `1036` professors and `4347` publications.

## Auto-deploy setup

GitHub Actions workflow:

```txt
.github/workflows/deploy-droplet-backend.yml
```

It runs on push to:

```txt
main
```

GitHub repository secrets configured:

```txt
DROPLET_HOST
DROPLET_SSH_KEY
```

These are deploy-only credentials used by GitHub Actions to SSH into the Droplet. They are not application runtime secrets.

Runtime secrets remain only on the Droplet in:

```txt
/opt/profmatch/.env
```

Runtime secrets include values such as `DATABASE_URL`, Supabase credentials, and OpenRouter key. They should not be committed to GitHub.

## Droplet commands

Check status:

```bash
cd /opt/profmatch
docker compose -f docker-compose.backend-full.yml ps
```

View logs:

```bash
cd /opt/profmatch
docker compose -f docker-compose.backend-full.yml logs -f backend
```

Manual deploy:

```bash
cd /opt/profmatch
git fetch origin main
git reset --hard origin/main
docker compose -f docker-compose.backend-only.yml down --remove-orphans || true
docker rm -f profmatch-backend-1 || true
docker compose -f docker-compose.backend-full.yml up -d --build --remove-orphans
docker image prune -f
```

## GitHub UI checks

In `bidwat/ProfMatch`:

1. `Settings -> Branches`
   - Default branch should be `main`.
2. `Settings -> Secrets and variables -> Actions`
   - Repository secrets should include `DROPLET_HOST` and `DROPLET_SSH_KEY`.
3. `Actions -> Deploy backend to DigitalOcean Droplet`
   - Recent deploy runs should be successful.

No Supabase/OpenRouter secrets are needed in GitHub for deploy-only workflow.

## Vercel action required

In Vercel, ensure the frontend env var is:

```env
BACKEND_URL=http://137.184.16.45
```

Then redeploy Vercel.

The user reported Vercel checks are good.

## Security notes

Secrets were pasted during troubleshooting. The user plans to rotate them later. After rotation, update:

```txt
/opt/profmatch/.env
```

Then redeploy/restart:

```bash
cd /opt/profmatch
docker compose -f docker-compose.backend-full.yml up -d --build
```

Do not commit secrets to either repo.

## Remaining recommended follow-ups

- Add a real domain and HTTPS for the backend instead of raw HTTP IP.
- Rotate exposed Supabase/OpenRouter keys.
- Consider moving admin/onboarding job state from container volumes into Postgres/object storage for stronger durability.
- Add formal Alembic migrations later.
- Consider external/distributed rate limiting if traffic increases.
