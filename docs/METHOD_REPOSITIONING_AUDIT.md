# METHOD_REPOSITIONING_AUDIT

## 1. What I checked

- Ranking extraction logic in `topological_ranking` and `greedy_fas`.
- Existing FAS-aware ranking variants already implemented in `scripts/run_real_experiment.py`.
- Synthetic multi-seed diagnostics at `n_items=20`, `noise=0.20`, for `margin` and `uniform` edge weights.

## 2. Core diagnosis

### Observation A — the current topological extraction is underpowered

Across 5 seeds with `margin` weights, mean Kendall τ is:
- `greedy_fas_topological`: 0.2821
- `lexicographic_topological`: 0.2926
- `priority_topological_score_sum`: 0.3116
- `fas_weighted_balance`: 0.5937
- `borda`: 0.7558

Across 5 seeds with `uniform` weights, mean Kendall τ is:
- `greedy_fas_topological`: -0.0063
- `lexicographic_topological`: 0.0253
- `priority_topological_score_sum`: 0.0337
- `fas_weighted_balance`: 0.2484
- `borda`: 0.7558

### Observation B — tie-breaking/linear-extension choice clearly matters

For `margin`, the best sampled random topological order beats the current one by 0.0505 τ on average.
For `uniform`, the best sampled random topological order beats the current one by 0.0505 τ on average.
The average number of ambiguous source-choice steps is 8.0 (`margin`) and 8.4 (`uniform`).

### Observation C — edge-weight information is likely being discarded too aggressively

`fas_weighted_balance` beats the current topological extraction in 5/5 `margin` runs and 5/5 `uniform` runs.
However, it still beats `borda` in only 0/5 `margin` runs and 0/5 `uniform` runs.

### Observation D — the repair objective and the final ranking objective look misaligned

The repaired DAG reduces inconsistency by 21.8 edges on average (`margin`) and 15.2 edges on average (`uniform`), yet the default topological ranking remains poor. This suggests the method may be optimizing graph acyclicity more than rank fidelity.

## 3. Ranked hypotheses for underperformance

1. **Arbitrary / unstable topological extraction is hurting the method the most.**
   - Evidence: large gaps between current topo and best sampled random topo; many ambiguous steps; lexicographic and priority topological variants improve markedly.
2. **Edge weights are lost after repair because `topological_ranking` ignores them entirely.**
   - Evidence: `fas_weighted_balance` and `priority_topological_score_sum` outperform the plain topological extraction in most runs.
3. **The MWFAS repair objective is misaligned with Kendall tau.**
   - Evidence: inconsistency drops substantially after repair, but ranking quality still lags behind baselines.
4. **Uniform-weight runs expose especially severe information loss and tie/pathology issues.**
   - Evidence: `greedy_fas_topological` has negative mean τ under `uniform`, while weighted/priority variants recover part of that loss.
5. **Cycle-edge deletion order in greedy FAS may damage useful ordering evidence before ranking extraction even begins.**
   - Evidence: even better extraction variants often still fail to beat `borda` consistently.

## 4. Smallest experiments / code changes to test each hypothesis

1. **Hypothesis: arbitrary topological extraction is the main culprit.**
   - Smallest test: replace `topological_ranking(dag)` with `_priority_topological_ranking(dag, original_score_sum_scores)` in synthetic runs.
2. **Hypothesis: edge weights are being discarded.**
   - Smallest test: evaluate `_weighted_out_minus_in_ranking(dag)` as the primary repaired-graph ranking on synthetic sweeps.
3. **Hypothesis: repair objective is misaligned with Kendall tau.**
   - Smallest test: compare pre/post repair inconsistency reduction against τ change across many seeds and noise levels.
4. **Hypothesis: tie-breaking pathologies are severe in uniform-weight settings.**
   - Smallest test: rerun the uniform-weight sweep with lexicographic vs priority topological ranking and record τ gaps.
5. **Hypothesis: greedy cycle-edge deletion itself is harming fidelity.**
   - Smallest test: keep the same repair but add local post-repair search / adjacent-swap improvement on τ proxy metrics such as backward edge weight.

## 5. Feasible improved variants already within repository reach

1. **Score-aware topological ordering** — use `_priority_topological_ranking` with original score-sum or balance priors.
2. **Weighted-balance DAG ranking** — use `_weighted_out_minus_in_ranking(dag)` instead of raw topological order.
3. **Copeland DAG ranking** — use `_copeland_ranking(dag)` as a repaired-graph alternative.
4. **Hybrid score + FAS ranking** — port the existing repaired-graph hybrid logic from `run_real_experiment.py` into the synthetic pipeline.
5. **Randomized / ensemble topological ranking** — sample multiple valid topological orders and choose the one with minimum backward-edge weight or best prior agreement.

## 6. Prioritized experiment plan

1. Replace the synthetic pipeline’s final extractor with `priority_topological_score_sum` and `fas_weighted_balance`; rerun noise + scale sweeps.
2. Add 5-seed evaluation for those variants on the current synthetic setting (`n=20`, `noise=0.20`) to see if either ever beats `borda`.
3. If either variant wins in some regimes, expand to a small noise sweep and report regime-dependent wins/losses.
4. If neither variant wins, run one stronger hybrid from the real pipeline on synthetic (`hybrid_rrf_fas_regularized` or repaired balance hybrid).
5. Only if a variant shows some clear wins should the project continue as a positive-method paper.

## 7. Repositioning option if wins do not materialize

- **Title direction:** consistency repair helps graph coherence but can hurt ranking quality.
- **Core claim:** optimizing pairwise consistency via FAS does not automatically yield better global rankings; extraction strategy and objective alignment matter.
- **Contribution framing:** a careful negative/diagnostic study of why repaired DAG rankings can underperform simple baselines, plus a benchmark of repair-vs-ranking tradeoffs.
- **Existing support:** current synthetic sweeps, the new multi-seed ablation, and the variant diagnostics all support that framing.

## 8. Decision

**Better repositioned as analysis/negative-results paper** unless a score-aware repaired-graph variant can quickly show wins over `borda` on at least some regimes. The present evidence suggests the default method fails mainly because ranking extraction from the repaired DAG is weak, but even improved variants do not yet clearly overturn the baseline story.
