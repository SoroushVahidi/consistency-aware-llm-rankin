# Method audit: ranking extraction stage

> Historical inventory of ranking-extraction methods added or transferred into
> this repository. Not a runnable experiment. Companion driver:
> `scripts/run_linear_extension_extraction_experiment.py`. See also
> `docs/experiments/OUTCOME_BCD_DRIVERS.md`.

## Hard-constraint topological methods

| Method | Status before | Status now | Notes |
|---|---|---|---|
| NetworkX `topological_ranking` | Implemented / used | Kept | Not explicitly lexicographic Kahn |
| Lexicographic Kahn (min id) | Missing as named API | **Added** | Deterministic baseline |
| Prior-priority topo | Implemented (`priority_topological_ranking`) | Wrapped / catalogued | Supports score-sum / RRF / CombSUM / Borda priors |
| Balance priority static/dynamic | Soft balance only; MWFAS had static weighted-net | **Added** | Hard constraint |
| Normalized balance static/dynamic | Soft hybrid min-max only; older MWFAS idea unused as topo tie-break | **Added** | Hard constraint |
| Degree-ratio / log-ratio static/dynamic | Missing | **Added** | Sources-only selection |
| Source/sink peeling | Missing (FAS peeling is not ranking peeling) | **Added** | Mechanically verified topo |
| Closest-valid-extension (greedy) | Missing | **Added** | Judgment-free prior |
| Closest/farthest exact (enumeration) | Missing | **Added** | Small-DAG oracle / diagnostic |
| Closest-valid-extension ILP (HiGHS) | Missing | **Added** | Medium-DAG exact reference |
| Random linear extensions | Missing | **Added** | Seed-reproducible |

## Soft score methods

| Method | Status before | Status now |
|---|---|---|
| Score-sum / Borda / Copeland / weighted balance | Implemented | Unchanged |
| Normalized weighted balance soft | Missing as dedicated method | **Added** |
| SpringRank | In related `ranking-by-feedback-arc-set` only | **Transferred** |
| SerialRank | In related repo only | **Transferred** |
| PageRank / RankCentrality / Markov | Implemented | Unchanged |
| Hybrid RRF+balance | Implemented (headline soft hybrid) | Unchanged |

## Judgment-free priors for prior-priority topo

| Prior | Status |
|---|---|
| Graph score-sum | `score_sum_prior_from_graph` |
| Graph tournament Borda | `borda_prior_from_graph` |
| Multi-system RRF | `rrf_prior_from_ranked_lists` |
| Multi-system CombSUM | `combsum_prior_from_score_maps` |
| Multi-system Borda fuse | `borda_fuse_prior_from_ranked_lists` |

## Older related repositories inspected

| Repo | Transferable ranking ideas | Action |
|---|---|---|
| `minimum-weighted-fas-heuristics` EXP11 | `min_id` / `max_id` / static `weighted_net` Kahn | Mapped to lexicographic + balance-static |
| `ranking-by-feedback-arc-set` | SpringRank, SerialRank | Transferred into `soft_score_ranking.py` |

## Manuscript claim hygiene

- Hard methods: every retained repaired edge is forward.
- Soft methods: may violate individual edges; report separately.
- Oracles that optimize proximity to a prior are diagnostics;
  qrels may score them after the fact but must not guide deployable ranking.
- Headline extraction method should change only under multiplicity-corrected
  paired significance against the current prior-priority topo baseline.
