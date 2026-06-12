# Professor Match — Comprehensive Architectural Breakdown

Generated for the repository at `/home/drl/pi-agent/profmatch-clean-git`.

## 1. Product and Architecture Thesis

Professor Match is a local-first professor discovery and graduate-advisor matching system. The central architectural decision is to treat professor discovery as a data-provenance problem first and a search/matching UI second. The product does not simply scrape names and render cards; it preserves source URLs, confidence, publication evidence, recruiting evidence, profile-photo provenance, scan artifacts, QA reports, and user state.

The current system is a monorepo with:

- `apps/backend/` — FastAPI backend, SQLModel persistence, auth, matching, admin scan APIs.
- `apps/frontend/` — Next.js App Router frontend, TypeScript API client, reusable UI components, local-first state fallback.
- `packages/scraper/` — reusable Python scraping, normalization, validation, deduplication, publication enrichment, artifact writing.
- `db/` — local SQLite databases, with the runtime default pointing at `db/professor_match_publications.sqlite`.
- `data/raw/`, `data/processed/`, `data/qa/` — audit-friendly scraper outputs before DB import.
- `docs/` — product, architecture, deployment, scraping playbooks, and QA reports.

The MVP deliberately optimizes for local reliability, inspectability, and evidence-backed recommendations over production scale. SQLite FTS5 is the default local search engine; PostgreSQL/Supabase support exists for deployment, but the design avoids paid APIs and avoids claiming recruiting status without explicit evidence.

## 2. Repository-Level Decisions

### Monorepo layout

The repository keeps frontend, backend, scraper package, data artifacts, documentation, and deployment descriptors in one source tree. This was chosen because Professor Match has tight coupling between data contracts and UI display: a field added by a scraper must be validated, persisted, served by FastAPI, typed in TypeScript, and rendered by Next.js. A monorepo reduces drift across those layers.

Key paths:

- `apps/backend/app/main.py` wires the FastAPI application.
- `apps/backend/app/api/` holds HTTP route modules.
- `apps/backend/app/services/` holds business logic.
- `apps/backend/app/models/` holds SQLModel/Pydantic model definitions.
- `apps/frontend/app/` holds Next.js App Router pages.
- `apps/frontend/components/` holds reusable UI components.
- `apps/frontend/lib/api.ts` is the frontend/backend contract surface.
- `apps/frontend/lib/types.ts` mirrors backend response shapes.
- `packages/scraper/core/` holds pipeline primitives.
- `packages/scraper/adapters/` holds university-specific adapters.

### Local-first default

The backend DB configuration in `apps/backend/app/db/__init__.py` defaults to:

```txt
db/professor_match_publications.sqlite
```

unless `DATABASE_URL`, Supabase pooler env vars, or `PROFESSOR_MATCH_DB_PATH` are set. This preserves the MVP principle that a developer can run the system locally without paid infrastructure.

### Canonical documentation

The architecture is grounded in:

- `docs/product/PRD.md`
- `docs/product/ACCEPTANCE_CRITERIA.md`
- `docs/product/DOD_DND.md`
- `docs/architecture/SPEC.md`
- `docs/scraping-playbooks/README.md`
- `README.md`

The docs explicitly define the core stack: Next.js + TypeScript + Tailwind, FastAPI + Python, SQLite, SQLModel/SQLAlchemy, Requests/BeautifulSoup, Pydantic validation, SQLite FTS5, pytest, and Playwright.

## 3. Backend Architecture

### FastAPI application composition

`apps/backend/app/main.py` owns application assembly. It creates a `FastAPI(title="Professor Match Backend")` app with a lifespan handler that calls `SQLModel.metadata.create_all(engine)` at startup. This is an intentional MVP choice: schema creation is automatic for local development and free-tier demos, avoiding a mandatory migration workflow while the data model is still evolving.

Routers are mounted under `/api`:

- `/api/professors` and `/api/professors/{id}` — professor directory and detail.
- `/api/professors/facets` — filter facet values.
- `/api/universities` — university list.
- `/api/stats` — explorer stats.
- `/api/match` — matching request.
- `/api/auth/*` — local user auth and state sync.
- `/api/scrape-runs` — scrape-run metadata.
- `/api/recommendations` — user-submitted department recommendations.
- `/api/admin/*` — scan, onboarding, indexed department, and admin recommendation workflows.

### Structured logging and errors

`main.py` defines a JSON log formatter so backend logs emit structured records with time, level, message, logger name, and exception details. Error handlers standardize response bodies as:

```json
{"error":{"code":"...","message":"...","details":"..."}}
```

This was mirrored by `apps/frontend/lib/api.ts`, which parses `error.code` and `error.message` into friendly user-facing errors. The frontend/backend error contract is therefore explicit instead of relying on raw FastAPI exception strings.

### CORS and cookies

The backend enables CORS from `settings.cors_origins` with credentials allowed. This decision supports Next.js running separately from FastAPI in local dev while still allowing HttpOnly session cookies to work.

### Rate limiting

`main.py` implements simple in-memory rate limiting. Read-heavy endpoints such as professor browsing, auth state, and admin job polling are exempt or relaxed. Write endpoints are limited by method and path. This is a pragmatic local-MVP safeguard: it discourages accidental request storms without introducing Redis.

### Database abstraction

`apps/backend/app/db/__init__.py` chooses the runtime database URL in this order:

1. `DATABASE_URL`, normalizing `postgres://` and `postgresql://` to `postgresql+psycopg://`.
2. Supabase pooler settings (`SUPABASE_POOLER_HOST`, `SUPABASE_DB_PASSWORD`, etc.), because Supabase direct hosts may be IPv6-only on free projects.
3. SQLite at `db/professor_match_publications.sqlite`.

SQLite gets `check_same_thread=False`; all DB access is provided through `get_session()` yielding a SQLModel `Session`. The system therefore supports local SQLite while keeping a path to PostgreSQL/Supabase deployment.

## 4. Backend Data Model Decisions

### Professor and publication tables

`apps/backend/app/models/professor.py` defines the primary research corpus:

- `Professor` includes identity fields, institutional fields, profile/homepage/scholar IDs, research text, generated research summary, recruiting signal/evidence, source confidence, timestamps, and an `extra` JSON field.
- `Publication` belongs to a professor and stores title, year, venue, abstract, URL, source, source author ID, and match confidence.

The `extra` JSON column is important. It allows data enrichment fields such as `tags`, `photo_url`, `photo_source_url`, `profile_text_confidence`, and audit metadata without requiring immediate schema migrations. The deliberate tradeoff is less relational strictness in exchange for agility while the MVP data pipeline is still maturing.

### Recruiting signal as an enum

Recruiting signal is constrained to `positive`, `negative`, or `unknown`. This reflects a product rule: the system must not invent recruiting status. If explicit evidence is absent, the state remains `unknown`.

### Auth and user state

`apps/backend/app/models/auth.py` defines:

- `User` — local email/password account with role and active status.
- `AuthSession` — hashed session token, expiry, last-seen time, revoked timestamp, user agent, and IP.
- `UserState` — JSON blobs for student profile, last match response, saved professor IDs, and tracker rows.

This supports a local-first frontend: users can work with browser `localStorage`, then sync persistent state when logged in.

### Student profiles and persisted matches

`apps/backend/app/models/student_profile.py` and `apps/backend/app/models/match.py` separate student input from match output. The matching request model captures background, research interests, target degree, preferred departments/locations/universities, result limits, shortlist size, and optional LLM reranking flags. The response model decomposes scores into interpretable components and evidence.

## 5. Backend Service Layer Decisions

The backend uses route modules as thin controllers and service classes for business logic. This is visible in `apps/backend/app/api/professors.py`, which delegates to `ProfessorService`, and `apps/backend/app/api/match.py`, which delegates to `MatchService`.

### ProfessorService

`apps/backend/app/services/professor_service.py` implements directory browsing and details.

Decisions:

- Text search uses SQL `ilike` across name, title, department, university, `research_text`, and `research_summary` for browsing. This is database-portable and sufficient for directory filtering.
- Multi-select filters are supported for university, department, and tags.
- Tags are read from `Professor.extra["tags"]`, which keeps taxonomy flexible.
- Sorting is constrained to `name`, `university`, and `recruiting` with asc/desc to prevent arbitrary SQL ordering.
- Pagination supports an opaque cursor encoded as base64 offset while still accepting page/limit. The frontend uses cursor-based lazy loading.
- Each summary includes publication count, profile display status, profile text source URL, profile text confidence, and photo metadata.
- Details return full professor fields plus publications sorted by year descending.

The service also exposes indexed department groups and deletion for admin workflows.

### MatchService

`apps/backend/app/services/match_service.py` is the core matching engine.

Major decisions:

1. **SQLite FTS5 first.** For SQLite, `_ensure_fts_index()` creates/rebuilds a `professor_match_fts` virtual table and uses `bm25()` to shortlist professors. The MVP corpus is small enough that rebuilding the FTS table per match request is acceptable and avoids trigger/migration complexity.
2. **Portable fallback for PostgreSQL.** If the DB dialect is not SQLite, the service uses an in-process lexical shortlist with keyword extraction and Jaccard similarity. This keeps production/free-tier Postgres viable before adding `pg_trgm` or `tsvector` migrations.
3. **Deterministic scoring.** Total score is a weighted blend:
   - 45% research text similarity
   - 30% recent publication similarity
   - 10% recruiting signal
   - 10% department/title relevance
   - 5% location preference fit
   - plus bounded metadata boost
4. **Publication evidence.** Recent/publication similarity is based on title, abstract, venue, recency, and source confidence. The response includes selected publication evidence, matched terms, and abstract snippets when requested.
5. **Risk surfacing.** Evidence includes risks/uncertainties so the UI can explain weak summaries, unknown recruiting signals, or sparse publication evidence.
6. **Optional free-model LLM rerank.** If `student.rerank` is true, the service can call OpenRouter, but only if the configured model ends with `:free`. This preserves the no-paid-API rule. The LLM is only allowed to rerank provided candidates and must not invent recruiting evidence.

This architecture gives users explainable local rankings immediately, with optional LLM assistance layered on top rather than replacing deterministic scoring.

### AuthService

`apps/backend/app/services/auth_service.py` handles local auth. It normalizes email, hashes passwords with PBKDF2-HMAC-SHA256, uses constant-time comparison, stores only hashed session tokens, and supports revocation. The backend intentionally does not use OAuth or external identity providers because the MVP is local-first and has no production user-account requirement.

### Admin scan and import services

`apps/backend/app/services/admin_scan_service.py` reads scraper artifacts from `data/raw`, `data/processed`, and `data/qa`, summarizes validation issues, duplicate candidates, missing fields, previews, and scan manifests. `apps/backend/app/services/import_service.py` imports approved processed records into the DB. The decision is explicit: scraping writes artifacts first; DB import is a later reviewed step.

### Agentic onboarding services

`apps/backend/app/services/agentic_onboarding_service.py` and `agentic_scraper_service.py` support admin workflows that generate or manage university onboarding jobs. They are isolated behind admin endpoints because adapter generation and publication enrichment can be slow, experimental, and operationally sensitive.

## 6. Backend API Surface

### Professor APIs

`apps/backend/app/api/professors.py` defines:

- `GET /api/professors/facets`
- `GET /api/professors`
- `GET /api/professors/{professor_id}`

Response models are Pydantic models, not raw ORM objects. This keeps frontend-facing shapes stable and lets the service include derived fields such as tags, photo metadata, and publication counts.

### Match API

`POST /api/match` accepts a `StudentProfile` and returns `MatchResponse`. It rejects empty matches with 404, which makes the frontend handle empty/failed matching explicitly instead of treating it as success.

### Auth APIs

`apps/backend/app/api/auth.py` exposes register, login, logout, current user, account deletion, and user-state get/patch. Sessions are stored server-side and sent through cookies. `UserState` enables saved professors, latest match results, profile drafts, and tracker rows to survive beyond localStorage.

### Admin APIs

`apps/backend/app/api/admin.py` groups operational endpoints under `/api/admin` and protects them with `require_admin`, which requires `current_user.role == "admin"`.

Admin capabilities include:

- listing registered scraper adapters;
- running scans in background tasks;
- reading scan status;
- listing scan artifacts;
- importing reviewed scans;
- agentic onboarding job management;
- streaming job events;
- homepage enrichment, publication fetch, summary generation, and publish steps;
- listing/deleting indexed department groups;
- reviewing user recommendation requests.

This isolates potentially destructive or expensive data operations from normal student flows.

## 7. Scraper and Data Pipeline Architecture

### Adapter pattern

University-specific logic lives in `packages/scraper/adapters/`. Implemented adapters include Berkeley, CMU, Cornell, Georgia Tech, Michigan, MIT, Stanford, TAMU CSE, UIUC, UT Austin, and Washington.

The shared adapter contract is defined around normalized outputs rather than page-specific DOM structure. Each adapter supplies university metadata, roster URL, and parser behavior; the rest of the pipeline stays reusable.

### Pipeline primitives

`packages/scraper/core/run_manager.py` orchestrates the scrape pipeline:

1. Generate a run ID.
2. Fetch the roster page with `SafeFetcher` or read a fixture.
3. Write raw fetch artifact.
4. Parse HTML into `ProfessorCandidate` objects.
5. Deduplicate obvious parser overlaps by URL/name.
6. Optionally enrich individual profiles.
7. Normalize candidates into `NormalizedProfessorRecord`.
8. Optionally enrich publications through OpenAlex, DBLP, and Semantic Scholar.
9. Normalize and dedupe publication records.
10. Validate professor and publication records.
11. Detect duplicates.
12. Write processed records, QA reports, and scan manifests.

### Data contracts

`packages/scraper/core/models.py` defines dataclasses for:

- `SourceArtifact` — raw source provenance.
- `FetchResult` — response body and artifact metadata.
- `ProfessorCandidate` — raw parsed faculty candidate.
- `PublicationCandidate` — raw publication enrichment candidate.
- `NormalizedProfessorRecord` — canonical professor record.
- `NormalizedPublicationRecord` — canonical publication record.
- `EnrichmentResult` — publication-source audit result.
- `ValidationIssue` — structured QA issue.
- `ScrapeRunRecord` — run-level status and metrics.

The architectural choice is to make raw, candidate, normalized, enriched, and validated states explicit. That makes it possible to audit where every field came from.

### Provenance and confidence

Professor and publication candidates carry `source_url`, `source_type`, `source_confidence`, `field_sources`, `source_provenance`, and `extra`. Publication enrichment includes `match_confidence`, source author IDs, and source-specific IDs. These fields support the product principle that every inferred claim needs source/confidence.

### Publication enrichment

The run manager defaults to OpenAlex, DBLP, and Semantic Scholar enrichers. Google Scholar is treated as an optional profile link source, not a scraping target. This is consistent with the no-aggressive-scraping rule and avoids large-scale Google Scholar scraping.

### Artifact-first import

The scan pipeline writes:

- raw source artifacts under `data/raw/`;
- processed professor/publication JSONL under `data/processed/`;
- QA manifests and validation outputs under `data/qa/`.

Only after review can the admin import service insert data into SQLite. This prevents unreviewed scraper output from polluting the canonical database.

## 8. Frontend Architecture

### Next.js App Router

The frontend uses Next.js App Router in `apps/frontend/app/`. Pages are route files:

- `/` — landing page (`app/page.tsx`).
- `/signin` and `/signup` — auth pages.
- `/dashboard` — student dashboard.
- `/profile` — student profile editor.
- `/intake` and `/match` — match intake flows.
- `/results` — match results.
- `/professors` — searchable directory.
- `/professors/[id]` — professor detail.
- `/saved` — saved professor list/tracker.
- `/recommend` — user recommends a department/faculty page.
- `/admin` — admin dashboard.
- `/admin/scans` and `/admin/scrapes` — scan/admin views.
- `/admin/onboarding` — agentic onboarding UI.

Most feature pages are client components because they use browser state, localStorage fallback, forms, debounced search, and authenticated cookie-backed API calls.

### Application shell

`apps/frontend/components/AppShell.tsx` wraps the UI with navigation and route-aware behavior. It distinguishes public routes (`/`, `/signin`, `/signup`) from authenticated application areas. Navigation is split around student workflows and admin capabilities.

### API client

`apps/frontend/lib/api.ts` is the single frontend API boundary. It uses `fetch()` with:

- `cache: 'no-store'` to avoid stale local data;
- `credentials: 'include'` for HttpOnly session cookies;
- JSON request headers;
- structured `ApiError` parsing of backend error envelopes.

Every backend operation has a typed wrapper: stats, universities, professor listing, facets, details, matching, auth, user state, admin scans, adapter runs, agentic jobs, indexed departments, and recommendations.

### TypeScript contracts

`apps/frontend/lib/types.ts` mirrors backend response objects. Key interfaces include:

- `ProfessorSummary`
- `ProfessorDetail`
- `PublicationResponse`
- `StudentProfile`
- `MatchEvidence`
- `MatchScore`
- `MatchResponse`
- `AuthUser`
- `UserStateResponse`
- `AdminScanDetail`
- `AgenticJobGroups`

This decision catches mismatches at compile/test time and documents the API shape for UI contributors.

### Local-first state

`apps/frontend/lib/local-store.ts` centralizes browser localStorage for user, saved professors, student profile, match response, and tracker-like state. The UI first works locally and then syncs with `/api/auth/state` when logged in. This is why pages such as `app/professors/page.tsx` initialize saved IDs from localStorage, then reconcile with backend state if available.

### Professor directory UI

`apps/frontend/app/professors/page.tsx` implements the main Discover page.

Decisions:

- Debounced text search with a 350ms delay avoids firing an API request on every keystroke.
- Facets are loaded from `/api/professors/facets`.
- Multi-select filters are used for universities, departments, and tags.
- Recruiting status is a single-select filter.
- Sorting is constrained to the backend-supported sort keys.
- Cursor-based lazy loading appends results instead of replacing them.
- Saving a professor requires login; otherwise a login modal is shown.
- The page shows total count and loaded count for user feedback.

### Professor cards and detail

`apps/frontend/components/ProfessorCard.tsx` standardizes summary rendering: cleaned titles, tags, recruiting signal badge, avatar/photo handling, match data overlays, and save actions.

`apps/frontend/app/professors/[id]/page.tsx` renders the detailed record: identity, profile links, summaries, publications, evidence, source URLs, photo source metadata, and confidence-related fields. This keeps unsupported fields out of the UI and only displays backend-provided data.

### Matching UI

`apps/frontend/app/match/page.tsx`, `app/intake/page.tsx`, and `app/results/page.tsx` form the matching workflow. The frontend sends a `StudentProfile` to `/api/match`, stores the `MatchResponse`, and renders ranked `MatchScore` cards with explanations and evidence. Because backend score components are decomposed, the UI can explain why a professor matched instead of presenting a black-box score.

### Auth UI

`app/signin/page.tsx` and `app/signup/page.tsx` call the local auth API. Auth is intentionally simple: email/password, HttpOnly cookies, and local user state. No external auth provider was chosen because the MVP is local-first and no production deployment is required before the local MVP works.

### Admin UI

Admin pages call `/api/admin/*` endpoints. They expose scan status, scan artifact review, adapter execution, indexed department refresh/delete, recommendation review, and agentic onboarding job controls. The UI design keeps ingestion/refresh operations out of the student-facing directory.

### Styling and UX system

The frontend uses Tailwind configuration plus a global CSS system in `apps/frontend/app/globals.css`. Reusable components such as `Filters`, `Toast`, `ConfirmDialog`, `LoginModal`, `Icon`, and `ProfessorCard` keep behavior and visual language consistent. The UI has been polished around cards, filter bars, screenshots, responsive states, empty states, and admin operational dashboards.

## 9. Deployment Architecture

### Docker and compose

The repo includes:

- `apps/backend/Dockerfile`
- `apps/backend/Dockerfile.runtime`
- `apps/frontend/Dockerfile`
- `docker-compose.yml`
- `docker-compose.backend-only.yml`
- `docker-compose.backend-full.yml`
- `docker-compose.digitalocean.yml`

The architecture supports local compose runs, backend-only deployment, and DigitalOcean-oriented deployment. The deployment docs include Postgres migration and DigitalOcean migration plans.

### Postgres/Supabase path

Postgres support is partial but intentional. The DB layer normalizes Postgres URLs and Supabase pooler credentials. The matching service detects non-SQLite dialects and avoids SQLite FTS5 by using portable lexical scoring. This allows deployment before investing in full Postgres text-search migrations.

## 10. Testing and QA Decisions

### Backend tests

`apps/backend/tests/` covers auth, account deletion, professors, matching, recommendations, and admin scans. Tests use FastAPI/pytest patterns and exercise the local DB/service boundaries.

### Frontend tests

`apps/frontend/tests/` includes Jest/React tests for pages, professor cards, toast behavior, UX shell/profile, plus Playwright E2E (`tests/e2e/home.spec.ts`). Playwright screenshots and visual audit artifacts live in `apps/frontend/test-results/`.

### Scraper tests

`packages/scraper/tests/` covers adapters, normalizer, models, validator, deduper, enrichers, run manager, and university scan workflow. The Stanford fixture test allows offline regression checks without live scraping.

### QA reports

`docs/qa-reports/` contains latest and historical QA reports for data cleanup, publication fetches, scraper review, screenshots, and agentic cleanup. This supports the Definition of Done requirement that QA evidence be written down.

## 11. Key Tradeoffs

1. **Automatic schema creation vs migrations:** automatic `create_all` is fast for MVP, but a mature deployment needs migrations.
2. **SQLite FTS rebuild per match vs triggers:** rebuild is simple and safe for the current corpus; triggers would be more efficient later.
3. **JSON `extra` vs rigid schema:** `extra` gives enrichment agility, but important fields should eventually graduate to typed columns.
4. **In-memory rate limits vs Redis:** no extra infra locally, but not horizontally scalable.
5. **Local auth vs OAuth:** local auth fits MVP and demos, but production would need stronger account/security review.
6. **Portable Postgres lexical fallback vs native Postgres search:** fallback enables deployment quickly, but full `tsvector`/`pg_trgm` would improve scale.
7. **Artifact-first scraper import vs direct DB writes:** slower operationally, but much safer for data quality and auditability.
8. **Optional free LLM rerank vs mandatory AI:** deterministic matching works offline; LLM rerank is additive and constrained by no-paid-API policy.

## 12. End-to-End Data Flow

1. A university adapter in `packages/scraper/adapters/` defines how to fetch/parse a faculty roster.
2. `ScrapeRunManager` fetches the source, writes a raw artifact, parses candidates, enriches profiles/publications, normalizes records, validates them, detects duplicates, and writes processed/QA artifacts.
3. An admin reviews scan outputs in the admin dashboard.
4. Approved data is imported into the `Professor` and `Publication` tables.
5. The frontend Discover page calls `/api/professors` and `/api/professors/facets` to browse the corpus.
6. A student submits a profile to `/api/match`.
7. `MatchService` builds/uses FTS or portable lexical shortlist, computes weighted scores, selects evidence publications, and returns ranked matches.
8. The frontend stores the match response locally and syncs it to `/api/auth/state` when the user is logged in.
9. Saved professors and tracker rows persist through `UserState` and localStorage fallback.

## 13. Current Architectural State

Professor Match is currently an integrated local MVP with a robust data pipeline, searchable professor directory, publication-backed matching, local auth, user state sync, admin scan operations, and a deployable backend path. The strongest architectural choices are evidence preservation, source confidence, scraper artifact review before import, explainable deterministic matching, and TypeScript/Pydantic contract alignment.

The main future hardening areas are formal DB migrations, richer Postgres search, production-grade rate limiting/session security, stricter typing for fields currently stored in `extra`, and continued QA automation around scraper outputs and UI regressions.
