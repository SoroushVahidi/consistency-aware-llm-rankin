# Limitations and Threats to Validity

*Required section content per the manuscript plan. Each item states the
limitation and, where possible, the concrete number that quantifies it.*

## Statistical / design limitations

- **Limited number of independent queries.** All headline statistics rest
  on n=419 distinct (dataset, query_id) units — a real but modest sample
  for detecting effects as small as those observed here. The 95% CI on
  the primary headroom estimate ([0.0020, 0.0030]) is itself evidence of
  this: it is narrow in absolute terms but represents real sampling
  uncertainty around an already-tiny point estimate.
- **Repeated regimes per query.** Each of the 419 queries is observed
  under a mean of ~292 experimental variants (regime × pool × pool size ×
  metric cutoff × pair/extraction method × protocol). These variants are
  not independent draws; the paper's primary inference uses query-level
  aggregation specifically to avoid pseudo-replication (see
  `docs/research/REPRODUCIBILITY_AND_ARTIFACTS.md`), and any table or
  figure using the row-level (122,203-row) unit must be labeled as such
  and not used for primary significance claims.
- **Row-level vs. query-level headroom by regime is not fully
  reconciled.** `manuscript_tables/table_3_oracle_headroom.csv`'s
  by-regime breakdown uses row-level (not query-level) CIs, because
  query-level-within-regime aggregation for every regime cell was not
  computed in this pass. The relative ranking across regimes (`ms1` ≫
  `ms1_drop_mutual` > `ms2`) is almost certainly robust to this (the
  effect is large and monotonic), but the exact CI widths for individual
  regime cells should be treated as approximate.

## Data / scope limitations

- **Dependence on the four available datasets** (SciDocs, FiQA, HotpotQA,
  BRIGHT). These are the datasets this repository's infrastructure
  supports; the finding has not been tested on datasets with different
  query characteristics (e.g., conversational, multi-hop-only, or
  extremely large candidate pools beyond what was tested here).
- **Dependence on the evaluated judges.** The large majority of the
  unified evidence (source families `pool_robustness_greedy`,
  `full_calibrated_core_greedy`, `pool_cutoff_*`, `exact_ilp_task4`) uses
  a single judge configuration per source; only
  `real_llm_integrity_policy_sensitivity` (1,974 of 122,203 rows) varies
  judge provider (Cohere, Azure) directly. The finding should not be
  assumed to generalize to substantially different judge models without
  further evidence.
- **Dependence on whole-graph repair.** This paper's entire scope is
  whole-graph MWFAS repair (greedy and exact). It says nothing about
  component-level, edge-level, or partial-repair interventions — these
  are explicitly out of scope and flagged as a distinct, unevaluated
  future question (`docs/research/DECISION_LOG.md` entry D6).
- **Downstream metric noise.** nDCG@10 (the primary metric throughout) is
  itself a noisy statistic at the per-query level; some fraction of the
  observed "benefit"/"harm" split reflects metric noise rather than a
  genuine repair effect, though the manuscript's own MDE-based framing
  (Claim 3) is precisely designed to account for this by asking whether
  the *effect*, not just its sign, clears a meaningful threshold.
- **Relevance-judgment limitations.** Downstream metrics depend on the
  qrels each dataset provides, which have their own known incompleteness/
  graded-relevance limitations independent of anything measured here.
- **Candidate-pool construction.** Multiple pool construction methods were
  tested (`rrf_union_topk`, `equal_depth_union`, `neutral_round_robin_union`,
  `bm25_only`, `combsum_union_topk`), but all are pool-construction methods
  already implemented in this repository; entirely different pooling
  strategies (e.g., learned or query-adaptive pooling) were not tested.
- **Repair-objective mismatch.** MWFAS repair minimizes total removed
  edge weight (a structural objective); it is not directly optimized for
  the evaluated downstream metric. Claim 5's hypotheses partly concern
  this mismatch but do not resolve it — a metric-aware repair objective
  (noted as implemented but not evaluated at scale in this repository,
  `reports/repair_selector_mining`-adjacent code) remains untested here.
- **Possible local effects hidden by aggregate metrics.** nDCG@10
  aggregates over the whole ranked list; a repair effect concentrated at
  a single rank position, or affecting relevance-graded documents outside
  the top-10 window, would not be fully visible in this metric even if
  locally large. This is the empirical motivation for the component/edge-
  level reformulation flagged as a distinct future question.
- **External validity to generative or non-IR ranking tasks.** All
  evidence here concerns retrieval ranking specifically. Nothing in this
  paper's evidence base speaks to consistency-repair questions in
  generative ranking, recommendation, or other non-IR pairwise-preference
  settings — any extrapolation there would be unsupported by this paper's
  evidence.

## Threats specific to the selector-attempt synthesis (Table 6)

- Two of the four attempts (`outputs/learned_selector/`,
  `experiments/failure_class_audit_20260711_212157/`) have incompletely
  documented methodology in their surviving artifacts (feature sets and
  training data are not fully specified for the second). Their inclusion
  in the synthesis is as corroborating, not primary, evidence — the
  paper's primary evidence is the repository-scale analysis (Claim 3/4),
  which is fully reproducible from committed code and cited artifacts.
- The externally-cited sibling-repository result
  (`papers/JDIQ_2026/CONTRIBUTION_AUDIT.md` line 103) is explicitly
  out-of-scope for direct citation (a different codebase) and is
  mentioned only as context, never as primary evidence, per that
  document's own scoping note.
