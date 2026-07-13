# CombSUM Implementation Audit

**Prepared:** 2026-07-12
**Scope:** Part B2 — trace `src/consistency_ranker/combsum_ranking.py` and every call site.

---

## Code trace

- **Module:** `src/consistency_ranker/combsum_ranking.py` (139 lines, read in full this session).
- **Call sites:** `scripts/run_real_experiment.py` — imports `combsum_scores`/`per_query_combsum_ranking_from_score_maps` (line 75-77); dispatches when `"combsum"` is in the requested method list (line 1606-1614); `combsum_normalization` parameter threaded through the CLI (`--combsum-normalization`, line 2019) with default `COMBSUM_NORM_MINMAX` (line 1334, 2193) — the canonical vote suite (`scripts/run_publication_vote_suite.py`, `METHODS` list includes `"combsum"`, verified in an earlier session) does not override this flag, so the canonical package uses **min-max normalization**, not the `"none"` alternative.

## Mathematical definition (verified against code, numbered-equation-ready)

For a query $q$ with constituent rankers $s \in \{1,\dots,S\}$ (in this repository, the same score-prior files used elsewhere: BM25, TF-IDF, MiniLM) and candidate documents $d \in D_q$:

1. **Deduplication.** For each ranker $s$, if a document appears more than once in that ranker's score list for the query, keep only the maximum score (`dedupe_best_scores`, lines 34-40) — "same convention as RRF" per the module's own comment.
2. **Per-ranker min-max normalization** (default mode):
$$
\hat{score}_s(d) = \frac{score_s(d) - \min_{d'\in D_q^{(s)}} score_s(d')}{\max_{d'\in D_q^{(s)}} score_s(d') - \min_{d'\in D_q^{(s)}} score_s(d')},
$$
computed only over $D_q^{(s)}$, the documents ranker $s$ actually scored for query $q$ (`_minmax_normalize_query_ranker`, lines 49-62). **Degenerate case:** if ranker $s$'s scores for this query are all equal (within a $10^{-12}$ tolerance), every normalized value is set to exactly $0.0$ rather than dividing by zero — "so that ranker adds no discriminative signal for CombSUM (the run is flat)" (module comment, lines 52-54).
3. **Missing-document handling.** If a ranker did not score document $d$ at all for this query, that ranker contributes **0** to $d$'s fused score (implicit in `_combsum_fused_and_best_ranks`'s loop, which only iterates over documents present in each ranker's own `best` dict; a document absent from ranker $s$ never receives a $\hat{score}_s$ term).
4. **Fusion:**
$$
\mathrm{CombSUM}(d) = \sum_{s=1}^{S} \hat{score}_s(d).
$$
5. **Ranking and tie-breaking** (`combsum_ranking`, lines 105-126): candidates are sorted by (a) descending $\mathrm{CombSUM}(d)$; (b) ascending "best original rank" — the smallest 1-based rank $d$ achieved in *any* individual ranker's own ranking, used only to break exact CombSUM ties; (c) ascending document id, as a final deterministic tie-break.

## Deviations from the "standard" CombSUM as defined by Fox & Shaw (1994)

Per `COMBSUM_REFERENCE_VERIFICATION.md`, Fox & Shaw's original CombSUM is simply the sum of individual (similarity) scores across runs — it does not, in the original 1994 paper, specify a particular normalization scheme, since TREC-era retrieval systems' similarity scores were often already comparable. Because this repository fuses heterogeneous rankers (BM25, TF-IDF, a neural cross-encoder) whose raw score scales are not comparable, **per-(query, ranker) min-max normalization to $[0,1]$ before summation is a necessary adaptation, not part of the original definition.** This should be described in the manuscript as "CombSUM with min-max score normalization" or "a min-max-normalized CombSUM fusion," not as an unqualified reproduction of Fox & Shaw's exact 1994 procedure — consistent with how this repository's own `docs/baselines_and_datasets_references.md` (in the sibling `minimum-weighted-fas-heuristics` repository) already handles an analogous situation for its "weighted adaptation of Eades (1993)" baseline, explicitly flagging adaptations as the implementers' own rather than attributing them to the original authors.

No other deviation was found: missing-document handling (contribute 0), tie-breaking, and the overall sum-of-normalized-scores structure are all standard and unremarkable.

## Exact method labels used in outputs

- CLI/method-list identifier: `"combsum"` (lowercase, no separator) — confirmed in `scripts/run_publication_vote_suite.py`'s `METHODS` tuple and `scripts/run_real_experiment.py`'s dispatch condition.
- Output/table label (pooled comparison): `combsum`, as it appears verbatim in `experiments/final_method_gap_audit_20260711_221113/task3/final_baseline_comparison.csv`'s `method` column.
- No variant suffix (e.g., no `_minmax` or `_norm` qualifier) distinguishes the normalization choice in any output file — the choice is only recoverable from the code default, not from the data itself. This is a minor internal-consistency note: if a future ablation ever runs CombSUM with `normalization="none"`, the output method label would need to be manually disambiguated, since the current naming convention does not encode it.

## Recommended manuscript wording

See `COMBSUM_MANUSCRIPT_PATCH.md` for the exact sentences to use in Methods, Experimental Setup, and Table 3.
