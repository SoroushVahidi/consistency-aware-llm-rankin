# Provenance and clearance limitations

- The historical experiment recorded commit `b0d48520b72dfa05f6cfe07309cb39ef980be032` with two modified helpers, an untracked study directory, and an untracked test. Later commits preserve relevant code, but no run-time patch or source-tree digest proves exact byte recovery. The clean rerun used later commit `b3926dee968840b10e1b2c17ef531347e172c236` and a documented path-only input-manifest overlay.
- All 32 inputs with historical SHA-256 records match the frozen copies. Four processed query and four processed document files were required by the loader and frozen now, but their historical hashes were never recorded.
- The Python environment was recorded with `environment-pip-freeze.txt` but reused the existing local virtual environment. No network access, new retrieval, LLM inference, or new judgments were used.
- Phase 5F found no full-key overlap in its checked public releases. The public GitHub main and Judgments dataset revisions were unchanged at the Phase 5G check; an exhaustive new public-release audit was not conducted overnight.
- The numerical table has pseudonymized query IDs, which are linkable to source IDs. The private source tree, score/vote inputs, benchmark text/qrels, raw rankings, and source map are not part of a public supplement.
- Upstream benchmark rights, derived metric redistribution, attribution and any share-alike duties, author-approved numerical-data license, JDIQ submission/anonymity/supplement rules, and author approval remain open. Numerical agreement does not grant publication clearance.
