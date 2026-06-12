# ProfMatch — Feature Inventory

Complete list of shipped functionality as of 2026-06-12 (main @ 85e77d7).
Backend: FastAPI + Supabase Postgres on a DigitalOcean droplet. Frontend:
Next.js 15 / React 19 / HeroUI v3 on Vercel. Auto-deploy on `main` for both.

## 1. Public discovery (no login required)

- **Landing page** (`/`): search-first hero with example topic chips routing
  to the directory, product preview, without/with comparison, how-it-works,
  feature panels, department-request banner, FAQ, footer CTAs.
- **Professor directory** (`/professors`): debounced keyword search across
  name/title/department/university/research text; multi-select filters
  (tags, universities, departments) with search-in-filter; recruiting-status
  filter; six sort orders; cursor-based "load more"; URL-param seeding
  (`?q= &university= &department= &tag=`) for cross-links and shared URLs;
  empty states and skeleton loaders.
- **Professor profile** (`/professors/[id]`): sticky header (photo, title,
  department, email, save/draft/report actions) that compacts on scroll;
  AI research summary explicitly labeled with provenance note and source
  link; canonical-ish research tags; recruiting signal with evidence;
  banded source-confidence chip (high ≥0.85 / medium ≥0.65 / low, exact %
  in tooltip); publications tab with per-paper author-match confidence,
  venue/year/source, abstracts; external links (homepage, faculty profile,
  Google Scholar, DBLP); match-insight banner for logged-in users with a
  prior match run; per-professor SEO page titles.
- **Universities directory** (`/universities`): all indexed institutions
  with department/professor/publication counts, client-side filter.
- **University page** (`/universities/[slug]`): department list with counts,
  breadcrumbs, link to prefiltered directory search.
- **Department page** (`/universities/[slug]/[department]`): full professor
  listing with save actions and login gating.
- **Pricing** (`/pricing`): free-vs-paid cards with trust copy (professors
  never pay for ranking; research fit ≠ admission chance).
- **SEO**: dynamic `sitemap.xml` (every professor, university, department
  page), `robots.txt` excluding app/admin routes, per-page titles.

## 2. Accounts & authentication

- Email/password signup and signin (PBKDF2-SHA256, 210k iterations);
  HttpOnly session cookies (14-day), server-side session revocation.
- Public/anonymous shell vs authenticated shell with role-aware nav
  (admin link for admins); `?next=` return URLs.
- Server-synced user state: student profile, saved professors, last match
  response, board tracker rows (works across devices).
- Account deletion: immediate deactivation + session revocation, then
  **permanent purge after the 30-day recovery window** (hourly worker job).
- Per-client rate limiting (proxy-aware), tighter buckets on auth routes.

## 3. Research-fit matching (logged-in)

- Student research profile: background, interests, target degree,
  preferred locations/universities/departments, photo.
- Deterministic, explainable scoring: lexical shortlist → weighted
  components (research-text similarity, recent-publication similarity,
  recruiting signal, department/title relevance, location preference,
  metadata boost/penalties).
- **Threshold controls**: match-percent threshold (default 40%) with
  top-N fallback (default 10) and status explanation.
- Per-match evidence: matched terms, tags, relevant publications with
  similarity scores and abstract snippets, recruiting evidence, risk
  notes ("recruiting unknown", "low source confidence", …).
- Optional LLM re-rank (OpenRouter free models) with ranking reasons,
  risks/uncertainties, suggested outreach angle.
- Language guarantee: "research fit" everywhere, never admission chance.

## 4. Workflow tools (logged-in)

- **Saved professors** (`/saved`): shortlist with filters/sort, links into
  compare and board.
- **Compare** (`/compare`): pick 2–4 saved professors; side-by-side table of
  research fit, university/department, recruiting, confidence band,
  publication count, tags, summaries.
- **Application board** (`/board`): spec's 15 default stages (Discovered →
  Archived), accessible stage select (non-drag), per-card notes, one-click
  import of saved professors, server-persisted.
- **Outreach drafts**: per-professor LLM drafts grounded only in stored
  evidence; six purposes (PhD inquiry, Master's, undergrad, RA, intro,
  follow-up); subject + body + suggested paper + personalization
  checklist; copy-to-clipboard; explicit never-auto-send reminder;
  refuses to draft without a research profile.
- **Report incorrect data**: nine reason categories, description, optional
  evidence URL → admin queue.
- **Request department** (`/recommend`): university/department/faculty-URL
  requests with SSRF-safe URL validation → admin list.

## 5. Admin operations (role-gated)

- **Dashboard** (`/admin`): indexed departments table (professor and
  publication counts) with per-department actions: rescan faculty page,
  fetch 10 OpenAlex publications (SSE progress), regenerate AI profiles,
  delete (confirm-gated); user request list; **data reports queue** with
  resolve/reject; **product metrics panel** (event counts, 30 days).
- **Durable scan jobs** (`/admin/scans`): Postgres-backed job → task →
  result → log pipeline with worker leasing/heartbeats/retries; per-job
  progress, task table, log stream; candidate review with approve /
  reject / import (idempotent, dedupe-keyed); OpenAlex publication
  refresh per job.
- **Agentic onboarding** (`/admin/onboarding`): Crawl4AI + LLM wizard —
  roster extraction, per-profile extraction, homepage enrichment,
  DBLP/Semantic Scholar publications, AI summaries, publish; automatic
  or step-by-step; live SSE job streaming.
- Legacy adapter scans with QA artifacts (validation/manifest/audit) and
  QA-gated import.

## 6. Data pipeline & trust

- **Crawl4AI is the crawler** for all ingestion (roster, profile,
  homepage pages); identifiable `ProfMatchBot/1.0` user-agent with
  policy link + contact (env-overridable); published crawler policy
  (scope, rate, takedown path) in `docs/policies/crawler-policy.md`.
- Artifact-first imports: every candidate requires admin review before
  touching canonical tables; raw artifacts retained for audit.
- Source provenance: source URLs stored per profile, photo-source and
  profile-text-source surfaced in UI; QA issue flags (missing email/URL).
- OpenAlex enrichment with author-match confidence; DBLP/Semantic Scholar
  fallbacks; duplicate detection on import.
- End-to-end pipeline test (crawl → extract → enrich → summarize →
  approve → import) in CI.

## 7. Analytics

- Privacy-safe first-party events (`/api/events`): allowlisted names,
  size-clamped properties, no raw queries/emails/document content.
- Wired: search_performed, profile_opened, professor_saved (per surface),
  outreach_draft_generated, report_submitted, board_card_moved.
- Admin metrics endpoint + dashboard panel.

## 8. Platform & operations

- CI on every PR/branch: backend pytest (47), scraper unittests (22),
  frontend tsc/jest (9)/build, gitleaks secret scan.
- E2E: 6 Playwright flows (landing, anonymous browse, signup→intake,
  design screenshots, admin dashboard, university pages).
- Deploys: droplet workflow with post-deploy health gates
  (`/health`, `/api/health/db`); scheduled 30-min uptime checks;
  TLS-ready compose + cutover runbook (waiting on domain).
- Observability: structured JSON access logs, X-Request-ID on every
  response and in error envelopes, standard error envelope.
- Design system: HeroUI v3 components on the Univya tokens (Rubik +
  DM Sans, navy/teal/amber/slate); keyboard focus outlines; banded
  confidence chips; toasts; modals with focus trapping.

## Gated / not built (owner decisions)

Stripe billing + paid gating (pricing undecided) · CV/SOP uploads
(privacy gates) · public reviews (moderation/legal gates) · professor
claim flow (verification rules) · privacy policy & ToS (legal) ·
domain + HTTPS cutover (DNS) · field-level provenance table, tag
canonicalization, six-month refresh cron (deferred engineering).
