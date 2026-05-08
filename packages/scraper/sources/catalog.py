from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from ..core.types import SOURCE_PRIORITY, SourceType

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SEED_PATH = ROOT / "data" / "seeds" / "universities.csv"

ALLOWED_HOST_SUFFIXES = {
    "csail.mit.edu",
    "eecs.mit.edu",
    "www.eecs.mit.edu",
    "cs.stanford.edu",
    "csd.cmu.edu",
    "eecs.berkeley.edu",
    "www2.eecs.berkeley.edu",
    "cs.washington.edu",
    "cs.illinois.edu",
    "siebelschool.illinois.edu",
    "cc.gatech.edu",
    "cse.umich.edu",
    "cse.engin.umich.edu",
    "cs.cornell.edu",
    "cs.utexas.edu",
}

SOURCE_PRIORITY_MAP = {source.value: priority for source, priority in SOURCE_PRIORITY.items()}


@dataclass(slots=True)
class UniversitySeed:
    university: str
    department: str
    url: str
    priority: int

    @property
    def university_slug(self) -> str:
        from .identifiers import slugify

        return slugify(self.university)

    @property
    def department_slug(self) -> str:
        from .identifiers import slugify

        return slugify(self.department)

    @property
    def host(self) -> str:
        return urlparse(self.url).netloc.lower()


def load_university_seeds(path: Path | None = None) -> List[UniversitySeed]:
    seed_path = path or DEFAULT_SEED_PATH
    rows: List[UniversitySeed] = []
    with seed_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(
                UniversitySeed(
                    university=row["university"].strip(),
                    department=row["department"].strip(),
                    url=row["url"].strip(),
                    priority=int(row.get("priority", "0") or 0),
                )
            )
    return rows


def get_seed_by_university(university_name: str, path: Path | None = None) -> UniversitySeed:
    normalized = university_name.strip().lower()
    for seed in load_university_seeds(path):
        if seed.university.lower() == normalized:
            return seed
    raise KeyError(f"No seed found for university: {university_name}")


def allowed_domain(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in ALLOWED_HOST_SUFFIXES)


def source_type_for_url(url: str) -> str:
    return SourceType.UNIVERSITY_FACULTY_PAGE.value if allowed_domain(url) else "unknown"
