# ProfMatch crawler policy

ProfMatch indexes public faculty information so prospective research
students can discover advisors. This page describes how our crawler
behaves and how to reach us.

## How the crawler behaves

- **User agent**: `ProfMatchBot/1.0` with a link to this policy and a
  contact address (configurable via `CRAWLER_USER_AGENT`).
- **Scope**: only admin-approved department faculty pages, the professor
  profile pages they link to, and (when present) personal/lab homepages.
  There is no broad or recursive crawling.
- **Rate**: pages within a department are fetched sequentially, one at a
  time, with normal page-load pacing; a department import touches at most
  the roster page plus its listed profile pages.
- **Frequency**: a department is only re-crawled when an admin triggers a
  refresh (target cadence: every six months) or a correction report
  requires it.
- **Provenance**: every crawled page's source URL is stored with the data
  extracted from it, and raw crawl artifacts are retained for audit.
- **What we never collect**: private pages, content behind logins,
  emails from non-public sources.

## Corrections and takedowns

If your page was crawled and you want data corrected or removed:

1. Use **Report issue** on the professor profile page, or
2. Email the contact address in the crawler user-agent string.

Admins review every report before public data changes. Professors can
also request updates to their own profiles.
