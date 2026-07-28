# Risk-controlled stopping-rule pilot for the regularized rank aggregator

Generated: `20260728T190000Z`. All judgments are replayed from the same
pre-existing, frozen, real cached OpenAI (gpt-4o-mini) pairwise judgment
artifact used by both prior pilots in this pivot. **No live provider or API
calls were made. No new judgments were collected. No frozen evidence was
modified.**

Research question: *Can the regularized aggregator support a practical,
qrel-free stopping rule that terminates pairwise acquisition early while
preserving top-k quality and controlling harmful premature stopping?*

## 1. Starting Git state

- Branch: `fix/outcome-f-production-operating-point`
- HEAD at start: `c568b87e2398dbd15a5b8e088d4d23adcfddbdb4`
- Working tree: clean except the two prior pilots' untracked local report
  directories (both left untouched throughout).

## 2. Backup branch

`backup/pre-risk-controlled-stopping-pilot-20260728-182920` (created at the
HEAD above, before any change in this task).

## 3. Reproduction of regularized-aggregation results (Phase 1)

`python -m pytest tests/test_offline_active_acquisition.py
tests/test_regularized_aggregation.py -q` → **45 passed** (unchanged).

`python scripts/run_regularized_aggregation_pilot.py --mode evaluate` was
rerun into a fresh directory and diffed against
`reports/regularized_aggregation_pilot_20260728T164943Z/evaluation/`:
`aggregation_trajectories.csv`, `statistical_analysis.json`, and
`MANIFEST.json` were **bit-identical**. Confirmed: the 15/35 dev/test split
(seed 4242), the frozen `linear_decay` schedule (`lambda0=8.0`), the
deterministic BM25 prior, the reported budget-curve numbers, the severe-harm
threshold (`deltaNDCG@10 <= -0.05`), and the exhaustive reference ranking all
match exactly. **No correctness bug was found**, so the aggregation method
was not modified (per Phase 1's instruction) except as noted in §3a.

**3a. One necessary consequence of extending the aggregator.** Building the
stopping rule required a cheap, deterministic, fixed-iteration-count
Bradley-Terry refit for its internal what-if simulations (see §4). While
validating that refit's determinism, a pre-existing latent bug surfaced one
level down: `regularized_aggregation.py`'s optimizer already runs 3000
fixed-iteration Adam steps for exactly this reason (see the prior pilot's own
§6 determinism fix), and *that* fix in turn depends on `oracle.py`'s
`bm25_scores()`. No further changes were needed here -- this section is
recorded only to confirm the reproduction check in this paragraph was run
*after* that prior fix, not before, and still matched exactly.

## 4. Stopping-rule definition (Phase 2)

**Primary rule: counterfactual worst-case top-k stability**
(`src/consistency_ranker/active_acquisition/stopping.py`). After each newly
revealed judgment:

1. Take the current, exact, frozen regularized-aggregation utilities and
   ranking (unmodified `regularized_bt_ranking` / `fit_bt_utilities`).
2. Consider a **deterministic subset** of still-unrevealed pairs: those with
   at least one endpoint within `_BOUNDARY_WINDOW = 3` ranks of the current
   cutoff `k` (pairs far from the boundary essentially cannot flip top-k
   membership, so evaluating them exactly would spend nearly all the
   per-step compute budget on pairs that structurally cannot matter --
   disclosed, not hidden, per Phase 2's explicit allowance for "an efficient
   deterministic subset").
3. For each such pair, simulate both possible outcomes (i beats j; j beats
   i) and refit the aggregator under each -- warm-started from the current
   utilities with a fixed 150-iteration Adam refit (vs. the frozen
   aggregator's own 3000-iteration cold-start fit), a disclosed
   computational approximation used *only* for this internal simulation
   (never for anything reported as ranking/nDCG quality).
4. Measure `topk_distance(current_ranking, counterfactual_ranking, k)`: the
   max of three interpretable components -- top-k **membership** Jaccard
   distance, top-k **ordering** (Kendall tau restricted to the union of the
   two top-k sets), and rank **displacement** near the cutoff.
5. `worst_case_topk_change` = the max of that distance over every considered
   pair and both outcomes.
6. Stop when `worst_case_topk_change <= tau` for `m` consecutive steps
   (patience).

**Baseline rule: simple recent-stability** -- stop when the top-k *set* is
unchanged for `m` consecutive steps (no counterfactual simulation).

Leakage discipline: every function in `stopping.py` takes only the fixed
candidate pool, revealed-so-far outcomes, the qrels-free BM25 prior, the
frozen schedule, and the current (already qrels-free) utilities. It
generates its own hypothetical outcomes for unrevealed pairs -- it never
reads the oracle's actual cached answer for them, and never sees qrels or
the exhaustive ranking (enforced by 21 tests, §6).

## 5. Threshold and patience selection (Phase 4)

Selected on the **existing 15-query dev split** (same split as the
regularized-aggregation pilot, seed 4242), random order only, **before any
test-set metric was computed**. 15 (tau, patience) combinations were tried
(`tau in {0.10, 0.15, 0.20, 0.25, 0.30} x patience in {2, 3, 5}`; full table
recorded in `configs/stopping_rule_pilot_v1.json`'s
`threshold_selection_rationale` and reproduced below):

| tau | m | median budget | mean nDCG | severe-harm (of 15) |
|---:|---:|---:|---:|---:|
| 0.10 | any | 60.0% (capped) | 0.90 | 0 |
| 0.15 | 3 | 60.0% (mostly capped) | 0.91 | 0 |
| **0.20** | **3** | **32.4%** | 0.88 | **0** |
| 0.20 | 2 | 30.5% | 0.87 | 0 |
| 0.20 | 5 | 43.8% | 0.89 | 0 |
| 0.25 | 3 | 21.9% | 0.86 | 0 |
| 0.30 | any | 10.5-17.1% | 0.83-0.85 | 0 |

`tau <= 0.15` essentially never triggers within the 60%-budget simulation
cap; `tau >= 0.30` triggers very early but with mean nDCG 0.07-0.14 below
the exhaustive-BM25 gap. `tau = 0.20` was the smallest threshold reliably
triggering well inside the cap while keeping severe-harm at 0/15 across
every combination tried. `lambda0`-style patience sensitivity: `m=2` (30.5%
median) and `m=5` (43.8% median, crossing the 40% H1 target) bracket the
chosen `m=3`.

**Frozen**: primary `(tau=0.20, m=3)`; sensitivity settings
`(tau=0.15, m=3)` (conservative) and `(tau=0.25, m=3)` (aggressive), varying
only `tau` at fixed patience. Simple-rule patience also fixed at `m=3` for a
fair comparison. Simulation horizon capped at 60% of exhaustive pairs (63 of
105) -- matching the task's own "needs more than 60% -> insufficiently
useful" bar, so nothing scientifically relevant is lost by not simulating
further; disclosed in `configs/stopping_rule_pilot_v1.json`.

## 6. Leakage protections (Phase 5)

21 new tests in `tests/test_stopping.py` (66 total across the three pilots'
test files, `python -m pytest tests/test_offline_active_acquisition.py
tests/test_regularized_aggregation.py tests/test_stopping.py -q` → **66
passed**), covering all nine required properties:

1. **Unrevealed-invariance**: a behavioral test builds a partial acquisition
   state, computes `worst_case_topk_change`, then constructs a *different*
   oracle with a still-unrevealed pair's cached answer flipped -- the
   recomputed result is bit-identical, because the function never received
   the oracle at all.
2. **No qrels/oracle/exhaustive-ranking in the interface**: parametrized
   signature inspection over every public function in `stopping.py`,
   checking for forbidden parameter-name substrings (`oracle`, `relevance`,
   `qrel`, `future`, `unrevealed_answer`, `exhaustive`).
3. **Determinism**: repeated calls to `worst_case_topk_change` with identical
   inputs return bit-identical results; verified additionally across two
   independent process launches (subprocess-based test).
4. **Zero unrevealed pairs always causes stopping**: `worst_case_topk_change`
   with an empty `remaining_pairs` list returns `scalar=0.0` exactly, and a
   history whose tail has zero remaining pairs is shown to trigger
   `stopped=True` after `m` such steps.
5. **Reducing the outcome set cannot increase the worst case**: a direct
   test on the real oracle shows `_worst_case_over_pairs` computed over a
   strict pair-subset is always `<=` the same computation over a superset.
6. **Identical hypothetical top-k gives zero membership instability**: a
   synthetic pair of rankings with the same top-k set but a reordered tail
   yields `membership == 0.0` exactly.
7. **Patience is applied correctly**: unit tests on `apply_patience` /
   `has_stopped` (reset-on-instability, triggers exactly at the configured
   count) and an end-to-end scan test with a scalar sequence containing one
   reset.
8. **No exhaustive-ranking access**: covered by the same signature test as
   property 2 (`exhaustive` is in the forbidden-substring list).
9. **Reproducible across process launches**: same subprocess test as
   property 3.

## 7. Baselines (Phase 3)

Six conditions compared, all consuming the same revealed-edge sequence at
each step (random order primary; static_adjacent secondary robustness
check, Phase 9 H4):

1. Fixed 5% / 10% / 20% budgets (the frozen regularized aggregator,
   evaluated at those fixed stopping points).
2. Simple recent-stability rule (`m=3`).
3. Proposed counterfactual worst-case rule (primary + 2 sensitivity
   settings).
4. Exhaustive acquisition reference.

## 8. Results by query and aggregate (Phase 6), held-out 35-query test set, random order

| Method | n | median budget | mean nDCG | mean Delta vs BM25 | mean Delta vs exhaustive | top-k overlap vs exh. | exact top-k match | n capped at 60% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `fixed_0.05` | 35 | 4.8% | 0.846 | +0.018 | -0.137 | 0.625 | 2/35 | -- |
| `fixed_0.10` | 35 | 9.5% | 0.864 | +0.036 | -0.119 | 0.633 | 1/35 | -- |
| `fixed_0.20` | 35 | 20.0% | 0.893 | +0.065 | -0.091 | 0.686 | 3/35 | -- |
| `simple_recent_stability` | 35 | 3.8% | 0.848 | +0.020 | -0.135 | 0.609 | 1/35 | 0/35 |
| `counterfactual_aggressive` (tau=.25) | 35 | 11.4% | 0.882 | +0.054 | -0.101 | 0.673 | 2/35 | 0/35 |
| **`counterfactual_primary` (tau=.20, proposed)** | 35 | **34.3%** | **0.924** | **+0.096** | **-0.060** | **0.791** | 5/35 | 4/35 |
| `counterfactual_conservative` (tau=.15) | 35 | 60.0% | 0.944 | +0.116 | -0.039 | 0.826 | 7/35 | 21/35 |
| `exhaustive` | 35 | 100.0% | 0.983 | +0.155 | 0.000 | 1.000 | 35/35 | -- |

## 9. Judgment savings (H1)

`counterfactual_primary`'s per-query stop budgets (test set, random order,
n=35, sorted): 2.9, 4.8, 9.5, 11.4, 16.2, 16.2, 17.1, 24.8, 27.6, 27.6, 29.5,
29.5, 30.5, 31.4, 32.4, 32.4, 32.4, 34.3, 35.2, 37.1, 46.7, 46.7, 47.6, 50.5,
51.4, 52.4, 52.4, 56.2, 57.1, 59.0, 60.0, 60.0, 60.0, 60.0, 60.0 (%).

**Median = 34.3%, mean = 37.2%** of exhaustive comparisons.
**H1 target met**: median acquisition is below 40% of exhaustive
comparisons. Only 4/35 (11.4%) queries hit the 60%-budget simulation cap
without triggering patience -- well under "most queries," so the task's own
disqualifying condition ("needs more than 60% for most queries") does not
apply.

**Important honest caveat**: this is savings *relative to exhaustive*, not
relative to a low fixed budget. `counterfactual_primary` spends *more*
budget than `fixed_0.20` for 28/35 queries (only 7/35 achieve an outright
lower budget than the flat 20% policy) -- see §11.

## 10. Retrieval-quality preservation (H2)

Fraction of the mean exhaustive-minus-BM25 improvement recovered by
`counterfactual_primary`: `(0.924 - 0.828) / (0.983 - 0.828) = 0.0956 /
0.1551 = 61.6%`. Mean nDCG deficit vs. exhaustive: **-0.060** (6.0 points).

H2 has three pre-registered sub-criteria:

| Sub-criterion | Target | Result | Met? |
|---|---|---:|---|
| Fraction of exhaustive improvement recovered | >= 95% | 61.6% | **No** |
| Mean nDCG vs. exhaustive | within 0.02 | -0.060 | **No** |
| Severe-harm rate vs. the aggregator's own fixed-10% condition (5.7%, from `regularized_aggregation_pilot_v1`) | <= 5.7% | 0.0% | **Yes** |

**H2 is only partially supported.** The severe-harm containment is met with
margin, but the two quality-recovery sub-criteria are missed by a wide
margin. This traces to a structural property of the aggregator itself (not
a stopping-rule defect): from the prior pilot's own budget-curve table,
`regularized_bt`'s mean nDCG only reaches ~0.958 at 60% budget and does not
reach ~0.983 until 100% -- the *aggregator's* quality curve has a long,
slow-rising tail past 60% coverage, so **no** stopping rule that saves a
substantial fraction of the budget can plausibly land within 0.02 of
exhaustive under this aggregator. This is disclosed as a finding about the
aggregator's convergence shape, not swept under the stopping rule's
evaluation.

## 11. Severe-harm analysis (Phase 7/8)

**Interval method note (post-audit correction, `schema_version: 2` in
`statistical_analysis.json`):** these confidence intervals are Wilson
binomial-proportion intervals (`consistency_ranker.statistical_inference.
proportion_interval`, `method="wilson"`), not the nonparametric percentile
bootstrap used in the original `schema_version: 1` output. A bootstrap
resample of an all-zero (or all-one) sample is degenerate -- every
resample is identical to the original, so the interval collapses to a
single point regardless of the true sample size. That previously produced
a literal `[0.0%, 0.0%]` interval for `counterfactual_primary`'s 0/35
observed severe-harm count, which understated uncertainty and is corrected
below. The point estimates (rates) are byte-identical to the original run;
only the interval width/validity changed -- no conclusion in this report
is reversed by the correction (re-verified: `primary_comparisons` in
`statistical_analysis.json` is unchanged).

| Method | Severe-harm rate (test, n=35) | 95% CI (Wilson) |
|---|---:|---:|
| `fixed_0.10` | 5.71% | [1.6%, 18.6%] |
| `fixed_0.20` | 2.86% | [0.5%, 14.5%] |
| `simple_recent_stability` | 2.86% | [0.5%, 14.5%] |
| **`counterfactual_primary`** | **0.0%** | **[0.0%, 9.9%]** |

Worst-query degradation (proposed vs. BM25, test set): **-0.0104** nDCG@10
-- i.e. even the single worst-performing query under the proposed rule loses
only about one nDCG point relative to the cheap BM25 baseline. 5th-percentile
degradation is identical (-0.0104), since no other query in the bottom 5%
performs worse. **Zero severe-harm queries were *observed* out of 35 test
queries under the proposed rule -- this is the strongest safety result in
this pilot, but zero observed events at n=35 does not imply a true
underlying rate of exactly zero; the Wilson 95% CI's upper bound is 9.9%,
i.e. a true rate as high as roughly 1 in 10 queries remains statistically
consistent with this observation.** A materially larger held-out set would
be needed to tighten this bound further.

### 11a. Stopped vs. capped runs (Phase 7/8, `run_status` in `statistical_analysis.json`)

Capped (censored) walks -- those that never triggered the patience
condition within the 60%-budget simulation cap and were evaluated at the
cap budget instead -- are counted explicitly below, and are **included**
in every nDCG/budget/severe-harm/premature-stop aggregate above and in
Section 13 (never excluded, and never relabeled as a triggered stop):

| Method | n | Stopped | Capped | Failed | Stopped rate (95% CI, Wilson) | Capped rate (95% CI, Wilson) |
|---|---:|---:|---:|---:|---:|---:|
| **`counterfactual_primary`** | 35 | **31** | **4** | 0 | 88.6% [74.0%, 95.5%] | 11.4% [4.5%, 26.0%] |
| `fixed_0.10` | 35 | 35 | 0 | 0 | 100% | 0% |
| `fixed_0.20` | 35 | 35 | 0 | 0 | 100% | 0% |
| `simple_recent_stability` | 35 | 35 | 0 | 0 | 100% | 0% |

The two fixed-budget probes and `exhaustive` are not adaptive rules, so
"capped" does not apply to them by construction (`n_capped=0` reflects
that, not an absence of data). `n_failed` is a reserved field for
optimizer/solver failures; no failure-detection instrumentation exists yet
in `stopping.py` (the Adam fit has no explicit convergence/NaN guard), so
this is always 0 -- a schema placeholder, not a claim that failures are
impossible. `counterfactual_primary`'s **31 stopped / 4 capped** matches
the figure already used in Sections 9 and 16 below; it is now also
machine-readable in `statistical_analysis.json["run_status"]` rather than
inferable only from `stopping_results.csv`'s per-row `stopped` column.

## 12. Premature-stop analysis (Phase 6)

Two separate notions, as required, never conflated. The qrel-based rate's
CI is likewise now a Wilson interval (see note in Section 11).

| Method | qrel-based premature-stop rate (>=0.02 nDCG missed AND top-k differs) | 95% CI (Wilson) | qrel-free instability rate (stopped top-k != exhaustive top-k) |
|---|---:|---:|---:|
| `fixed_0.10` | 71.4% | [55.0%, 83.7%] | 97.1% |
| `simple_recent_stability` | 74.3% | [57.9%, 85.8%] | 97.1% |
| `fixed_0.20` | 62.9% | [46.3%, 76.8%] | 91.4% |
| **`counterfactual_primary`** | **48.6%** | **[33.0%, 64.4%]** | **85.7%** |

The proposed rule has the *lowest* rate on both notions among every method
compared, including the two low fixed budgets and the simple baseline. In
absolute terms, however, both rates remain high: the qrel-free exact-top-k
match criterion is strict (any single tail-document swap counts as a
"differs"), and at these budgets even `fixed_0.20` differs from the
exhaustive top-k for 91.4% of queries -- exact top-k match is rare for
*any* method tested at these budgets, which is why nDCG-based comparisons
(§8-10) carry the primary evidentiary weight, not the exact-match rate.

## 13. Statistical results (Phase 8, held-out 35-query test set, Holm-corrected family of 5)

| Comparison | Mean Delta | Cohen's d | 95% CI | Holm p | W/T/L |
|---|---:|---:|---:|---:|---:|
| proposed vs fixed_0.10, nDCG | +0.0594 | 0.79 | [0.036, 0.084] | **0.0005** | 21/11/3 |
| proposed vs fixed_0.20, nDCG | +0.0310 | 0.57 | [0.014, 0.049] | **0.0017** | 18/10/7 |
| proposed vs fixed_0.10, budget | +0.2770 | 1.57 | [0.218, 0.333] | **0.0005** | 32/1/2 |
| proposed vs fixed_0.20, budget | +0.1722 | 0.98 | [0.113, 0.228] | **0.0005** | 28/0/7 |
| proposed vs simple-rule, nDCG | +0.0757 | 0.89 | [0.049, 0.104] | **0.0005** | 21/12/2 |

All five pre-registered comparisons are statistically significant after
Holm correction. The two "budget" comparisons have the *opposite* sign from
what a naive "savings" story would want: proposed uses **significantly more**
comparisons than both fixed_0.10 and fixed_0.20 (32/35 and 28/35 queries
respectively use more), not fewer. The two "nDCG" comparisons show it uses
that extra budget productively: significantly higher quality than both fixed
anchors and the simple baseline.

## 14. Robustness to acquisition order (H4)

Static-adjacent secondary check, test set, `counterfactual_primary`: median
budget 32.4% (vs. 34.3% under random order), mean nDCG 0.937 (vs. 0.924),
mean Delta vs. BM25 +0.109 (vs. +0.096), severe-harm 0/35 (vs. 0/35). The
qualitative pattern -- proposed clearly beats both fixed baselines on nDCG,
zero severe harm, median budget in the low-to-mid 30s% -- holds under both
acquisition orders. **H4 is supported.**

## 15. Runtime

5,355 timed stopping decisions (all queries x both orders x every simulated
step up to the 60%-budget cap or the query's stop point, whichever came
first): **mean 0.344s, max 0.563s per decision**. This is the cost of one
full 3000-iteration frozen-aggregator refit plus the windowed
counterfactual simulation (up to ~130 warm-started 150-iteration refits).
Full pilot wall time: simulate stage ~25 minutes (85 query x order walks,
capped at 63 steps each, resumable/cached), analyze stage seconds, mechanism
stage seconds.

## 16. Mechanism analysis (Phase 9, exploratory only -- not a validated predictor)

Test-set queries (random order, `counterfactual_primary`) grouped into
budget terciles:

| Group | n | mean stop budget | mean exhaustive-BM25 gap available | mean BM25 gap at cutoff | mean "upset" fraction in revealed evidence | frac. with a cycle at stop |
|---|---:|---:|---:|---:|---:|---:|
| Early-stop (bottom tercile) | 11 | 17.1% | 0.174 | 0.028 | 0.273 | 0.0% |
| Mid | 13 | 37.4% | 0.150 | 0.014 | 0.350 | 23.1% |
| Late-stop / capped (top tercile) | 11 | 57.1% | 0.143 | 0.006 | 0.364 | **81.8%** |

A clear, interpretable (but exploratory, uncorroborated by any held-out
predictive test) association: queries whose revealed evidence forms a
**cycle** (an intransitive triple among revealed judgments) by the time
they stop are dramatically over-represented in the late-stopping/capped
group (81.8% vs. 0% in the early group), and late-stopping queries also show
a higher "upset fraction" (revealed judgments that contradict the BM25
prior's ordering: 36.4% vs. 27.3%) and a smaller initial BM25 margin at the
cutoff (0.6% vs. 2.8%). This is consistent with the intuitive story: sparse
evidence that is internally consistent with itself and with the prior
settles quickly; evidence that disagrees with the prior or forms cycles
takes longer for the aggregator to reconcile, and the stopping rule
correctly (if only associationally) waits longer in those cases.

**Predeclared examples** (selected by fixed criteria, not hand-picked):

- *Earliest stop*: query `5f1f12015d55c51764be27df92de175d2de8ee0d` stopped
  at 2.9% budget (3 edges) -- but this is also the **earliest premature-stop
  failure**: despite stopping almost immediately, its revealed evidence had
  a 66.7% upset fraction (2 of 3 revealed edges contradicted the BM25
  prior), and the qrel-based premature-stop label fires (further acquisition
  would have gained >=0.02 nDCG and changed the top-k). Its actual
  Delta-vs-BM25 was still mildly positive (+0.024, not a severe-harm case),
  but this is a clean, disclosed illustration that the mechanism-analysis
  associations above are not a reliable per-query predictor -- a query can
  look "easy" (3 stable steps) while still being a case the rule got wrong
  in hindsight.
- *Latest stop / capped*: query `b045f045e331700cdef309e0d40b15a64cdf5b8a`
  never stabilized within the 60% cap (has a cycle at that point), but was
  *not* a premature-stop failure -- its nDCG at the cap was already
  substantially above BM25 (+0.243), illustrating that "capped" does not
  imply "harmful," just "did not save budget."

## 17. Failure cases

- The single clearest failure mode is the quality-preservation shortfall
  documented in §10: the proposed rule cannot plausibly hit the H2 "within
  0.02 of exhaustive" bar given the aggregator's own slow late-stage
  convergence, regardless of threshold tuning (even the conservative
  `tau=0.15` setting, which caps at 60% budget for most queries, only
  reaches -0.039).
- Early-but-wrong stops exist (§16 example) -- a small but real minority of
  queries look stable very early despite later evidence that would have
  changed the top-k meaningfully. The rule's zero severe-harm record shows
  these misses are rarely *damaging* (the aggregator's regularization keeps
  early rankings anchored near BM25), but they are not zero.
- The rule does not save budget relative to low fixed budgets (10%/20%) in
  the majority of queries (§9/§13) -- its value proposition is "spend
  adaptively more when needed, less when not, and do so safely," not "always
  cheaper."

## 18. Scientific interpretation

- **H1 (cost reduction)**: supported. Median 34.3% < 40% target, only 4/35
  queries hit the simulation cap.
- **H2 (quality preservation)**: only partially supported. Severe-harm
  containment relative to the aggregator's own fixed-10% condition is met
  with margin; the two quality-recovery sub-criteria (95% of improvement,
  within 0.02 of exhaustive) are both missed by a wide margin, traced to the
  aggregator's own slow-converging tail past 60% budget, not a stopping-rule
  defect.
- **H3 (better tradeoff than fixed budgets)**: supported. Statistically
  significant, Holm-corrected nDCG improvement over *both* fixed_0.10 and
  fixed_0.20 (not just one), though achieved partly by spending more budget
  on average -- an honest, disclosed nuance, not a violation of H3's letter.
- **H4 (robustness)**: supported under the static-adjacent secondary check.
- Stop/go numeric threshold (Phase 10, >=3 of 7 required): **met, 4 of 7**
  -- (1) median < 40% [met], (4) severe-harm <= fixed-10% condition [met],
  (6) equal-or-better than fixed_0.10 [met], (7) improvement over the simple
  rule [met]; (2) >=95% recovered [not met], (3) within 0.02 of exhaustive
  [not met], (5) statistically supported *savings* vs. fixed_0.20 [not met
  -- the sign is reversed, proposed costs more].
- Outcome classification: closest to **Outcome B (useful but incomplete)**.
  The rule is a genuine, statistically robust, well-powered improvement in
  *safety* (zero severe harm, lowest premature-stop rate of every method
  compared, both notions) and in *quality-per-dollar* relative to naive
  fixed low budgets -- but it does not achieve near-exhaustive quality at a
  net-reduced cost relative to a simple fixed 10-20% policy, so it is not
  yet a complete standalone "safe anytime reranking" contribution on its
  own. The numeric stop/go threshold is cleared, but the outcome
  classification is intentionally more conservative than that threshold
  alone would suggest, per the task's instruction to be "especially
  cautious" and to report honestly rather than from the threshold rule
  mechanically.

## 19. Stop/go recommendation

**Continue refining the stopping rule's uncertainty model** (Outcome B
guidance) rather than declaring a complete contribution. Concretely: the
next useful increment is *not* a broader acquisition-policy search (still
out of scope) but a better-calibrated worst-case statistic or schedule that
narrows the gap to exhaustive at moderate budgets -- e.g. investigating
whether the cycle/upset-fraction association found in §16 could inform a
coverage-and-consistency-aware (not just coverage-aware) regularization
schedule, tested as a small, separate follow-up, not implemented here. Do
not yet expand into acquisition-policy research; do not yet present this as
a complete, deployment-ready contribution.

## 20. Files changed

Original pilot commits (`fc866d7`, `b007a13`):
- `src/consistency_ranker/active_acquisition/stopping.py` (new)
- `scripts/run_stopping_rule_pilot.py` (new)
- `tests/test_stopping.py` (new, 21 tests)
- `configs/stopping_rule_pilot_v1.json` (new, frozen)

No changes to `regularized_aggregation.py` or `oracle.py` were needed or
made in this pilot (Phase 1 found no correctness bug to fix).

**Post-audit polish pass (this update), addressing two findings from an
independent branch audit:**
- `src/consistency_ranker/statistical_inference.py` -- added
  `proportion_interval()` (Wilson by default, Clopper-Pearson available),
  a centralized replacement for using a nonparametric bootstrap on a 0/1
  indicator to estimate a rate.
- `scripts/run_stopping_rule_pilot.py` -- `_statistical_analysis` now uses
  `proportion_interval` for `severe_harm`/`premature_stop` rates (was
  `bootstrap_mean_interval`, which degenerates to a zero-width interval at
  0/n or n/n), and adds an explicit `run_status` section
  (`n_stopped`/`n_capped`/`n_failed`/rates+CIs per method,
  `schema_version: 2`). `run_analyze` now also refuses to proceed if the
  simulate output is missing expected `(order, query_id)` walks.
- `tests/test_stopping_rule_pilot_analysis.py` (new, 7 tests) --
  regression-guards the CI fix and the stopped/capped bookkeeping.
- `tests/test_statistical_inference.py` -- 12 new tests for
  `proportion_interval` (0/n, n/n, interior, invalid inputs).
- `reports/stopping_rule_pilot_20260728T190000Z/analyze/` and `mechanism/`
  -- regenerated offline from the unchanged cached
  `simulate/raw_stopping_histories.jsonl` (no new simulation, no new
  judgments); `stopping_results.csv` and `mechanism_*` are byte-identical
  to the original run, `statistical_analysis.json` gained the corrected
  CIs and `run_status` section, `primary_comparisons` unchanged.
- This `REPORT.md` -- Sections 11/11a/12 updated with the corrected CIs and
  explicit capped-run counts; this section and §21-23 updated with final
  numbers.
- `reports/stopping_rule_pilot_20260728T190000Z/` as a whole -- now tracked
  in Git (see §22; supersedes the "kept local" note in the original
  version of this section).

## 21. Tests and quality checks

- `python -m pytest tests/test_offline_active_acquisition.py
  tests/test_regularized_aggregation.py
  tests/test_regularized_aggregation_pilot_analysis.py
  tests/test_stopping.py tests/test_stopping_rule_pilot_analysis.py
  tests/test_statistical_inference.py -q` -> **102 passed** (the original
  66 pilot tests + 36 new: 7 stopping-analysis, 4 regularized-aggregation-
  analysis, 12 proportion-interval, plus 13 pre-existing
  `test_statistical_inference.py` tests not previously counted in the "66"
  figure).
- `python -m pytest tests/ -q` (full repository suite) -> **1127 passed, 0
  skipped, 0 failed** in 162.25s -- no regression; the prior "1082 passed,
  22 skipped" figure in an earlier version of this section was from a
  different environment/dependency-install state, not a discrepancy in
  this branch's code (skip counts are environment-dependent, e.g.
  exact-repair tests skip without PySCIPOpt).
- `ruff check` on all new/touched files (this pass and the original pilot)
  -> clean. Full-repository `ruff check .` -> 1,545 pre-existing findings,
  unchanged by this pass (unrelated historical debt outside this branch's
  scope; see `PROJECT_STATUS.md`).
- **Correction:** no type checker is configured in this repository (no
  `[tool.mypy]` in `pyproject.toml`; `mypy` is not a dev dependency and is
  not installed in this environment). The original version of this section
  claimed a clean `mypy` run; that described a different
  environment/session's ad hoc use of the tool, not a repository
  convention -- do not expect `mypy` to be runnable without installing and
  configuring it first.
- Determinism verified empirically: the `analyze` stage is a pure function
  of the cached simulation data (deterministic by construction, verified by
  re-running and diffing, including in this polish pass); the `simulate`
  stage's core statistic (`worst_case_topk_change`) is verified
  deterministic both within-process and across independent process
  launches (§6, property 3/9).

## 22. Commits created

1. Implementation and tests (`src/`, `scripts/`, `tests/`) -- `fc866d7`.
2. Frozen configuration (`configs/stopping_rule_pilot_v1.json`) --
   `b007a13`.
3. Post-audit statistics fix (`statistical_inference.py`'s
   `proportion_interval`, wired into this pilot's severe-harm/premature-
   stop CIs and new `run_status` section, plus regression tests) -- see
   this branch's git log for the exact commit created in this polish pass.
4. Regenerated `analyze`/`mechanism` outputs and this `REPORT.md`'s
   updated sections -- same polish pass.
5. This directory tracked in Git (minus one deterministically-regenerable
   raw log, `simulate/raw_stopping_histories.jsonl`, kept local via a
   narrow `.gitignore` rule) -- **now created**, overriding the original
   version of this section, which had left this as a flagged open decision
   for the user. See `docs/ARTIFACT_POLICY.md`.

## 23. Final Git status

Working tree clean on all tracked files after the commits above. This
report directory, `reports/regularized_aggregation_pilot_20260728T164943Z/`,
and `reports/offline_active_acquisition_pilot_20260728T142414Z/` are now
tracked (each minus at most one regenerable raw log, per
`docs/ARTIFACT_POLICY.md`). Branch pushed to `origin` only if the "Push
safely" checks in the polish pass's own final report passed; see that
report for the exact push outcome. No history rewritten, no force-push, no
merge into `main`.

## Explicit confirmations

- No live provider or API calls were made.
- No new judgments were collected.
- No frozen evidence was modified (`outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl`
  was only read; its SHA-256 in `MANIFEST.json` matches both prior pilots').
- No history was rewritten.
- No push was performed.

**SAFE STOPPING PARTIAL — AGGREGATION PROMISING, STOPPING NEEDS REVISION**
