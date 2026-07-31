# Offline pilot — consistency-aware active preference acquisition for budgeted reranking

Generated: `20260728T142414Z`. All judgments are replayed from a pre-existing,
frozen, real cached OpenAI (gpt-4o-mini) pairwise judgment artifact. **No live
provider or API calls were made in this pilot. No new judgments were
collected.**

## 1. Starting Git state

- Branch: `fix/outcome-f-production-operating-point`
- HEAD at start: `8e70029bd559c3aba1b090729a6960ea15bf4c2f`
- Working tree: clean

## 2. Backup branch

`backup/pre-active-acquisition-pilot-20260728-141641` (created at the HEAD above, before any change in this task).

## 3. Existing-data feasibility findings (Phase 1)

- The repository already contains a large `adaptive_acquisition/` package and a
  prior experiment (`reports/adaptive_acquisition_20260725T220000Z/`) covering
  nearly the same strategy space (random / static / uncertainty / cycle /
  `uncertainty_x_topk_impact`). **That prior work is entirely synthetic**
  (synthetic ground-truth permutations, synthetic judges, `INCOMPLETE.md`:
  "All headline claims here are synthetic") — it does not satisfy this task's
  requirement of an *offline oracle built from already-collected real
  judgments*, so it could not be reused as-is for this pilot, only as prior
  context.
- `outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl` **does**
  satisfy the requirement: 50 SciDocs queries × exactly `C(15,2) = 105`
  real gpt-4o-mini pairwise comparisons each (5,250 total, verified
  exhaustive), with `query_id`, `winner_doc_id`, `loser_doc_id` present for
  every row. Local qrels/queries/documents caches
  (`data/processed/beir/scidocs/`) make evaluation and a cheap initial ranking
  computable fully offline.
- **Confidence/margin is not available**: every judgment's `weight` field is
  `1.0` (binary win/loss only, single orientation, no repeats). This is
  disclosed, not hidden — it rules out any uncertainty signal based on
  provider confidence or repeated-judgment disagreement, and is the reason
  this pilot's uncertainty signal is instead a *current-evidence score-margin*
  measure (see §7).
- The candidate pool for each query was **built from qrels** (top-15
  judged docs sorted by relevance) by the original artifact-generating
  script, not from an independent retriever. Pool *membership* is therefore
  not qrels-free — but it is (a) fixed and identical across every strategy
  compared here, and (b) never touched by any acquisition-scoring function
  (only the fixed pool, revealed-so-far evidence, and BM25 prior are). This
  is disclosed as an inherited property of the source artifact, not
  something this pilot introduced or could leak through.
- Checked and confirmed reusable: `graph_construction.build_graph`,
  `evaluation.kendall_tau` / `ndcg_at_k`, `statistical_inference.*`
  (bootstrap CIs, Holm correction, sign-flip tests), `data.unified_loader`.
  The existing `adaptive_acquisition` package's `pair_uncertainty.py` /
  `ranking_impact.py` were inspected in depth but **not wired in**: they
  assume a repeated, multi-provider, multi-orientation evidence world (vote
  entropy, orientation/repetition/cross-model disagreement) that does not
  exist in this single-shot, one-judgment-per-pair oracle — using them as-is
  would have been cosmetic reuse of the wrong model, not a "large framework"
  violation avoided. Their *exact formulas* were mirrored where meaningful
  (see §8, existing UHT).
- **Dataset selected: SciDocs, `outputs/openai_scidocs_real_pairwise_q50_k15/`**
  — the only dataset/package found with real, exhaustive, per-pair cached
  judgments, canonical local provenance, a real qrels-bearing evaluation
  target, and a manageable size (50 queries × 105 pairs). No other dataset
  package in the repo had exhaustive real pairwise coverage (HotpotQA/FIQA
  real runs are `_run_`/`_pointwise_`/`_listwise_`, not exhaustive pairwise).

## 4. Selected dataset and justification

SciDocs, 50 queries, candidate pool size 15 (fixed), 105 pairs/query,
gpt-4o-mini judgments, `temperature=0.0`, `debias_position=False`. Chosen
over all alternatives because it is the *only* package meeting every Phase-1
requirement simultaneously (exhaustive, real, locally reproducible qrels,
manageable runtime), not because its early results looked favorable — the
dataset was selected and the pilot config frozen (`configs/offline_active_acquisition_pilot_v1.json`)
before the strategy comparison was run.

## 5. Exact offline-oracle definition

`QueryOracle.oracle: dict[frozenset({doc_i, doc_j}), winner_doc_id]`, one
exhaustive entry per unordered pair per query, loaded verbatim from
`judgments.jsonl` (SHA-256 of the input file recorded in `MANIFEST.json`).
`QueryOracle.reveal(i, j)` is the only way a strategy may learn a judgment,
and it is called exactly once per pair, only for pairs the strategy itself
selects.

## 6. Leakage controls

- Every acquisition-scoring function (`scoring.uncertainty_score`,
  `ambiguity_score`, `topk_impact_score`, `proposed_score`, and all four
  ablations) has the literal signature `(ctx, i, j)` — enforced by a
  parametrized test (`test_scoring_functions_do_not_accept_oracle_or_qrels`)
  that inspects each function's signature and fails if any extra parameter
  (let alone one named `oracle`/`relevance`/`qrel`) is even *possible* to pass.
- A behavioral test (`test_scoring_is_invariant_to_the_unrevealed_answer`)
  builds a partial acquisition state, then flips the cached oracle answer for
  a still-unrevealed pair and recomputes every score — asserted bit-identical,
  because the scoring functions are built only from the `revealed`-so-far
  Copeland tally and the qrels-free BM25 prior.
- qrels (`QueryOracle.relevance`) are read only inside `evaluate.py`
  (post-hoc metrics), never passed into `scoring.py` / `strategies.py`.
- 24/24 tests pass (`tests/test_offline_active_acquisition.py`), including
  the two leakage tests above and extraction-rule order-invariance /
  determinism checks.

## 7. Acquisition strategies (Phase 3)

Seven distinct algorithms were simulated (five other requested labels are the
same algorithm under a disclosed alias — see below and `strategies.py`'s
module docstring):

| Label | Algorithm |
|---|---|
| `random_unobserved` | uniform-random remaining pair, seeded |
| `static_adjacent` | pairs sorted once by initial-BM25-rank adjacency, fixed order |
| `uncertainty_only` | score-margin uncertainty (current Copeland+BM25 combined score) |
| `cycle_scc` | same-SCC / cycle-participation first, uncertainty tie-break |
| `existing_uht` | production UHT's `uncertainty_x_topk_impact`; see finding below |
| `proposed` | `uncertainty × impact × (1 + ambiguity)` |
| `exhaustive` | derived, not simulated (see §9) |
| `initial` | derived, not simulated (see §9) |

**Finding, disclosed rather than hidden:** production UHT's vote-based
uncertainty measure is `1.0` for every never-yet-judged pair and only
differs once *repeated* judgments exist for the same pair (`pair_uncertainty.py`,
`vote_uncertainty`). This oracle has exactly one judgment per pair, no
repeats — so `u × impact` reduces exactly to ranking by `impact` alone.
`existing_uht` is therefore **algorithmically identical to
`ablation_impact_only`** in this regime; both are reported, not omitted.

## 8. Proposed scoring formula (Phase 2/4)

```
uncertainty(i, j) = 1 / (1 + |combined_score(i) − combined_score(j)|)
    combined_score(d) = Copeland(d)/(n−1) + normalized_BM25(d)
ambiguity(i, j)  = 1.0 if i, j share a strongly-connected component of the
                   currently-revealed graph; 0.5 if either is in some other
                   cycle; else 0.0
impact(i, j)     = exact counterfactual: add hypothetical edge i→j, then j→i;
                   recompute the same Copeland+BM25 extraction both times;
                   impact = 0.5·(1 − top-k Jaccard(A, B)) + 0.5·(1 − τ(A,B))/2
score(i,j) = uncertainty(i,j) · impact(i,j) · (1 + ambiguity(i,j))
```

Acquisition cost is uniform in this dataset (every judgment costs one unit),
so no explicit cost term is included — stated, not hidden. The extraction
rule used everywhere (both for the running ranking and inside the exact
counterfactual) is Copeland aggregation (wins − losses over revealed edges),
BM25 tie-break, doc-id tie-break — **not graph repair**; this pilot studies
the acquisition policy, not the repairer, consistent with the pivot's intent.

## 9. Evaluation protocol (Phase 5)

Primary cutoff **k = 10** (chosen because the candidate pool is 15 documents;
using k = 15 = pool size would make "top-k membership" trivially constant
for every candidate, destroying the concept of top-k impact — this is a
methodological necessity, not a favorable-result search). nDCG@15 was also
tracked for continuity with the source artifact's convention and shows the
same qualitative pattern throughout (§12).

Budgets: 0%, 5%, 10%, 20%, 40%, 60%, 100% of 105 pairs → {0, 5, 11→(rounds
to 11 but realized set was {5,10,21,42,63,105} after rounding — see
`MANIFEST.json`)}. The same realized integer budgets were used for every
strategy.

**Exact, not approximate, simplification used:** because Copeland aggregation
depends only on the *set* of revealed edges, not the order revealed, (a) the
0%-budget ranking is identical for every strategy (pure BM25 — no edges
revealed yet) and (b) the 100%-budget ranking is identical for every strategy
(the full-oracle Copeland ranking). Both are computed once per query
(`reference_rankings`) rather than re-simulated per algorithm — verified by
test (`test_exhaustive_ranking_is_order_invariant_across_algorithms`).

## 10. Statistical protocol (Phase 6)

Pre-registered rule (frozen in `configs/offline_active_acquisition_pilot_v1.json`
before results were inspected): compare `proposed` against whichever of
{`random_unobserved`, `static_adjacent`, `uncertainty_only`, `cycle_scc`,
`existing_uht`} has the highest mean nDCG@10 at the 20%-budget checkpoint, at
both the 10% and 20% budgets. Family of 10 primary comparisons
(proposed vs. each of 5 baselines × 2 budgets), Holm-corrected. Paired
bootstrap CIs (10,000 reps), exact/Monte-Carlo sign-flip p-values, Cohen's d,
win/tie/loss — all via the repository's existing `statistical_inference.py`.

## 11. Results at each budget (mean nDCG@10, n = 50 queries)

| Strategy | 0% | 5% | 10% | 20% | 40% | 60% | 100% |
|---|---:|---:|---:|---:|---:|---:|---:|
| **random_unobserved** | 0.801 | **0.823** | **0.862** | **0.902** | 0.936 | 0.965 | 0.972 |
| static_adjacent | 0.801 | 0.769 | 0.756 | 0.846 | 0.886 | 0.926 | 0.972 |
| existing_uht / ablation_impact_only | 0.801 | 0.742 | 0.769 | 0.840 | 0.908 | 0.938 | 0.972 |
| ablation_impact_x_uncertainty | 0.801 | 0.675 | 0.717 | 0.770 | 0.864 | 0.925 | 0.972 |
| **proposed / ablation_full** | 0.801 | 0.675 | 0.717 | 0.772 | 0.823 | 0.907 | 0.972 |
| uncertainty_only / cycle_scc (≈tied) | 0.801 | 0.674 | 0.711 | 0.776 | 0.813–0.822 | 0.892–0.900 | 0.972 |

The pre-registered strongest non-oracle baseline (by the frozen rule) is
**`random_unobserved`**.

**Primary comparison result:** `proposed` is *significantly worse* than
`random_unobserved` at both pre-registered budgets:

| Budget | Mean Δ nDCG (proposed − random) | Cohen's d | 95% CI | Holm p | W/T/L |
|---|---:|---:|---:|---:|---:|
| 10% (11 pairs) | −0.145 | −0.86 | [−0.191, −0.099] | 0.0010 | 9/0/41 |
| 20% (21 pairs) | −0.130 | −0.76 | [−0.176, −0.083] | 0.0010 | 14/0/36 |

## 12. Quality–budget frontier

AUC of the mean-nDCG-vs-budget-fraction curve (higher = better):

| Strategy | AUC | Budget to 90% of exhaustive gain | Budget to 95% | Top-10 stabilization budget |
|---|---:|---:|---:|---:|
| random_unobserved | **0.933** | **41.4 (39%)** | **51.0 (49%)** | 86.5 (82%) |
| existing_uht / impact_only | 0.898 | 56.7 (54%) | 64.2 (61%) | 80.4 (77%) |
| static_adjacent | 0.892 | 60.0 (57%) | 67.5 (64%) | 88.2 (84%) |
| ablation_impact_x_uncertainty | 0.868 | 74.5 (71%) | 78.5 (75%) | 66.3 (63%) |
| proposed / ablation_full | 0.855 | 80.0 (76%) | 83.5 (80%) | 69.3 (66%) |
| cycle_scc | 0.851 | 75.2 (72%) | 82.5 (79%) | 71.8 (68%) |
| uncertainty_only | 0.850 | 72.7 (69%) | 80.5 (77%) | 72.7 (69%) |

(Budget-to-X% is computed only over the 42/50 queries where exhaustive
actually improves nDCG over the initial ranking — see §15; the other 8 are
excluded, not given a misleading ratio, per the task's explicit requirement.)

AUC comparisons (`proposed` vs. each baseline, Holm-corrected):

| Baseline | Mean Δ AUC | Holm p | W/T/L |
|---|---:|---:|---:|
| random_unobserved | −0.078 | 0.0005 | 9/0/41 |
| existing_uht | −0.044 | 0.0008 | 15/0/35 |
| static_adjacent | −0.037 | 0.0012 | 12/0/38 |
| cycle_scc | +0.004 | 1.000 (n.s.) | 28/0/22 |
| uncertainty_only | +0.005 | 1.000 (n.s.) | 26/0/24 |

`proposed` is statistically significantly **worse** than random, static, and
impact-only selection, and statistically indistinguishable from
uncertainty-only / cycle-based selection.

## 13. Runtime

Mean acquisition-decision time: **0.52 ms**; max observed: **1.57 ms**
(2,500 timed decisions across all queries/budgets/exact-counterfactual
strategies). Exact counterfactual top-k impact is trivially cheap at this
pool size (15 docs); no approximation is needed for a pilot at this scale.

## 14. Ablation results (Phase 7)

| From → To | Budget | Mean Δ nDCG | Sign-flip p | W/T/L |
|---|---:|---:|---:|---:|
| uncertainty_only → impact_only | 10% | **+0.058** | 0.037 | 32/0/18 |
| uncertainty_only → impact_only | 20% | **+0.064** | 0.018 | 30/0/20 |
| impact_only → impact×uncertainty | 10% | **−0.052** | 0.041 | 18/0/32 |
| impact_only → impact×uncertainty | 20% | **−0.070** | 0.002 | 15/0/35 |
| impact×uncertainty → +ambiguity (proposed) | 10% | 0.000 | 1.00 | 0/50/0 |
| impact×uncertainty → +ambiguity (proposed) | 20% | +0.002 | 0.75 | 2/47/1 |

**Interpretation:** impact alone is the strongest non-random, non-oracle
signal tested. Multiplying by the uncertainty term *significantly hurts*
(the opposite of the hoped-for effect). The graph-ambiguity factor adds
essentially nothing (50/50 exact ties at the 10% budget) — with only 15 docs
and few revealed edges, cycles are rare early on, so `(1 + ambiguity)` is 1.0
for nearly every candidate pair at the budgets that matter.

## 15. Failure cases

- **8/50 queries (16%)**: exhaustive acquisition does not improve nDCG@10
  over the qrels-free BM25 initial ranking at all. These are excluded from
  `budget_to_90pct`/`budget_to_95pct` (reported as undefined, not a
  misleading ratio), per the task's explicit requirement.
- **Low-budget harm.** At 5–20% budgets, every non-random strategy that
  targets "informative" pairs (impact, uncertainty, cycle-participation)
  scores *below* the 0%-budget initial ranking (e.g. `proposed`: 0.801 → 0.675
  at 5%) before eventually recovering past it. The leading hypothesis,
  supported by the ablation chain (§14): the extraction rule gives any
  nonzero Copeland tally **strict lexicographic priority** over the BM25
  prior (a documented, pre-existing repo convention, not introduced by this
  pilot — see `run_openai_real_pairwise_q30.py`'s own `llm_pairwise_copeland`
  method). Impact- and uncertainty-seeking strategies concentrate their first
  few judgments exactly on pairs near the current top-k boundary — precisely
  where a single (real, occasionally noisy) LLM judgment can eject an
  otherwise-relevant, high-BM25-prior document from the top-10 based on one
  comparison. Random selection spreads its early judgments broadly and
  triggers this instability far less often. This is a plausible, testable
  mechanism, not a proven one — a smoother (non-lexicographic) blend of the
  prior and revealed evidence is the natural follow-up experiment, but building
  it is out of scope for this pilot (see §17).

## 16. Scientific interpretation

- **Not Outcome D**: exhaustive acquisition clearly, substantially improves
  ranking quality over the cheap initial ranking (mean nDCG@10 0.801 → 0.972;
  42/50 queries individually improve) — the acquisition problem is
  meaningful on this dataset.
- **Not Outcome A or B**: no budget, and no query regime inspected, shows the
  proposed top-k-impact-aware consistency strategy dominating or even
  matching the strongest simple baseline (random selection). The one
  positive, Holm-significant finding among the ablations (impact alone beats
  uncertainty alone) does not rescue the *combined* proposed formula, which
  is dragged down by the uncertainty term.
- **Outcome C**: "Top-k-impact-aware selection does not beat simple
  uncertainty or static baselines" — and, more starkly, none of the tested
  adaptive/structural strategies beat **plain random pair selection** under
  this extraction rule, at any budget checked. This is a clean, well-powered
  (n = 50, Holm-corrected, large effect sizes) negative result, not a
  underpowered null.

## 17. Stop/go recommendation

None of the four "continue" conditions are met: no statistically supported
advantage over strong simple baselines at low budgets (the opposite is
observed); no large fraction of exhaustive quality reached with fewer
comparisons relative to the strongest baseline; no regime found where the
proposed method wins; the one interpretable new finding (impact-only beats
uncertainty-only, and combining them hurts) argues *against* the specific
proposed formula rather than for it. Two of the "stop" conditions are met
directly: results are dominated by a baseline (random) at every tested
budget, and this holds across all 50 queries, not a tiny subgroup.

**Recommendation: do not build the larger active-acquisition framework**
around this proposed formula. If this direction is revisited, the most
promising next step suggested by this pilot's evidence is narrower than the
original proposal: investigate *why* naive Copeland extraction interacts
badly with boundary-seeking acquisition (§15) — e.g. a softer, magnitude-aware
blend of the BM25 prior and partial evidence — before re-testing any
impact/uncertainty-based selection rule. That is new, separate work, not
performed here.

## 18. Files changed

- `src/consistency_ranker/active_acquisition/{__init__,oracle,scoring,strategies,simulate,evaluate,stats}.py` (new)
- `scripts/run_offline_active_acquisition_pilot.py` (new)
- `tests/test_offline_active_acquisition.py` (new, 24 tests)
- `configs/offline_active_acquisition_pilot_v1.json` (new, frozen)
- `reports/offline_active_acquisition_pilot_20260728T142414Z/` (this report + data — **now tracked in Git minus one file**, see §20; supersedes the original "kept local, not committed" note)

No code in this pilot's own files changed during the post-audit polish
pass (the Wilson-interval and capped-run-reporting fixes applied to the
other two pilots do not apply here: this pilot has no severe-harm-rate or
stopping/capped concept — it compares nDCG/AUC deltas via
`bootstrap_mean_interval`, which is the statistically appropriate tool for
those continuous paired statistics and was not touched).

## 19. Tests and quality checks

- `pytest tests/test_offline_active_acquisition.py -q` → **24 passed**
  (unchanged).
- `pytest -q` (full repository suite, re-verified during the post-audit
  polish pass) → **1127 passed, 0 skipped, 0 failed** in 162.25s.
- `ruff check` → clean on all new files.
- **Correction (post-audit polish pass):** no type checker is configured
  in this repository (no `[tool.mypy]` in `pyproject.toml`; `mypy` is not
  a dev dependency and is not installed in this environment). The original
  version of this section claimed a clean `mypy` run; that described a
  different environment/session's ad hoc use of the tool, not a repository
  convention.

## 20. Commits created

1. Pilot implementation and tests (`src/`, `scripts/`, `tests/`) —
   `756495d`.
2. Frozen configuration (`configs/offline_active_acquisition_pilot_v1.json`)
   — `e4566aa`.
3. This report directory tracked in Git (minus one deterministically-
   regenerable raw log, `raw_trajectories.jsonl`, kept local via a narrow
   `.gitignore` rule) — **now created** in the post-audit polish pass,
   overriding the original version of this section (which had left this as
   a flagged open decision for the user). See `docs/ARTIFACT_POLICY.md`'s
   updated classification table.

## 21. Final Git status

Working tree clean on all tracked files after the commits above. This
report directory is now tracked (minus `raw_trajectories.jsonl`), along
with the other two consistency-aware-pivot report directories. See the
post-audit polish pass's own final report for the exact push outcome. No
history rewritten, no force-push, no merge into `main`.

## Explicit confirmations

- No live provider or API calls were made.
- No new judgments were collected.
- No frozen canonical evidence was modified.
- No history was rewritten.
- No push was performed.

**PIVOT NOT SUPPORTED — CHANGE RESEARCH DIRECTION**
