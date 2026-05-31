# Free Deployment Plan — ProfMatch

Goal: deploy ProfMatch on free tiers that stop, sleep, pause, or fail when limits are reached instead of unexpectedly charging.

## Target architecture

- **Frontend:** DigitalOcean App Platform or Vercel
  - Hosts the Next.js app.
  - Public web entry point.
- **Backend:** DigitalOcean App Platform
  - Hosts the FastAPI API from `apps/backend/Dockerfile`.
  - Replaces Render Free to avoid backend sleep/cold-start problems.
- **Database:** Supabase Free or Neon Free Postgres
  - Persistent managed Postgres.
  - Replaces production SQLite.
  - Keep SQLite for local development and seed/offline workflows.

## Why not SQLite in production free hosting?

The current app uses SQLite locally, which is ideal for development. But production SQLite needs durable disk storage. Free app hosts usually provide ephemeral filesystems; platforms with real persistent volumes are often usage-billed. To avoid surprise charges, production should use a free managed Postgres database.

## Migration plan

1. Add backend support for `DATABASE_URL`.
   - SQLite remains the local default.
   - Postgres is used when `DATABASE_URL=postgresql+psycopg://...` is set.
2. Add Postgres driver dependency.
3. Add DB initialization helper that creates SQLModel tables in Postgres.
4. Add a migration/export script to copy the local SQLite seed data into Postgres.
5. Update deployment env examples.
6. Deploy backend to DigitalOcean App Platform with `DATABASE_URL` and CORS configured.
7. Deploy frontend to DigitalOcean App Platform or Vercel with API URL/proxy configured.
8. Smoke test:
   - sign up / sign in,
   - profile save,
   - match generation,
   - discover filters,
   - saved professors,
   - recommendation modal.

## Preferred first deployment

```txt
DigitalOcean App Platform frontend
DigitalOcean App Platform backend
Supabase Free Postgres or DigitalOcean Managed Postgres
```

Alternative:

```txt
Vercel Free frontend
Koyeb Free backend
Neon Free Postgres
```

## Free-tier expectation

Free services may sleep or pause. For public signup flows, a sleeping backend is a product risk; set DigitalOcean budgets/alerts and prefer an always-on backend when inviting real users.

See `docs/deployment/DIGITALOCEAN_MIGRATION.md` for the Render-to-DigitalOcean migration runbook.
