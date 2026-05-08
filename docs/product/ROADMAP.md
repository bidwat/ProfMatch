# Product Roadmap — Next Major Improvements

## Roadmap Decision

Professor Match should finish and QA the local MVP before expanding into production operation. The next major improvements are prioritized as: (1) local MVP hardening, (2) richer matching evidence with 10 relevant abstracts/papers, (3) professor photos as source-backed profile enrichment, (4) routine OpenRouter-assisted university scanning as an opt-in local workflow, and (5) production readiness plus real authentication only after local MVP acceptance passes.

## Product Rationale

The current PRD explicitly defines a local-first MVP with no paid APIs, no production deployment, no user accounts, conservative scraping, source/confidence for inferred claims, and no unsupported recruiting claims. Several requested improvements are valuable but change MVP boundaries. They should be introduced as gated phases so the system remains auditable, local-first, and useful to prospective MS/PhD applicants without overclaiming data quality or recruiting status.

## Phased Roadmap

### Phase 0 — Complete Local MVP Baseline

**Goal:** Pass existing MVP acceptance criteria before scope expansion.

**Includes:**
- 10 seed US CS departments.
- 3+ proven scraper adapters before scaling.
- Professor search, profile pages, student match form, match explanations, admin scrape/QA view.
- QA report covering data counts, missing fields, duplicates, API smoke tests, and screenshots.

**Exit criteria:** `make test` and `make qa` are passing or documented with explicit PARTIAL/FAIL reasons.

### Phase 1 — Matching Evidence: 10 Abstracts / Relevant Papers

**User story:** As a prospective applicant, I want each match to cite up to 10 relevant recent papers or abstracts so I can judge research fit without manually opening many pages.

**Acceptance criteria:**
- Matching results expose up to 10 source-backed relevant publications per professor when available.
- Each cited paper includes title, year, source, URL when available, abstract when available, and match confidence.
- Explanations reference actual stored publication/profile data.
- Missing abstracts are displayed honestly rather than hallucinated.
- Matching still returns within the local MVP performance target for the MVP corpus.

**Non-goals:**
- No paid publication APIs.
- No large-scale Google Scholar scraping.
- No claim that paper relevance proves the professor is recruiting.

**QA implications:** Add checks that match explanations cite existing publication IDs/titles and never reference absent abstracts.

### Phase 2 — Professor Photos

**User story:** As a student reviewing professor profiles, I want to see a source-backed professor photo when available so profiles are easier to scan and recognize.

**Acceptance criteria:**
- Profile may include `photo_url`, `photo_source_url`, and confidence/source metadata.
- UI displays photos only when backend data exists; otherwise it shows a neutral placeholder.
- Photos are fetched only from faculty/profile pages or explicitly permitted public profile assets.
- Broken or low-confidence photo URLs are flagged in QA.

**Non-goals:**
- No face recognition.
- No scraping private/social photos.
- No UI-invented image fields unsupported by backend.

**QA implications:** Add link checks and profile screenshots for photo present/missing states.

### Phase 3 — Routine OpenRouter-Assisted University Scanning

**User story:** As a project owner, I want an opt-in local workflow that uses OpenRouter to help identify candidate CS faculty-directory pages and extraction hints so adding universities is faster.

**Acceptance criteria:**
- OpenRouter use is optional and disabled unless a local API key is configured.
- Scanning produces candidate URLs, extraction notes, confidence, and raw evidence files before any database write.
- Human review or QA gate is required before a new adapter is treated as accepted.
- Conservative request pacing and robots/terms awareness remain required.
- All LLM-generated findings are marked as suggestions, not facts, until source-verified.

**Scope change:** This relaxes the current "no paid APIs" MVP rule if OpenRouter billing is used. It must be treated as post-MVP or explicitly approved as an optional developer-assisted workflow.

**Non-goals:**
- No autonomous global-scale crawling.
- No mass university ingestion before 3 adapters are proven and QA-approved.
- No LLM-only professor records without source-backed extraction.

**QA implications:** Add audit report section for LLM-assisted scans: inputs, outputs, accepted/rejected candidates, and source evidence.

### Phase 4 — Production Readiness

**User story:** As a project owner, I want the local MVP architecture prepared for safe deployment later, so the system can move beyond a single-machine prototype after data quality and UX are validated.

**Acceptance criteria:**
- Config/secrets are environment-based and documented.
- SQLite-local development remains supported; migration path to Postgres/Supabase is documented.
- Backend has structured logging, error handling, CORS configuration, and basic operational checks.
- QA documents deployment blockers separately from local MVP blockers.

**Scope change:** Production deployment is currently a PRD non-goal. Production readiness can be planned after MVP QA, but actual deployment should remain out of scope until explicitly approved.

**Non-goals:**
- No production launch before local MVP works.
- No deployment infrastructure as a substitute for data/API/UI QA.
- No global scaling assumptions.

**QA implications:** Add preflight checklist; keep local `make test`/`make qa` as the primary completion gate.

### Phase 5 — Real Authentication

**User story:** As a returning user, I want a real account so my student profile, shortlist, and notes can persist securely across sessions.

**Acceptance criteria:**
- Authentication requirements are documented before implementation.
- Auth protects user-specific student profiles, saved matches, and notes if those features exist.
- Local development can still run without external production dependencies where feasible.
- Privacy/security expectations for applicant data are explicit.

**Scope change:** The MVP currently says no user accounts. Real auth is post-MVP unless the product owner explicitly changes MVP scope.

**Non-goals:**
- No auth before core local matching and professor profiles pass QA.
- No collecting sensitive applicant data without privacy guidance.
- No enterprise SSO in the near-term roadmap.

**QA implications:** Add auth smoke tests, unauthorized/authorized access checks, and data isolation checks.

## Priority Summary

1. **Must do first:** Complete local MVP baseline and QA.
2. **Highest user-value enhancement:** 10 relevant papers/abstracts in matching.
3. **Low-risk profile enrichment:** Professor photos with source/confidence.
4. **Power-user workflow:** Optional OpenRouter-assisted university scanning, gated because it may violate no-paid-API MVP constraints.
5. **Post-MVP platform work:** Production readiness and real auth after local MVP acceptance.

## Open Questions

- Should OpenRouter be allowed as an optional local developer tool despite the current no-paid-API MVP rule?
- Is production readiness documentation acceptable now if actual deployment remains out of scope?
- Should professor photos be stored as remote URLs only, or should the system cache thumbnails locally with source metadata?
- For the 10 papers/abstracts feature, should "10" mean top 10 overall recent papers or top 10 most relevant to the submitted student profile?
