# Production Readiness Checklist — ProfMatch → Univya

Derived from `docs/new/doc.md` (PRD/BRD/QA pack) and `docs/new/spec.md` (full product spec) in the planning repo,
plus the current state of this codebase. Work proceeds top to bottom; phases gate each other.

Deployment shape: backend on DigitalOcean (auto-deploy on `main`), frontend on Vercel (auto-deploy on `main`),
data platform moving to **Firebase** (Firestore + Firebase Auth). Nothing lands on `main` until verified.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked (reason noted)

---

## Phase 0 — Cleanup & Firebase migration (CURRENT)

### 0.1 Remove legacy persistence
- [~] Replace SQLModel/SQLAlchemy data layer (`app/db/__init__.py`) with Firestore client layer
- [ ] Remove SQLite fallback, `db/professor_match_publications.sqlite` seed, `load_data.py`
- [ ] Remove Supabase/Postgres env plumbing (`SUPABASE_*`, `DATABASE_URL`) from code, `.env.example`, compose files, `.do/app.yaml`
- [ ] Remove sqlite seed/volume logic from `docker-compose*.yml` and backend Dockerfile
- [ ] Drop `sqlmodel`/`psycopg` from `requirements.txt`; add `firebase-admin`

### 0.2 Firebase foundation
- [~] Firestore client init from env: `FIREBASE_SERVICE_ACCOUNT_JSON` (inline JSON), `GOOGLE_APPLICATION_CREDENTIALS` (path), or emulator (`FIRESTORE_EMULATOR_HOST`)
- [ ] In-memory store implementation for tests/local dev without credentials
- [ ] Collections: `users`, `sessions`, `professors`, `publications`, `student_profiles`, `scan_jobs`, `scrape_runs`, `onboarding_jobs`
- [ ] Port models from SQLModel tables to plain Pydantic documents (string IDs)
- [ ] Migration script: export Supabase Postgres → import to Firestore (one-time, run before cutover)

### 0.3 Service/API ports (keep REST contract stable for frontend)
- [ ] `auth_service` + `api/auth` (users, sessions, account deletion)
- [ ] `professor_service` + `api/professors` (list/search/filters/facets/detail)
- [ ] `university_service` + `api/universities`, `api/stats`
- [ ] `student_profile_service` + `api/student_profiles`
- [ ] `match_service` + `api/match`/`api/matches` (replace SQLite FTS shortlist with in-memory scoring)
- [ ] `recommendation_service` + `api/recommendations`
- [ ] `scan_job_service`, `scrape_run_service`, `scan_task_runner`, `workers/scan_worker`
- [ ] `agentic_onboarding_service` publish step (currently "publish to SQLite")
- [ ] `admin_scan_service`, `import_service`, `durable_agentic_scan_service`, `api/admin`
- [ ] Port backend tests (conftest currently builds a SQLite engine)

### 0.4 Cutover (requires user/console action — flag before merge)
- [!] `FIREBASE_SERVICE_ACCOUNT_JSON` set on DigitalOcean backend env — **no Firebase credentials found locally; must be set in DO console**
- [!] Data migrated from Supabase to Firestore (run 0.2 migration script with creds)
- [ ] Merge branch → main, verify deploy health (`/health`, `/api/stats`)
- [ ] Decommission Supabase database after verification window

## Phase 1 — UI revamp

- [ ] Design system pass: typography, spacing, color tokens in `globals.css` (Tailwind), consistent with `design_reference/`
- [ ] Landing page per spec §21: hero + search-first, problem section, how-it-works, free-vs-paid clarity, FAQ
- [ ] Professor cards (spec §11.5): photo, tags, confidence badge, recruiting status, AI summary snippet
- [ ] Professor detail page (spec §10): header, labeled "AI Summary", tags, recent papers with confidence labels, source links, actions
- [ ] Discover/search page: filters (university, department, tags, recruiting), sort, empty states, skeletons
- [ ] Match/intake flow polish: threshold controls (defaults 40% / min 10), match explanation display, evidence, mismatch notes
- [ ] Dashboard, saved, profile pages: consistent shell, responsive, dark-mode sanity
- [ ] Admin pages: import monitoring, review queue tables (spec §20.5)
- [ ] Accessibility pass: focus states, contrast, semantic landmarks
- [ ] Update Jest + Playwright tests for revamped UI; capture QA screenshots

## Phase 2 — Production hardening (launch gates from doc.md §7.5)

- [ ] Rate limiting backed by something durable (current: in-memory per-process)
- [ ] Structured error responses audited; no stack traces leaked
- [ ] HTTPS for backend (droplet currently plain `http://137.184.16.45`; needs domain + TLS via Caddy or DO App Platform)
- [ ] Secrets audit: rotate any keys committed/leaked (`.env` contains live OpenRouter/Supabase secrets — rotate after cutover)
- [ ] Health checks + uptime monitoring; deploy alerts
- [ ] Logging/observability: request logs, import job logs, error tracking
- [ ] Backups/export strategy for Firestore
- [ ] CI: backend pytest + frontend jest/build on PR (`.github/` exists — verify and extend)
- [ ] Analytics instrumentation (doc.md §7.3 core events: search, profile open, save, match, draft)

## Phase 3 — Product completion toward Univya MVP (spec §30)

### Free/public tier
- [ ] Public professor pages without login (verify), SEO meta/titles (spec §10.4), sitemap
- [ ] University & department public pages (spec §22)
- [ ] Keyword search + filters as free tier; confidence labels visible
- [ ] Report incorrect data flow (spec §14.6) + admin report queue
- [ ] Request university/department flow (spec §14.7)

### Paid tier (after pricing decision)
- [ ] Paywall/upgrade modal flow (spec §23.4); free-vs-paid gating per spec §34.1
- [ ] Personalized matching with thresholds (40%/10% defaults) — exists, gate + polish
- [ ] Saved professors + comparison view (spec §15.6)
- [ ] Kanban application board (spec §16, default stages)
- [ ] CV/SOP upload + extraction → student research profile (private storage, signed URLs, deletion policy spec §26)
- [ ] Outreach email drafting (spec §17) — draft only, never auto-send
- [ ] Payments integration (provider TBD), referral system (spec §24: 20% invitee / 50% cap referrer)

### Admin & data pipeline
- [ ] Agentic import: confidence scoring bands (spec §9.9), auto-publish vs review queues
- [ ] Field-level provenance storage (spec §9.11)
- [ ] Duplicate detection + merge flow (spec §20.7)
- [ ] Tag canonicalization + alias system + admin tag management (spec §13)
- [ ] Six-month refresh cron + manual refresh triggers (spec §27)
- [ ] Admin dashboard: report queue, dispute queue, refresh status (spec §20)

### Professor-side (recommended before broad launch)
- [ ] Professor claim flow w/ institutional email verification (spec §19.1)
- [ ] Professor-added fields shown separately from Univya-generated data
- [ ] Recruiting status controls + last-updated dates

### Reviews (CONDITIONAL — high risk, launch gate per doc.md §6)
- [ ] Do not build public written reviews until moderation policy, dispute workflow, serious-allegation policy, and legal review are approved
- [ ] If approved: verified reviewers, relationship types, anonymous ratings aggregate-only, dispute flow

## Phase 4 — Trust, privacy, policy

- [ ] Account deletion: 30-day deactivation → permanent deletion incl. uploaded docs (spec §26.4) — partially exists, verify end-to-end
- [ ] Student profiles default private
- [ ] Crawler policy: rate limits, identifiable user-agent, source URL storage, takedown path (spec §25.1)
- [ ] AI summary labeling: "Univya AI Summary" + confidence note; no unsupported claims (recruiting/funding/admission)
- [ ] Match language audit: "research fit", never "admission chance" (FR-009)
- [ ] Privacy policy + terms of use drafts before broad launch

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
