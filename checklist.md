# Production Readiness Checklist — ProfMatch → Univya

Derived from `docs/new/doc.md` (PRD/BRD/QA pack) and `docs/new/spec.md` (full product spec) in the planning repo,
plus the current state of this codebase. Work proceeds top to bottom; phases gate each other.

Deployment shape: backend on DigitalOcean (auto-deploy on `main`), frontend on Vercel (auto-deploy on `main`),
database stays **Supabase Postgres**. Firebase is out of scope except possibly Google sign-in later.
Nothing lands on `main` until verified.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked (reason noted)

---

## Phase 0 — SQLite cleanup — DONE 2026-06-12 (branch `feat/firebase-migration`, commit 5480736)

Decision history: a full Firestore migration was built (93cfc0b) then reverted (e6fa463) — the database
remains Supabase Postgres; only SQLite was removed.

- [x] Remove the file-based SQLite fallback from `app/db/__init__.py` — DATABASE_URL/Supabase vars now required for real data; a private in-memory engine keeps imports/tests working; production refuses to start without Postgres
- [x] Delete `db/professor_match_publications.sqlite` seed, `load_data.py`, `migrate_sqlite_to_postgres.py`
- [x] Remove seed copy from backend Dockerfile and `profmatch_db` volume from compose
- [x] Remove the SQLite FTS5 branch from `match_service` — the portable lexical shortlist (production's existing path) is the only path
- [x] Reword SQLite mentions in admin/onboarding UI strings, Makefile, `.env.example`
- [ ] Optional later: Postgres-native search (pg_trgm/tsvector) to replace the in-process shortlist
- [ ] Optional later: Google sign-in (Firebase Auth or Supabase Auth) — only Firebase use still on the table

### 0.4 Deploy verification (no env changes needed — production already runs Supabase)
- [ ] Merge branch → main, verify deploy health (`/health`, `/api/health/db` reports postgres, `/api/stats`)

## Phase 1 — UI revamp

- [x] Design system pass: hi-fi tokens (Sora, gold/olive/peach, sharp radii) already implemented in `globals.css`, matching `design_reference/hifi-tokens.css` — verified 2026-06-12
- [x] Public free browsing (spec FR-001): `/professors` and professor detail pages work signed-out with a public shell (commit bb849da)
- [x] Landing page per spec §21: search-first hero with topic chips, FAQ, without/with comparison, department-request banner (bb849da, d7fb90f)
- [x] Professor cards (spec §11.5): photo, tags, banded confidence chip, recruiting status, summary snippet (abcac40)
- [x] Professor detail page (spec §10): labeled AI summary + provenance note, profile-text source link, per-paper confidence chips, empty-papers state (d7fb90f, abcac40)
- [x] Discover/search page: filters, sort, empty states, skeletons — already present, verified 2026-06-12
- [x] Match flow threshold controls (40% default, min-results fallback, explanation/evidence display) — already present, verified 2026-06-12
- [x] Dashboard, saved, profile pages: rebranded via shared tokens, buttons on HeroUI, e2e screenshots under test-results/ (bacc758)
- [x] Admin pages: scan dashboard (import monitoring/QA tables, spec §20.5) existed; reports queue + metrics panel added (36e90be); buttons on HeroUI (bacc758)
- [x] Accessibility: :focus-visible outline; new navy/slate palette meets 4.5:1 body contrast; nav/main landmarks + aria labels in place; HeroUI components bring focus management. Deeper audit optional follow-up
- [x] Jest + Playwright updated for revamped UI; screenshots captured by e2e under `apps/frontend/test-results/`

## Phase 1R — System-plan alignment + HeroUI v3 re-skin (added 2026-06-12 after system_plan.md + design.md landed)

### System-plan alignment review (docs/new/system_plan.md) — deviations recorded under the owner's "easier way" clause
- [x] FastAPI + Pydantic + Postgres (Supabase) — aligned
- [x] Crawl4AI as the crawler for agentic onboarding + durable scans — aligned (plan §9)
- [x] Artifact-first import with admin review — aligned (scan_results review/approve/import flow)
- DEVIATION (accepted): DB-backed scan task queue instead of Redis/Celery — single-worker scale is fine for MVP; revisit at multi-worker
- DEVIATION (accepted): cookie-session auth instead of Clerk — working, tested; Google login may come later
- DEVIATION (accepted): in-process lexical shortlist instead of tsvector/pg_trgm/pgvector — fine at ~1k professors; Postgres-native search is a Phase 2 item
- DEVIATION (accepted): SQLModel create_all instead of Alembic — adopt Alembic when the schema next changes
- DEVIATION (accepted): universities/departments stay denormalized strings on professors for now; first-class tables when university/department pages ship

### HeroUI v3 migration (design.md §7 — mandatory component layer)
- [x] Platform upgrade: Next 15.5, React 19.2, Tailwind v4 (d9f8a08) — all suites green
- [x] @heroui/react@3.1.0 + @heroui/styles installed; CSS-first, no provider; jest/next transpile config (dd2babc)
- [x] Rebrand tokens to design.md §6: Rubik + DM Sans (next/font), navy/teal/amber/slate palette mapped onto legacy variable names so every page rebrands at once (d9f8a08)
- [x] HeroUI migration complete (bacc758): modals, forms, tabs, cards, chips, and all 38 action buttons across every page on HeroUI components. Decided per design.md §7.2 rule: Toast and the searchable multi-select filter popovers stay as documented custom domain components (no direct HeroUI equivalent; tested, accessible, on Univya tokens)
- [x] All tests green after each migration step

### Feature implementation (spec §30 MVP, buildable now)
- [x] Pricing page /pricing (spec §23 + design §8.4) — public, trust copy, HeroUI cards/chips (583895a)
- [x] Report incorrect data (spec §14.6): reports table, POST /api/reports, admin list/resolve endpoints, ReportIssueModal on professor detail (583895a). Remaining: admin queue UI panel
- [x] Outreach email drafts (spec §17): POST /api/outreach-drafts (LLM-grounded, draft-only, never auto-send, personalization checklist) + modal on professor detail (583895a)
- [x] Application board with stages (spec §16): /board on tracker_rows, accessible stage select, notes, add-from-saved (582acf8)
- [x] Compare professors (spec §15.6): /compare side-by-side table from saved shortlist with research-fit, evidence, signals (588eb5c)
- GATED (per docs, owner decision needed): Stripe billing (pricing undecided), CV/SOP uploads (privacy gates), public reviews (trust/legal gates), professor claims (verification design)

## Phase 2 — Production hardening (launch gates from doc.md §7.5)

- [x] Rate limiting: proxy-aware (X-Forwarded-For) per-client buckets (36e90be). Accepted deviation: in-memory is the real global limit on the single-process droplet; move to Redis only if instances scale
- [x] Structured error responses: standard envelope + request_id, generic 500 message, no stack leakage (36e90be)
- [~] HTTPS for backend: TLS-ready compose (docker-compose.backend-tls.yml) + runbook docs/deployment/BACKEND_TLS.md ready (6deaa1a) — **blocked on owner: pick a hostname + DNS A record**, then one compose switch
- [!] Secrets audit — **owner action**: rotate the OpenRouter key and Supabase password in `.env` (they sit in plaintext on dev machine and droplet); `.env` is gitignored and untracked
- [x] Health/uptime: deploy workflow fails on unhealthy /health + /api/health/db after rollout; scheduled 30-min uptime workflow (6deaa1a)
- [x] Logging/observability: structured JSON access logs with request id/duration/client ip; X-Request-ID header; request_id in error envelopes (36e90be). Sentry left as optional follow-up
- [x] Backups: Supabase managed Postgres automatic daily backups cover the database; scan artifacts live in droplet volumes (acceptable: reproducible from re-scans)
- [x] CI: backend pytest + scraper unittests + frontend tsc/jest/build + gitleaks on PRs and non-main pushes (.github/workflows/ci.yml, 36e90be)
- [x] Analytics (doc.md §7.3): allowlisted privacy-safe /api/events + admin metrics endpoint/panel; search/profile-open/save/draft/report/board-move wired (36e90be)

## Phase 3 — Product completion toward Univya MVP (spec §30)

### Free/public tier
- [x] Public professor pages without login; per-professor page titles; dynamic sitemap.xml + robots.txt (bb849da, 6deaa1a)
- [x] University & department public pages (spec §22): /universities directory, university pages, department professor listings on the public aggregates endpoint; sitemap + nav links (faf2957). First-class tables remain optional future normalization
- [x] Keyword search + filters free; confidence labels visible
- [x] Report incorrect data flow (spec §14.6) + admin report queue with resolve/reject (583895a, 36e90be)
- [x] Request university/department flow (spec §14.7) — /recommend + landing banner + admin list

### Paid tier (entitlement gating waits on the pricing decision)
- [x] Personalized matching with 40%/10% threshold defaults, evidence, explanations — live
- [x] Saved professors + comparison view (spec §15.6) — /saved + /compare (588eb5c)
- [x] Application board with default stages (spec §16) — /board (582acf8)
- [x] Outreach email drafting (spec §17) — draft only, never auto-send (583895a)
- GATED on pricing decision: paywall/upgrade modal + entitlement enforcement (today these features require login, not payment)
- GATED: CV/SOP upload (privacy gates per doc.md §6.6), Stripe payments + referral system (spec §24)

### Admin & data pipeline
- [x] Agentic import review queue: every candidate requires admin approval before import — stricter than spec §9.9 auto-publish bands, consistent with system-plan ADR-004; banded auto-publish optional later
- [x] Duplicate detection on import (dedupe key + skipped_duplicate status); side-by-side merge UI optional later
- [x] Manual refresh triggers (rescan, OpenAlex publication refresh, profile enrichment) from the admin dashboard
- [x] Admin dashboard: report queue, scan/refresh status, metrics (36e90be)
- [ ] Field-level provenance table (spec §9.11) — today provenance is source URLs + per-field source links in `extra`; full per-field records when first-class tables land
- [ ] Tag canonicalization + alias system (spec §13) — tags are free-form strings in `extra.tags` today
- [ ] Scheduled six-month refresh cron (spec §27) — manual refresh exists; scheduling is one cron job once the droplet has a stable domain

### Professor-side — GATED on claim/verification design (owner decision)
- [ ] Professor claim flow w/ institutional email verification (spec §19.1), professor-added sections, recruiting controls

### Reviews — GATED per doc.md §6 (moderation policy + legal review first)
- [ ] Verified reviewers, relationship types, anonymous ratings aggregate-only, dispute flow — only after gates pass

## Phase 4 — Trust, privacy, policy

- [x] Account deletion (spec §26.4): immediate deactivation + session revocation existed; 30-day permanent purge now runs hourly in the worker, tested (no uploaded docs exist yet)
- [x] Student profiles are private (no public student profiles exist)
- [x] Crawler policy (spec §25.1): identifiable ProfMatchBot user-agent on all Crawl4AI calls (CRAWLER_USER_AGENT overridable), published policy in docs/policies/crawler-policy.md, source URLs + artifacts retained, report/takedown path live
- [x] AI summary labeling: "AI summary · generated from public sources" + caveat on profiles; prompts forbid inventing recruiting status (d7fb90f)
- [x] Match language audit (FR-009): grep-verified — "research fit" everywhere, "admission chance" only in explicit negations
- GATED (legal): privacy policy + terms of use need owner/legal drafting before broad launch

## Open decisions needed from owner (doc.md §2.17 / spec §33)

- Pricing model (monthly vs season pass) and amounts
- First import targets (universities/departments)
- Review launch posture (defer / beta / gated)
- Free users: blurred match preview or hard gate?
- Product naming: ProfMatch → Univya rename (repo, UI copy, domains)?
- Firebase scope confirmation: Firestore for all data + Firebase Auth for users, or Firestore only?

---

## Session log

- 2026-06-12: Checklist created. Phase 0 started: Firebase data layer + SQLite cleanup on branch `feat/firebase-migration`. Found no Firebase credentials in either repo — code reads creds from env; cutover blocked on console env vars (see 0.4).
- 2026-06-12 (cont.): Phase 0.1–0.3 complete (commit 93cfc0b, 41 backend tests). Phase 1 started: public professor browsing + search-first landing with FAQ (commit bb849da; 9 jest + 5 playwright green, build clean).
- 2026-06-12 (course correction): Owner decision — keep Supabase Postgres; Firebase only ever for Google login. Firestore migration reverted (e6fa463) and SQLite-only cleanup re-applied on the SQLModel layer (5480736). All tests green. Production needs no env changes. Next: remaining Phase 1 landing sections + professor detail page.
- 2026-06-12 (system plan + design + HeroUI): Reviewed docs/new/{system_plan,design}.md; deviations recorded in Phase 1R. Platform upgraded to Next 15/React 19/Tailwind 4; HeroUI v3.1 adopted with the Univya navy/teal/amber + Rubik/DM Sans rebrand (d9f8a08, dd2babc). Shipped: /pricing, report-incorrect-data (backend + modal), outreach drafts (backend + modal), /board with spec stages, /compare (583895a–588eb5c). 43 backend + 9 jest + 5 playwright + build green. Remaining: HeroUI page-by-page button/filter sweep, admin reports queue UI, gated features pending owner decisions (pricing/Stripe, uploads, reviews, claims).
- 2026-06-12 (hardening): Branch renamed to `feat/production-readiness`. Phase 2 done except two owner actions (DNS for TLS cutover; key rotation): CI + gitleaks, request-id observability, proxy-aware rate limits, analytics events + admin metrics/reports panels, deploy health gates, uptime workflow, TLS compose + runbook, sitemap/robots, per-professor titles. Crawl4AI flow verified by an end-to-end durable-scan pipeline test (crawl→extract→enrich→summarize→approve→import). 45 backend + 9 jest + 5 playwright green.
- 2026-06-12 (final sweep): University/department public pages shipped (faf2957) and the HeroUI button sweep completed across all pages (bacc758). All engineering checklist items are now done or recorded decisions. Open items are owner-gated only: DNS+TLS cutover (runbook ready), secret rotation, and the four feature gates (Stripe pricing, CV/SOP uploads, public reviews, professor claims). 46 backend + 22 scraper + 9 jest + 6 playwright green.
