# Technical Spec — Professor Match Local MVP

## Recommended Stack

- Frontend: Next.js + TypeScript + Tailwind CSS
- Backend: FastAPI + Python
- Database: SQLite for local development
- ORM: SQLModel or SQLAlchemy
- Scraping: Python, Requests, BeautifulSoup, Playwright only when necessary
- Data validation: Pydantic
- Search: SQLite FTS5 first
- Embeddings: local sentence-transformers later in MVP, optional for first vertical slice
- Testing: pytest, FastAPI TestClient, Playwright
- Agent orchestration: Pi with pi-subagents, Claude Code-compatible mirrored agents

## Repository Structure

```txt
professor-match/
  AGENTS.md
  CLAUDE.md
  README.md

  .pi/
    agents/
      product-agent.md
      spec-agent.md
      agent-sync-agent.md
      data-architect-agent.md
      scraper-agent.md
      backend-agent.md
      frontend-agent.md
      matching-agent.md
      qa-agent.md
      docs-agent.md

  .claude/
    agents/
      product-agent.md
      spec-agent.md
      agent-sync-agent.md
      data-architect-agent.md
      scraper-agent.md
      backend-agent.md
      frontend-agent.md
      matching-agent.md
      qa-agent.md
      docs-agent.md
    skills/
      professor-data-model/SKILL.md
      scraper-playbook/SKILL.md
      qa-verification/SKILL.md

  apps/
    backend/
      app/
        main.py
        api/
        db/
        models/
        services/
      tests/

    frontend/
      app/
      components/
      lib/
      tests/

  packages/
    scraper/
      core/
      adapters/
      sources/
      tests/
    matcher/
      tests/
    shared/

  data/
    seeds/universities.csv
    raw/
    processed/
    qa/

  db/
    professor_match.sqlite
    migrations/

  docs/
    product/
    architecture/
    agents/
    scraping-playbooks/
    qa-reports/
```

## Core Data Model

### professors
- id
- name
- normalized_name
- title
- university
- department
- email
- faculty_profile_url
- homepage_url
- google_scholar_url
- openalex_id
- dblp_url
- semantic_scholar_id
- research_text
- research_summary
- recruiting_signal: positive | negative | unknown
- recruiting_evidence_url
- recruiting_evidence_text
- source_confidence
- created_at
- updated_at

### publications
- id
- professor_id
- title
- year
- venue
- abstract
- url
- source
- source_author_id
- match_confidence

### scrape_runs
- id
- university
- department
- adapter_name
- started_at
- completed_at
- status
- pages_attempted
- pages_successful
- records_created
- records_updated
- errors_json

### users
- id
- email
- password_hash
- display_name
- role
- is_active
- created_at
- updated_at
- last_login_at

### auth_sessions
- id
- user_id
- session_token_hash
- created_at
- expires_at
- last_seen_at
- revoked_at
- user_agent
- ip_address

### user_states
- id
- user_id
- student_profile JSON
- last_match_response JSON
- saved_professor_ids JSON
- tracker_rows JSON
- created_at
- updated_at

### student_profiles
- id
- background
- research_interests
- target_degree
- preferred_locations
- preferred_universities
- created_at

### matches
- id
- student_profile_id
- professor_id
- total_score
- research_similarity_score
- publication_similarity_score
- recruiting_score
- metadata_score
- explanation
- created_at

## Scraper Architecture

All school-specific scrapers must output the same normalized object:

```json
{
  "name": "Jane Doe",
  "title": "Assistant Professor",
  "university": "Example University",
  "department": "Computer Science",
  "email": "jane@example.edu",
  "faculty_profile_url": "https://example.edu/cs/faculty/jane-doe",
  "homepage_url": "https://janedoe.example.edu",
  "research_text": "Human-computer interaction, augmented reality...",
  "recruiting_signal": "unknown",
  "source_confidence": 0.82
}
```

Scraper layers:

1. Fetcher: downloads pages safely.
2. Parser: extracts candidate professor records.
3. Normalizer: maps school-specific fields to canonical schema.
4. Enricher: adds OpenAlex/DBLP/Semantic Scholar data.
5. Validator: checks required fields and confidence.
6. Writer: persists raw, processed, and database records.

## Backend API

Required endpoints:

```txt
GET /health
GET /professors
GET /professors/{id}
GET /universities
GET /scrape-runs
POST /student-profiles
POST /match
POST /auth/register
POST /auth/login
POST /auth/logout
GET /auth/me
GET /auth/state
PATCH /auth/state
GET /admin/scans             admin-only, read-only scan artifact summaries
GET /admin/scans/{scan_id}   admin-only, read-only scan detail with validation issues and duplicates
```

## Frontend Pages

```txt
/                    landing + search
/professors          searchable professor directory
/professors/[id]     professor profile
/match               student profile input + match results
/admin/scans         admin-only local scan status, QA summaries, issue details, duplicate candidates, and artifact links
```

## Matching v1

MVP matching is a two-stage SQLite-first pipeline. Do not introduce a vector database or heavy local embedding model until the backend MVP is complete.

### Stage 1 — Local shortlist

Normalize the student profile into a query string from research interests, background, target degree, preferred departments, preferred universities, and preferred locations. Use SQLite FTS5 over professor name, title, department, university, research text, synthesized research summary, generated tags, and recruiting evidence text. Retrieve roughly the top 30–50 candidates using BM25 and then apply lightweight metadata boosts/penalties.

Local metadata signals:

- boost same department or adjacent department
- boost professors with synthesized `research_summary`
- boost explicit positive recruiting signal only when evidence exists
- boost assistant/associate/professor titles for advisor fit
- boost homepage/faculty profile availability
- penalize weak `source_confidence`
- penalize unknown or empty research text/summary

Initial deterministic scoring formula:

```txt
total_score =
  0.45 * research_text_similarity +
  0.30 * recent_publication_similarity +
  0.10 * recruiting_signal_score +
  0.10 * department/title relevance +
  0.05 * location/preference fit +
  bounded metadata_boost
```

The local score creates a good candidate pool and remains the canonical debug/QA score; it is not expected to be the final semantic judgment.

### Stage 2 — LLM reranking

When enabled and an OpenRouter API key is available, send only the top 15–20 deterministic candidates to the LLM. The reranker compares the full student profile against each professor's summary, tags, department, recruiting signal/evidence, and recent publication evidence, then returns the best matches with:

- final match score
- ranking reason
- risks/uncertainties
- suggested outreach angle

Recruiting signal must not be overstated. If no explicit evidence exists, use `unknown`, not `negative`, and never claim the professor is actively recruiting.

## Local Run Commands

```bash
make setup
make db-init
make scrape-seed
make backend
make frontend
make test
make qa
```

## Deployment Later

Local SQLite should be swappable with Supabase/Postgres later. Avoid SQLite-specific logic in business services except FTS5 search. Keep database access behind repository/service classes.
