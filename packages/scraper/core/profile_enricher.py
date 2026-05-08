from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from time import sleep
from typing import Optional
from urllib.parse import urljoin, urlparse

from .fetcher import SafeFetcher
from .models import ProfessorCandidate


@dataclass
class ProfileEnrichmentResult:
    title: Optional[str] = None
    research_text: Optional[str] = None
    email: Optional[str] = None
    homepage_url: Optional[str] = None
    image_url: Optional[str] = None
    bio: Optional[str] = None
    parser_used: str = "generic"
    success: bool = False
    error: Optional[str] = None


class ProfileEnricher:
    def __init__(self, fetcher: Optional[SafeFetcher] = None, delay_seconds: float = 1.0):
        self.fetcher = fetcher or SafeFetcher()
        self.delay_seconds = delay_seconds

    def enrich_candidate(self, candidate: ProfessorCandidate) -> ProfessorCandidate:
        if not candidate.faculty_profile_url:
            return candidate

        sleep(self.delay_seconds)  # conservative pacing

        try:
            fetch_result = self.fetcher.fetch(
                candidate.faculty_profile_url,
                run_id="enrich",
                university=candidate.university,
                department=candidate.department,
                adapter_name="profile",
                artifact_name="profile.html",
                source_type="faculty_profile",
            )
            if fetch_result.source_artifact.status_code != 200:
                candidate.extra["enrichment_error"] = f"HTTP {fetch_result.source_artifact.status_code}"
                return candidate

            enrichment = self.parse_profile_html(
                fetch_result.body_text,
                profile_url=candidate.faculty_profile_url,
                candidate_name=candidate.name,
                university=candidate.university,
            )

            # Apply profile enrichment first (acts as fallback for text fields).
            if enrichment.success:
                if enrichment.title and not candidate.title:
                    candidate.title = enrichment.title
                if enrichment.research_text and not candidate.research_text:
                    candidate.research_text = enrichment.research_text
                    candidate.extra["research_source"] = "university_profile"
                if enrichment.email and not candidate.email:
                    candidate.email = enrichment.email

                existing_homepage = (candidate.homepage_url or "").strip().lower()
                has_real_homepage = bool(
                    existing_homepage
                    and not existing_homepage.startswith("mailto:")
                    and not self._is_bad_homepage_url(existing_homepage)
                )
                if not has_real_homepage:
                    candidate.homepage_url = None
                if enrichment.homepage_url and not self._is_bad_homepage_url(enrichment.homepage_url):
                    candidate.homepage_url = enrichment.homepage_url

                candidate.extra["enriched"] = True
                candidate.extra["profile_parser"] = enrichment.parser_used
                if enrichment.image_url:
                    candidate.extra["image_url"] = enrichment.image_url
                    candidate.extra["image_source"] = "university_profile"
                if enrichment.bio:
                    candidate.extra["bio"] = enrichment.bio
                    candidate.extra["bio_source"] = "university_profile"
                    if not candidate.research_text:
                        candidate.research_text = enrichment.bio
                        candidate.extra["research_source"] = "university_profile"
            else:
                candidate.extra["enrichment_error"] = enrichment.error or "Parse failed"

            # Second hop: personal homepage. Homepage text should be preferred;
            # university profile text remains fallback.
            homepage_url = (candidate.homepage_url or "").strip()
            if self._is_valid_homepage_url(homepage_url):
                homepage_enrichment = self._enrich_from_homepage(
                    homepage_url=homepage_url,
                    candidate_name=candidate.name,
                    university=candidate.university,
                    department=candidate.department,
                )
                if homepage_enrichment is not None:
                    if homepage_enrichment.research_text:
                        candidate.research_text = homepage_enrichment.research_text
                        candidate.extra["research_source"] = "personal_homepage"
                    if homepage_enrichment.bio:
                        candidate.extra["bio"] = homepage_enrichment.bio
                        candidate.extra["bio_source"] = "personal_homepage"
                        if not candidate.research_text:
                            candidate.research_text = homepage_enrichment.bio
                            candidate.extra["research_source"] = "personal_homepage"
                    if homepage_enrichment.image_url:
                        current_image = (candidate.extra or {}).get("image_url")
                        if (not current_image) or self._is_placeholder_image(str(current_image)):
                            candidate.extra["image_url"] = homepage_enrichment.image_url
                            candidate.extra["image_source"] = "personal_homepage"
                    if homepage_enrichment.title and not candidate.title:
                        candidate.title = homepage_enrichment.title
                    if homepage_enrichment.email and not candidate.email:
                        candidate.email = homepage_enrichment.email
                    candidate.extra["homepage_parser"] = homepage_enrichment.parser_used
                    candidate.extra["homepage_enriched"] = homepage_enrichment.success

        except Exception as e:
            candidate.extra["enrichment_error"] = str(e)

        return candidate

    def parse_profile_html(
        self,
        html: str,
        *,
        profile_url: str,
        candidate_name: str,
        university: str,
    ) -> ProfileEnrichmentResult:
        try:
            from bs4 import BeautifulSoup  # type: ignore
        except Exception:
            BeautifulSoup = None

        result = ProfileEnrichmentResult(parser_used=self._parser_name(university, profile_url))

        if BeautifulSoup is None:
            return self._regex_fallback(html, result)

        soup = BeautifulSoup(html, "html.parser")
        self._remove_noise(soup)
        cfg = self._selectors_for(university, profile_url)

        # ---------- title ----------
        title_text = self._extract_first_text(soup, cfg["title_selectors"])
        title_text = self._sanitize_title(title_text, candidate_name)
        if self._is_good_title(title_text, candidate_name):
            result.title = title_text
        if not result.title:
            fallback_title = self._sanitize_title(self._extract_title_line(soup), candidate_name)
            if self._is_good_title(fallback_title, candidate_name):
                result.title = fallback_title

        # ---------- research ----------
        result.research_text = self._extract_research_text(
            soup,
            cfg["research_selectors"],
            cfg["research_heading_keywords"],
            profile_url,
        )
        result.research_text = self._sanitize_long_text(result.research_text, candidate_name)
        if result.research_text and self._looks_like_title_line(result.research_text):
            if not result.title and self._is_good_title(result.research_text, candidate_name):
                result.title = result.research_text
            result.research_text = None

        # ---------- bio ----------
        result.bio = self._extract_bio_text(
            soup,
            cfg["bio_selectors"],
            cfg["bio_heading_keywords"],
            profile_url,
        )
        result.bio = self._sanitize_long_text(result.bio, candidate_name)

        # ---------- image ----------
        image_url = self._extract_first_attr(soup, cfg["image_selectors"], "src")
        if image_url:
            result.image_url = urljoin(profile_url, image_url)
        else:
            og_image = self._meta_content(soup, property_name="og:image")
            if og_image:
                result.image_url = urljoin(profile_url, og_image)

        # ---------- email ----------
        email_link = soup.find("a", href=lambda h: h and str(h).startswith("mailto:"))
        if email_link:
            result.email = str(email_link.get("href")).replace("mailto:", "").strip()
        else:
            plain_email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", soup.get_text(" ", strip=True))
            if plain_email:
                result.email = plain_email.group(0)

        # ---------- homepage ----------
        profile_host = urlparse(profile_url).netloc.lower()
        homepage_candidates: list[tuple[int, str]] = []

        for link in soup.find_all("a", href=True):
            href = str(link.get("href"))
            text = self._clean_text(link.get_text(" ", strip=True)).lower()
            abs_href = urljoin(profile_url, href)
            if abs_href == profile_url or abs_href.startswith("mailto:"):
                continue
            if self._is_bad_homepage_url(abs_href):
                continue

            # Hard skips for known non-homepage links
            skip_tokens = ["google scholar", "dblp", "openalex", "semantic scholar", "linkedin", "twitter", "facebook", "youtube", "cv", "resume", "publication"]
            if any(tok in text for tok in skip_tokens):
                continue

            score = self._homepage_candidate_score(
                candidate_name=candidate_name,
                profile_host=profile_host,
                url=abs_href,
                anchor_text=text,
            )
            if score >= 2:
                homepage_candidates.append((score, abs_href))

        if homepage_candidates:
            homepage_candidates.sort(key=lambda x: (-x[0], len(x[1])))
            result.homepage_url = homepage_candidates[0][1]

        if result.research_text and result.bio and result.research_text == result.bio:
            # Keep one copy to avoid presenting duplicated blocks in UI.
            result.bio = None

        result.success = bool(result.title or result.research_text or result.email or result.bio or result.image_url)
        if not result.success:
            result.error = "No high-confidence profile fields found"
        return result

    def _regex_fallback(self, html: str, result: ProfileEnrichmentResult) -> ProfileEnrichmentResult:
        text = re.sub(r"<[^>]+>", " ", html)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()

        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        if email_match:
            result.email = email_match.group(0)

        result.success = bool(result.email)
        if not result.success:
            result.error = "No high-confidence profile fields found"
        return result

    def _selectors_for(self, university: str, profile_url: str) -> dict[str, list[str]]:
        common = {
            "title_selectors": [
                ".job-title",
                ".position",
                ".person-title",
                ".profile-title",
            ],
            "research_selectors": [
                ".research-interests",
                "#research-interests",
                ".research-summary",
                ".field--name-field-research-interests .field__item",
                ".field-name-field-research-interests .field-item",
            ],
            "bio_selectors": [
                ".biography",
                ".bio",
                "#bio",
                ".field--name-body .field__item",
                ".field-name-body .field-item",
            ],
            "image_selectors": [
                ".profile-image img",
                ".person-image img",
                ".field--name-user-picture img",
                ".field-name-field-person-photo img",
            ],
            "research_heading_keywords": ["research", "interests", "areas"],
            "bio_heading_keywords": ["biography", "bio", "about"],
        }

        if "stanford" in university.lower() or "stanford.edu" in profile_url:
            return {
                **common,
                "title_selectors": [
                    ".field-name-field-staff-title .field-item",
                    ".field--name-field-staff-title .field__item",
                    ".su-person-title",
                    ".person-position",
                ] + common["title_selectors"],
                "research_selectors": [
                    ".field-name-field-research-focus .field-item",
                    ".field--name-field-research-focus .field__item",
                ] + common["research_selectors"],
                "bio_selectors": [
                    ".field-name-field-short-bio .field-item",
                    ".field--name-field-short-bio .field__item",
                ] + common["bio_selectors"],
                "image_selectors": [
                    ".field-name-field-person-photo img",
                ] + common["image_selectors"],
            }

        if "carnegie mellon" in university.lower() or "cmu.edu" in profile_url:
            return {
                **common,
                "title_selectors": [
                    ".field--name-field-title .field__item",
                    ".field-name-field-title .field-item",
                    ".views-field-field-title",
                ] + common["title_selectors"],
                "research_selectors": [
                    ".field--name-field-research-areas .field__item",
                    ".field-name-field-research-areas .field-item",
                ] + common["research_selectors"],
                "image_selectors": [
                    ".views-field-user-picture img",
                    ".field--name-user-picture img",
                ] + common["image_selectors"],
            }

        if "berkeley" in university.lower() or "berkeley.edu" in profile_url:
            return {
                **common,
                "title_selectors": [
                    ".faculty-title",
                    ".position-title",
                    "h2 strong",
                    "h3 strong",
                ] + common["title_selectors"],
                "research_selectors": common["research_selectors"],
                "bio_selectors": common["bio_selectors"],
                "image_selectors": [
                    "img[alt*='portrait' i]",
                    "img[alt*='professor' i]",
                ] + common["image_selectors"],
                "research_heading_keywords": ["research", "interests", "areas", "projects"],
                "bio_heading_keywords": ["biography", "bio", "about", "overview"],
            }

        return common

    def _extract_first_text(self, soup, selectors: list[str]) -> Optional[str]:
        for sel in selectors:
            node = soup.select_one(sel)
            if not node:
                continue
            text = self._clean_text(node.get_text(" ", strip=True))
            if text:
                return text
        return None

    def _extract_first_attr(self, soup, selectors: list[str], attr: str) -> Optional[str]:
        for sel in selectors:
            node = soup.select_one(sel)
            if node and node.get(attr):
                return str(node.get(attr)).strip()
        return None

    def _meta_content(self, soup, *, property_name: str) -> Optional[str]:
        tag = soup.find("meta", attrs={"property": property_name})
        if tag and tag.get("content"):
            return str(tag.get("content")).strip()
        return None

    def _extract_research_text(self, soup, selector_candidates: list[str], heading_keywords: list[str], profile_url: str) -> Optional[str]:
        for sel in selector_candidates:
            nodes = soup.select(sel)
            if not nodes:
                continue
            text = self._clean_text(" ".join(n.get_text(" ", strip=True) for n in nodes[:8]))
            if self._is_good_research_text(text):
                return text

        section_text = self._extract_text_from_heading_sections(soup, heading_keywords)
        if self._is_good_research_text(section_text):
            return section_text

        # fallback: meta description if not generic
        desc = self._meta_content(soup, property_name="og:description") or self._meta_description_by_name(soup)
        if self._is_good_research_text(desc):
            return desc

        # fallback: first meaningful paragraph in main/article with research terms
        paragraph = self._best_main_paragraph(soup, require_research_keywords=True)
        if self._is_good_research_text(paragraph):
            return paragraph
        return None

    def _extract_bio_text(self, soup, selector_candidates: list[str], heading_keywords: list[str], profile_url: str) -> Optional[str]:
        for sel in selector_candidates:
            nodes = soup.select(sel)
            if not nodes:
                continue
            text = self._clean_text(" ".join(n.get_text(" ", strip=True) for n in nodes[:10]))
            if self._is_good_bio(text):
                return text

        section_text = self._extract_text_from_heading_sections(soup, heading_keywords)
        if self._is_good_bio(section_text):
            return section_text

        paragraph = self._best_main_paragraph(soup, require_research_keywords=False)
        if self._is_good_bio(paragraph):
            return paragraph
        return None

    def _extract_text_from_heading_sections(self, soup, keywords: list[str]) -> Optional[str]:
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5"])
        for heading in headings:
            heading_text = self._clean_text(heading.get_text(" ", strip=True)).lower()
            if not any(k in heading_text for k in keywords):
                continue
            texts: list[str] = []
            for sib in heading.find_next_siblings():
                if getattr(sib, "name", None) in {"h1", "h2", "h3", "h4", "h5"}:
                    break
                t = self._clean_text(sib.get_text(" ", strip=True))
                if t:
                    texts.append(t)
                if len(" ".join(texts)) > 1400:
                    break
            candidate = self._clean_text(" ".join(texts))
            if candidate:
                return candidate
        return None

    def _best_main_paragraph(self, soup, *, require_research_keywords: bool) -> Optional[str]:
        containers = [soup.select_one("main"), soup.select_one("article"), soup.select_one(".content"), soup]
        keywords = ["research", "interest", "machine learning", "systems", "theory", "vision", "nlp"]
        for container in containers:
            if not container:
                continue
            for p in container.find_all("p")[:20]:
                text = self._clean_text(p.get_text(" ", strip=True))
                if len(text) < 80:
                    continue
                lowered = text.lower()
                if require_research_keywords and not any(k in lowered for k in keywords):
                    continue
                if self._looks_generic(lowered):
                    continue
                return text
        return None

    def _meta_description_by_name(self, soup) -> Optional[str]:
        tag = soup.find("meta", attrs={"name": "description"})
        if tag and tag.get("content"):
            return str(tag.get("content")).strip()
        return None

    def _remove_noise(self, soup) -> None:
        for tag in soup.select("script,style,noscript,header,footer,nav,.menu,.breadcrumb,.site-footer"):
            tag.decompose()

    @staticmethod
    def _clean_text(text: Optional[str]) -> str:
        return " ".join((text or "").split()).strip()

    def _is_good_title(self, text: Optional[str], candidate_name: str) -> bool:
        if not text:
            return False
        t = text.lower()
        name = (candidate_name or "").lower().strip()
        if name and t == name:
            return False
        if "faculty home page" in t:
            return False
        if len(t) > 120:
            return False
        return any(tok in t for tok in ["professor", "lecturer", "research", "chair", "assistant", "associate", "adjunct", "emeritus"])

    def _is_good_research_text(self, text: Optional[str]) -> bool:
        if not text:
            return False
        t = text.lower().strip()
        if len(t) < 90:
            return False
        if self._looks_generic(t):
            return False
        if self._looks_like_title_line(t):
            return False
        contact_noise = [" tel", "fax", "office", "soda hall", "cory hall", "sutardja", "@berkeley.edu"]
        if sum(1 for n in contact_noise if n in t) >= 2 and len(t) < 240:
            return False
        return True

    def _is_good_bio(self, text: Optional[str]) -> bool:
        if not text:
            return False
        t = text.lower().strip()
        if len(t) < 120:
            return False
        if self._looks_generic(t):
            return False
        return True

    def _looks_generic(self, lowered_text: str) -> bool:
        generic_phrases = [
            "research opportunities",
            "consistently ranked among the highest programs",
            "department of electrical engineering and computer sciences",
            "computer science department",
            "admissions",
            "apply now",
            "events",
            "news",
            "privacy policy",
            "all rights reserved",
            "directory submenu",
        ]
        return any(p in lowered_text for p in generic_phrases)

    def _looks_like_title_line(self, text: str) -> bool:
        t = text.lower().strip()
        if len(t) > 240:
            return False
        title_markers = [
            "assistant professor",
            "associate professor",
            "professor of",
            "teaching professor",
            "adjunct",
            "emeritus",
            "chair",
        ]
        return any(m in t for m in title_markers)

    def _sanitize_title(self, text: Optional[str], candidate_name: str) -> Optional[str]:
        if not text:
            return None
        cleaned = self._clean_text(text)
        cleaned = re.sub(r"^main content start\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"^larger photo\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"^below the line\s*", "", cleaned, flags=re.I)
        if candidate_name:
            name_pat = re.escape(self._clean_text(candidate_name))
            cleaned = re.sub(rf"^{name_pat}\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\b(contact|website|publications?)\b.*$", "", cleaned, flags=re.I)
        cleaned = self._clean_text(cleaned)
        return cleaned or None

    def _sanitize_long_text(self, text: Optional[str], candidate_name: str) -> Optional[str]:
        if not text:
            return None
        cleaned = self._clean_text(text)
        cleaned = re.sub(r"^main content start\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"^larger photo\s*", "", cleaned, flags=re.I)
        if candidate_name:
            name_pat = re.escape(self._clean_text(candidate_name))
            cleaned = re.sub(rf"^{name_pat}\s*", "", cleaned, flags=re.I)

        # Drop obvious contact/address lead-ins common on directory-style pages.
        cleaned = re.sub(r"^\s*(\d{2,5}[A-Za-z\s,-]+hall\s+)?(tel[:\s(\d\-)]+)?", "", cleaned, flags=re.I)
        cleaned = re.sub(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\s+", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\b(publications?|website|contact|email for appt|personal homepage|dissertations?)\b\s*", " ", cleaned, flags=re.I)

        # Cut off common trailing education tails, but do not split on inline "Ph.D." mentions.
        cleaned = re.split(r"\b(\d{4}\s*,\s*(?:Ph\.?D\.?|M\.?S\.?|B\.?S\.?))\b", cleaned, maxsplit=1, flags=re.I)[0]
        cleaned = re.split(r"\b(Selected Publications?|Curriculum Vitae|CV)\b", cleaned, maxsplit=1, flags=re.I)[0]

        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;")

        # Keep payload concise to avoid giant mixed blocks.
        if len(cleaned) > 1400:
            cleaned = cleaned[:1400].rsplit(" ", 1)[0].strip(" ,.;")
        return cleaned or None

    def _extract_title_line(self, soup) -> Optional[str]:
        containers = [soup.select_one("main"), soup.select_one("article"), soup.select_one(".content"), soup]
        for container in containers:
            if not container:
                continue
            for node in container.find_all(["p", "li", "div"])[:30]:
                text = self._clean_text(node.get_text(" ", strip=True))
                if self._looks_like_title_line(text):
                    return text
        return None

    def _is_valid_homepage_url(self, value: str) -> bool:
        if not value:
            return False
        v = value.strip().lower()
        if v.startswith("mailto:"):
            return False
        if self._is_bad_homepage_url(v):
            return False
        return v.startswith("http://") or v.startswith("https://")

    def _is_bad_homepage_url(self, value: str) -> bool:
        parsed = urlparse(value)
        path = (parsed.path or "").lower()
        if any(path.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf"]):
            return True
        return any(
            bad in path
            for bad in ["/research/areas/", "/publications", "/pubs", "/news", "/events", "/photos/"]
        )

    def _is_placeholder_image(self, url: str) -> bool:
        lowered = (url or "").lower()
        return any(token in lowered for token in ["default-profile-image", "placeholder", "no-photo", "avatar-default"])

    def _homepage_candidate_score(self, *, candidate_name: str, profile_host: str, url: str, anchor_text: str) -> int:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = (parsed.path or "").lower()
        text = (anchor_text or "").lower()

        score = 0
        if any(k in text for k in ["personal website", "homepage", "home page", "my site", "website"]):
            score += 6
        if host and host != profile_host:
            score += 1
        if "~" in path or "/user/" in path:
            score += 2

        parts = [p.lower() for p in re.split(r"\s+", (candidate_name or "").strip()) if p]
        if parts:
            last = parts[-1]
            if last and last in (host + " " + path):
                score += 2
            first = parts[0]
            if first and first in (host + " " + path):
                score += 1

        if any(bad in path for bad in ["award", "news", "event", "press", "blog", "article", "photo", "gallery"]):
            score -= 4
        if len(path) <= 1:
            score -= 1
        return score

    def _enrich_from_homepage(self, *, homepage_url: str, candidate_name: str, university: str, department: str) -> Optional[ProfileEnrichmentResult]:
        try:
            sleep(max(0.4, self.delay_seconds * 0.6))
            fetch_result = self.fetcher.fetch(
                homepage_url,
                run_id="enrich-homepage",
                university=university,
                department=department,
                adapter_name="homepage",
                artifact_name="homepage.html",
                source_type="professor_homepage",
            )
            if fetch_result.source_artifact.status_code != 200:
                return None

            try:
                from bs4 import BeautifulSoup  # type: ignore
            except Exception:
                return None

            soup = BeautifulSoup(fetch_result.body_text, "html.parser")
            self._remove_noise(soup)

            result = ProfileEnrichmentResult(parser_used="personal-homepage")

            # Generic title extraction from personal pages.
            h_title = self._extract_first_text(soup, [".title", ".position", "h2", "h3"])
            h_title = self._sanitize_title(h_title, candidate_name)
            if self._is_good_title(h_title, candidate_name):
                result.title = h_title

            # Prefer first meaningful paragraph for research/bio.
            research = self._best_main_paragraph(soup, require_research_keywords=True)
            research = self._sanitize_long_text(research, candidate_name)
            if self._is_good_research_text(research):
                result.research_text = research

            bio = self._extract_text_from_heading_sections(soup, ["bio", "biography", "about", "about me"])
            if not bio:
                bio = self._best_main_paragraph(soup, require_research_keywords=False)
            bio = self._sanitize_long_text(bio, candidate_name)
            if self._is_good_bio(bio) and bio != result.research_text:
                result.bio = bio

            image_url = self._extract_first_attr(
                soup,
                ["img[alt*='profile' i]", "img[alt*='portrait' i]", "article img", "main img"],
                "src",
            )
            if image_url:
                result.image_url = urljoin(homepage_url, image_url)
            else:
                og_image = self._meta_content(soup, property_name="og:image")
                if og_image:
                    result.image_url = urljoin(homepage_url, og_image)

            email_link = soup.find("a", href=lambda h: h and str(h).startswith("mailto:"))
            if email_link:
                result.email = str(email_link.get("href")).replace("mailto:", "").strip()

            result.success = bool(result.title or result.research_text or result.bio or result.image_url or result.email)
            return result
        except Exception:
            return None

    def _parser_name(self, university: str, profile_url: str) -> str:
        u = university.lower()
        p = profile_url.lower()
        if "stanford" in u or "stanford.edu" in p:
            return "stanford-specific"
        if "carnegie mellon" in u or "cmu.edu" in p:
            return "cmu-specific"
        if "berkeley" in u or "berkeley.edu" in p:
            return "berkeley-specific"
        return "generic"
