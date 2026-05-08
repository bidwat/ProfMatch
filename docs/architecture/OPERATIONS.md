# Professor Match Operations & Production Readiness

This document outlines the operational strategies and production readiness checklists for the Professor Match backend and data pipeline, intended for deployment beyond the local-first MVP.

## 1. Database Migration Strategy

Currently, Professor Match uses SQLite for local development (`db/professor_match_publications.sqlite`), and schema changes are handled by dropping and recreating tables (for testing) or relying on simple SQLAlchemy/SQLModel additions.

For production:
- **Tooling:** Implement **Alembic** for structured database migrations.
- **Process:** Generate Alembic revisions locally using `alembic revision --autogenerate -m "description"`.
- **Deployment:** Run `alembic upgrade head` automatically in the CI/CD pipeline or startup script before the FastAPI application accepts traffic.
- **SQLite to Postgres:** If moving to Postgres or Supabase, use an Alembic environment capable of multi-dialect generation, and ensure the local MVP SQLite fallback remains intact by writing dialect-agnostic models.
- **FTS5 Considerations:** Postgres does not support SQLite's `FTS5` directly. If migrating, the `professor_match_fts` virtual table must be replaced with Postgres `tsvector` / `pg_trgm` full-text search, abstracted behind a repository layer.

## 2. Backup and Export Strategy

Because Professor Match separates raw scraped data, processed JSONL, and the final SQLite database, backups must cover multiple tiers.

- **Raw Data & Processed Scans:** Stored in `data/raw/` and `data/processed/`. These are the source of truth for rebuilding the database. They should be checked into Git (using Git LFS for large payloads) or synced to an S3 bucket (e.g., `s3://profmatch-data-lake/`).
- **SQLite Database:** The SQLite `.sqlite` file should be regularly backed up using `sqlite3 db.sqlite ".backup 'backup.sqlite'"` to ensure atomic snapshots without locking.
- **User State / Auth Exports:** In a production setting (e.g., Postgres), configure daily automated logical dumps (`pg_dump`) to secure blob storage, preserving student profiles, tracked contacts, and saved matching data.

## 3. Operational Checklist

Before moving to a live production environment (e.g., a managed VM, Docker container, or PaaS like Render/Heroku), ensure the following are verified:

### Infrastructure
- [ ] Ensure `PROFESSOR_MATCH_DB_PATH` is set to a persistent volume (not an ephemeral container layer) if using SQLite in production.
- [ ] Set a strong, randomly generated secret key for authentication (JWT/Session tokens) if adapting the auth service. Currently, PBKDF2 hashes and `secrets.token_urlsafe` manage sessions, so no static secret is required for signing, but verify cookie security (`Secure=True` in prod).

### Security & Access
- [ ] `ALLOWED_ORIGINS` environment variable is set to the production frontend URL (e.g., `https://profmatch.app`).
- [ ] Admin access requires strict role validation. Ensure the first admin user is seeded manually via a backend script, not an open registration endpoint.
- [ ] Run `npm audit` and resolve all Critical/High vulnerabilities before deploying the frontend.
- [ ] Confirm basic IP rate limiting is active (via `RATE_LIMIT_PER_MINUTE`) or replaced with a robust Redis-backed solution.

### Observability
- [ ] Structured JSON logging is enabled (`LOG_LEVEL=INFO`). Ensure logs are routed to a centralized aggregator (e.g., Datadog, AWS CloudWatch, or Papertrail).
- [ ] Exception handlers return `{"error": ...}` safely without leaking internal stack traces to the client.
- [ ] Uptime monitoring (e.g., Pingdom or BetterStack) is configured to ping `GET /health`.

### Application Resilience
- [ ] Frontend React Error Boundaries (`error.tsx`) and Loading states (`loading.tsx`) are correctly capturing UI failures and network delays.
- [ ] The routine university scanning workflow is disabled in the production web worker and runs strictly as an isolated asynchronous task or local CLI job that pushes approved artifacts to production.
