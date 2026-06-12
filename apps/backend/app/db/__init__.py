"""Document database layer for ProfMatch.

Production uses Firebase Firestore (firebase-admin). Tests and local
development without Firebase credentials use an in-memory store with the
same interface. Select with env vars:

- FIREBASE_SERVICE_ACCOUNT_JSON: inline service-account JSON (preferred for
  DigitalOcean/Vercel style env config)
- GOOGLE_APPLICATION_CREDENTIALS: path to a service-account JSON file
- FIRESTORE_EMULATOR_HOST (+ FIREBASE_PROJECT_ID): local emulator
- PROFMATCH_DB=memory: force the in-memory store (tests/local)

Documents keep small auto-incrementing integer ids (allocated through a
`counters` document) so the existing REST contract and frontend types are
unchanged. Write volume is admin-driven and low, so a transactional counter
is acceptable here.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Iterator, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def is_production_mode() -> bool:
    return os.environ.get("APP_ENV", "").strip().lower() in {"prod", "production"}


def _utc_to_plain(value: Any) -> Any:
    """Firestore returns tz-aware datetimes; the API layer expects naive UTC."""
    from datetime import datetime, timezone

    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    if isinstance(value, dict):
        return {k: _utc_to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_utc_to_plain(v) for v in value]
    return value


class Collection:
    """Minimal document collection interface shared by both backends."""

    def get(self, doc_id: int | str) -> Optional[dict]:
        raise NotImplementedError

    def add(self, data: dict) -> int:
        raise NotImplementedError

    def set(self, doc_id: int | str, data: dict) -> None:
        raise NotImplementedError

    def update(self, doc_id: int | str, patch: dict) -> Optional[dict]:
        raise NotImplementedError

    def delete(self, doc_id: int | str) -> None:
        raise NotImplementedError

    def all(self) -> list[dict]:
        raise NotImplementedError

    def find(self, **equals: Any) -> list[dict]:
        return [doc for doc in self.all() if all(doc.get(k) == v for k, v in equals.items())]

    def find_one(self, **equals: Any) -> Optional[dict]:
        for doc in self.all():
            if all(doc.get(k) == v for k, v in equals.items()):
                return doc
        return None

    def count(self, **equals: Any) -> int:
        return len(self.find(**equals)) if equals else len(self.all())


class Database:
    def collection(self, name: str) -> Collection:
        raise NotImplementedError

    def reset(self) -> None:
        """Drop all data. Only supported by the in-memory store (tests)."""
        raise NotImplementedError("reset() is only available on MemoryDatabase")


# ---------------------------------------------------------------------------
# In-memory backend (tests / local dev without credentials)
# ---------------------------------------------------------------------------


class MemoryCollection(Collection):
    def __init__(self) -> None:
        self._docs: dict[int, dict] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    @staticmethod
    def _key(doc_id: int | str) -> int:
        return int(doc_id)

    def get(self, doc_id: int | str) -> Optional[dict]:
        doc = self._docs.get(self._key(doc_id))
        return dict(doc) if doc else None

    def add(self, data: dict) -> int:
        with self._lock:
            doc_id = self._next_id
            self._next_id += 1
            self._docs[doc_id] = {**data, "id": doc_id}
        return doc_id

    def set(self, doc_id: int | str, data: dict) -> None:
        key = self._key(doc_id)
        with self._lock:
            self._next_id = max(self._next_id, key + 1)
            self._docs[key] = {**data, "id": key}

    def update(self, doc_id: int | str, patch: dict) -> Optional[dict]:
        key = self._key(doc_id)
        with self._lock:
            doc = self._docs.get(key)
            if doc is None:
                return None
            doc.update(patch)
            doc["id"] = key
            return dict(doc)

    def delete(self, doc_id: int | str) -> None:
        self._docs.pop(self._key(doc_id), None)

    def all(self) -> list[dict]:
        return [dict(doc) for doc in self._docs.values()]


class MemoryDatabase(Database):
    def __init__(self) -> None:
        self._collections: dict[str, MemoryCollection] = {}

    def collection(self, name: str) -> Collection:
        if name not in self._collections:
            self._collections[name] = MemoryCollection()
        return self._collections[name]

    def reset(self) -> None:
        self._collections.clear()


# ---------------------------------------------------------------------------
# Firestore backend
# ---------------------------------------------------------------------------


class FirestoreCollection(Collection):
    def __init__(self, client: Any, name: str):
        self._client = client
        self._ref = client.collection(name)
        self._name = name

    def get(self, doc_id: int | str) -> Optional[dict]:
        snap = self._ref.document(str(doc_id)).get()
        if not snap.exists:
            return None
        return self._to_doc(snap)

    def add(self, data: dict) -> int:
        doc_id = self._allocate_id()
        payload = {**data, "id": doc_id}
        self._ref.document(str(doc_id)).set(payload)
        return doc_id

    def set(self, doc_id: int | str, data: dict) -> None:
        self._ref.document(str(doc_id)).set({**data, "id": int(doc_id)})

    def update(self, doc_id: int | str, patch: dict) -> Optional[dict]:
        ref = self._ref.document(str(doc_id))
        snap = ref.get()
        if not snap.exists:
            return None
        ref.update(patch)
        return self._to_doc(ref.get())

    def delete(self, doc_id: int | str) -> None:
        self._ref.document(str(doc_id)).delete()

    def all(self) -> list[dict]:
        return [self._to_doc(snap) for snap in self._ref.stream()]

    def find(self, **equals: Any) -> list[dict]:
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self._ref
        for key, value in equals.items():
            query = query.where(filter=FieldFilter(key, "==", value))
        return [self._to_doc(snap) for snap in query.stream()]

    def find_one(self, **equals: Any) -> Optional[dict]:
        results = self.find(**equals)
        return results[0] if results else None

    @staticmethod
    def _to_doc(snap: Any) -> dict:
        doc = _utc_to_plain(snap.to_dict() or {})
        doc.setdefault("id", int(snap.id) if str(snap.id).isdigit() else snap.id)
        return doc

    def _allocate_id(self) -> int:
        from google.cloud import firestore as gcf

        counter_ref = self._client.collection("counters").document(self._name)

        @gcf.transactional
        def _incr(transaction: Any) -> int:
            snap = counter_ref.get(transaction=transaction)
            current = int((snap.to_dict() or {}).get("value", 0)) if snap.exists else 0
            transaction.set(counter_ref, {"value": current + 1})
            return current + 1

        return _incr(self._client.transaction())


class FirestoreDatabase(Database):
    def __init__(self) -> None:
        self._client = _init_firestore_client()
        self._collections: dict[str, FirestoreCollection] = {}

    def collection(self, name: str) -> Collection:
        if name not in self._collections:
            self._collections[name] = FirestoreCollection(self._client, name)
        return self._collections[name]


def _init_firestore_client() -> Any:
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        inline_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
        options = {}
        project_id = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
        if project_id:
            options["projectId"] = project_id
        if inline_json:
            cred = credentials.Certificate(json.loads(inline_json))
            firebase_admin.initialize_app(cred, options or None)
        else:
            # Falls back to GOOGLE_APPLICATION_CREDENTIALS or emulator/ADC.
            firebase_admin.initialize_app(options=options or None)
    return firestore.client()


# ---------------------------------------------------------------------------
# Store selection
# ---------------------------------------------------------------------------

_db_instance: Optional[Database] = None
_db_lock = threading.Lock()


def _firebase_configured() -> bool:
    return bool(
        os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        or os.environ.get("FIRESTORE_EMULATOR_HOST", "").strip()
    )


def _create_database() -> Database:
    forced = os.environ.get("PROFMATCH_DB", "").strip().lower()
    if forced == "memory":
        if is_production_mode():
            raise RuntimeError("APP_ENV=production cannot run with PROFMATCH_DB=memory")
        return MemoryDatabase()
    if forced == "firestore" or _firebase_configured():
        return FirestoreDatabase()
    if is_production_mode():
        raise RuntimeError(
            "APP_ENV=production requires Firebase credentials "
            "(FIREBASE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS)"
        )
    return MemoryDatabase()


def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = _create_database()
    return _db_instance


def set_db(database: Optional[Database]) -> None:
    """Override the active database (tests)."""
    global _db_instance
    _db_instance = database


def get_session() -> Iterator[Database]:
    """FastAPI dependency. Name kept from the SQLModel era to minimize churn."""
    yield get_db()


def database_kind() -> str:
    db = get_db()
    return "firestore" if isinstance(db, FirestoreDatabase) else "memory"
