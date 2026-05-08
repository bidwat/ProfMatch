# Data Validation Agent Report

Date: 2026-04-29

## Scope

Built a local validation script for `db/professor_match_clean.sqlite` that writes one CSV row per professor without mutating the database.

Script:

```txt
scripts/validate_professor_data.py
```

Outputs:

```txt
data/validation/professor_data_validity.csv
data/validation/professor_data_ai_reviews.jsonl
```

Secrets file:

```txt
.env.openrouter
```

The secrets file is ignored via `.gitignore` and is mode `600` locally.

## Validation checks

Deterministic checks currently cover:

- name plausibility / non-person scraped names
- invalid URL syntax
- missing faculty profile URL
- faculty profile URL equal to homepage URL
- missing or low-information research text
- missing research summary
- recruiting signal without evidence when positive/negative
- low source confidence

Optional OpenRouter review can be enabled with `OPENROUTER_API_KEY` in `.env.openrouter`.

## Command run

```bash
python scripts/validate_professor_data.py --no-ai
```

## Current heuristic results

Rows inspected: 890

| Final status | Count |
|---|---:|
| valid | 563 |
| suspect_needs_review | 326 |
| invalid_or_needs_removal_review | 1 |

Top issue counts:

| Issue | Count |
|---|---:|
| missing_title | 541 |
| faculty_and_homepage_same_url | 178 |
| missing_research_text | 112 |
| missing_research_summary | 112 |
| missing_faculty_profile_url | 73 |
| research_text_low_information | 15 |
| possible_non_person_name | 1 |
| name_contains_digit | 1 |

Immediate removal-review candidate:

```txt
id=41, name="People", university="Stanford University"
issues=possible_non_person_name|missing_faculty_profile_url|research_text_low_information
```

## OpenRouter command

After filling `.env.openrouter`, run AI validation for every row using the configured OpenRouter `:free` model:

```bash
python scripts/validate_professor_data.py --sleep 1
```

For faster triage, AI validation can be restricted to deterministic suspect rows:

```bash
python scripts/validate_professor_data.py --ai-only-suspect --sleep 1
```

Free OpenRouter models may be rate-limited; use `--limit` and `--offset` for batches.
