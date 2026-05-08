from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from apps.backend.app.db import PROJECT_ROOT
from apps.backend.app.models.auth import User

REQUESTS_PATH = PROJECT_ROOT / "data" / "qa" / "recommendation_requests.jsonl"


class RecommendationService:
    def __init__(self, path: Path | None = None):
        self.path = path or REQUESTS_PATH

    def create(self, user: User, payload: Any) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        record = {
            "id": now.strftime("%Y%m%d%H%M%S%f"),
            "user_id": user.id,
            "user_email": user.email,
            "university": payload.university,
            "department": payload.department,
            "faculty_page_url": payload.faculty_page_url,
            "status": "submitted",
            "created_at": now.isoformat(),
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        return record

    def list(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if isinstance(record, dict):
                    rows.append(record)
            except json.JSONDecodeError:
                rows.append({"id": "malformed", "status": "invalid", "error": "Could not parse recommendation request row"})
        rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return rows
