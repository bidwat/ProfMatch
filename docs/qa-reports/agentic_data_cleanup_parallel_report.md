# Agentic Data Cleanup Report

Source DB: `/home/drl/pi-agent/pi-prof-idea/db/professor_match_clean.sqlite`
Output cleaned DB: `/home/drl/pi-agent/pi-prof-idea/db/professor_match_agent_clean.sqlite`
Rows evaluated: 890
Rows with corrected fields: 754
AI batch errors: 0

## Decision Counts

| Decision | Count |
|---|---:|
| keep_needs_enrichment | 818 |
| keep | 58 |
| exclude | 14 |

## Validity Counts

| Validity | Count |
|---|---:|
| valid_with_warnings | 802 |
| valid | 58 |
| invalid | 30 |

## Top Issues

| Issue | Count |
|---|---:|
| recruiting_signal_missing_evidence | 569 |
| missing_title | 541 |
| missing_email | 508 |
| faculty_and_homepage_same_url | 178 |
| missing_research_text | 116 |
| missing_research_summary | 113 |
| missing_faculty_profile_url | 73 |
| invalid_research_text | 42 |
| invalid_research_summary | 40 |
| research_summary_invalid | 33 |
| scraped_navigation_content | 28 |
| research_summary_scraped_navigation | 21 |
| invalid_homepage_url | 21 |
| research_text_generic | 20 |
| research_text_scraped_navigation | 18 |
| homepage_is_directory | 18 |
| research_text_irrelevant | 17 |
| research_text_low_information | 16 |
| research_text_invalid | 15 |
| research_summary_irrelevant | 15 |
| irrelevant_research_text | 13 |
| missing_homepage_url | 12 |
| university_url_mismatch | 11 |
| homepage_url_404 | 11 |
| research_text_404 | 11 |

## Decisions by University

| University | keep | keep_needs_enrichment | exclude |
|---|---:|---:|---:|
| Carnegie Mellon University | 27 | 92 | 2 |
| Cornell University | 0 | 138 | 8 |
| Georgia Institute of Technology | 0 | 26 | 1 |
| Massachusetts Institute of Technology | 12 | 35 | 0 |
| Stanford University | 3 | 34 | 2 |
| UC Berkeley | 16 | 99 | 0 |
| University of Illinois Urbana-Champaign | 0 | 214 | 1 |
| University of Texas at Austin | 0 | 114 | 0 |
| University of Washington | 0 | 66 | 0 |

## Excluded Rows

| ID | Name | University | Issues | Rationale |
|---:|---|---|---|---|
| 38 | CS PhD Student Resources | Stanford University | possible_non_person_name|missing_faculty_profile_url|research_text_low_information|missing_title | Non-person resource page, not an individual professor, excluded. |
| 41 | People | Stanford University | single_token_or_generic_name|possible_non_person_name|missing_faculty_profile_url|research_text_low_information|missing_email | Generic directory page, not an individual professor, excluded. |
| 152 | Pieter Abbeel | Carnegie Mellon University | missing_title|missing_email|scraped_navigation_content | Row contains scraped navigation content, qualifying as a scraped content row, hence excluded. |
| 153 | Ahmed Alaa | Carnegie Mellon University | missing_title|missing_email|scraped_navigation_content | Row contains scraped navigation content, qualifying as a scraped content row, hence excluded. |
| 286 | Alberto Apostolico (1948-2015) | Georgia Institute of Technology | malformed_name|missing_faculty_profile_url|missing_title|missing_email|irrelevant_research_text|recruiting_signal_missing_evidence | Row contains malformed name with lifespan, irrelevant news feed research content, and directory-level homepage URL, not a valid professor entry. |
| 508 | Joy Arulraj | Cornell University | missing_title|missing_email|research_text_garbage|homepage_is_directory|faculty_university_mismatch|recruiting_signal_missing_evidence | Row contains irrelevant news feed research text, directory homepage URL, and faculty URL mismatched with listed university. |
| 509 | Teodora Baluta | Cornell University | missing_title|missing_email|research_text_garbage|homepage_is_directory|faculty_university_mismatch|recruiting_signal_missing_evidence | Row contains irrelevant news feed research text, directory homepage URL, and faculty URL mismatched with listed university. |
| 510 | Sababu Barashango | Cornell University | missing_title|missing_email|research_text_garbage|homepage_is_directory|faculty_university_mismatch|recruiting_signal_missing_evidence | Row contains irrelevant news feed research text, directory homepage URL, and faculty URL mismatched with listed university. |
| 511 | Michael Best | Cornell University | missing_title|missing_email|research_text_garbage|homepage_is_directory|faculty_university_mismatch|recruiting_signal_missing_evidence | Row contains irrelevant news feed research text, directory homepage URL, and faculty URL mismatched with listed university. |
| 512 | Zachary Bischof | Cornell University | missing_title|missing_email|research_text_garbage|homepage_is_directory|faculty_university_mismatch|recruiting_signal_missing_evidence | Row contains irrelevant news feed research text, directory homepage URL, and faculty URL mismatched with listed university. |
| 513 | Alexandra Boldyreva | Cornell University | missing_title|missing_email|research_text_garbage|homepage_is_directory|faculty_university_mismatch|recruiting_signal_missing_evidence | Row contains irrelevant news feed research text, directory homepage URL, and faculty URL mismatched with listed university. |
| 514 | Mark Borodovsky | Cornell University | missing_title|missing_email|research_text_garbage|homepage_is_directory|faculty_university_mismatch|recruiting_signal_missing_evidence | Row contains irrelevant news feed research text, directory homepage URL, and faculty URL mismatched with listed university. |
| 515 | Gerandy Brito | Cornell University | missing_title|missing_email|research_text_garbage|homepage_is_directory|faculty_university_mismatch|recruiting_signal_missing_evidence | Row contains irrelevant news feed research text, directory homepage URL, and faculty URL mismatched with listed university. |
| 639 | Daniel  Gonzalez Cedre | University of Illinois Urbana-Champaign | missing_title|missing_email|scraped_navigation_content|recruiting_signal_missing_evidence | Record contains scraped department navigation content, not a valid individual professor entry. |
