# Data Cleanup Report

**Generated:** 2026-04-28 17:44:55

## Summary

- **Total records reviewed:** 972
- **Records kept/updated:** 895
- **Records removed:** 77
- **Validation errors:** 0
- **Records imported to clean DB:** 895

## Decision Breakdown

- **Kept:** 219
- **Updated:** 676
- **Removed:** 77

## Removed Records by University

- **unknown:** 77 records removed

## Top Removal/Update Reasons

- Invalid homepage URL (faculty classification page); junk research text (news feed content); missing title/email; set invalid fields to empty. (100)
- Cleaned homepage URL and research text (99)
- Cleaned junk research text (navigation menu content); lowered source confidence from 0.9 to 0.6 due to incomplete data (missing title, email, research text) (90)
- Valid professor record (82)
- Record validated successfully (78)
- Updated source confidence to good (0.75) (63)
- Missing valid email (54)
- Research text cleaned or email invalid (41)
- Valid identity (UW faculty), correct affiliation (UW Paul G. Allen School), faculty URL works, missing title/email/research text, recruiting signal unknown (valid) (38)
- Invalid identity: not a professor or no institutional email (35)

## Data Quality Improvements

1. **Invalid URLs fixed:** Homepage URLs corrected from duplicate faculty profile URLs
2. **Missing emails:** Kept empty (not invented)
3. **Research text:** Kept minimal or empty (not invented)
4. **Recruiting signal:** Set to 'unknown' where not verified
5. **Department corrections:** Fixed incorrect department assignments

## Next Steps

1. Validate clean database: `sqlite3 db/professor_match_clean.sqlite 'SELECT COUNT(*) FROM professor;'`
2. Compare with backup: `sqlite3 db/professor_match_backup_20260428_171515.sqlite 'SELECT COUNT(*) FROM professor;'`
3. Run backend API tests against clean database
4. Update frontend to use clean database
5. Once validated, replace original database with clean version
