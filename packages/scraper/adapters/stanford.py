from __future__ import annotations

from .base import BaseUniversityAdapter


class StanfordAdapter(BaseUniversityAdapter):
    def __init__(self) -> None:
        super().__init__(
            university="Stanford University",
            department="Computer Science",
            faculty_roster_url="https://www.cs.stanford.edu/people/faculty",
            adapter_name="stanford",
        )
