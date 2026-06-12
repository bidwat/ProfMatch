"""Shared base for document models stored in Firestore/memory collections."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DocModel(BaseModel):
    """A document with an integer id. Unknown fields are ignored on load so
    older documents with extra keys keep deserializing."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    id: Optional[int] = None

    def to_doc(self) -> dict:
        doc = self.model_dump()
        if doc.get("id") is None:
            doc.pop("id", None)
        return doc

    @classmethod
    def from_doc(cls, doc: dict):
        return cls(**doc)
