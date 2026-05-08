from __future__ import annotations

from .base import BaseUniversityAdapter


class BerkeleyAdapter(BaseUniversityAdapter):
    def __init__(self) -> None:
        super().__init__(
            university="UC Berkeley",
            department="Electrical Engineering and Computer Sciences",
            faculty_roster_url="https://www2.eecs.berkeley.edu/Faculty/Lists/CS/faculty.html",
            adapter_name="berkeley",
        )
