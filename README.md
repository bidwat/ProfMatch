# ProfMatch

ProfMatch helps prospective MS and PhD applicants discover professors who fit their academic background, research interests, and target degree.

Instead of manually browsing hundreds of faculty pages, students can create an academic profile and get a focused shortlist of professors with explainable match reasons, recent publication context, recruiting/source signals, and a saved-professor list.

## What you can do with ProfMatch

- Create an academic profile with your degree goal, department, background, and research interests.
- Browse a professor database across universities and departments.
- Search and filter professors by tags, university, department, recruiting signal, and other metadata.
- Generate professor matches based on your profile.
- Understand why a professor matched your interests.
- Review recent publication evidence for each match.
- Save professors to a shortlist.
- Recommend universities or departments to add next.

## Main pages

- **Home** — overview of your profile, matches, and saved professors.
- **Matches** — personalized ranked professor matches.
- **Discover** — searchable professor directory.
- **Saved** — your saved professor shortlist.
- **Profile** — your academic profile and research interests.
- **Professor detail** — professor summary, links, publications, tags, recruiting/source evidence, and save controls.

## Data and matching

ProfMatch uses a local professor database with professor profiles, research summaries, tags, publications, universities, departments, source confidence, and recruiting evidence where available.

Matches are explainable. Each match can include:

- a match score,
- why the professor matched,
- relevant publication count,
- recruiting signal,
- source/confidence indicators,
- professor profile and publication links.

ProfMatch should not be treated as a guarantee that a professor is recruiting. Recruiting information is shown only when there is supporting evidence or is marked as unknown when evidence is unavailable.

---

# Developer setup

## Repository layout

```txt
apps/frontend/      Next.js frontend
apps/backend/       FastAPI backend
packages/scraper/   reusable scraper/data utilities
db/                 SQLite seed database
docs/               product, architecture, and QA docs
```

## Requirements

- Node.js 20+
- Python 3.12+
- SQLite

## Backend setup

```bash
cd apps/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ../..
PYTHONPATH=. apps/backend/venv/bin/uvicorn apps.backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend default URL:

```txt
http://127.0.0.1:8000
```

## Frontend setup

```bash
cd apps/frontend
npm install
npm run dev
```

Frontend default URL:

```txt
http://localhost:3000
```

## Environment

Copy the example file and adjust as needed:

```bash
cp .env.example .env
```

Local development uses SQLite by default when no Postgres variables are set.

Important local variables:

```txt
ALLOWED_ORIGINS=http://localhost:3000
RATE_LIMIT_PER_MINUTE=300
LOG_LEVEL=INFO
```

## Useful commands

From the repository root:

```bash
make test
```

Frontend checks:

```bash
cd apps/frontend
npm run lint
npm run test -- --runInBand
npm run build
```

Backend checks:

```bash
apps/backend/venv/bin/python -m pytest apps/backend/tests -q
```
