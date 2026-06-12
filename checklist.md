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
- [ ] Dashboard, saved, profile pages: visual audit pass (consistent shell, responsive)
- [ ] Admin pages: import monitoring, review queue tables (spec §20.5)
- [~] Accessibility: global :focus-visible outline added; still to do: contrast audit, landmark review
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
- [~] Shared components on HeroUI: LoginModal, ConfirmDialog, ReportIssueModal, OutreachDraftModal, auth forms (Modal/TextField/Input/TextArea/Button/Chip/Card). Remaining: Toast→HeroUI Toast, Filters dropdowns→Select/ListBox, tabs on detail page→Tabs, per-page button sweep
- [ ] Page-by-page sweep: landing CTAs, discover, match, dashboard, saved, profile, admin tables
- [x] All tests green after each migration step

### Feature implementation (spec §30 MVP, buildable now)
- [x] Pricing page /pricing (spec §23 + design §8.4) — public, trust copy, HeroUI cards/chips (583895a)
- [x] Report incorrect data (spec §14.6): reports table, POST /api/reports, admin list/resolve endpoints, ReportIssueModal on professor detail (583895a). Remaining: admin queue UI panel
- [x] Outreach email drafts (spec §17): POST /api/outreach-drafts (LLM-grounded, draft-only, never auto-send, personalization checklist) + modal on professor detail (583895a)
- [ ] Application board with stages (spec §16): board page on tracker_rows state, stage select (accessible alternative to drag)
- [ ] Compare professors (spec §15.6): compare view from saved professors
- GATED (per docs, owner decision needed): Stripe billing (pricing undecided), CV/SOP uploads (privacy gates), public reviews (trust/legal gates), professor claims (verification design)

## Phase 2 — Production hardening (launch gates from doc.md §7.5)

- [ ] Rate limiting backed by something durable (current: in-memory per-process)
- [ ] Structured error responses audited; no stack traces leaked
- [ ] HTTPS for backend (droplet currently plain `http://137.184.16.45`; needs domain + TLS via Caddy or DO App Platform)
- [ ] Secrets audit: rotate any keys committed/leaked (`.env` contains live OpenRouter/Supabase secrets)
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
- 2026-06-12 (cont.): Phase 0.1–0.3 complete (commit 93cfc0b, 41 backend tests). Phase 1 started: public professor browsing + search-first landing with FAQ (commit bb849da; 9 jest + 5 playwright green, build clean).
- 2026-06-12 (course correction): Owner decision — keep Supabase Postgres; Firebase only ever for Google login. Firestore migration reverted (e6fa463) and SQLite-only cleanup re-applied on the SQLModel layer (5480736). All tests green. Production needs no env changes. Next: remaining Phase 1 landing sections + professor detail page.
