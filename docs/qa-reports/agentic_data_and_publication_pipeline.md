# Agentic Data Cleanup and Publication Pipeline Notes

Generated: 2026-04-29

## Professor data validation/cleanup

### Script

```bash
python scripts/project/agentic_data_cleanup_parallel.py
```

### Purpose

Validate Professor Match professor rows using an OpenRouter free model and produce:

- autonomous keep/enrich/exclude decisions
- corrected safe fields where possible
- incremental CSV and JSONL reports
- a copied cleaned SQLite DB at completion

### Free-model requirement

The script loads `.env.openrouter` and refuses to run if the configured model does not end in `:free`.

Current model:

```txt
OPENROUTER_MODEL=tencent/hy3-preview:free
```

### Current full-run command

The current validation run was started in the background with:

```bash
nohup python scripts/project/agentic_data_cleanup_parallel.py \
  --batch-size 10 \
  --workers 4 \
  --retries 0 \
  --fresh \
  > logs/agentic_data_cleanup_parallel.log 2>&1 &
```

### Monitoring

```bash
tail -f logs/agentic_data_cleanup_parallel.log
```

Structured progress:

```bash
python -m json.tool data/validation/runtime/agentic_data_cleanup_progress.json
```

PID file:

```txt
data/validation/runtime/agentic_data_cleanup_parallel.pid
```

### Outputs

```txt
data/validation/agentic_data_cleanup_parallel_report.csv
data/validation/agentic_data_cleanup_parallel_records.jsonl
data/validation/agentic_data_cleanup_parallel_batches.jsonl
data/validation/runtime/agentic_data_cleanup_progress.json
docs/qa-reports/agentic_data_cleanup_parallel_report.md
db/professor_match_agent_clean.sqlite
```

### Stuck-worker recovery, 2026-04-29

The full parallel run reached `870/890` rows and then stopped making progress for roughly 16 minutes. Investigation showed:

- process was still alive but idle/blocked on worker threads
- progress file and JSONL artifacts had not changed since `870/890`
- two HTTPS sockets to OpenRouter remained open
- missing batch indices were `86` and `88`
- missing row IDs were `866-875` and `886-895`

The stuck process was terminated and the incremental artifacts were finalized with:

```bash
python scripts/project/finalize_agentic_cleanup_from_incremental.py
```

This preserves all completed AI-reviewed rows and applies the same deterministic fallback path used by the main runner for missing rows. The final progress status is:

```txt
complete_with_fallback_finalization
```

Final counts:

```txt
source rows: 890
finalized rows: 890
fallback-finalized rows: 20
output DB rows after exclusions: 876
keep: 58
keep_needs_enrichment: 818
exclude: 14
```

Because 20 rows were finalized by deterministic fallback rather than OpenRouter, and because some excluded rows look like real faculty names, the exclusion set should receive a targeted QA pass before making `db/professor_match_agent_clean.sqlite` the active app DB.

### Decision labels

- `keep`: row is a valid professor record.
- `keep_needs_enrichment`: row is a valid/plausible professor but has missing or weak fields.
- `exclude`: row is not a professor row or is too corrupt to keep.

No human-review terminal status is used.

## Publication enrichment

### Script

```bash
python scripts/project/fetch_publications.py
```

### Purpose

Fetch 5 recent papers with usable abstracts for each professor.

### Current data sources

1. OpenAlex for author resolution, works, metadata, and abstract reconstruction.
2. Semantic Scholar as fallback when OpenAlex abstracts are missing or low-quality.

No AI is currently needed for this workflow. The script loads `.env.openrouter` only to ensure any future AI use remains restricted to an OpenRouter `:free` model.

### Test command

```bash
python scripts/project/fetch_publications.py --ids 1,13,28 --papers-per-prof 5
```

### Test result

- Professors tested: 3
- Papers fetched: 15
- Papers with usable abstracts: 15
- Errors: 0

### Recommended all-professors command

Using current clean DB:

```bash
python scripts/project/fetch_publications.py \
  --db db/professor_match_clean.sqlite \
  --papers-per-prof 5 \
  --write-db \
  --output-db db/professor_match_publications.sqlite
```

Using the final agent-cleaned DB after validation finishes:

```bash
python scripts/project/fetch_publications.py \
  --db db/professor_match_agent_clean.sqlite \
  --papers-per-prof 5 \
  --write-db \
  --output-db db/professor_match_agent_clean_with_publications.sqlite
```

### Outputs

```txt
data/raw/publications/openalex/
data/raw/publications/semantic_scholar/
data/processed/publications/publication_fetch_<timestamp>.jsonl
data/processed/publications/publication_fetch_<timestamp>.csv
docs/qa-reports/publication_fetch_report.md
```

When `--write-db` is used, rows are inserted into the copied output DB's `publication` table.

### Notes for editing later

- Author matching is implemented in `score_author()` in `scripts/project/fetch_publications.py`.
- Abstract quality is implemented in `has_usable_abstract()`.
- OpenAlex works retrieval is implemented in `fetch_openalex_works()`.
- Semantic Scholar fallback is implemented in `semantic_scholar_by_doi()` and `semantic_scholar_title_search()`.
- SQLite insert behavior is implemented in `write_db()`.
