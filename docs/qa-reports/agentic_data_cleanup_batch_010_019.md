# Agentic Data Cleanup Report

Source DB: `/home/drl/pi-agent/pi-prof-idea/db/professor_match_clean.sqlite`
Output cleaned DB: `db/professor_match_agent_clean_batch_010_019.sqlite`
Rows evaluated: 10
Rows with corrected fields: 0
AI batch errors: 0

## Decision Counts

| Decision | Count |
|---|---:|
| keep_needs_enrichment | 8 |
| keep | 2 |

## Validity Counts

| Validity | Count |
|---|---:|
| valid_with_warnings | 8 |
| valid | 2 |

## Top Issues

| Issue | Count |
|---|---:|
| missing_email | 5 |
| missing_research_text | 3 |
| missing_research_summary | 3 |
| missing_title | 2 |

## Decisions by University

| University | keep | keep_needs_enrichment | exclude |
|---|---:|---:|---:|
| Stanford University | 2 | 8 | 0 |
