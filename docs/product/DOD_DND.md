# Definition of Done and Do-Not-Do Rules

## Definition of Done

A task is done only when all relevant checks below pass.

### For Product/Spec Tasks
- Requirement is written in `docs/product/` or `docs/architecture/`.
- Acceptance criteria are updated.
- Out-of-scope items are explicitly marked.
- Agent-sync-agent has checked whether `.pi/agents/`, `.claude/agents/`, `AGENTS.md`, or `CLAUDE.md` need updates.

### For Scraper Tasks
- Adapter produces canonical normalized records.
- Raw source data is saved.
- Processed JSON/CSV output is saved.
- Database write path is tested.
- Missing fields and confidence are reported.
- Scraper respects conservative request pacing.
- No scraper uses paid APIs.
- No large-scale Google Scholar scraping is added.

### For Backend Tasks
- Endpoint is implemented.
- Request/response schemas are validated.
- Tests cover success and failure cases.
- Errors are structured and readable.
- Database access goes through service/repository layer.

### For Frontend Tasks
- Page/component works against real local backend or mocked fixture.
- Empty/loading/error states exist.
- UI matches product requirements.
- Playwright screenshot exists for core views.

### For Matching Tasks
- Scoring formula is documented.
- Explanation references actual professor data.
- Unknown or low-confidence signals are not overstated.
- Component scores are returned for QA/debugging.

### For QA Tasks
- `make test` passes or failures are documented.
- `make qa` writes a report.
- Data, API, UI, and requirements are checked together.
- QA report clearly says PASS, PARTIAL, or FAIL.

## Do-Not-Do Rules

- Do not build deployment infrastructure before local MVP works.
- Do not use paid APIs.
- Do not scrape aggressively.
- Do not scrape Google Scholar at scale.
- Do not claim a professor is recruiting without source evidence.
- Do not mix raw scraped HTML, normalized records, and database rows without clear separation.
- Do not let frontend invent fields not supported by backend data.
- Do not let backend silently swallow scraper/data errors.
- Do not let agents make architecture changes without updating docs.
- Do not edit only `.pi/agents/` or only `.claude/agents/` when the change should apply to both.
- Do not rely on hidden chat history; write decisions into repo files.
- Do not scale to all US universities before 3 adapters are proven and QA-approved.
