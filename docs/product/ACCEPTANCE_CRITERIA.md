# Acceptance Criteria — Professor Match Local MVP

## Product Acceptance

- A user can search professors by name, university, title, department, and research keywords.
- A user can open a professor profile and inspect source-backed profile data.
- A user can submit a student profile and receive ranked professor matches.
- Each match includes a readable explanation based on recent research overlap and profile data.
- Unknown recruiting status is displayed honestly as unknown.

## Data Acceptance

- At least 10 seed universities are represented in `data/seeds/universities.csv`.
- At least 3 scraper adapters are implemented before scaling to 10 schools.
- Each normalized professor record includes `name`, `university`, `department`, `faculty_profile_url`, and `source_confidence`.
- Raw scraped HTML or source payloads are stored under `data/raw/` for auditability.
- Processed normalized records are stored under `data/processed/` before database insertion.
- Duplicate professor records are flagged by normalized name + university + department + URL similarity.
- Publication enrichment stores source and match confidence.
- Recruiting signal includes evidence URL/text when marked positive or negative.

## Backend Acceptance

- `GET /health` returns healthy status.
- `GET /professors` supports pagination and filters.
- `GET /professors/{id}` returns professor details plus recent publications.
- `POST /student-profiles` validates required fields.
- `POST /match` returns ranked professor matches with component scores and explanations.
- API errors return structured JSON errors.
- Backend tests cover success and failure cases.

## Frontend Acceptance

- Professor directory renders from backend data.
- Professor profile page displays all available normalized fields.
- Student match form validates empty or malformed inputs.
- Match results show ranked cards with scores and explanations.
- Admin scrape page shows scrape runs, error summaries, and data-quality warnings.
- Playwright screenshots are generated for core pages.

## QA Acceptance

- `make test` runs backend, scraper, and matcher tests.
- `make qa` produces `docs/qa-reports/latest.md`.
- QA report includes database counts, missing-field counts, duplicate candidates, backend smoke-test results, and frontend screenshot paths.
- QA agent compares implementation against PRD and flags unmet requirements.
- No feature is considered complete until QA verifies code, data, API, and UI.

## Agent Workflow Acceptance

- Pi project agents exist under `.pi/agents/`.
- Claude-compatible mirrors exist under `.claude/agents/`.
- Every agent change is followed by the agent-sync-agent.
- `AGENTS.md` remains the cross-tool source of truth.
- `CLAUDE.md` contains only Claude-specific orchestration notes.
- Pi-specific configuration stays in `.pi/`.
- No agent relies on hidden chat context for project requirements.
