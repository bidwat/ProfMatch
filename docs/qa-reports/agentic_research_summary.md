# Agentic Research Summary and Tagging Report

Date: 2026-04-29

## Scope

Built an autonomous pipeline to generate professional, third-person academic research summaries and assign standard computer science taxonomy tags for each professor using an LLM.

Script:

```txt
scripts/agentic_research_summary.py
```

Cache Output:

```txt
data/validation/agentic_research_summary_cache.jsonl
```

Target Database:

```txt
db/professor_match_publications.sqlite
```

Secrets file:

```txt
.env.openrouter
```

## Processing Details

The script operates directly on the existing `professor_match_publications.sqlite` database and accomplishes the following:

- Gathers up to the 5 most recent publication abstracts for each professor, along with the first 3000 characters of their `research_text` bio.
- Sends the payload to an OpenRouter model using the system prompt instructed to act as an expert academic research summarizer and taxonomist.
- Generates a concise, 1-2 paragraph `research_summary` in the third-person describing the professor's active focus areas.
- Generates an array of 3-7 `tags` representing their core research areas using standard computer science terminology.
- Instantly caches the result in a JSONL file so that intermittent failures and rate limits do not lose generated results.
- Natively stores the updated `research_summary` string in the `professor` table, and the `tags` array inside the `extra` JSON column.

## Pipeline Architecture

- **Fault Tolerance**: The script uses a local `.jsonl` cache. If it hits an API limit or terminates, it reads the cache on reboot, skips already-processed professors, and resumes perfectly.
- **Batching**: Operates in chunks of 5 by default, to work safely within free-tier OpenRouter limits without massive payloads causing timeouts.
- **Progress Tracking**: Uses terminal output to show rate (rows/s), percentage complete, errors, and an ETA.

## Command run

```bash
python scripts/agentic_research_summary.py
```

Background execution via `nohup` was utilized to let the process complete its run over the 890 dataset entries without tying up an interactive session:

```bash
nohup python3 scripts/agentic_research_summary.py > logs/agentic_research_summary.log 2>&1 &
tail -f logs/agentic_research_summary.log
```

## Summary / Results

The process successfully processed professors, replacing any previously blank, overly dense, or unreadable scraped `research_summary` column with an LLM-synthesized, readable, normalized third-person account. Furthermore, standard tags were seeded into the `extra` column for use in future categorical search workflows on the frontend explorer.
