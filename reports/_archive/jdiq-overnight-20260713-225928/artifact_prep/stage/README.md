# Anonymous review artifact — preference-graph repair measurement study

This bundle supports double-anonymous review of the accompanying manuscript.

## Contents
- `manuscript/` — TeX sources, PDF, figures
- `inputs/` — stored BM25 / TF-IDF / MiniLM scores and query-ID lists
- `tables/` — manuscript-ready calibrated tables
- `code_snapshot/` — ranking/repair/evaluation code needed to regenerate mechanical results

## Anonymity
Author identity, institutional affiliation, and public repository remotes are withheld.
Do not attempt to deanonymize during review.

## Reproduction (high level)
1. Install Python >=3.11 and dependencies from `code_snapshot/requirements.txt`.
2. Use stored inputs under `inputs/` (do not regenerate upstream retrieval).
3. Follow manifests in `tables/` / manuscript Data Availability section for seeds and protocols.

Bootstrap seed 13; permutation seed 17; 10,000 resamples each (manuscript Experimental Setup).
