# Regularized partial-information rank aggregation pilot

Generated: `20260728T164943Z`. All judgments are replayed from the same
pre-existing, frozen, real cached OpenAI (gpt-4o-mini) pairwise judgment
artifact used by the prior offline active-acquisition pilot. **No live
provider or API calls were made in this pilot. No new judgments were
collected. No frozen evidence was modified** (only `outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl`
is read, never written).

Research question: *Can a regularized partial-information rank aggregator
safely combine a strong initial BM25 ranking with sparse LLM pairwise
judgments, producing an effective anytime quality-budget frontier?*

## 1. Starting Git state

- Branch: `fix/outcome-f-production-operating-point`
- HEAD at start: `e4566aaa0161854feb9b8a0e9338d1110d362349`
- Working tree: clean except the untracked, previously-generated
  `reports/offline_active_acquisition_pilot_20260728T142414Z/` (left untouched
  throughout this pilot).

## 2. Backup branch

`backup/pre-regularized-aggregation-pilot-20260728-163011` (created at the
HEAD above, before any change in this task).

## 3. Reproduction of the prior failure (Phase 1)

The prior pilot's frozen script/config was rerun byte-for-byte into a fresh
local output directory:

```
python scripts/run_offline_active_acquisition_pilot.py \
    --config configs/offline_active_acquisition_pilot_v1.json \
    --output-dir <fresh dir>
```

`budget_curve_summary.csv`, `per_query_summary.csv`, and
`statistical_analysis.json` (including `strongest_baseline_selected` and
`primary_comparisons`) were **bit-identical** to the committed
`reports/offline_active_acquisition_pilot_20260728T142414Z/` outputs.
Confirmed:

- initial BM25 mean nDCG@10 = 0.801, exhaustive = 0.972 (n = 50);
- exhaustive acquisition improves 42/50 queries;
- `proposed` (uncertainty x impact x ambiguity) is significantly *worse*
  than `random_unobserved` at 10% (Holm p = 0.0010) and 20% (Holm p =
  0.0010) budgets, matching the frozen report exactly.

This reproduction was re-verified a second time after the determinism fix
described in §6 below (which touches a function shared with this pilot's
BM25 tie-break): outputs remained bit-identical, confirming that fix does
not alter any previously-committed claim.

## 4. Mechanism analysis (Phase 1)

A new, narrowly-scoped fine-grained replay (`scripts/run_regularized_aggregation_pilot.py
--mode fragility`) checkpoints the **existing** sparse Copeland-over-BM25
extraction rule after *every single* revealed edge (not just the coarse
budget grid) for the first 21 edges (0-20% budget) under random-order
acquisition, across all 50 queries (1,050 query-step observations):

| Quantity | Value |
|---|---:|
| Steps with any top-10 membership change | 435 / 1050 (41.4%) |
| Steps ejecting a relevant document from top-10 | 60 / 1050 (5.7%) |
| **Queries with top-10 churn after just 1 revealed edge** | **36 / 50 (72%)** |
| **Queries ejecting a relevant document after just 1 revealed edge** | **7 / 50 (14%)** |
| Ejection events at <=10% budget | 44 / 60 |
| Ejected documents that reappear in the exhaustive top-10 | **56 / 60 (93.3%)** |
| Mean \|deltaNDCG\| at <=10% budget, churn steps | 0.067 |
| Mean \|deltaNDCG\| at <=10% budget, no-churn steps | 0.036 |

The mechanism stated in the task prompt is **confirmed, not merely
plausible**: a single revealed edge, at the very first acquisition step,
already changes top-10 membership for nearly three-quarters of queries and
wrongly ejects a genuinely relevant document (one that reappears once
evidence is exhaustive 93.3% of the time) for 1 in 7 queries. This is a
direct, mechanical consequence of `rank_from_copeland`'s strict lexicographic
priority: any nonzero Copeland tally outranks every document still at zero,
regardless of BM25 margin.

Two concrete, non-cherry-picked examples (first two step-1 ejection events in
query-id order; full list of all 60 events in `fragility_ejection_events.csv`):

- Query `2747421989619d293c05b0b82a547009128ebadb`: the BM25-rank-1,
  qrel-relevant document is ejected from top-10 by the *very first* revealed
  edge (it loses one pairwise comparison). nDCG@10 drops 0.684 -> 0.553. That
  document is present in the exhaustive top-10.
- Query `4ec90b7da43e6438cbdc756624b1083f30288064`: the BM25-rank-10
  relevant document is ejected by the first edge; nDCG@10 drops
  0.544 -> 0.316. This is the one step-1 example (of 7) where the ejected
  document does *not* return in the exhaustive top-10 -- disclosed rather
  than omitted, since not every early ejection is "wrong" in hindsight.

Mechanism confirmed -> proceeded to Phase 2 as instructed.

## 5. Primary aggregation method (Phase 2)

**Prior-regularized Bradley-Terry aggregation**
(`src/consistency_ranker/active_acquisition/regularized_aggregation.py`):

- document utilities initialized from normalized BM25 score (the same
  `normalize_bm25` used throughout the existing module);
- fit by minimizing pairwise negative log-likelihood over revealed
  (winner, loser) outcomes plus an L2 penalty toward the BM25 prior;
- with **zero** revealed judgments, the pairwise term is a sum over zero
  outcomes, so the exact minimizer is the prior itself -- returned directly
  (not "converged close to"), so the regularized ranking is *bit-identical*
  to the BM25 ranking at 0% budget (test-enforced);
- regularization strength `lambda(c)` is a predeclared, monotone
  non-increasing function of observation coverage `c = |revealed| /
  n_total_pairs`, frozen before any test-set evaluation (§7);
- extraction: sort by fitted utility (descending), BM25 tie-break, doc-id
  tie-break -- same tie-break convention as the existing
  `rank_from_copeland`.

## 6. Mathematical objective, regularization schedule, and a determinism fix

Objective for one query, given revealed outcomes `R` and prior `u0`:

```
L(u) = sum_{(w,l) in R} -log(sigmoid(u_w - u_l))  +  lambda(c) * sum_d (u_d - u0_d)^2
```

Three predeclared schedules were implemented (`SCHEDULES` in
`regularized_aggregation.py`):

| Schedule | Form | lambda0 |
|---|---|---:|
| `linear_decay` (frozen primary) | `lambda0 * (1 - c)` | 8.0 |
| `inverse_coverage` (alternate) | `lambda0 / (eps + c)`, eps=0.05 | 0.5 |
| `pseudo_count_cutoff` (alternate) | `lambda0 * max(0, 1 - c/c*)`, c*=0.4 | 8.0 |

**Determinism fix (discovered during this pilot, not pre-existing in scope):**
the first fitting implementation used SciPy's L-BFGS-B with adaptive
convergence tolerances. At full coverage, `linear_decay`'s declared
`lambda(1.0) = 0` exactly, making the objective invariant to a uniform shift
of every utility (a genuine flat direction in the Hessian). Two otherwise
byte-identical process runs were observed to land at measurably different
points along that flat direction (invisible in nDCG/top-k membership, but
visible in full-list Kendall tau against the exhaustive ranking). Root-caused
to two contributing factors, both now fixed:

1. `oracle.py`'s `bm25_scores()` accumulated the BM25 score with `for term in
   set(q_terms): score += ...` -- Python `set` iteration order depends on
   `PYTHONHASHSEED`, which differs by default across separate process
   launches, so floating-point summation order (and therefore the BM25 prior
   itself, at the ~1e-15 level) was not run-to-run reproducible. Changed to
   `sorted(set(q_terms))`. Verified: `bm25_scores` is now byte-identical
   across `PYTHONHASHSEED` values 0 and 99999 (was not, before the fix).
   **This is a latent bug in already-committed code**, invisible to the prior
   Copeland-based pilot (ties at the ~1e-15 level essentially never flip a
   sort order there) but load-bearing for this pilot's much more
   numerically-sensitive optimizer. Reproduction of the prior pilot's frozen
   numbers was re-verified bit-identical after this fix (§3).
2. `fit_bt_utilities` was switched from SciPy L-BFGS-B (adaptive stopping) to
   a fixed-iteration-count Adam optimizer (3000 iterations, no data-dependent
   early stopping) plus a numerical-stability floor
   (`lambda >= 1e-9`, applied only inside the optimizer, never changing any
   schedule's *declared* value). A fixed-length computation has no
   opportunity for run-to-run divergence in *how many* steps are taken.

After both fixes: two independent process runs of the full evaluation
(`--mode evaluate`) produced byte-identical `aggregation_trajectories.csv`
and `statistical_analysis.json` (`diff` clean). Trade-off: the fixed-iteration
optimizer is slower than adaptive L-BFGS-B (~57ms mean per ranking decision
vs. sub-millisecond for the Copeland/blend methods, §13) -- acceptable for
this offline pilot's scale (full evaluation completes in ~92s) and disclosed
rather than hidden.

## 7. Development/test protocol (Phase 4)

- 15/35 dev/test query split, deterministic seed 4242
  (`random.Random(4242).shuffle(sorted(query_ids))[:15]` = dev).
- All schedule/lambda0 selection used **only** the 15-query dev split, at
  5%/10% budgets, under random-order acquisition, before any test-set metric
  was computed.

Recorded dev-set comparison of all three schedules (mean deltaNDCG vs BM25,
severe-harm count out of 15):

| Schedule | 5% mean Delta | 5% severe-harm | 10% mean Delta | 10% severe-harm |
|---|---:|---:|---:|---:|
| `linear_decay` | +0.0121 | 2/15 | +0.0653 | **0/15** |
| `inverse_coverage` | +0.0202 | 3/15 | +0.0735 | 1/15 |
| `pseudo_count_cutoff` | +0.0205 | 2/15 | +0.0672 | **0/15** |

`linear_decay` and `pseudo_count_cutoff` tied on dev safety;
`linear_decay` was tie-broken in by interpretability (reaches exactly
`lambda=0` at full coverage, unlike `inverse_coverage`, which never fully
releases the prior).

`lambda0` magnitude, 3 values tried for `linear_decay` on dev (recorded per
Phase 4's "record all attempted variants" requirement):

| lambda0 | 5% mean Delta | 5% severe-harm | 10% mean Delta | 10% severe-harm |
|---:|---:|---:|---:|---:|
| 2.0 | +0.0512 | 4/15 | +0.1064 | 1/15 |
| **8.0 (frozen)** | +0.0121 | 2/15 | +0.0653 | **0/15** |
| 20.0 | +0.0083 | 2/15 | +0.0506 | **0/15** |

`lambda0=2.0` had the highest mean gain but markedly worse safety;
`lambda0=8.0` and `20.0` tied on safety but `8.0` had higher mean gain, so
`8.0` was frozen. All of this is recorded in
`configs/regularized_aggregation_pilot_v1.json` before any test-set number
was computed.

## 8. Leakage protections (Phase 5)

`regularized_aggregation.py`'s public functions take only `(candidates,
revealed-so-far outcomes, qrels-free BM25 prior, coverage-derived lambda)`.
21 tests in `tests/test_regularized_aggregation.py` cover all seven required
properties:

1. **Zero-observation exactness**: `fit_bt_utilities(..., [], prior, lam)
   == prior` bit-exact, for all three schedules, at every budget.
2. **Unrevealed-invariance**: ranking depends only on the `revealed` list
   passed in; the function signature cannot even accept an oracle/qrels
   object (structural test, mirroring the existing pilot's leakage tests).
3. **Repeated-evidence direction**: repeating the same (winner, loser)
   outcome monotonically increases the winner's utility advantage.
4. **Monotone lambda(c)**: all three schedules are non-increasing over
   `c in [0, 1]` (parametrized test, 101 sample points each).
5. **Determinism**: `fit_bt_utilities` and `regularized_bt_ranking` return
   identical output across repeated calls; verified at pilot scale across
   independent process launches (§6).
6. **No qrel-bearing object in the interface**: parametrized signature
   inspection over every public function, checking for forbidden parameter
   name substrings (`oracle`, `relevance`, `qrel`, `future`,
   `unrevealed_answer`).
7. **Malformed input fails clearly**: self-pair judgments and judgments
   referencing documents outside the candidate pool raise `ValueError` with
   a specific message, for both `fit_bt_utilities` and `fixed_blend_ranking`.

`45/45` tests pass (`24` pre-existing + `21` new):
`python -m pytest tests/test_offline_active_acquisition.py tests/test_regularized_aggregation.py -q`.

## 9. Baselines and comparison protocol (Phase 3/6)

Acquisition order is fixed to **random** (primary; the strongest policy from
the prior pilot) with **static_adjacent** as a secondary robustness check --
per Phase 3's instruction to avoid confounding aggregation quality with a new
acquisition heuristic. All five non-reference methods consume the *same*
revealed-edge prefix at each budget checkpoint:

1. `initial_bm25` -- constant BM25 ranking.
2. `sparse_copeland` -- the existing extraction rule (`rank_from_copeland`),
   unchanged.
3. `pure_bt_no_prior` -- Bradley-Terry regularized only toward the zero
   vector with a fixed tiny numerical stabilizer (`lambda=1e-3`, disclosed as
   a stabilizer, not an informative prior); BM25 used only for tie-break.
4. `fixed_blend` -- `0.5 * bm25_norm + 0.5 * (copeland / (n-1))`, weight
   frozen before evaluation, not tuned.
5. `regularized_bt` -- the proposed coverage-adaptive method (§5/§6).
6. `exhaustive` -- the full-Copeland reference (same as the prior pilot).

Budgets: 0, 1 judgment, 5%, 10%, 20%, 40%, 60%, 100% of 105 pairs -> realized
integer budgets `{0, 1, 5, 10, 21, 42, 63, 105}`.

## 10. Results by budget (mean nDCG@10, random order, **held-out 35-query test set**)

| Method | 0 | 1 | 5% | 10% | 20% | 40% | 60% | 100% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `initial_bm25` | 0.828 | 0.828 | 0.828 | 0.828 | 0.828 | 0.828 | 0.828 | 0.828 |
| `sparse_copeland` | 0.828 | **0.731** | **0.796** | 0.880 | 0.923 | 0.959 | 0.975 | 0.983 |
| `pure_bt_no_prior` | 0.828 | **0.731** | 0.763 | 0.859 | 0.921 | 0.972 | **0.983** | 0.982 |
| `fixed_blend` | 0.828 | 0.821 | 0.859 | 0.878 | 0.902 | 0.942 | 0.954 | 0.976 |
| **`regularized_bt` (proposed)** | 0.828 | **0.823** | **0.846** | 0.864 | 0.893 | 0.924 | 0.958 | 0.983 |
| `exhaustive` | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 |

At 1 revealed judgment and at 5%, the proposed method is the *only*
evidence-using method that does not drop measurably below the BM25 baseline
(sparse Copeland and pure BT both crater to 0.731-0.796; the proposed method
stays at 0.823-0.846). It converges to exhaustive-level quality (0.983) by
100% budget, matching sparse Copeland exactly there.

`static_adjacent` secondary robustness check (test set) shows the same
qualitative pattern -- `regularized_bt` stays flat near BM25 at 1
judgment/5% (0.828/0.842) while `sparse_copeland` drops hard (0.744/0.777),
confirming the safety property is a property of the *aggregation rule*, not
specific to random acquisition order.

Test-set **AUC** of the nDCG-vs-budget-fraction curve (random order):

| Method | AUC |
|---|---:|
| `initial_bm25` | 0.828 |
| `sparse_copeland` | 0.944 |
| `pure_bt_no_prior` | 0.946 |
| `fixed_blend` | 0.935 |
| `regularized_bt` (proposed) | 0.931 |
| `exhaustive` | 0.983 |

The proposed method's AUC is **not** better than the strongest non-oracle
baseline (`pure_bt_no_prior`, selected on the dev split, §11) -- it trades a
small amount of total-curve area (mostly from `sparse_copeland`/`pure_bt`'s
faster mid-budget recovery) for its much safer low-budget behavior. This is
reported transparently, not minimized.

## 11. Statistical results (Phase 8, held-out 35-query test set, Holm-corrected family of 5)

| Comparison | Mean Delta | Cohen's d | 95% CI | Holm p | W/T/L |
|---|---:|---:|---:|---:|---:|
| proposed vs sparse_copeland @ 5% | +0.0500 | 0.38 | [0.006, 0.092] | 0.092 (n.s.) | 25/0/10 |
| proposed vs sparse_copeland @ 10% | -0.0152 | -0.14 | [-0.051, 0.020] | 0.416 (n.s.) | 18/1/16 |
| **proposed vs BM25 @ 10%** | **+0.0361** | 0.50 | [0.013, 0.060] | **0.015** | 16/11/8 |
| **proposed vs BM25 @ 20%** | **+0.0646** | 0.81 | [0.040, 0.091] | **0.0005** | 21/12/2 |
| AUC: proposed vs `pure_bt_no_prior` (dev-selected strongest baseline) | -0.0149 | -0.25 | [-0.036, 0.003] | 0.318 (n.s.) | 19/0/16 |

`strongest_baseline_selected_on_dev = pure_bt_no_prior` (dev AUC means:
`pure_bt_no_prior` 0.9136, `sparse_copeland` 0.9101, `fixed_blend` 0.8850 --
selected before any test-set AUC was computed).

**Interpretation**: the proposed method beats BM25 with strong, Holm-corrected
significance at both 10% and 20% budgets (H2, strongly supported). It is
*not* significantly better than sparse Copeland in raw mean nDCG at either
5% or 10% (point estimate favorable at 5%, essentially a wash at 10%) -- the
mean-nDCG advantage over sparse Copeland claimed by H1 is **not**
established with statistical confidence on the held-out set, even though the
raw point estimate is positive at 5%.

## 12. Safety-tail results (Phase 7/8)

Severe harm defined and frozen before test-set inspection: per-query
`deltaNDCG@10 <= -0.05` vs. BM25.

Per-method rate now also carries a Wilson binomial-proportion 95% CI
(post-audit addition, `schema_version: 2` in `statistical_analysis.json`;
these are new fields, not a correction -- no CI existed for these raw
per-method rates before). This is a *different* statistic from the paired
severe-harm-rate-*reduction* CI below (a mean of a paired difference of two
correlated indicators, still bootstrap-based, unaffected and unchanged by
this addition):

| Budget | Method | Severe-harm rate | 95% CI (Wilson) | Worst-query Delta |
|---|---|---:|---:|---:|
| 5% | `sparse_copeland` | **15/35 (42.9%)** | [28.0%, 59.1%] | -0.285 |
| 5% | `pure_bt_no_prior` | 21/35 (60.0%) | [43.6%, 74.4%] | -0.385 |
| 5% | `fixed_blend` | 2/35 (5.7%) | [1.6%, 18.6%] | -0.102 |
| 5% | **`regularized_bt`** | **2/35 (5.7%)** | **[1.6%, 18.6%]** | **-0.102** |
| 10% | `sparse_copeland` | **8/35 (22.9%)** | [12.1%, 39.0%] | -0.166 |
| 10% | `pure_bt_no_prior` | 13/35 (37.1%) | [23.2%, 53.7%] | -0.347 |
| 10% | `fixed_blend` | 1/35 (2.9%) | [0.5%, 14.5%] | -0.098 |
| 10% | **`regularized_bt`** | **2/35 (5.7%)** | **[1.6%, 18.6%]** | **-0.098** |
| 20% | `sparse_copeland` | 4/35 (11.4%) | [4.5%, 26.0%] | -0.155 |
| 20% | `pure_bt_no_prior` | 7/35 (20.0%) | [10.0%, 35.9%] | -0.112 |
| 20% | `fixed_blend` | 1/35 (2.9%) | [0.5%, 14.5%] | -0.098 |
| 20% | **`regularized_bt`** | **1/35 (2.9%)** | **[0.5%, 14.5%]** | **-0.060** |

All rates above are point-estimate-identical to the original run (only the
CI columns are new); no conclusion in this report changes. Note the
individual-method CIs overlap substantially even where the paired
comparison below excludes zero -- this is expected and not a
contradiction: the paired test below controls for per-query correlation
(both methods scored on the *same* queries), which is a more powerful,
more appropriate comparison than eyeballing two overlapping single-group
intervals.

Paired bootstrap CI (10,000 reps) for the severe-harm-rate reduction
(`regularized_bt` vs `sparse_copeland`, same 35 test queries):

| Budget | Mean rate reduction | 95% CI |
|---|---:|---:|
| 5% | 0.371 | **[0.200, 0.543]** (excludes 0) |
| 10% | 0.171 | **[0.029, 0.314]** (excludes 0) |
| 20% | 0.086 | [-0.029, 0.200] (includes 0) |

**H1 (low-budget safety) is substantially, statistically supported on
severe-harm rate and worst-tail at both 5% and 10%**, with 95% CIs excluding
zero at both budgets -- even though the *mean-nDCG* half of H1 is not
established (§11). `fixed_blend` achieves comparably strong safety numbers
to `regularized_bt` at these budgets (a disclosed, honest finding: naive
fixed-weight blending is nearly as safe at low budgets as the adaptive
method, though it plateaus below exhaustive quality at high budgets, §10).

## 13. Convergence behavior (H3)

`topk_overlap_vs_exhaustive` (test set, random order), `regularized_bt`:
`0.60 -> 0.60 -> 0.63 -> 0.63 -> 0.69 -> 0.78 -> 0.86 -> 0.98` (0% to 100%
budget) -- smooth, monotone increase, reaching 0.98 by full coverage (vs.
`sparse_copeland`'s trivial 1.00, since at full coverage sparse_copeland *is*
the exhaustive extraction rule by construction). nDCG at 100% budget matches
exhaustive exactly (0.983). **H3 is supported**: the method is not
excessively anchored to BM25 at high budgets, and converges smoothly rather
than discontinuously.

Fraction of exhaustive improvement recovered (test set; `sum(exhaustive) -
sum(BM25) = 0.155` mean nDCG points): 41.9% recovered by 20% budget, 61.9%
recovered by 40% budget -- clears the Phase 10 "50% by 20-40%" threshold at
the 40% checkpoint.

## 14. Runtime

Mean / max wall-clock time per single ranking decision, 800 (order x budget x
query) observations per method, test+dev combined:

| Method | Mean | Max |
|---|---:|---:|
| `initial_bm25` | 0.17 us | 0.84 us |
| `sparse_copeland` | 7.1 us | 36 us |
| `fixed_blend` | 9.4 us | 24 us |
| `pure_bt_no_prior` | 56.6 ms | 157 ms |
| `regularized_bt` | 57.5 ms | 169 ms |

The two Bradley-Terry-based methods are ~4 orders of magnitude slower than
the Copeland/blend methods because of the fixed 3000-iteration Adam
optimizer required for cross-process determinism (§6) -- still fast enough
for offline batch evaluation (full pilot: fragility mode ~2s, evaluate mode
~92s for 50 queries x 6 methods x 2 orders x 8 budgets).

## 15. Failure cases

- `pure_bt_no_prior` is the **least safe** method at low budgets (60%
  severe-harm rate at 5%, worse than `sparse_copeland`'s 43%) -- confirming
  that an informative prior, not just "any Bradley-Terry model," is what
  provides the safety property; a BT fit with no prior information is *more*
  erratic early on than even naive Copeland lexicographic override, because
  early BT utility estimates on 1-5 sparse observations are themselves poorly
  determined.
- `fixed_blend` is nearly as safe as `regularized_bt` at low budgets but
  plateaus at 0.976 nDCG / 0.948 top-k overlap at 100% budget (vs. `regularized_bt`'s
  0.983 / 0.984) -- because its blend weight never adapts, it never fully
  trusts dense evidence even when warranted. This is the expected
  Outcome-C-style signature of a non-adaptive blend, and is why the
  coverage-adaptive schedule is preferred over just shipping `fixed_blend`.
- `regularized_bt`'s AUC is not better than the strongest non-oracle
  baseline (§10/§11) -- the safety gain at low budgets is not "free"; it
  costs a small amount of total-curve area relative to methods that recover
  faster once past their own unsafe early region.
- One step-1 fragility example (query `4ec90b7da43e6438cbdc756624b1083f30288064`,
  §4) shows an ejected relevant document that does *not* return in the
  exhaustive top-10 -- not every early sparse-Copeland ejection is
  "obviously wrong in hindsight"; disclosed rather than omitted.

## 16. Scientific interpretation

- **H1 (low-budget safety)**: substantially supported on severe-harm rate and
  worst-tail (statistically, with CIs excluding zero at 5%/10%); the
  mean-nDCG-vs-sparse-Copeland comparison is directionally favorable at 5%
  but not Holm-significant, and is a statistical wash at 10%. Partial
  support, honestly reported.
- **H2 (useful evidence integration)**: strongly supported -- significant,
  Holm-corrected improvement over BM25 at both 10% (p=0.015) and 20%
  (p=0.0005) budgets.
- **H3 (high-budget convergence)**: supported -- smooth, monotone approach to
  exhaustive-level quality (0.983, matching exhaustive exactly) by 100%
  budget, without remaining anchored to BM25.
- Per Phase 10's stop/go rule (>= 2 of 6 criteria): **(2) materially lower
  severe-harm rate** -- met (CI excludes zero at 5%/10%); **(3) positive mean
  improvement over BM25 by 10-20% budget** -- met (Holm-significant at both);
  **(4) >=50% of exhaustive improvement recovered by 20-40% budget** -- met
  (61.9% at 40%); **(6) smooth convergence** -- met. **(1) statistically
  supported improvement over sparse Copeland at low budgets** -- not met on
  mean nDCG (though met on the safety tail specifically); **(5) improved
  AUC** -- not met. **4 of 6 criteria are met**, clearing the continuation
  threshold with margin.
- Classification: closest to **Outcome A (strongly promising)** on three of
  its four defining bullets (substantially reduces low-budget harm; improves
  over BM25; converges appropriately), with one explicit caveat the task
  requires reporting honestly: the method does **not** decisively "beat
  sparse Copeland" in raw mean nDCG (only in the safety tail) and does not
  improve total-curve AUC over the strongest non-oracle baseline. This is a
  genuine, well-powered, safety-dominant improvement over the existing
  extraction rule, not an unqualified win on every axis tested.

## 17. Stop/go recommendation

**Continue toward a full safe-anytime reranking method** (Outcome A
direction), with the AUC/mean-nDCG caveat above carried forward explicitly:
future work on this path should target closing the AUC gap to
`pure_bt_no_prior`/`sparse_copeland` (e.g., a schedule that trusts evidence
faster in the 20-60% range without reopening the low-budget instability) --
not just re-litigating the low-budget safety win, which is already
well-established. **Do not yet resume active-acquisition-policy work**; that
was explicitly out of scope here and remains contingent on this aggregation
result, which is now positive but not unqualified.

## 18. Files changed

- `src/consistency_ranker/active_acquisition/regularized_aggregation.py` (new)
- `src/consistency_ranker/active_acquisition/oracle.py` (modified: one-line
  determinism fix in `bm25_scores`, §6)
- `scripts/run_regularized_aggregation_pilot.py` (new)
- `tests/test_regularized_aggregation.py` (new, 21 tests)
- `configs/regularized_aggregation_pilot_v1.json` (new, frozen)
- `reports/regularized_aggregation_pilot_20260728T164943Z/` (this report +
  data -- **now tracked in Git in full**, see §20; supersedes the original
  "kept local, not committed" note)

**Post-audit polish pass (this update), addressing a finding from an
independent branch audit** (no per-method severe-harm-rate CI existed
before, a gap rather than a bug):
- `src/consistency_ranker/statistical_inference.py` -- added
  `proportion_interval()` (Wilson by default), shared with the stopping
  pilot's fix.
- `scripts/run_regularized_aggregation_pilot.py` -- `_statistical_analysis`
  now attaches a Wilson CI to each method's raw `frac_severe_harm`
  (`schema_version: 2`). The paired `severe_harm_rate_reduction_vs_
  sparse_copeland` statistic (a mean of a paired difference of two
  correlated indicators, not a single-group proportion) is unchanged and
  intentionally still bootstrap-based.
- `tests/test_regularized_aggregation_pilot_analysis.py` (new, 4 tests).
- `reports/regularized_aggregation_pilot_20260728T164943Z/evaluation/` --
  regenerated offline (`--mode evaluate`, no new judgments);
  `aggregation_trajectories.csv`/`aggregation_auc.csv` and
  `primary_comparisons` in `statistical_analysis.json` are byte-identical
  to the original run; only the new CI fields and `schema_version` were
  added.
- This `REPORT.md` -- §12 updated with the new CI column; this section and
  §19-21 updated with final numbers.

## 19. Tests and quality checks

- `python -m pytest tests/test_offline_active_acquisition.py
  tests/test_regularized_aggregation.py
  tests/test_regularized_aggregation_pilot_analysis.py -q` -> **49 passed**
  (original 45 + 4 new).
- `pytest -q` (full repository suite, re-verified during the post-audit
  polish pass) -> **1127 passed, 0 skipped, 0 failed** in 162.25s.
- `ruff check` on all new/touched files -> clean.
- **Correction (post-audit polish pass):** no type checker is configured
  in this repository (no `[tool.mypy]` in `pyproject.toml`; `mypy` is not
  a dev dependency and is not installed in this environment). The original
  version of this section claimed a clean `mypy` run; that described a
  different environment/session's ad hoc use of the tool, not a repository
  convention.
- Determinism verified empirically at pilot scale: two independent process
  launches of `--mode evaluate` produced byte-identical
  `aggregation_trajectories.csv` and `statistical_analysis.json`, and this
  remained true when re-run during the post-audit polish pass (only the
  new CI fields and `schema_version` differ from the original output).
- Prior pilot's frozen numbers re-verified bit-identical after the `oracle.py`
  fix (§3).

## 20. Commits created

1. Implementation and tests (`src/`, `scripts/`, `tests/`), including the
   `oracle.py` determinism fix -- `91b8973`.
2. Frozen configuration (`configs/regularized_aggregation_pilot_v1.json`)
   -- `c568b87`.
3. Post-audit severe-harm-rate CI addition (`statistical_inference.py`'s
   `proportion_interval`, wired into this pilot, plus regression tests) --
   see this branch's git log for the exact commit created in this polish
   pass.
4. This report directory tracked in Git in full (no file large enough to
   warrant splitting) -- **now created** in the post-audit polish pass,
   overriding the original version of this section (which had left this
   as a flagged open decision for the user). See `docs/ARTIFACT_POLICY.md`.

## 21. Final Git status

Working tree clean on all tracked files after the commits above. This
report directory is now tracked in full, along with the other two
consistency-aware-pivot report directories (each minus at most one
regenerable raw log). See the post-audit polish pass's own final report
for the exact push outcome. No history rewritten, no force-push, no merge
into `main`.

## Explicit confirmations

- No live provider or API calls were made.
- No new judgments were collected.
- No frozen evidence was modified (`outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl`
  was only read; its SHA-256 in `MANIFEST.json` matches the prior pilot's).
- No history was rewritten.
- No push was performed.

**REGULARIZED AGGREGATION PROMISING — CONTINUE SAFE ANYTIME RERANKING**
