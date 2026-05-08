from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin, urlparse, urlunparse


WHITESPACE_RE = re.compile(r"\s+")
NON_WORD_RE = re.compile(r"[^a-z0-9\s-]")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("&", " and ")
    value = NON_WORD_RE.sub(" ", value)
    value = WHITESPACE_RE.sub(" ", value)
    return value.strip().replace(" ", "-")


def normalize_name(name: str) -> str:
    cleaned = NON_WORD_RE.sub(" ", name.lower())
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    if "," in name:
        parts = [p.strip().lower() for p in name.split(",", 1)]
        return " ".join([parts[0], parts[1]])
    tokens = [token for token in cleaned.split(" ") if token]
    if len(tokens) >= 2:
        return " ".join(reversed(tokens))
    return cleaned


def canonicalize_url(url: str, base_url: str | None = None) -> str:
    if base_url:
        url = urljoin(base_url, url)
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = re.sub(r"/+$", "", parsed.path or "")
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def guess_university_slug(university: str) -> str:
    return slugify(university)


def guess_department_slug(department: str) -> str:
    return slugify(department)


def person_slug(name: str) -> str:
    return slugify(name)
