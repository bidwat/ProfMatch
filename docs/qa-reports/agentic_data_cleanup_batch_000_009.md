# Agentic Data Cleanup Report

Source DB: `/home/drl/pi-agent/pi-prof-idea/db/professor_match_clean.sqlite`
Output cleaned DB: `db/professor_match_agent_clean_batch_000_009.sqlite`
Rows evaluated: 10
Rows with corrected fields: 0
AI batch errors: 0

## Decision Counts

| Decision | Count |
|---|---:|
| keep_needs_enrichment | 7 |
| keep | 3 |

## Validity Counts

| Validity | Count |
|---|---:|
| valid_with_warnings | 7 |
| valid | 3 |

## Top Issues

| Issue | Count |
|---|---:|
| missing_title | 3 |
| missing_email | 3 |
| missing_research_text | 2 |
| missing_research_summary | 2 |

## Decisions by University

| University | keep | keep_needs_enrichment | exclude |
|---|---:|---:|---:|
| Stanford University | 3 | 7 | 0 |
