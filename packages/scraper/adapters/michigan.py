from __future__ import annotations

from .base import BaseUniversityAdapter


class MichiganAdapter(BaseUniversityAdapter):
    def __init__(self) -> None:
        super().__init__(
            university="University of Michigan",
            department="Computer Science and Engineering",
            faculty_roster_url="https://cse.engin.umich.edu/people/faculty/",
            adapter_name="michigan",
        )
