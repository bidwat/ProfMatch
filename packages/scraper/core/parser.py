from __future__ import annotations

import re
from html import unescape
from typing import List, Optional

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    BeautifulSoup = None

from .models import ProfessorCandidate, PublicationCandidate
from ..sources.identifiers import canonicalize_url

CARD_CLASS_RE = re.compile(
    r'(<(?P<tag>li|article|div)[^>]*(?:data-faculty-card|faculty-card|faculty-entry|person-card|profile-card)[^>]*>.*?</(?P=tag)>)',
    re.I | re.S,
)
TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
ANCHOR_RE = re.compile(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
ATTR_RE = re.compile(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*["\']([^"\']*)["\']')
TEXT_LINE_RE = re.compile(r"\s+")


def _strip_tags(text: str) -> str:
    text = TAG_RE.sub(" ", text)
    text = unescape(text)
    text = TEXT_LINE_RE.sub(" ", text)
    return text.strip()


def _attrs_from_html(fragment: str) -> dict[str, str]:
    return {key.lower(): value for key, value in ATTR_RE.findall(fragment)}


def _best_text_from_block(block: str) -> str:
    return _strip_tags(block)


def _first_anchor(block: str) -> tuple[Optional[str], Optional[str]]:
    match = ANCHOR_RE.search(block)
    if not match:
        return None, None
    return canonicalize_url(match.group(1).strip(), None), _strip_tags(match.group(2))


def _class_text(block: str, class_name: str) -> Optional[str]:
    pattern = re.compile(rf'<[^>]*class=["\"][^"\"]*?{re.escape(class_name)}[^"\"]*["\"][^>]*>(.*?)</[^>]+>', re.I | re.S)
    match = pattern.search(block)
    if not match:
        return None
    text = _strip_tags(match.group(1))
    return text or None


class FacultyRosterParser:
    def parse_roster_html(
        self,
        html: str,
        *,
        source_url: str,
        university: str,
        department: str,
        source_type: str = "university_faculty_page",
    ) -> List[ProfessorCandidate]:
        candidates: List[ProfessorCandidate] = []
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            elements = []
            selectors = [
                "[data-faculty-card]",
                ".faculty-card",
                ".faculty-entry",
                ".person-card",
                ".profile-card",
                ".cc-image-list__item",
                ".views-row",
                "article",
                "tr",
                "li",
            ]
            seen = set()
            for selector in selectors:
                for element in soup.select(selector):
                    marker = str(element)
                    if marker in seen:
                        continue
                    seen.add(marker)
                    if self._looks_like_faculty_card(element):
                        elements.append(str(element))
            if not elements:
                elements = [str(tag) for tag in soup.find_all(["article", "li", "div"])]
            blocks = elements
        else:
            blocks = [match.group(1) for match in CARD_CLASS_RE.finditer(html)]
            if not blocks and "faculty" in html.lower():
                blocks = [html]

        for block in blocks:
            candidate = self._parse_card_block(block, source_url=source_url, university=university, department=department, source_type=source_type)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def _looks_like_faculty_card(self, element) -> bool:  # pragma: no cover - bs4 path optional
        text = element.get_text(" ", strip=True).lower()
        classes = " ".join(element.get("class", [])).lower()
        attrs = " ".join(f"{k}={v}" for k, v in element.attrs.items()).lower()
        markers = ["faculty", "professor", "assistant professor", "associate professor"]
        return any(marker in text or marker in classes or marker in attrs for marker in markers)

    def _parse_card_block(
        self,
        block: str,
        *,
        source_url: str,
        university: str,
        department: str,
        source_type: str,
    ) -> Optional[ProfessorCandidate]:
        if BeautifulSoup is not None and block.lstrip().startswith("<"):
            soup = BeautifulSoup(block, "html.parser")
            node = soup.find(True)
            if node is None:
                return None
            attrs = {k.lower(): v for k, v in node.attrs.items()}
            text = node.get_text(" ", strip=True)
            links = node.find_all("a", href=True)
            name = self._extract_name_from_node(node)
            faculty_profile_url = canonicalize_url(links[0]["href"], source_url) if links else source_url
            homepage_url = None
            for a in links[1:]:
                href = canonicalize_url(a["href"], source_url)
                if href and href != faculty_profile_url:
                    homepage_url = href
                    break
            title = attrs.get("data-title") or self._text_by_class(node, ["title", "position", "rank"])
            email = attrs.get("data-email") or self._extract_email(text)
            research_text = attrs.get("data-research-text") or self._text_by_class(node, ["research", "interests", "areas"])
            confidence = self._extract_confidence(attrs, text, name)
            if not name and not faculty_profile_url:
                return None
            field_sources = {
                "name": [{"source_type": source_type, "url": source_url, "confidence": confidence}],
                "faculty_profile_url": [{"source_type": source_type, "url": source_url, "confidence": 1.0}],
            }
            if title:
                field_sources["title"] = [{"source_type": source_type, "url": source_url, "confidence": confidence}]
            if email:
                field_sources["email"] = [{"source_type": source_type, "url": source_url, "confidence": confidence}]
            if homepage_url:
                field_sources["homepage_url"] = [{"source_type": source_type, "url": source_url, "confidence": confidence}]
            if research_text:
                field_sources["research_text"] = [{"source_type": source_type, "url": source_url, "confidence": confidence}]
            return ProfessorCandidate(
                name=name or _strip_tags(text)[:80],
                university=university,
                department=department,
                faculty_profile_url=faculty_profile_url,
                source_url=source_url,
                source_type=source_type,
                source_confidence=confidence,
                title=title,
                email=email,
                homepage_url=homepage_url,
                research_text=research_text,
                raw_text=text,
                field_sources=field_sources,
            )

        attrs = _attrs_from_html(block)
        text = _best_text_from_block(block)
        links = HREF_RE.findall(block)
        faculty_profile_raw = attrs.get("data-faculty-profile-url") or attrs.get("data-profile-url") or (links[0] if links else source_url)
        faculty_profile_url = canonicalize_url(faculty_profile_raw, source_url)
        homepage_url = attrs.get("data-homepage-url")
        if homepage_url:
            homepage_url = canonicalize_url(homepage_url, source_url)
        _first_href, first_anchor_text = _first_anchor(block)
        name = attrs.get("data-name") or first_anchor_text or self._extract_name_from_text(text)
        title = attrs.get("data-title") or _class_text(block, "title") or self._value_after_label(text, ["title", "position", "rank"])
        email = attrs.get("data-email") or self._extract_email(text)
        research_text = attrs.get("data-research-text") or _class_text(block, "research") or self._value_after_label(text, ["research", "interests", "areas"])
        confidence = self._extract_confidence(attrs, text, name)
        if not name and not attrs.get("data-faculty-profile-url") and not links:
            return None
        if not homepage_url and len(links) > 1:
            homepage_url = canonicalize_url(links[1], source_url)
            if homepage_url == faculty_profile_url and len(links) > 2:
                homepage_url = canonicalize_url(links[2], source_url)
        field_sources = {
            "name": [{"source_type": source_type, "url": source_url, "confidence": confidence}],
            "faculty_profile_url": [{"source_type": source_type, "url": source_url, "confidence": 1.0}],
        }
        if title:
            field_sources["title"] = [{"source_type": source_type, "url": source_url, "confidence": confidence}]
        if email:
            field_sources["email"] = [{"source_type": source_type, "url": source_url, "confidence": confidence}]
        if homepage_url:
            field_sources["homepage_url"] = [{"source_type": source_type, "url": source_url, "confidence": confidence}]
        if research_text:
            field_sources["research_text"] = [{"source_type": source_type, "url": source_url, "confidence": confidence}]
        return ProfessorCandidate(
            name=name or self._first_phrase(text),
            university=university,
            department=department,
            faculty_profile_url=faculty_profile_url,
            source_url=source_url,
            source_type=source_type,
            source_confidence=confidence,
            title=title,
            email=email,
            homepage_url=homepage_url,
            research_text=research_text,
            raw_text=text,
            field_sources=field_sources,
        )

    def _extract_name_from_node(self, node) -> Optional[str]:  # pragma: no cover - bs4 path optional
        for selector in [".name", ".faculty-name", "h2", "h3", "h4", "a"]:
            found = node.select_one(selector)
            if found:
                text = found.get_text(" ", strip=True)
                if text:
                    return text
        return None

    def _text_by_class(self, node, names: List[str]) -> Optional[str]:  # pragma: no cover - bs4 path optional
        for name in names:
            found = node.select_one(f".{name}")
            if found:
                text = found.get_text(" ", strip=True)
                if text:
                    return text
        return None

    def _extract_email(self, text: str) -> Optional[str]:
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        return match.group(0) if match else None

    def _extract_name_from_text(self, text: str) -> Optional[str]:
        if not text:
            return None
        text = text.strip()
        match = re.match(r"^([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){1,4})", text)
        return match.group(1).strip() if match else None

    def _value_after_label(self, text: str, labels: List[str]) -> Optional[str]:
        lowered = text.lower()
        for label in labels:
            pattern = rf"{label}\s*[:\-]\s*([^;|\n]+)"
            match = re.search(pattern, lowered, re.I)
            if match:
                return match.group(1).strip().title()
        return None

    def _first_phrase(self, text: str) -> str:
        return text.split(".")[0].split("|")[0].strip()

    def _extract_confidence(self, attrs: dict[str, str], text: str, name: Optional[str]) -> float:
        for key in ("data-confidence", "data-source-confidence"):
            if key in attrs:
                try:
                    return max(0.0, min(1.0, float(attrs[key])))
                except ValueError:
                    pass
        if name and attrs.get("data-faculty-profile-url"):
            return 0.88
        if name:
            return 0.72
        return 0.5


class ProfessorSiteParser:
    def parse_publications(self, html: str, *, source_url: str, source_author_id: str, source: str) -> List[PublicationCandidate]:
        publications: List[PublicationCandidate] = []
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.select('a[href]'):
                href = canonicalize_url(link.get('href', ''), source_url)
                text = link.get_text(" ", strip=True)
                if not text:
                    continue
                if any(marker in href.lower() for marker in ["doi.org", "dblp", "openalex", "semanticscholar", "arxiv", "acm"]):
                    publications.append(
                        PublicationCandidate(
                            title=text,
                            year=0,
                            venue="",
                            url=href,
                            source=source,
                            source_author_id=source_author_id,
                            match_confidence=0.5,
                            source_provenance={"url": [{"source_type": source, "url": source_url, "confidence": 0.5}]},
                        )
                    )
        return publications
