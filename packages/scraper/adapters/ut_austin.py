from __future__ import annotations

from .base import BaseUniversityAdapter


class UTAustinAdapter(BaseUniversityAdapter):
    def __init__(self) -> None:
        super().__init__(
            university="University of Texas at Austin",
            department="Computer Science",
            faculty_roster_url="https://www.cs.utexas.edu/people",
            adapter_name="utaustin",
        )
