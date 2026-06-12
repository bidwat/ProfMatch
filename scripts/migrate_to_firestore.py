#!/usr/bin/env python3
"""One-time migration of ProfMatch data into Firebase Firestore.

Reads the legacy SQL database (Supabase Postgres via --database-url, or a
local SQLite file via --sqlite) and writes documents into Firestore using the
backend's document layer. Document ids and the per-collection counters are
preserved so existing frontend links keep working.

Usage:
  # Postgres (Supabase pooler URL, postgresql:// or postgresql+psycopg://)
  FIREBASE_SERVICE_ACCOUNT_JSON=... python scripts/migrate_to_firestore.py \
      --database-url "postgresql://user:pass@host:5432/postgres?sslmode=require"

  # Local SQLite seed
  FIREBASE_SERVICE_ACCOUNT_JSON=... python scripts/migrate_to_firestore.py \
      --sqlite db/professor_match_publications.sqlite

  # Dry run prints row counts without writing.
  python scripts/migrate_to_firestore.py --sqlite db/... --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Legacy SQL table -> Firestore collection
TABLE_COLLECTIONS = {
    "professor": "professors",
    "publication": "publications",
    "users": "users",
    "user_states": "user_states",
    "auth_sessions": "auth_sessions",
    "studentprofile": "student_profiles",
    "scan_jobs": "scan_jobs",
    "scan_tasks": "scan_tasks",
    "scan_results": "scan_results",
    "scan_logs": "scan_logs",
    "scraperun": "scrape_runs",
}

JSON_TEXT_FIELDS = {
    "extra", "input_payload", "settings", "result_summary", "source_urls",
    "professor_payload", "publications_payload", "qa_issues", "research_tags",
    "payload", "student_profile", "last_match_response", "saved_professor_ids",
    "tracker_rows",
}


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    doc = {}
    for key, value in row.items():
        if key in JSON_TEXT_FIELDS and isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
        doc[key] = value
    return doc


def _read_sqlite(path: Path, table: str) -> list[dict[str, Any]]:
    import sqlite3

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        return [_normalize_row(dict(row)) for row in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def _read_postgres(database_url: str, table: str) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url, row_factory=dict_row) as conn:
        try:
            rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
        except psycopg.errors.UndefinedTable:
            conn.rollback()
            return []
        return [_normalize_row(dict(row)) for row in rows]


def migrate(reader, *, dry_run: bool) -> None:
    if not dry_run:
        os.environ.setdefault("PROFMATCH_DB", "firestore")
    from apps.backend.app.db import FirestoreDatabase

    db = None if dry_run else FirestoreDatabase()
    for table, collection_name in TABLE_COLLECTIONS.items():
        rows = reader(table)
        print(f"{table} -> {collection_name}: {len(rows)} row(s)")
        if dry_run or not rows:
            continue
        collection = db.collection(collection_name)
        max_id = 0
        for row in rows:
            doc_id = row.get("id")
            if doc_id is None:
                continue
            collection.set(int(doc_id), row)
            max_id = max(max_id, int(doc_id))
        # Keep the id counter ahead of migrated documents.
        db._client.collection("counters").document(collection_name).set({"value": max_id})
        print(f"  wrote {len(rows)} doc(s), counter set to {max_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--database-url", help="Legacy Postgres URL (Supabase pooler)")
    source.add_argument("--sqlite", type=Path, help="Legacy SQLite database path")
    parser.add_argument("--dry-run", action="store_true", help="Print row counts without writing to Firestore")
    args = parser.parse_args()

    if args.sqlite:
        if not args.sqlite.exists():
            raise SystemExit(f"SQLite file not found: {args.sqlite}")
        reader = lambda table: _read_sqlite(args.sqlite, table)
    else:
        reader = lambda table: _read_postgres(args.database_url, table)

    if not args.dry_run and not (
        os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("FIRESTORE_EMULATOR_HOST")
    ):
        raise SystemExit("Set FIREBASE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS before migrating (or use --dry-run)")

    migrate(reader, dry_run=args.dry_run)
    print("Done.")


if __name__ == "__main__":
    main()
