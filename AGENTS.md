# AGENTS.md — Professor Match Orchestration

This repo builds **Professor Match**, a professor discovery and graduate-advisor matching application for prospective MS/PhD applicants.

## Repository Identity and Current Deployment Context

This repository is the **clean authoritative deployment repository** for Professor Match, not the older working directory at `/home/drl/pi-agent/pi-prof-idea`.

- Authoritative path: `/home/drl/pi-agent/profmatch-clean-git`
- Active deployment branch: `postgres`
- Git remote: `git@github.com:bidwat/ProfMatch.git`
- Legacy/reference repo: `/home/drl/pi-agent/pi-prof-idea` contains older WIP artifacts and should not be pushed unless explicitly reconciling history.

Current app shape:

- Frontend: Next.js app in `apps/frontend`
- Backend: FastAPI app in `apps/backend`
- Production database: Supabase/Postgres via SQLModel/SQLAlchemy
- Local fallback database: SQLite under `db/`
- Current public deployment before migration: Vercel frontend + Render backend
- Desired migration direction: move backend/app hosting away from Render Free toward DigitalOcean App Platform or another always-on Docker host.

Before deployment or Git operations, verify you are in the authoritative repo:

```bash
pwd
git status -sb
git remote -v
```

The detailed operational handoff is `docs/PROJECT_STATUS_ARCHITECTURE_HANDOFF.md`.

## Canonical Docs

Always ground work in these files; do not rely on hidden chat history:

- `docs/product/PRD.md`
- `docs/product/ACCEPTANCE_CRITERIA.md`
- `docs/product/DOD_DND.md`
- `docs/architecture/SPEC.md`
- `docs/agents/AGENT_AND_SKILL_SETUP_PLAN.md`

`spec_files/` contains the original imported files for audit/reference. The canonical working copies are under `docs/`.

## Orchestration Role

The main agent is the orchestrator. It should:

1. Read the relevant canonical docs before planning.
2. Choose the correct specialist agent for each task.
3. Keep writes single-threaded unless worktree isolation is explicitly used.
4. Ask product/architecture questions instead of silently expanding scope.
5. Run QA before calling a task done.
6. Run/summon `agent-sync-agent` after any change to agent files, skills, or orchestration instructions.

## Context-Mode Requirement

Use `context-mode` at every reasonable opportunity to save tokens.

- Prefer `ctx_execute`, `ctx_execute_file`, `ctx_index`, `ctx_search`, and `ctx_fetch_and_index` for commands, logs, tests, data files, docs, API calls, screenshots, Playwright snapshots, and any output that may exceed ~20 lines.
- Use normal file reads only when the exact file text is needed for editing or when output is guaranteed small.
- For tests/builds, analyze full output in context-mode and print only failures/summaries.
- For large source/data files, process in sandbox and return concise findings.
- For Playwright/browser snapshots, always save to a file first, then process/index by path.
- Do not pipe large command output through `head`; analyze all data outside context and summarize.

If context-mode MCP tools are unavailable in a given client, keep outputs aggressively summarized and prefer targeted reads.

## Default Workflow

1. Product/spec changes update docs first.
2. Implementation follows docs.
3. QA verifies code, data, API, UI, and docs.
4. Agent-sync-agent checks `.pi/settings.json`, `.pi/agents/`, `.pi/agents/*.chain.md`, `.pi/skills/`, `.pi/prompts/`, `.claude/agents/`, `.claude/skills/`, `.claude/commands/`, `AGENTS.md`, `CLAUDE.md`, and `.pi/APPEND_SYSTEM.md` after any agent/process change.

## Local-First and Free Deployment Rules

- Use SQLite for local development by default.
- Use Supabase Free Postgres for free-tier deployed persistence.
- Do not rely on free app-host filesystem persistence for production data.
- Prefer providers that stop, sleep, pause, or fail at free limits instead of surprise billing.
- No paid APIs.
- No production deployment until the local MVP works.
- No aggressive scraping.
- No large-scale Google Scholar scraping.
- Keep scraper adapters reusable.
- Store raw scraped data in `data/raw/` and processed normalized records in `data/processed/` before database insertion.
- Every inferred claim needs source/confidence.
- Do not claim a professor is recruiting without evidence.
- Keep database access behind service/repository layers.
- Frontend must not invent fields unsupported by backend data.

## Supabase Postgres Flow

The backend supports local SQLite and production Supabase Postgres.

Database configuration order:

1. `DATABASE_URL` when set.
2. Supabase component variables when set.
3. Local SQLite fallback.

Use these variables for Supabase:

```txt
SUPABASE_DB_HOST=db.<project-ref>.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=<database-password>
SUPABASE_DB_SSLMODE=require
SUPABASE_POOLER_HOST=<session-pooler-host>
SUPABASE_POOLER_PORT=5432
SUPABASE_POOLER_USER=postgres.<project-ref>
```

Use the Session Pooler for free projects when Supabase marks the direct DB host as not IPv4 compatible.

Migration command:

```bash
PYTHONPATH=. RESET_POSTGRES=true apps/backend/venv/bin/python scripts/migrate_sqlite_to_postgres.py
```

Never commit `.env` or real Supabase keys/passwords. Keep `.env.example` current with placeholders only.

Relevant docs:

- `docs/deployment/FREE_DEPLOYMENT_PLAN.md`
- `docs/deployment/POSTGRES_MIGRATION.md`

## Specialist Agents

Use project agents in `.pi/agents/` for Pi and mirrored agents in `.claude/agents/` for Claude Code. Pi loads project packages/skills/prompts from `.pi/settings.json`, including `pi-subagents`, `context-mode`, `.pi/skills/`, and `.pi/prompts/`.

Pi chain workflows live in `.pi/agents/*.chain.md`:

- `full-mvp-slice` — product/spec/data/backend/frontend/QA/docs/sync workflow.
- `add-scraper-adapter` — data contract/scraper/QA/docs/sync workflow.
- `backend-frontend-feature` — API contract/backend/frontend/QA/sync workflow.

Specialist agents:

- `product-agent` — PRD, scope, user stories, product tradeoffs.
- `spec-agent` — technical specs, API contracts, architecture docs.
- `agent-sync-agent` — mirrors/validates agent, skill, and orchestration files.
- `data-architect-agent` — schema, identity, dedupe, confidence scoring.
- `scraper-agent` — safe reusable scrapers and publication enrichers.
- `backend-agent` — FastAPI, DB layer, validation, backend tests.
- `frontend-agent` — Next.js/Tailwind UI and frontend tests.
- `matching-agent` — search, scoring, explanations, local embeddings later.
- `qa-agent` — strict verification across requirements, data, API, UI.
- `docs-agent` — README, setup, architecture, playbooks, reports.

## Definition of Done

A task is done only when relevant checks in `docs/product/DOD_DND.md` pass and QA evidence is written down. For MVP features, prefer a `docs/qa-reports/latest.md` update with PASS/PARTIAL/FAIL status.
