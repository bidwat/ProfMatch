# PRD — Professor Match Local MVP

## Product Summary
Professor Match is a local-first system that builds a structured database of computer science and CS-adjacent professors in the United States, enriches each profile with recent research activity, and matches prospective MS/PhD applicants to suitable professors based on research alignment, background, goals, and recruiting signals.

## Problem
Students applying to graduate programs often rely on outdated department pages, scattered professor websites, Google Scholar, and manual spreadsheet tracking. Professors' current research directions are often better reflected in recent publications than static university profiles. The product should reduce discovery time and improve professor-student fit.

## Target Users
1. Prospective PhD applicants in CS and adjacent computational fields.
2. Prospective research-based MS applicants.
3. Undergraduate researchers exploring graduate advisors.
4. Later: universities, labs, and advisors helping students find research fit.

## MVP Scope
The MVP will run locally and cover a small but useful corpus:

- 10 US universities.
- CS departments only for the first pass.
- 300–800 professor records if feasible.
- Structured professor profiles.
- Recent-publication-based research summaries.
- Basic student profile input.
- Ranked professor matches with explanations.
- Local QA reports verifying scraped data, APIs, and UI.

## Core User Stories

### Student Discovery
As a prospective PhD student, I can enter my background, research interests, target degree, and preferences so that I can see ranked professor matches.

### Professor Profile Review
As a student, I can open a professor profile and see name, title, institution, department, email, homepage/profile links, recent publications, inferred research areas, and recruiting signal.

### Research-Fit Matching
As a student, I can see why a professor is recommended, including overlap with recent papers, lab description, and declared student interests.

### Admin/Data Validation
As a project owner, I can run scrapers, inspect scrape status, view data-quality reports, and see which records are incomplete or low-confidence.

## Non-Goals for MVP
- No paid APIs.
- No production deployment.
- No global professor database yet.
- No user accounts.
- No large-scale Google Scholar scraping.
- No email automation to professors.
- No claim that a professor is recruiting unless explicitly evidenced.

## Success Metrics
- At least 10 university CS departments ingested.
- At least 80% of professor records have name, university, department, title or role, and profile URL.
- At least 60% of professor records have email or homepage URL.
- At least 50% of professor records have recent publication enrichment from OpenAlex/DBLP/Semantic Scholar or a marked reason for missing data.
- Student matching returns ranked results within 5 seconds locally for the MVP corpus.
- QA report flags duplicates, missing required fields, broken links, and empty summaries.

## Product Principles
1. Recent research beats stale profile text.
2. Every inferred claim must have a source or confidence level.
3. Local-first development before deployment.
4. Reusable scraper architecture over one-off scripts.
5. Strict separation between raw scraped data, normalized data, enriched data, and UI display.
