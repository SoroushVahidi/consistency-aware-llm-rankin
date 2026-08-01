# Stage 6 Changelog

Date: 2026-07-31
Branch: `papers/sncs-2026-foundation`

## Manuscript

- Replaced the structured abstract placeholder with a complete 196-word
  Purpose/Methods/Results/Conclusion abstract matching SN Computer Science
  requirements.
- Wrote the full Conclusion, answering RQ1--RQ4 and separating structural
  improvement from retrieval improvement.
- Completed Data Availability and Reproducibility prose.
- Added Acknowledgments for Professor Ioannis Koutis, the author's mother,
  Anders Borum, and verified in-kind API/cloud-credit support.
- Replaced the unresolved Funding placeholder with a completed funding
  declaration.
- Updated declaration wording from "Conflict of interest" to "Competing
  interests."
- Kept the generative-AI disclosure in the Reproducibility and Implementation
  section, consistent with the Stage 5 Springer policy check.

## Factual and Consistency Fixes

- Corrected the real-large-language-model pilot provider count from five to
  four.
- Corrected the main ranker-scope description from "three classical and one
  dense" to "two lexical base rankers, one dense base ranker."
- Softened `ms2` cyclicity language from "by construction" to "in the observed
  evidence."
- Smoothed one hyphenated phrase in Related Work for cleaner PDF text
  extraction.

## Bibliography

- Updated `LLM-RankFusion` from an arXiv-only entry to its TMLR 2026 record.
- Updated the acyclic preference-evaluation reference to its AAAI 2026
  proceedings record with DOI and pages.
- Updated manuscript citation keys accordingly.

## Reports Added

- `STAGE6_CONSISTENCY_REPORT.md`
- `STAGE6_REVIEWER_AUDIT_REPORT.md`
- `STAGE6_BIBLIOGRAPHY_AUDIT_REPORT.md`
- `STAGE6_PAGE_BUDGET_REPORT.md`
- `STAGE6_CHANGELOG.md`

## Validation

- Rechecked SN Computer Science structured-abstract requirement against the
  official Springer Nature journal submission guidelines.
- Verified abstract word count: 196 words.
- Verified citation keys: 59 cited keys, 0 missing, 62 unique BibTeX entries.
- Verified labels and references: 65 unique labels, 161 references, 0 missing.
- Verified float metadata: 5 figures, 6 tables, 1 algorithm; all have captions
  and labels.
- Compiled `papers/SNCS_2026/manuscript/main.pdf` successfully with Tectonic.
- Final PDF page count: 41 pages.

## Known Build Warnings

- Tectonic reports a UTF-8 warning from `algorithm.sty`, outside the manuscript
  source.
- Tectonic reports underfull box warnings typical of the template and table-heavy
  layout. No missing references, missing citations, or fatal layout errors were
  observed.
