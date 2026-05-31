# CLAUDE.md — Claude Code Orchestration Notes

Use this file only for Claude Code-specific behavior. Shared rules live in `AGENTS.md`.

Repository identity: this is the clean authoritative Professor Match deployment repo at `/home/drl/pi-agent/profmatch-clean-git`, branch `main`, remote `git@github.com:bidwat/ProfMatch.git`. The older `/home/drl/pi-agent/pi-prof-idea` directory is historical/WIP reference and should not be pushed for production unless explicitly reconciled. See `docs/PROJECT_STATUS_ARCHITECTURE_HANDOFF.md` for the full operational handoff.

## Claude Code Agents

Use project agents in `.claude/agents/`:

- Product/spec: `product-agent`, `spec-agent`
- Data/scraping: `data-architect-agent`, `scraper-agent`
- Build: `backend-agent`, `frontend-agent`, `matching-agent`
- Verification/docs/sync: `qa-agent`, `docs-agent`, `agent-sync-agent`

For multi-step work, delegate to the narrowest specialist agent. After modifying any agent file, skill, `AGENTS.md`, `CLAUDE.md`, or `.pi/APPEND_SYSTEM.md`, invoke `agent-sync-agent` to check mirrors.

## Claude Skills

Use `.claude/skills/` when relevant. Mirrored Pi skills live under `.pi/skills/`.

- `professor-data-model` for schema, dedupe, confidence, and data contracts.
- `scraper-playbook` for faculty scrapers and publication enrichment.
- `qa-verification` for acceptance/DoD checks.

## Claude Commands

Project workflow prompts live under `.claude/commands/pm/`:

- `/pm/full-mvp-slice` for product-to-QA vertical slices.
- `/pm/add-scraper-adapter` for safe scraper adapter work.
- `/pm/agent-sync` for Pi/Claude orchestration sync.

## Context Mode

Context-mode is installed for Claude Code. Use it by default for large or uncertain outputs:

- test/build/log output
- API responses
- scraping output
- database inspection
- Playwright snapshots/screenshots metadata
- large files and generated artifacts

Prefer sandboxed analysis and concise summaries over raw dumps. If context-mode tools are unavailable, use targeted commands that emit only relevant findings.

## Supabase Deployment Flow

For deployment work, follow the shared rules in `AGENTS.md` plus:

- Keep SQLite as the local fallback.
- Use Supabase Free Postgres for deployed persistence.
- Prefer Session Pooler settings when Supabase direct DB says it is not IPv4 compatible.
- Do not commit `.env` or any real Supabase keys/passwords.
- Update `.env.example` only with placeholders.
- Use `scripts/migrate_sqlite_to_postgres.py` for SQLite → Supabase migration.
- Verify with `/api/stats`, `/api/professors?limit=3`, and `/api/match` after migration.

Detailed docs:

- `docs/deployment/FREE_DEPLOYMENT_PLAN.md`
- `docs/deployment/POSTGRES_MIGRATION.md`

## Source Files

`spec_files/` contains the originally downloaded project files. The canonical working docs are copied under `docs/` and should be updated there first.
