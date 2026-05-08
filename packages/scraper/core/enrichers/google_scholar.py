from __future__ import annotations

import re
from typing import Optional


class GoogleScholarLinkExtractor:
    profile_url_pattern = re.compile(r"https?://scholar\.google\.[^\s\"'<>]+", re.I)

    def extract_profile_url(self, text: str) -> Optional[str]:
        match = self.profile_url_pattern.search(text)
        return match.group(0) if match else None
