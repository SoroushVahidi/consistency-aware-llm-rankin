# Related Work / Literature Positioning Changelog

Date: 2026-08-02  
Branch: `papers/sncs-2026-foundation`  
Scope: Related Work rewrite, closest-work table, bibliography additions,
External Validity baseline framing. No experiment/result/table-number changes.

## Structure after revision

1. **§2.1 Pairwise Ranking and Preference Aggregation** — probabilistic vs.\
   combinatorial traditions; GNNRank as learned upset minimization; gap =
   graph-internal objective ≠ qrel utility.
2. **§2.2 Pairwise and Graph-Based Ranking in IR** — pairwise/listwise LLM
   ranking and TourRank as *using* pairwise evidence; PRP-Graph /
   LLM-RankFusion as graph aggregation; this paper’s marginal-repair audit.
3. **§2.3 Inconsistency, Cycles, and Preference Repair** — MWFAS / exact
   controls; LLM-judge cycles; PGED and TCR as acyclicity gains on
   non-retrieval downstream tasks; compact **Table `tab:closest-works`**.
4. **Preprint relationship** — retained **Table `tab:preprint-comparison`**.
5. **§2.4 Structural Quality vs.\ Downstream Utility** — intrinsic vs.\
   contextual quality; corrected IR inference; joint-gap statement (hedged).

## Bibliography entries added

| Key | Source verification |
|---|---|
| `chen2025tourrank` | Crossref DOI `10.1145/3696410.3714863`; WWW 2025 |
| `he2022gnnrank` | PMLR `https://proceedings.mlr.press/v162/he22b.html` |
| `vahidi2024mwfas` | arXiv `2412.16181` (preprint note) |
| `liu2025votinggraph` | arXiv `2510.15514` (preprint note) |

## Claim registries

`docs/CONTRIBUTIONS.md`, `docs/claim_evidence_registry.yaml`,
`papers/SNCS_2026/result_claims.yaml`, and `EVIDENCE_MAP.md` were **not**
changed (no scientific claim reclassification).

## Compile / page count

- Clean `tectonic` build of `papers/SNCS_2026/manuscript/main.tex`
- Pages: **36** (unchanged vs.\ post-novelty-positioning PDF)
- Approx.\ body words (crude strip): ~10.6k
- No undefined citations/references in the TeX log

## External Validity

Limitations now state explicitly that BM25/TF-IDF/MiniLM and graph-free
fusion anchors are **not** claimed to be SOTA; modern neural/LLM rerankers
are out of scope for the repair audit.
