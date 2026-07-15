# Candidate-Pool, Conditional-Analysis, and Baseline Audit

Prepared before implementing any new pool, subset, or baseline, per task
instruction. Two read-only research passes (candidate-pool construction;
existing-but-unused baselines) were run first; this document consolidates
both into a single reviewed record with file:line citations, cross-checked
against source where the two passes overlapped.

## 1. Candidate-pool construction: current implementation

**Canonical definition**, imported and executed by the manuscript pipeline:
`reports/full_calibrated_core/scripts/run_phase0_phase1.py:223-232`

```python
def _select_candidates(ranker_scores: dict[str, dict[str, float]], top_k: int) -> list[str]:
    union_docs = sorted({doc_id for scores in ranker_scores.values() for doc_id in scores})
    if len(union_docs) <= top_k:
        return union_docs
    rrf_scores: dict[str, float] = defaultdict(float)
    for ranker in sorted(ranker_scores):
        ranked = sorted(ranker_scores[ranker].items(), key=lambda x: (-x[1], x[0]))
        for rank, (doc_id, _score) in enumerate(ranked, start=1):
            rrf_scores[doc_id] += 1.0 / (60.0 + rank)
    return sorted(union_docs, key=lambda d: (-rrf_scores.get(d, 0.0), d))[:top_k]
```

Imported into `full_calibration_utils.py:38`; sole call site
`full_calibration_utils.py:1041` inside `prepare_dataset_inputs()`:
`candidate_pool = _select_candidates(ranker_scores, spec.top_k)`.

- **Contributing rankers**: `RANKERS = ("bm25", "tfidf", "minilm")`
  (`run_phase0_phase1.py:37`). Pool = union of all three rankers' scored
  docs; RRF-truncated (fusion constant $k{=}60$) to `top_k` only when the
  union exceeds `top_k`.
- **Pool depth `top_k`**: from
  `experiments/method_improvement_audit_20260711_205733/phase_reports/canonical_rerun_manifest.json`
  via `_dataset_specs()`: **SciDocs 20, FiQA 20, HotpotQA 10, BRIGHT 20**
  (per-ranker retrieval depth `top_n` before pooling: 50/50/35/50).
- **Truncation logic**: top-$k$ of an RRF-fused ranking over the *union*,
  not top-$k$ per ranker then union.
- **Deduplication**: by `doc_id`, via a `set` comprehension
  (`run_phase0_phase1.py:224`); per-ranker score-file loading also dedups
  by keeping the max score per `(query_id, doc_id)`
  (`_load_score_file`, `run_phase0_phase1.py:185-199`).
- **Tie-breaking**: fully deterministic at every stage — `union_docs` is
  lexicographically sorted; per-ranker rank uses `(-score, doc_id)`;
  ranker iteration uses `sorted(ranker_scores)` (alphabetical); final
  truncation uses `(-rrf_score, doc_id)`. No reliance on Python dict/set
  iteration order.
- **Qrels leakage**: none in the canonical path — `_select_candidates`'s
  signature has no qrels parameter, and qrels are loaded and attached to
  per-query records only *after* `candidate_pool` is already fixed
  (`prepare_dataset_inputs`, `full_calibration_utils.py:1026-1060`).
  Caveat: two *non-canonical* scripts build genuinely qrels-driven pools
  for unrelated purposes — `src/rerankers/common.py:155-172`
  `build_candidate_pool` (reranker training pools) and
  `scripts/run_small_llm_pairwise_experiment.py:97-127`
  `_build_candidate_pool` (an LLM-pairwise pilot). Neither is imported by
  or reachable from the canonical files; flagged here only so the new
  alternative-pool module is never accidentally built by copying one of
  these.
- **Fairness across methods**: the pool is computed **once per query**,
  purely from raw per-ranker scores, before any graph/vote/repair/baseline
  computation, and is then shared by object identity across all 15 methods
  scored per query (Prior, RRF, CombSUM, Borda-fuse, graph Borda, Copeland,
  balance, Markov, topological/priority-topological, and the repaired
  variants of each graph method) — `CalibrationEvaluator.evaluate_query()`
  (`full_calibration_utils.py:909-1023`) takes `candidate_pool` as a
  read-only input parameter and never recomputes it; `graph.add_nodes_from(candidate_pool)`
  pins graph construction to the same fixed node set, and repair can only
  remove/reweight edges, never add or remove pool membership. This
  satisfies the task's "identical candidate pools across baselines"
  fairness requirement structurally, for the existing methods — the same
  discipline must be preserved for any new baselines added.
- **RRF's dual, non-identical role — the core finding.** RRF is used in
  two different places that are easy to conflate but are not the same
  computation:
  1. *Pool selection* (`_select_candidates`, above): ranks each ranker's
     entire native score map (not restricted to any candidate set), fuses
     with $k{=}60$, and truncates the union to this fused ranking's top
     `top_k`.
  2. *Comparison baseline* (`"rrf"` method,
     `full_calibration_utils.py:984`, via
     `consistency_ranker.rrf_ranking.per_query_rrf_ranking_from_score_maps`):
     same formula family and same $k{=}60$, but its output is restricted
     to the *already-fixed* `candidate_pool` from (1).
  3. A third RRF usage as the *repair prior*
     (`_rrf_prior_scores_for_query`, `scripts/run_real_experiment.py:954-984`)
     filters to candidate nodes **before** computing rank indices — a
     different rank-indexing scope again.

  This confound is not new to this task: it was already identified and
  quantified in a prior, uncommitted investigation
  (`reports/rrf_pool_investigation/`), whose `EXECUTIVE_CONCLUSION.md`
  states *"Classification: A. Severe confounding ... The baseline
  comparison is conditional on an RRF-centered candidate pool"*, and whose
  `CANDIDATE_POOL_ANALYSIS.md` already measured Jaccard overlap between the
  canonical RRF pool and five alternative pool policies (bm25-only 0.571,
  combsum 0.659, deterministic union 0.150, minilm-only 0.306,
  round-robin 0.476, tfidf-only 0.542) on a mean pool size of 17.56 docs.
  A companion audit table already exists on disk:
  `reports/full_calibrated_core/tables/rrf_implementation_used_in_full_run.csv`
  and `reports/full_calibrated_core/RRF_IMPLEMENTATION_NOTE.md`
  ("Prior vs RRF exact ranking match count: 216/6156"). **This task's pool
  robustness work supersedes and extends that investigation using the
  canonical engine and per-query records, the same relationship Task 2's
  work had to `retention_matching_investigation/`.**
- **Duplicate implementation** (consolidate, don't duplicate — same class
  of issue Task 2 found for threshold policies): `scripts/build_votes_file.py:109-131`
  defines a byte-for-byte identical copy of `_select_candidates`, used only
  to pre-build `ms1`/`ms1_drop_mutual`/`ms2` vote files consumed by other
  diagnostic phases — **not** read by `full_calibrated_core`'s own pool
  computation (which always recomputes fresh from raw scores). Currently
  in sync, but an unenforced duplication risk.
- **No caching**: candidate pools are recomputed fresh from raw score
  files on every run; only a scalar `candidate_count` is persisted to
  structural tables, never the doc-id list itself. The new alternative-pool
  module must persist actual pool contents (or a stable hash) in its
  manifests, since none of the existing infrastructure does this today.

## 2. Existing-but-excluded baseline methods

Canonical comparison currently persists exactly **9 methods** as
paired-delta pairs (`PAIR_SPECS`, `run_full_calibrated_core.py:206-222`):
`copeland_graph`, `balance_graph`, `markov_graph` (each vs. its repaired
counterpart, family `graph`), `copeland_hybrid`, `balance_hybrid` (vs.
repaired, family `hybrid`) — plus Prior/RRF/CombSUM/Borda-fuse as
non-graph reference methods in the broader retrieval-results table.

**Computed per query but silently dropped before persistence** (present in
`add_method(...)` calls inside `CalibrationEvaluator.evaluate_query()`,
`full_calibration_utils.py:978-996`, but filtered out because their method
key is not in `METHOD_KEYS`, `run_full_calibrated_core.py:188-204,525`):
`score_sum`, `borda` (graph Borda; distinct from the persisted
`borda_fuse`), `topological_repaired`, `priority_topological_repaired`.

**Imported but never called anywhere in either canonical file** (dead
imports, confirmed by grepping for `name(` beyond the `from ... import`
line): `pagerank_ranking`, `rank_centrality_ranking`,
`rank_centrality_scores` — all defined in
`src/consistency_ranker/baseline_ranking.py` (PageRank at lines 292-345:
`nx.pagerank` on the reversed preference graph; RankCentrality at
429-498: the Negahban-Oh-Shah stationary-distribution estimator, a known
consistent approximation to Bradley-Terry MLE).

**Bradley-Terry: fully implemented, never wired into the canonical
pipeline.** `src/rerankers/tournament_agg.py:109-186`
(`bradley_terry_ranking`, MLE via MM/iterative scaling,
$P(i \succ j) = p_i/(p_i+p_j)$). Already used and tested elsewhere
(`src/consistency_ranker/failure_mining/query_processor.py`,
`tests/test_modern_baselines.py:127-160`, several pilot scripts), but
`reports/full_calibrated_core/scripts/*.py` never imports
`tournament_agg`/`rerankers`. A **prior in-repo audit already flagged this
exact gap**:
`reports/manuscript_improvement_audit/MANUSCRIPT_CODE_DISCREPANCIES.md:111-113`
("D26: Bradley-Terry is implemented, used in real-LLM pilots, but absent
from the manuscript's main baseline table") and
`reports/manuscript_improvement_audit/REQUIRED_EXPERIMENTS.md:257-261`
("P1 — Add Bradley-Terry to the main baseline table ... only needs wiring
into the main pipeline"). That audit referenced an older results package,
not the current `full_calibrated_core` engine, but the underlying fact —
no import of Bradley-Terry code anywhere in the canonical scripts — was
independently re-verified against the current code.

**HodgeRank / Helmholtz decomposition: does not exist anywhere in the
repository** (`grep -rniE "hodge"` repo-wide: zero code matches, only two
mentions in a manuscript-positioning doc as a citation, not code). **Elo /
TrueSkill: also not implemented anywhere.** Building HodgeRank from scratch
(graph Helmholtz/harmonic decomposition of pairwise comparisons) is
nontrivial numerical-linear-algebra work, not "reasonable effort using
existing infrastructure" — **decision: do not implement HodgeRank in this
task**, consistent with the instruction to add new baselines "only if they
are scientifically justified and do not introduce excessive complexity."
Bradley-Terry, by contrast, is already implemented, tested, and previously
recommended for exactly this integration — **decision: wire in
Bradley-Terry.**

**Low-effort integration path already exists for PageRank/RankCentrality.**
`experiments/method_improvement_audit_20260711_205733/run_method_improvement_audit.py`
(dynamically loaded by `full_calibration_utils.py:141-151` purely to reuse
its `_apply_repair`/`_graph_component_scores`/`_hybrid_ranking` helpers)
already has a `_graph_component_scores(graph, method)` dispatcher
(`run_method_improvement_audit.py:783-797`) with working `"pagerank"` and
`"rank_centrality"` branches — the *same* dispatcher the canonical
pipeline already calls for `"copeland"`/`"balance"`
(`full_calibration_utils.py:878-879`), just never invoked with those two
method names. Adding PageRank and RankCentrality as new graph-method pairs
is therefore "call the existing dispatcher with a different string and add
two `PAIR_SPECS` entries," not new ranking-algorithm code — **decision:
integrate both as new `*_graph` pairs**, matching the existing
Copeland/balance/Markov pattern (repaired-vs-unrepaired, no hybrid
variant initially, to keep the new-baseline count proportionate and avoid
"weak or redundant baselines merely to increase the count").

**Markov has no hybrid counterpart even though the dispatcher supports
it** (`run_method_improvement_audit.py:788-789` already has a `"markov"`
branch). Adding `markov_hybrid` mirrors the existing
`copeland_hybrid`/`balance_hybrid` construction exactly — **decision: add
it**, since it closes a documented asymmetry (`PAIR_SPECS` audit found "no
`markov_hybrid`... a `markov_hybrid` pair could be added the same way")
rather than introducing a new baseline family.

**`pair_name`/`pair_family` convention** (for anyone extending
`PAIR_SPECS`): `*_graph` = the ranking method computed directly on the
preference graph with no fusion against the RRF-derived prior; `*_hybrid`
= the same graph component score linearly fused with the RRF prior via
`_hybrid_ranking(alpha=0.3, mode="minmax")`
(`full_calibration_utils.py:997-1000`). Both variants are always compared
unrepaired-graph vs. repaired-graph.

## 3. Net new-baseline decision (final, before implementation)

Add exactly four new persisted pairs, all reusing existing, already-tested
ranking code (no new ranking algorithms written), all following the
existing `*_graph`/`*_hybrid` naming and repaired-vs-unrepaired pattern:
`pagerank_graph`, `rank_centrality_graph`, `markov_hybrid`, and a
Bradley-Terry pair `bradley_terry_graph` (wiring
`tournament_agg.bradley_terry_ranking` into the same repaired/unrepaired
comparison the graph methods already use). Do **not** implement HodgeRank,
Elo, or TrueSkill. Do **not** resurrect `score_sum`/graph-`borda`/
topological methods into the paired-delta family — they were computed and
deliberately excluded already, and reviving them was not asked for and
would inflate the comparison without a stated justification.
