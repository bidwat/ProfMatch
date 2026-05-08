# QA Report — Professor Match Current Baseline

Date: 2026-05-08
Status: PASS for the current local MVP baseline plus the hi-fi design-reference frontend refresh. Overall MVP acceptance remains complete for tested local-first flows.

## Scope

This report covers the current local-first Professor Match baseline after the frontend rebuild, next-phase improvements, and the 2026-05-06 UX cleanup completion:

- Cleaned current QA/test ergonomics.
- Kept matching local-first by default.
- Added relevant publication evidence from up to 10 recent papers/abstracts per professor candidate.
- Filtered publication evidence so unrelated recent papers are not labeled relevant solely due to recency/confidence boosts.
- Added source-backed professor photo fields from existing `extra.image_url` / photo metadata.
- Updated frontend match cards and professor cards/detail pages to show relevant papers and photos when available.
- Added a routine university scan wrapper that writes raw, processed, QA, manifest, and OpenRouter audit artifacts without DB import.
- Added first-party local backend auth using email/password and HttpOnly session cookies.
- Added authenticated backend state sync for intake profile, latest matches, saved professors, and tracker rows.
- Added read-only admin scan APIs and `/admin/scans` dashboard backed by `data/qa/scraper_runs` artifacts.
- Added QA-gated DB Import endpoint `POST /api/admin/scans/{scan_id}/import` to safely upsert scanned professors and publications into the SQLite DB.
- Added server-side professor facets, filtering, sorting, and cursor-style lazy loading for Discover.
- Added recommendation request API and frontend page with SSRF-aware URL validation.
- Added expanded academic profile form, dirty-state update/match action, and account deletion.
- Added consolidated `/admin` dashboard with indexed department counts, grouped agentic jobs, staged refresh, confirmed delete, and requested-item visibility.
- Added follow-up UX polish: profile photo upload/resizing, reusable confirmation modals, reusable filters/search/chips, auth route guard, friendly API errors, saved-preview fix, sticky professor detail card, and SSE agentic job status.
- Added structured JSON logging, exception handling, and endpoint-aware rate-limiting middleware (Phase 6 Production Readiness).
- Admin-only access gating for scan APIs and frontend navigation.
- Added scan issue breakdowns, missing-required-field counts, individual validation issue previews, duplicate candidate previews, and Playwright screenshot evidence.
- Refreshed the frontend visual system against `design_reference/` hi-fi assets: Sora typography, warm paper/gold/olive/peach palette, sharp editorial cards, top navigation, chips, filters, modals, dialogs, toast styling, match score breakdown cards, and `/match` plus `/admin/scrapes` route parity.
- Tightened the public landing page against `design_reference/hifi-screens.jsx`: 52px public nav, two-column 1100px hero, content-width discovery chip, gold accent line, inline dataset stats, compact match-preview card, and reference-style value-prop band.
- Added shared frontend primitives for icons and compact filter/sort controls, including horizontal active-filter chips so multi-select values no longer stack inside dropdown controls.
- Canonicalized the logged-in Matches experience at `/match`; `/results` remains only as a legacy alias.
- Reduced local rate-limit false positives for read-heavy professor discovery by exempting professor read endpoints from the in-memory local-development limiter; admin agentic job status still uses SSE support and low-frequency dashboard refresh.
- Registered `/api/student-profiles` and fixed its legacy SQLModel mapper/response issues so the required student-profile smoke endpoint no longer 404s.

## Database evidence

From `db/professor_match_publications.sqlite` via previous smoke checks:

- Professors: 890
- Publications: 4,094
- Universities: 9
- Professors with publications: 844

## Backend changes verified

- `POST /api/match` remains deterministic/local-first by default (`rerank=false`).
- Match request now supports:
  - `include_publication_evidence`
  - `max_abstracts_per_professor` capped at 10.
- Match response now includes relevant publication evidence with:
  - publication id, title, year, venue, URL, source, match confidence,
  - similarity score,
  - matched terms,
  - full abstract and abstract snippet when available.
- Match explanations cite actual selected publication titles.
- Match/professor responses include source-backed photo fields when available:
  - `photo_url`
  - `photo_source_url`
  - `photo_confidence`.
- `GET /api/professors` exposes photo metadata in list cards.
- `GET /api/professors/{id}` exposes photo metadata and license/source note in detail data.
- Backend-local pytest now works via `apps/backend/pytest.ini`.
- Routine scan command added at `scripts/project/run_university_scan.py`.
- `packages/scraper` CLI now lazily loads adapters so optional heavy adapter dependencies do not break basic tests.
- `make test` now runs scraper unit tests and backend pytest.
- Whitespace-only `research_interests` is rejected instead of returning arbitrary fallback matches.
- Auth API added:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `GET /api/auth/me`
  - `GET /api/auth/state`
  - `PATCH /api/auth/state`
- Auth stores PBKDF2 password hashes and hashed session tokens in SQLite tables `users` and `auth_sessions`.
- User app state is stored in `user_states` as JSON payloads for local-MVP persistence.
- Admin scan API added:
  - `GET /api/admin/scans`
  - `GET /api/admin/scans/{scan_id}`
  - `POST /api/admin/scans/{scan_id}/import`
  - `GET /api/admin/indexed-departments`
  - `POST /api/admin/indexed-departments/refresh`
  - `DELETE /api/admin/indexed-departments`
  - `GET /api/admin/agentic/jobs/grouped`
  - `GET /api/admin/agentic/job/{job_id}/events`
  - `GET /api/admin/recommendations`
- Admin scan summaries expose QA status, run status, candidate professor/publication counts, issue counts, duplicate counts, issue breakdowns, missing-field counts, duplicate candidates, OpenRouter audit status, artifact paths, and `db_import_allowed`.
- Admin import endpoint creates/updates `Professor` and `Publication` records safely mapping `faculty_profile_url` and `normalized_name` to avoid duplicates.
- Admin scan endpoints require `role == "admin"` via the authenticated session dependency.

## Frontend changes verified

- Match result cards show up to 10 relevant papers with snippets and matched terms.
- Professor cards and match cards show source-backed professor photos where available.
- Professor detail page keeps source-backed photo indicators in Overview and no longer exposes a student-facing Evidence tab.
- Missing photos fall back to initials placeholders.
- Playwright config now starts/reuses the frontend dev server for e2e tests.
- Sign-up and sign-in pages call real auth APIs; AppShell restores `/api/auth/me` sessions and logs out via backend.
- Intake, results, saved professors, tracker, and profile pages read/write `/api/auth/state` when authenticated and fall back to `localStorage` when anonymous/offline.
- `/admin` displays indexed universities/departments, professor/publication counts, update/delete controls, ongoing workflows, ready-to-publish jobs, and completed jobs.
- `/admin/scans` remains available for artifact review but is no longer the primary admin UX.
- `/admin/scans` exposes a functional "Import to SQLite Database" button that triggers the import for approved scans, displaying inserted/updated record counts.
- App navigation shows the Admin item only for restored users with `role: "admin"`.
- Discover, Matches, Saved, Profile, Recommend, and Professor Detail now follow the requested top-nav, list-row, filtering, multi-select chip, and no-evidence-tab UX cleanup.
- Protected app pages are guarded by backend session checks; unauthenticated users are redirected to sign in and private local app state is cleared.
- Frontend API errors parse backend structured JSON and show friendly messages instead of raw JSON payloads.
- Global UI tokens now mirror `design_reference/hifi-tokens.css` with warm paper surfaces, Sora font, gold/olive/peach accents, compact radii, and hi-fi shadows.
- AppShell navigation now matches the reference information architecture: Home, Matches, Discover, Saved, and Admin.
- `/match` now renders the matching intake experience directly instead of redirecting, while `/intake` remains available.
- `/admin/scrapes` is available as a hi-fi/admin route alias for scan artifact review, while `/admin/scans` remains backwards-compatible.
- Professor, match, saved, discover, profile, recommend, admin, auth, modal, dialog, chip/filter, and toast surfaces share the refreshed design system.
- Public landing now follows the hi-fi reference structure: standalone nav, 44px editorial headline, gold divider, inline stats, right-side overlap SVG inside a card, and three value-prop cards on a white band.
- Top navigation now uses shared SVG icons and routes Admin users to canonical `/admin`; `/admin/scrapes` is no longer promoted from the main dashboard.
- Discover, Saved, and Matches use reusable `SearchBox`, `MultiSelectFilter`, `SortSelect`, and active filter summary chips with bounded dropdown menus.
- Dashboard saved/match previews reuse the same avatar/photo component and do not show “No saved professors yet” while saved preview records are still loading.
- Match result cards now match the hi-fi `HFProfCard` pattern more closely: top-right match score, olive-tinted “Why matched” box, relevant-paper count, Expand and Save actions, and no visible tags or component score grid in the match list.

## Commands run

```bash
python -m unittest discover packages/scraper/tests -v
make test
apps/backend/venv/bin/python -m pytest apps/backend/tests -q
cd apps/backend && venv/bin/python -m pytest tests -q
cd apps/frontend && npm run test -- --runInBand
cd apps/frontend && npm run build
cd apps/frontend && npx playwright test
cd apps/frontend && npm run lint
cd apps/frontend && npm run test -- --runInBand
cd apps/frontend && npm run build
apps/backend/venv/bin/python -m pytest apps/backend/tests -q
make test
node /tmp/profmatch_visual_audit.js
node /tmp/profmatch_visual_audit_robust.js
```

## Results

- Scraper/unit scan workflow tests: PASS, 22/22
- `make test`: PASS; runs scraper unit tests and backend pytest.
- Backend tests from `apps/backend`: PASS, 27/27 after registering `/api/student-profiles`.
- Frontend Jest: PASS, 8/8 across 4 suites on 2026-05-08 after final profile/match visual cleanup.
- Frontend lint: PASS with no ESLint warnings.
- Frontend production build: PASS on 2026-05-08 with no lint/type warnings.
- Playwright e2e: PASS, 4/4 on 2026-05-07.
- Frontend lint after landing refresh: PASS exit code, with the two pre-existing warnings for admin onboarding `<img>` and admin scans `fetchScans` dependency.
- File-based visual audit after final profile/match/admin refresh: PASS runtime in production Next mode, `consoleErrors: 0`, `failedRequests: []`, `errors: []`; screenshots regenerated under `apps/frontend/test-results/visual-audit`.
- Desktop landing screenshot evidence: `apps/frontend/test-results/visual-audit/01-landing.png` (`1440x1000`).
- Mobile public landing screenshot evidence: `apps/frontend/test-results/visual-audit/mobile-01-landing.png` (`375x1506`), captured in a separate anonymous Playwright context so `/` is not redirected to the authenticated dashboard.
- `make qa`: previously PASS for baseline; not rerun after visual-only refresh.

## API smoke evidence

Manual FastAPI `TestClient` smoke verified:

- `GET /api/professors?limit=3`: HTTP 200, photo fields present in response schema.
- `GET /api/professors/1`: HTTP 200, Stanford professor photo URL returned from existing source metadata.
- `POST /api/match`: HTTP 200, match rows include photo fields and relevant publication evidence.

Example observed match evidence keys:

```txt
id, title, year, url, venue, source, match_confidence,
similarity_score, matched_terms, abstract, abstract_snippet
```

## Phase 3/5 scan workflow and dashboard evidence

The scan wrapper writes canonical artifacts in the required locations:

```txt
data/raw/university_scans/{date}/{school}/roster.html
data/raw/university_scans/{date}/{school}/manifest.json
data/processed/university_scans/{date}/{school}_professors.jsonl
data/processed/university_scans/{date}/{school}_publications.jsonl
data/qa/scraper_runs/{date}_{school}_validation.json
data/qa/scraper_runs/{date}_{school}_scan_manifest.json
data/qa/scraper_runs/{date}_{school}_openrouter_audit.json
```

Fixture-backed test verified Stanford scan output with 2 professor records, no validation errors, and `db_import_allowed: true`. The command performs no SQLite import.

Admin scan API tests verify that validation, manifest, and OpenRouter audit artifacts are discovered from `data/qa/scraper_runs`, summarized, exposed through `/api/admin/scans`, and available through `/api/admin/scans/{scan_id}`. Tests cover missing-field issue breakdowns, issue previews, duplicate candidates, missing scan 404s, and admin role enforcement.

Import tests verify that `POST /api/admin/scans/{scan_id}/import` accurately extracts JSONL rows, upserts DB records intelligently resolving duplicates, and correctly surfaces error responses.

Frontend Playwright verifies `/admin/scans` with mocked admin auth and scan artifacts, including issue breakdowns and duplicate candidate display, and writes screenshot evidence to:

```txt
apps/frontend/test-results/admin-scans-dashboard.png
apps/frontend/test-results/design-match-intake.png
apps/frontend/test-results/design-discover.png
```

## Known notes / follow-ups

- Auth/state persistence is complete for the local MVP, but it uses a compact `user_states` JSON table rather than fully normalized `student_profiles`, `matches`, saved-professor, and tracker tables. Normalize those tables before multi-user production hardening.
- Profile photo upload currently resizes/crops to a small 256×256 browser-generated image and stores it in profile state. A binary authenticated upload/file-store endpoint can be added later if needed.
- Photo metadata currently reuses existing `Professor.extra` fields such as `image_url` and should later migrate to a dedicated `professor_assets` table.
- Relevant publication scoring is deterministic keyword/FTS-based and filters out papers with no lexical overlap; semantic matching can be improved later with local embeddings or optional free-model reranking.
- OpenRouter rerank remains opt-in and restricted to models ending in `:free`.
- Admin scan dashboard effectively triggers SQLite database import logic.
- `--openrouter-extract` currently writes a gated audit record only; it does not perform live LLM extraction yet.
- `npm install` during `make qa` reports existing frontend dependency audit findings (5 vulnerabilities: 1 moderate, 4 high); dependency remediation is a production-readiness follow-up.
- Jest output includes the existing ReactDOMTestUtils `act` deprecation warning from the testing-library/react stack.
- Landing value-prop icons are lightweight text glyphs rather than the exact reusable SVG `HFIcon` set from the design reference; replace with shared icon components if pixel-level parity becomes required.
- `/results`, `/intake`, `/admin/scans`, and `/admin/scrapes` remain as compatibility routes/pages; product navigation now favors `/match` and `/admin`.
