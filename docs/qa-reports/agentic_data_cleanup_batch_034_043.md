# Agentic Data Cleanup Report

Source DB: `/home/drl/pi-agent/pi-prof-idea/db/professor_match_clean.sqlite`
Output cleaned DB: `db/professor_match_agent_clean_batch_034_043.sqlite`
Rows evaluated: 10
Rows with corrected fields: 0
AI batch errors: 0

## Decision Counts

| Decision | Count |
|---|---:|
| keep_needs_enrichment | 8 |
| keep | 1 |
| exclude | 1 |

## Validity Counts

| Validity | Count |
|---|---:|
| valid_with_warnings | 8 |
| valid | 1 |
| invalid | 1 |

## Top Issues

| Issue | Count |
|---|---:|
| missing_email | 8 |
| missing_faculty_profile_url | 7 |
| research_text_low_information | 2 |
| missing_title | 1 |
| single_token_or_generic_name | 1 |
| possible_non_person_name | 1 |
| directory_row | 1 |
| recruiting_signal_missing_evidence | 1 |
| missing_research_text | 1 |
| missing_research_summary | 1 |

## Decisions by University

| University | keep | keep_needs_enrichment | exclude |
|---|---:|---:|---:|
| Carnegie Mellon University | 0 | 5 | 0 |
| Stanford University | 1 | 3 | 1 |

## Excluded Rows

| ID | Name | University | Issues | Rationale |
|---:|---|---|---|---|
| 41 | People | Stanford University | single_token_or_generic_name|possible_non_person_name|missing_faculty_profile_url|research_text_low_information|missing_email|directory_row|recruiting_signal_missing_evidence | Entry is a generic directory/category row with non-person name 'People', not an individual professor. |
