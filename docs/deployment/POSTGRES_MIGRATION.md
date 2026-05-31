# Postgres Migration Guide

This app now supports both local SQLite and production Postgres.

## Local default

If `DATABASE_URL` is not set, the backend uses:

```txt
db/professor_match_publications.sqlite
```

## Production Postgres

Set `DATABASE_URL` to your Supabase or Neon connection string:

```bash
DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres'
```

The backend also accepts provider-style URLs and normalizes them:

```txt
postgres://...
postgresql://...
```

## Install dependency

```bash
cd apps/backend
source venv/bin/activate
pip install -r requirements.txt
```

## Create a free Postgres database

Recommended no-surprise free options:

- Supabase Free
- Neon Free

Do not enable paid billing unless you intentionally want paid capacity.

## Supabase database password

The password in this URL:

```txt
postgresql://postgres:[YOUR-PASSWORD]@db.<project-ref>.supabase.co:5432/postgres
```

is the **database password** for the `postgres` database user. It is not the Supabase publishable key and not the Supabase secret/service-role key.

Find or reset it in Supabase:

1. Open the Supabase dashboard.
2. Select the project.
3. Go to **Project Settings → Database**.
4. Open **Connection string** / **Connection info**.
5. If you do not know the password, use **Reset database password**.
6. Store it locally only in `.env` as `SUPABASE_DB_PASSWORD`.

If the password contains symbols like `@`, `:`, `/`, `#`, `$`, `*`, or `%`, prefer using the component variables below because the migration script URL-encodes them safely.

If Supabase shows **Not IPv4 compatible**, direct host access may fail from local machines or many free hosts. In that case use **Session Pooler** settings from the same Database settings page.

## Import SQLite seed data into Postgres

From the repo root, either set a full URL:

```bash
DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres' \
RESET_POSTGRES=true \
python scripts/migrate_sqlite_to_postgres.py
```

or set Supabase components in `.env`:

```txt
SUPABASE_DB_HOST=db.<project-ref>.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-db-password
SUPABASE_DB_SSLMODE=require
```

If direct DB host is not IPv4-compatible, use session pooler values too:

```txt
SUPABASE_POOLER_HOST=<session-pooler-host-from-dashboard>
SUPABASE_POOLER_PORT=5432
SUPABASE_POOLER_USER=<pooler-user-from-dashboard-usually-postgres.project-ref>
```

then run:

```bash
RESET_POSTGRES=true python scripts/migrate_sqlite_to_postgres.py
```

Optional source DB override:

```bash
SQLITE_DB_PATH=db/professor_match_publications.sqlite
```

The script:

1. Creates SQLModel tables in Postgres.
2. Copies professors and publications.
3. Copies auth/user state tables if present.
4. Refreshes Postgres sequences.

## Matching behavior

- SQLite local mode uses FTS5.
- Postgres production mode uses a portable lexical shortlist first. This avoids needing custom Postgres extensions for the first free deployment.
- A later optimization can add Postgres `tsvector` or `pg_trgm` indexes.

## Smoke test after migration

Run the backend with `DATABASE_URL` set, then verify:

```txt
GET  /health
GET  /api/stats
GET  /api/professors?limit=3
POST /api/auth/register
PATCH /api/auth/state
POST /api/match
```
