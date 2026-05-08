# Agentic Data Cleanup Report

Source DB: `/home/drl/pi-agent/pi-prof-idea/db/professor_match_clean.sqlite`
Output cleaned DB: `db/professor_match_agent_clean_batch_040_049.sqlite`
Rows evaluated: 10
Rows with corrected fields: 0
AI batch errors: 0

## Decision Counts

| Decision | Count |
|---|---:|
| keep_needs_enrichment | 10 |

## Validity Counts

| Validity | Count |
|---|---:|
| valid_with_warnings | 10 |

## Top Issues

| Issue | Count |
|---|---:|
| missing_faculty_profile_url | 10 |
| missing_email | 10 |
| missing_research_text | 1 |
| missing_research_summary | 1 |

## Decisions by University

| University | keep | keep_needs_enrichment | exclude |
|---|---:|---:|---:|
| Carnegie Mellon University | 0 | 10 | 0 |
