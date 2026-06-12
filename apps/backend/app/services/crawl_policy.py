"""Crawler policy helpers (spec §25.1).

The crawler must be identifiable so site owners can reach us for
corrections or takedowns. Override with CRAWLER_USER_AGENT; keep the
contact pointer accurate in docs/policies/crawler-policy.md.
"""

import os

DEFAULT_CRAWLER_USER_AGENT = (
    "UnivyaBot/1.0 (+https://prof-match-chi.vercel.app/crawler-policy; "
    "research-advisor discovery; contact: bidwatcs@gmail.com)"
)


def crawler_user_agent() -> str:
    return os.environ.get("CRAWLER_USER_AGENT", "").strip() or DEFAULT_CRAWLER_USER_AGENT
