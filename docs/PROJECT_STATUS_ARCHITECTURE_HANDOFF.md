# Professor Match — Comprehensive Project Status, Architecture, Deployment, and Handoff

_Last updated: 2026-05-31_

This document is a concrete, operational handoff for the current Professor Match application. It is written to answer the immediate questions about which Git directory is authoritative, why there are extra files in another folder, what has been built, what remains unfinished, how deployment currently works, what is stored in SQL/Supabase versus local browser or filesystem state, what `AGENTS.md` requires, and what the realistic production-readiness status is.

This file intentionally does **not** include secrets, passwords, full Supabase URLs, OpenRouter keys, Render keys, Vercel tokens, or any environment values that should not be committed. Use `.env` locally and provider dashboards for production secrets.

---

## 1. Executive summary

Professor Match is a professor discovery and graduate-advisor matching application for prospective MS and PhD applicants. The product lets a student create an academic profile, search a database of professors, generate ranked professor matches, inspect why a professor matched, review recent-publication evidence, save professors to a shortlist, and recommend additional universities or departments to add.

The current application is no longer just an initial local prototype. It has a working Next.js frontend, a FastAPI backend, authentication, user-state persistence, a migrated Supabase Postgres database, a deployed Vercel frontend, and a deployed Render backend. However, it is **not yet production-grade** in the sense of reliability, persistent background jobs, image storage, secure-cookie settings, and always-on backend availability. Render Free works for demos and MVP validation, but it sleeps and can be slow or unavailable after inactivity. If the goal is a real production app with public sign-up flows, Render Free should be replaced or upgraded, and several security/reliability improvements should be completed before inviting real users.

The authoritative Git working directory for deployment and pushing is:

```txt
/home/drl/pi-agent/profmatch-clean-git
```

The current active branch in that directory is:

```txt
postgres
```

The remote for that directory is:

```txt
git@github.com:bidwat/ProfMatch.git
```

The older/current shell directory where some commands were run is:

```txt
/home/drl/pi-agent/pi-prof-idea
```

That directory is **not** the clean deployment repository. It contains many modified and untracked files from earlier design/audit/work-in-progress activity. Those extra files explain the “new items here” confusion. The clean repo is `../profmatch-clean-git`, not the original `pi-prof-idea` folder. Pushes for the app should be from `profmatch-clean-git` on the `postgres` branch unless you intentionally decide to change the deployment branch.

As of this document, `profmatch-clean-git` has a clean working tree after the recent skeleton-loader and UI updates. A new documentation file, this one, is now the only expected new work item unless further edits occur.

---

## 2. Direct answers to the immediate questions

### 2.1 Which Git folder are we pushing?

Push from:

```bash
cd /home/drl/pi-agent/profmatch-clean-git
git status
git push origin postgres
```

Do **not** push from:

```bash
/home/drl/pi-agent/pi-prof-idea
```

unless you intentionally want to resurrect or merge the old working directory. That older folder has a large set of unrelated modified and untracked files. It is not the clean deployment source we have been using for Vercel/Render/Supabase work.

### 2.2 Why are there new items “here”?

The terminal session initially started inside:

```txt
/home/drl/pi-agent/pi-prof-idea
```

That folder contains many changes and untracked items, including design reference screenshots, visual audit screenshots, docs, frontend files, backend changes, and migration/deployment artifacts. Those are likely accumulated from earlier phases of development. When `git status` is run there, it shows many new and modified files. This is expected for that folder but it is not the clean deployment repo.

The folder we switched to for the actual app is:

```txt
/home/drl/pi-agent/profmatch-clean-git
```

That repo is clean, has the actual Git remote configured, and is on branch `postgres`. The recent work has been applied and committed there, including:

- Render/Vercel deployment support.
- Supabase/Postgres support.
- Crawl4AI dependency deployment fixes.
- Landing page refresh.
- Skeleton loader improvements.
- User-facing copy cleanup.
- Modal behavior fixes.

### 2.3 What is the backend deployment status?

The backend is currently deployed to Render Free:

```txt
https://profmatch-backend.onrender.com
```

Render Free is acceptable for demos and early MVP testing, but it is not ideal for production because:

- It sleeps when idle.
- First request after sleep can take roughly 30–60 seconds.
- Background tasks can be interrupted by restarts/redeploys.
- Local files written in the container are not durable.
- Reliability and latency are not suitable for public sign-up flows without user-facing degradation.

If the plan is to make this a production app with sign-up flows, the backend should move to an always-on host or paid tier, or the architecture should be adjusted so the public-facing app has no fragile always-on backend requirement. Practical options are discussed later in this document.

### 2.4 What are we storing in SQL versus Supabase?

The phrasing is slightly confusing because Supabase Postgres **is** SQL. The project has two database modes:

1. **Production / deployed persistence:** Supabase Postgres, accessed through SQLAlchemy/SQLModel using `DATABASE_URL` or Supabase pooler env vars.
2. **Local fallback:** SQLite file under `db/`, used when no Postgres/Supabase env vars are set.

So the distinction is not “SQL versus Supabase.” It is:

- **Supabase Postgres SQL** for production persistent app data.
- **SQLite SQL** for local fallback/development.
- **Browser localStorage** for client-side quick restore/cache.
- **Render filesystem** for temporary agentic onboarding job artifacts, which is not production-durable.
- **No Supabase Storage yet** for profile pictures.

### 2.5 What is the actual status of production readiness?

The app is a functional MVP with deployment plumbing. It is **not yet production hardened**.

Ready or mostly ready:

- User registration and login exist.
- Sessions are stored server-side and represented client-side with an HTTP-only cookie.
- Student profile and saved professor state persist in the database.
- Professor data and publication data are in Supabase Postgres.
- The frontend is deployable to Vercel.
- The backend is deployable to Render Docker.
- The app builds and lints successfully.

Not yet production-grade:

- Backend hosting on Render Free is unreliable due to sleep/cold starts.
- Cookie settings need production-specific `secure=True` handling.
- Profile photos are stored as base64 data URLs in profile JSON, not real file objects.
- Agentic onboarding job files are written to local container filesystem and should be moved to Postgres or object storage.
- No formal migration system like Alembic is in place; tables are created through SQLModel metadata.
- Rate limiting is in-memory, so it resets on restart and is not distributed.
- Admin onboarding flows are powerful but still experimental.
- Production monitoring, error reporting, backups, and rollback playbooks need to be made explicit.

---

## 3. Repository map and Git situation

### 3.1 Directory map around this project

The parent directory contains multiple projects:

```txt
/home/drl/pi-agent/
  pi-prof-idea/
  profmatch-clean-git/
  bidwat-pm-resume-agent-v3/
  hiring-cafe-scraper/
  nidhi/
  pi-dynamic-blog/
  pi-job-apps/
  ...
```

The relevant directories are:

```txt
pi-prof-idea         Older/original working directory with many uncommitted artifacts.
profmatch-clean-git  Clean Git repo tied to GitHub remote and deployment branch.
```

### 3.2 Authoritative repository

Use:

```txt
/home/drl/pi-agent/profmatch-clean-git
```

Current branch:

```txt
postgres
```

Remote:

```txt
origin git@github.com:bidwat/ProfMatch.git
```

This repo is the one to push to GitHub and use for deployment. It is also the repo where the final app changes have been made.

### 3.3 Non-authoritative / older working directory

The current shell originally sat in:

```txt
/home/drl/pi-agent/pi-prof-idea
```

That folder is a Git repo on `main` with many modified and untracked files. It includes design references and visual audit artifacts, among other things. It is useful for historical reference, screenshots, and imported design assets, but should not be used as the deployment source unless a deliberate merge/migration is planned.

If you see a massive `git status` in `pi-prof-idea`, that does not mean the clean app deployment repo is dirty. It means you are in the wrong folder for production deployment.

### 3.4 Recommended Git workflow from here

For any production work:

```bash
cd /home/drl/pi-agent/profmatch-clean-git
git status -sb
git pull --ff-only origin postgres
# make changes
git status -sb
git add <files>
git commit -m "clear message"
git push origin postgres
```

Before pushing, ensure:

- `.env` is not committed.
- No project-specific Supabase URL, pooler host, project ref, DB password, OpenRouter key, or Render/Vercel secret is committed.
- `.env.example` uses placeholders only.
- The frontend builds.
- Backend starts locally when appropriate env vars are present.

---

## 4. Product overview

Professor Match helps prospective graduate applicants find faculty advisors whose recent research aligns with their interests and background. The product is centered on the idea that recent papers and structured evidence are better than manually browsing stale department pages.

### 4.1 Primary user

The primary user is a prospective MS/PhD applicant in computer science or an adjacent computational field. They are trying to identify which professors might be relevant advisors, understand why those professors fit, and keep an organized shortlist.

### 4.2 Core user value

The app reduces manual research time by combining:

- A searchable professor directory.
- Recent publication context.
- Research summaries and tags.
- Matching explanations.
- Saved professor shortlists.
- Academic profile-driven recommendations.

Instead of opening dozens of university faculty pages, Google Scholar profiles, lab pages, and spreadsheets, the user can browse and compare professors from a unified interface.

### 4.3 Main user-facing flows

1. **Landing page**
   - Explains the value proposition.
   - Shows product screenshots.
   - Emphasizes professor discovery and evidence-backed matching.

2. **Signup/signin**
   - Users create accounts or sign in.
   - Session is handled with HTTP-only cookie authentication.

3. **Academic profile**
   - User enters name, email, target degree, target department, highest degree, academic background, areas of interest, preferred universities, and preferred locations.
   - Profile can include a profile photo, currently stored as a base64 data URL in state.

4. **Discover**
   - User searches and filters professor records.
   - Filters include tags, universities, departments, recruiting status, and sort options.

5. **Match**
   - User gets ranked professor recommendations.
   - Each match explains relevant research overlap and publication evidence.

6. **Professor detail**
   - User sees title, department, university, contact links, tags, source confidence, recruiting signal, summary, and recent publications.

7. **Saved**
   - User saves and revisits professors.

8. **Recommend universities/departments**
   - User can suggest a university, department, and faculty page URL to add later.

### 4.4 Admin-facing flows

Admin functionality exists but should be treated as operational tooling, not the primary public product:

- Scan dashboard.
- Agentic onboarding wizard.
- Indexed department management.
- Recommendation review.
- Scan artifact inspection.
- Refresh/delete indexed departments.

The admin pipeline is useful for internal data operations but still has production caveats because agentic job artifacts are not yet durable on Render Free.

---

## 5. Frontend architecture

### 5.1 Stack

The frontend is a Next.js application using the App Router, TypeScript, and CSS/Tailwind-style global classes. It lives in:

```txt
apps/frontend
```

Important files:

```txt
apps/frontend/app/layout.tsx
apps/frontend/app/globals.css
apps/frontend/components/AppShell.tsx
apps/frontend/lib/api.ts
apps/frontend/lib/local-store.ts
apps/frontend/lib/types.ts
```

### 5.2 Routing and pages

The main pages are:

```txt
/                    Landing page
/signin              Sign in
/signup              Create account
/dashboard           Home dashboard after login
/profile             Academic profile
/professors          Discover/search directory
/professors/[id]     Professor detail
/match               Canonical match results page
/results             Legacy compatibility route
/saved               Saved professor shortlist
/recommend           Recommendation submission page
/admin               Admin home
/admin/scans         Scan artifacts and import review
/admin/onboarding    Agentic onboarding wizard
/admin/scrapes       Compatibility/admin route
```

### 5.3 API communication

The frontend calls relative paths like:

```txt
/api/stats
/api/professors
/api/auth/login
```

The Next.js config rewrites these to the backend:

```js
const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

rewrites() {
  return [{ source: '/api/:path*', destination: `${backendUrl}/api/:path*` }];
}
```

In production, Vercel must have:

```txt
BACKEND_URL=https://profmatch-backend.onrender.com
```

If this is missing or wrong, the frontend API calls will fail even if the UI itself loads.

### 5.4 App shell and session checks

`components/AppShell.tsx` wraps authenticated pages. It calls `/api/auth/me` to verify the HTTP-only session cookie. If the user is not authenticated and visits a protected page, it redirects to `/signin?next=<path>`.

Earlier, the app displayed text such as “Checking your session…” during this verification. That has been replaced with skeleton loaders so the experience is visually consistent.

### 5.5 Skeleton loaders and UI polish

Recent UI work added:

```txt
apps/frontend/components/Skeleton.tsx
```

Skeleton loaders are now used for:

- Global route loading.
- Protected route session verification.
- Discover list loading.
- Saved list loading.
- Professor detail loading.
- Dashboard saved-preview loading.
- Admin scan/detail loading.

The sign-in notice “Active session/local profile for ...” was removed because it was confusing and not useful to users.

### 5.6 Local browser state

The frontend uses `localStorage` through:

```txt
apps/frontend/lib/local-store.ts
```

Local storage keys include:

```txt
profmatch:user
profmatch:studentProfile
profmatch:lastMatches
profmatch:savedProfessorIds
profmatch:tracker
```

This local storage is a convenience cache for fast UI restore. It is not the source of truth when a user is authenticated. The backend database state is the durable source for user profile, saved professors, and match responses.

### 5.7 Profile photos in frontend

When a user uploads a profile photo, the browser resizes it to a 256x256 image and converts it into a base64 data URL. This data URL is stored as `photo_url` inside the student profile state.

This means profile photos are not true uploaded image files. They are JSON string data. This works for an MVP but is not ideal for production. The production fix is to use Supabase Storage or another object store, then store only a URL/path in Postgres.

---

## 6. Backend architecture

### 6.1 Stack

The backend is FastAPI with SQLModel/SQLAlchemy. It lives in:

```txt
apps/backend
```

Important files:

```txt
apps/backend/app/main.py
apps/backend/app/config.py
apps/backend/app/db/__init__.py
apps/backend/app/api/*.py
apps/backend/app/models/*.py
apps/backend/app/services/*.py
apps/backend/requirements.txt
apps/backend/Dockerfile
```

### 6.2 Application entrypoint

`apps/backend/app/main.py` creates the FastAPI app, configures CORS, installs rate limiting, sets JSON error handlers, registers routers, and creates DB tables at startup via:

```python
SQLModel.metadata.create_all(engine)
```

This approach is simple and useful for MVP development but is not a full migration system. For production evolution, the project should adopt Alembic migrations so schema changes are controlled, reversible, and reviewable.

### 6.3 Routers

Current backend routers include:

- `auth.py` — register, login, logout, current user, account delete, user state get/patch.
- `professors.py` — list/search professors, facets, professor detail.
- `match.py` — match endpoint.
- `student_profiles.py` — student profile endpoints.
- `universities.py` — university listing.
- `stats.py` — dataset stats.
- `recommendations.py` — user-submitted department/university recommendations.
- `admin.py` — admin scan/onboarding/indexed-department tools.
- `scrape_runs.py` — scrape run status/history.

### 6.4 Services

Backend service files include:

- `auth_service.py` — password hashing, session token creation/validation, revocation.
- `professor_service.py` — professor data access.
- `match_service.py` — deterministic matching and optional LLM reranking logic.
- `student_profile_service.py` — profile operations.
- `recommendation_service.py` — recommendation storage/retrieval.
- `admin_scan_service.py` — scan artifact reading.
- `import_service.py` — importing scan results.
- `scrape_run_service.py` — scrape run bookkeeping.
- `agentic_onboarding_service.py` — Crawl4AI + LiteLLM powered onboarding workflow.
- `university_service.py` — university metadata.

### 6.5 Rate limiting

Rate limiting is currently an in-memory dictionary in `main.py`. It is scoped by client IP, method, and path. Auth write endpoints have stricter limits.

This is acceptable for a single-process MVP but not production-grade because:

- It resets on restart.
- It does not coordinate across multiple instances.
- It can be bypassed by scaling or redeploying.

For production, move rate limiting to Redis, Upstash, Cloudflare, or provider-level middleware.

### 6.6 Error handling

Backend error responses are normalized into JSON structures like:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid request parameters",
    "details": []
  }
}
```

The frontend `api.ts` maps common errors to friendlier messages, including rate limits, auth errors, permission errors, and validation errors.

---

## 7. Database and persistence

### 7.1 Database selection order

The backend determines the database URL in `apps/backend/app/db/__init__.py` in this order:

1. If `DATABASE_URL` is set, use it.
2. Else, if Supabase component variables are set, build a Postgres URL.
3. Else, fall back to SQLite at `db/professor_match_publications.sqlite`.

This lets the same code run locally with SQLite and in production with Supabase Postgres.

### 7.2 Supabase Postgres

Production data is stored in Supabase Postgres. The project should connect through Supabase Session Pooler for IPv4 compatibility. In deployment, use provider environment variables, not committed files.

Production database contains professor data, publications, user accounts, sessions, user state, student profile data, match data, scrape run records, and recommendation records.

### 7.3 SQLite fallback

SQLite remains useful for:

- Local development without Supabase credentials.
- Offline inspection.
- Seed database distribution.
- Development tests.

The Dockerfile currently copies a SQLite seed DB into the image as a fallback. But production should use Supabase Postgres for durable persistence.

### 7.4 Main tables

Core tables include:

```txt
professors
publications
users
auth_sessions
user_states
student_profiles
matches
scrape_runs
```

Additional admin/recommendation-related persistence exists through service/model code, depending on current schema definitions.

### 7.5 Migrated dataset

The local handoff notes say the migration moved approximately:

```txt
professor: 1039
publication: 4358
users: 4
user_states: 4
auth_sessions: 33
scraperun: 0
studentprofile: 3
```

This means the deployed Supabase database already has a useful professor/publication corpus plus initial user/session/profile data.

### 7.6 Browser localStorage versus database

Authenticated state should be considered durable only after it is saved to the backend. The browser also stores mirrored state for responsiveness:

- User display info.
- Student profile.
- Last match response.
- Saved professor IDs.
- Tracker rows.

This is helpful but can become stale. On app load, authenticated pages call backend state endpoints to restore the server-side version.

### 7.7 Filesystem persistence

Render filesystem is not durable. The agentic onboarding service currently writes job JSON files under paths like:

```txt
data/qa/onboarding/
```

Inside Render, those files can disappear on container redeploy/restart. This is not acceptable for production workflows that users or admins depend on. Move job state to Postgres and large artifacts to object storage.

---

## 8. Authentication and account system

### 8.1 How login works

Authentication is implemented in the custom FastAPI backend, not Supabase Auth.

Flow:

1. User submits email/password.
2. Backend normalizes email.
3. Backend verifies password against a stored PBKDF2-SHA256 hash.
4. Backend creates a random session token.
5. Backend stores only a SHA-256 hash of the session token in `auth_sessions`.
6. Backend sends the raw token to the browser as an HTTP-only cookie named `profmatch_session`.
7. Future requests include the cookie automatically.
8. `/api/auth/me` validates the cookie by hashing the token and looking up an active, unexpired session.

### 8.2 Password storage

Passwords are not stored plaintext. The backend uses:

- PBKDF2-HMAC-SHA256.
- Random salt.
- 210,000 iterations.
- Constant-time comparison through `hmac.compare_digest`.

This is a reasonable MVP password-hashing approach. For production, Argon2id or bcrypt would also be acceptable, but PBKDF2 with high iteration count is not inherently wrong.

### 8.3 Session duration

Sessions are configured for 14 days through `SESSION_DAYS = 14` in `auth_service.py`.

### 8.4 Production auth concerns

The cookie currently uses:

```python
httponly=True
samesite="lax"
secure=False
```

For production HTTPS, `secure` should be `True`. The app needs environment-aware cookie config, for example:

- `secure=False` for localhost.
- `secure=True` for Vercel/Render HTTPS.

Also consider:

- CSRF review for cookie-auth state-changing endpoints.
- Password reset flow.
- Email verification.
- Account deletion behavior and data retention policy.
- Admin role assignment policy.
- Session revocation UI.

---

## 9. Matching system

### 9.1 MVP matching model

The matching system is designed as a deterministic-first pipeline:

- Build a query/profile from research interests, background, target degree, preferred universities, departments, and locations.
- Shortlist professors based on lexical/research overlap.
- Score candidates using research overlap, publication overlap, recruiting signal, metadata, and preferences.
- Return ranked matches with explanations.

### 9.2 SQLite versus Postgres matching

Local SQLite can use FTS5 when available. Production Postgres currently uses a portable lexical shortlist rather than a dedicated vector database. This was intentional to keep the MVP lightweight and deployable without paid services.

### 9.3 Optional LLM reranking

If OpenRouter is configured, optional LLM reranking can improve semantic quality for the top deterministic candidates. The current configured free model in handoff notes is:

```txt
inclusionai/ring-2.6-1t:free
```

The app should not depend on this being permanently free or available. The code includes fallback logic related to older free model issues. For production, either remove LLM dependency from the core flow or use a paid/controlled model budget with clear fallback behavior.

### 9.4 Recruiting claims

The product principle is that the app must not overclaim recruiting status. Unknown means unknown. The UI and explanations should avoid implying a professor is actively recruiting unless there is explicit evidence.

---

## 10. Data ingestion and admin onboarding

### 10.1 Existing dataset

The current deployed database has a professor/publication corpus migrated from SQLite to Supabase Postgres. The reported counts are approximately 1,039 professors and 4,358 publications.

### 10.2 Traditional scraper architecture

The original architecture expects reusable scraper adapters. Each adapter should output normalized professor records with fields such as name, title, university, department, email, profile URL, homepage URL, research text, recruiting signal, and source confidence.

### 10.3 Admin scan dashboard

The admin scan dashboard is meant to review scan artifacts before importing. It supports concepts like:

- Scan runs.
- Candidate professor counts.
- Publication counts.
- QA issues.
- Import readiness.
- Scan detail review.

### 10.4 Agentic onboarding

The agentic onboarding flow lets an admin provide a faculty directory URL. The backend uses Crawl4AI to crawl pages and LiteLLM/OpenRouter to help extract/structure data and generate summaries.

This is powerful but risky for production because:

- It relies on external LLM availability.
- It depends on crawling behavior that may fail on many sites.
- It writes job artifacts to ephemeral storage today.
- It can be slow.
- It requires careful admin-only access.

It should remain admin-only and experimental until job persistence and monitoring are improved.

---

## 11. Deployment status and production hosting concerns

### 11.1 Current deployment

Current deployment shape:

```txt
Frontend: Vercel Free
Backend: Render Free Docker web service
Database: Supabase Free Postgres via Session Pooler
```

Frontend URL:

```txt
https://prof-match-chi.vercel.app
```

Backend URL:

```txt
https://profmatch-backend.onrender.com
```

Active Git branch:

```txt
postgres
```

### 11.2 Why Render Free is not ideal

Render Free sleeps. For a production sign-up application, that creates serious user experience problems:

- Landing page may load, but API calls hang until backend wakes.
- Login/signup can feel broken.
- First authenticated page can stall.
- Health checks can appear flaky.
- Background onboarding tasks can be interrupted.

If users are signing up, a sleeping backend is not acceptable unless the UI explicitly communicates cold starts and the product is still in demo mode.

### 11.3 Better hosting options

For a production app, consider:

1. **Render paid instance**
   - Easiest migration.
   - Keeps Dockerfile and deployment shape.
   - Always-on service.
   - Minimal code changes.

2. **Fly.io**
   - Good Docker support.
   - Can run always-on with small VM.
   - More operational work.

3. **Railway**
   - Simple DX.
   - Paid usage-based hosting.
   - Good for small FastAPI services.

4. **Google Cloud Run with minimum instances**
   - Production-grade, but configuration complexity.
   - Can avoid cold starts with min instances, which costs money.

5. **AWS App Runner / ECS / Lightsail**
   - Production-capable but more ops overhead.

6. **Supabase Edge Functions or Vercel serverless**
   - Could reduce backend hosting needs, but the current backend uses Python, Crawl4AI, Playwright/Patchright, and long-running tasks, so a direct migration is nontrivial.

The fastest production improvement is likely a paid always-on Render service or equivalent Docker host.

### 11.4 Environment variables

Vercel needs:

```txt
BACKEND_URL=<backend-url>
```

Backend host needs:

```txt
DATABASE_URL=<Supabase Session Pooler Postgres URL>
ALLOWED_ORIGINS=<allowed frontend origins>
OPENROUTER_API_KEY=<optional OpenRouter key>
OPENROUTER_MODEL=<optional model>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Do not commit these values.

---

## 12. What `AGENTS.md` contains and requires

`AGENTS.md` is the orchestration instruction file for coding agents working on this repo. It is not product code, but it describes how future AI-agent work should be done.

Key points from `AGENTS.md`:

### 12.1 Canonical docs

Agents must ground work in:

```txt
docs/product/PRD.md
docs/product/ACCEPTANCE_CRITERIA.md
docs/product/DOD_DND.md
docs/architecture/SPEC.md
docs/agents/AGENT_AND_SKILL_SETUP_PLAN.md
```

The instruction explicitly says not to rely on hidden chat history.

### 12.2 Orchestrator role

The main agent should:

1. Read relevant canonical docs before planning.
2. Choose specialist agents when appropriate.
3. Keep writes single-threaded unless using isolated worktrees.
4. Ask product/architecture questions instead of silently expanding scope.
5. Run QA before calling a task done.
6. Run or summon `agent-sync-agent` after changing agent files, skills, or orchestration instructions.

### 12.3 Context-mode requirement

`AGENTS.md` asks agents to use context-mode tools for large output, tests, logs, data files, docs, API calls, screenshots, Playwright snapshots, and anything that might exceed about 20 lines. If those tools are not available, agents should keep outputs summarized.

### 12.4 Local-first and free deployment rules

The file says:

- Use SQLite for local development by default.
- Use Supabase Free Postgres for free-tier deployed persistence.
- Do not rely on free app-host filesystem persistence for production data.
- Prefer providers that stop/sleep/pause/fail at free limits rather than surprise billing.
- No paid APIs.
- No aggressive scraping.
- No large-scale Google Scholar scraping.
- Store raw scraped data in `data/raw/` and normalized data in `data/processed/` before DB insertion.
- Every inferred claim needs source/confidence.
- Do not claim a professor is recruiting without evidence.
- Keep database access behind service/repository layers.
- Frontend must not invent fields unsupported by backend data.

### 12.5 Supabase Postgres flow

`AGENTS.md` describes the database config order:

1. `DATABASE_URL`.
2. Supabase component variables.
3. Local SQLite fallback.

It also documents the shape of Supabase variables but does not include real secrets.

### 12.6 Specialist agents

It lists specialist agents such as:

- `product-agent`
- `spec-agent`
- `agent-sync-agent`
- `data-architect-agent`
- `scraper-agent`
- `backend-agent`
- `frontend-agent`
- `matching-agent`
- `qa-agent`
- `docs-agent`

It also lists Pi chain workflows:

- `full-mvp-slice`
- `add-scraper-adapter`
- `backend-frontend-feature`

### 12.7 Definition of done

A task is done only when relevant checks in `docs/product/DOD_DND.md` pass and QA evidence is recorded. For MVP features, prefer updating `docs/qa-reports/latest.md` with PASS/PARTIAL/FAIL evidence.

---

## 13. Recent work completed in this session

Recent completed changes include:

1. **Landing page revitalization**
   - Expanded short landing page into a fuller product marketing page.
   - Used product screenshots.
   - Removed internal/admin/data-pipeline language from user-facing landing copy.
   - Removed technical terms such as FTS5/BM25 from customer-facing text.
   - Made landing copy focus on student outcomes.

2. **Landing card layout fixes**
   - Equalized product preview cards so Discover does not appear much taller than the other screenshot cards.
   - Equalized two feature panels: “Built around the decisions students actually make” and “Spend more time evaluating fit, less time collecting links.”

3. **Profile recommendation wording**
   - Changed “Add Universities and Departments” to “Recommend Universities and Departments.”

4. **Modal behavior**
   - Login modal closes on outside click and Escape.
   - Confirm dialog closes on outside click and Escape.
   - Recommend modal closes on outside click and Escape.

5. **Skeleton loaders**
   - Added reusable skeleton component.
   - Replaced generic loading messages in several places.
   - Replaced AppShell “Checking your session...” with skeleton loader.

6. **Sign-in cleanup**
   - Removed confusing “Active session/local profile for ...” notice.

7. **Makefile and env cleanup**
   - Added easy `make backend` and `make frontend` commands.
   - Avoided shell-sourcing `.env` to protect passwords with special characters.
   - Removed project-specific Supabase values from `.env.example` and Makefile.

8. **Supabase local DB URL fix**
   - Fixed local `DATABASE_URL` encoding issue by rebuilding it from password with correct URL encoding.
   - Confirmed local backend can connect to Supabase Postgres.

9. **Build validation**
   - Frontend lint and build pass after the latest changes.

---

## 14. Known gaps and production TODOs

This is the most important section if the goal is a real public sign-up product.

### 14.1 Replace Render Free for production

Render Free is the biggest operational risk. Move backend to an always-on service before public launch.

Minimum acceptable improvement:

- Upgrade Render to a paid always-on web service.

Better medium-term improvement:

- Use a production Docker host with monitoring, predictable restarts, logs, and alerting.

### 14.2 Secure cookies in production

Update cookie handling so production cookies use:

```txt
Secure=true
HttpOnly=true
SameSite=Lax or Strict depending on deployment
```

Because frontend and backend are on different domains but API calls are proxied through Vercel rewrites, `SameSite=Lax` may continue to work, but this should be tested carefully.

### 14.3 Migrations

Replace `SQLModel.metadata.create_all` as the primary schema management strategy with Alembic migrations.

### 14.4 Profile image storage

Move profile pictures out of JSON/base64 and into object storage. Supabase Storage is the natural fit because Supabase is already used for Postgres.

### 14.5 Durable admin job storage

Move agentic onboarding job state from container filesystem to Postgres. If artifacts are large, store them in object storage and keep references in Postgres.

### 14.6 Monitoring and logging

Add:

- Error reporting.
- Uptime monitoring.
- Backend health checks.
- Slow endpoint tracking.
- Database connection monitoring.
- Deployment rollback notes.

### 14.7 Backups

Confirm Supabase backup strategy. Free tier backups may not satisfy production expectations. For real users, define backup frequency and restore process.

### 14.8 Auth product features

Add or plan:

- Password reset.
- Email verification.
- Change password.
- Session/device management.
- Admin user management.
- Privacy policy and terms.

### 14.9 Data quality workflow

The dataset exists, but production credibility depends on maintaining quality:

- Periodic stale-data checks.
- Broken link checks.
- Duplicate detection.
- Source-confidence review.
- Publication refresh schedule.
- Clear disclaimers about recruiting uncertainty.

### 14.10 Cost and API dependency strategy

No paid APIs is an MVP constraint. For production, decide whether to:

- Keep no-paid-API mode with lexical matching only.
- Add paid LLM reranking with budget controls.
- Add local embeddings.
- Use batch enrichment offline rather than runtime LLM calls.

---

## 15. Recommended production roadmap

### Phase 1 — Stabilize deployment

- Move backend off Render Free or upgrade Render.
- Set production cookie security.
- Verify CORS and Vercel rewrite behavior.
- Add health check and uptime monitor.
- Confirm Supabase connection pooling.
- Confirm latest `postgres` branch is deployed.

### Phase 2 — Harden auth and user persistence

- Add password reset.
- Add email verification if public sign-ups are enabled.
- Move profile photos to Supabase Storage.
- Add privacy/terms pages.
- Review account deletion behavior.

### Phase 3 — Database operations

- Add Alembic migrations.
- Document schema and migration process.
- Confirm backups.
- Add seed/load scripts that are safe against accidental data loss.

### Phase 4 — Data quality and admin durability

- Move agentic onboarding job state to Postgres.
- Add job status persistence.
- Add admin audit logs.
- Add scan/import history persistence.
- Create a scheduled publication refresh process.

### Phase 5 — Product polish

- Improve match explanations.
- Improve saved professor workflows.
- Add compare view if desired.
- Add outreach tracking only if it is actually implemented and product-approved.
- Add onboarding guidance for new users.

---

## 16. Local runbook

From the clean repo:

```bash
cd /home/drl/pi-agent/profmatch-clean-git
```

Backend:

```bash
make backend
```

Frontend:

```bash
make frontend
```

Frontend URL:

```txt
http://localhost:3000
```

Backend URL:

```txt
http://127.0.0.1:8000
```

Check environment mode:

```bash
make env-check
```

Frontend validation:

```bash
npm --prefix apps/frontend run lint
npm --prefix apps/frontend run build
```

Backend tests:

```bash
apps/backend/venv/bin/python -m pytest apps/backend/tests -q
```

---

## 17. Deployment runbook

### 17.1 Push code

```bash
cd /home/drl/pi-agent/profmatch-clean-git
git status -sb
git add <changed-files>
git commit -m "message"
git push origin postgres
```

### 17.2 Vercel

Vercel should be configured with:

```txt
Root Directory: apps/frontend
Framework: Next.js
Build Command: npm run build
Install Command: npm install
Output Directory: leave blank
```

Environment:

```txt
BACKEND_URL=<backend public URL>
```

### 17.3 Backend host

Current Render deployment uses `apps/backend/Dockerfile`.

Backend environment variables should include:

```txt
DATABASE_URL=<Supabase session pooler Postgres URL>
ALLOWED_ORIGINS=<frontend origins>
OPENROUTER_API_KEY=<optional>
OPENROUTER_MODEL=<optional>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

For production, replace Render Free with always-on hosting or upgrade.

---

## 18. Final current-state assessment

Professor Match is a strong MVP. The core user journey exists: landing page, sign-up, profile, discover, matching, professor detail, saved list, and recommendations. The database is migrated to Supabase Postgres. The frontend and backend can be deployed. The UI has been cleaned up substantially and now uses skeleton loading states rather than generic messages.

The biggest issue is not whether the code can run; it can. The biggest issue is production reliability. Render Free is not good enough for a public production application with sign-ups. The app also needs production security hardening around cookies, password lifecycle, image storage, durable admin jobs, migrations, and monitoring.

The clean deployment repo is `profmatch-clean-git`, branch `postgres`. The old `pi-prof-idea` directory should be treated as historical work/reference and not pushed unless intentionally reconciled. The next meaningful production step is to choose an always-on backend hosting strategy and harden authentication/session/image persistence before inviting real users.
