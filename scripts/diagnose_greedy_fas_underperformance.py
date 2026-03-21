#!/usr/bin/env python
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path
from statistics import mean, pstdev

import networkx as nx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))
sys.path.insert(0, str(REPO_ROOT))

from consistency_ranker.baseline_ranking import borda_ranking, score_sum_ranking, topological_ranking
from consistency_ranker.evaluation import kendall_tau, pairwise_inconsistency_count
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.pairwise_prefs import generate_preferences
from consistency_ranker.synthetic_data import generate_items, ground_truth_ranking, quality_map
from scripts.run_real_experiment import (
    _copeland_ranking,
    _priority_topological_ranking,
    _weighted_out_minus_in_ranking,
)

DOCS = REPO_ROOT / 'docs'
TABLES = DOCS / 'tables'


SEEDS = [42, 123, 456, 789, 1234]
SCHEMES = ['margin', 'uniform']
N_ITEMS = 20
NOISE = 0.20
RANDOM_TOPO_SAMPLES = 128


def _score_sum_scores(graph: nx.DiGraph) -> dict[str, float]:
    scores = {n: 0.0 for n in graph.nodes()}
    for u, _, data in graph.edges(data=True):
        scores[u] += data.get('weight', 1.0)
    return scores


def _balance_scores(graph: nx.DiGraph) -> dict[str, float]:
    scores = {n: 0.0 for n in graph.nodes()}
    for u, v, data in graph.edges(data=True):
        w = data.get('weight', 1.0)
        scores[u] += w
        scores[v] -= w
    return scores


def _random_topological_ranking(dag: nx.DiGraph, rng: random.Random) -> list[str]:
    in_deg = {n: dag.in_degree(n) for n in dag.nodes()}
    available = [n for n, d in in_deg.items() if d == 0]
    ranking: list[str] = []
    while available:
        idx = rng.randrange(len(available))
        chosen = available.pop(idx)
        ranking.append(chosen)
        for child in dag.successors(chosen):
            in_deg[child] -= 1
            if in_deg[child] == 0:
                available.append(child)
    return ranking


def _frontier_profile(dag: nx.DiGraph, ranking: list[str]) -> tuple[int, int]:
    in_deg = {n: dag.in_degree(n) for n in dag.nodes()}
    available = {n for n, d in in_deg.items() if d == 0}
    ambiguous_steps = 0
    max_frontier = len(available)
    for chosen in ranking:
        if len(available) > 1:
            ambiguous_steps += 1
        max_frontier = max(max_frontier, len(available))
        available.remove(chosen)
        for child in dag.successors(chosen):
            in_deg[child] -= 1
            if in_deg[child] == 0:
                available.add(child)
    return ambiguous_steps, max_frontier


METHOD_ORDER = [
    'score_sum',
    'borda',
    'greedy_fas_topological',
    'lexicographic_topological',
    'priority_topological_score_sum',
    'priority_topological_balance',
    'fas_weighted_balance',
    'fas_copeland',
]


def _run_case(seed: int, scheme: str) -> dict:
    items = generate_items(n=N_ITEMS, seed=seed)
    qmap = quality_map(items)
    gt = ground_truth_ranking(items)
    prefs = generate_preferences(qmap, noise=NOISE, weight_scheme=scheme, seed=seed)
    graph = build_graph(prefs)
    dag, removed_edges = greedy_fas(graph)

    score_prior = _score_sum_scores(graph)
    balance_prior = _balance_scores(graph)

    rankings = {
        'score_sum': score_sum_ranking(graph),
        'borda': borda_ranking(graph),
        'greedy_fas_topological': topological_ranking(dag),
        'lexicographic_topological': list(nx.lexicographical_topological_sort(dag, key=lambda n: n)),
        'priority_topological_score_sum': _priority_topological_ranking(dag, score_prior),
        'priority_topological_balance': _priority_topological_ranking(dag, balance_prior),
        'fas_weighted_balance': _weighted_out_minus_in_ranking(dag),
        'fas_copeland': _copeland_ranking(dag),
    }

    tau = {name: kendall_tau(ranking, gt) for name, ranking in rankings.items()}
    inconsistent_pre = pairwise_inconsistency_count(graph, gt)
    inconsistent_post = pairwise_inconsistency_count(dag, gt)

    rng = random.Random(f'{scheme}:{seed}:random_topo')
    random_taus = []
    for _ in range(RANDOM_TOPO_SAMPLES):
        ranking = _random_topological_ranking(dag, rng)
        random_taus.append(kendall_tau(ranking, gt))

    ambiguous_steps, max_frontier = _frontier_profile(dag, rankings['greedy_fas_topological'])
    best_method = max(tau, key=tau.get)

    return {
        'scheme': scheme,
        'seed': seed,
        'best_method': best_method,
        'score_sum_tau': tau['score_sum'],
        'borda_tau': tau['borda'],
        'greedy_fas_topological_tau': tau['greedy_fas_topological'],
        'lexicographic_topological_tau': tau['lexicographic_topological'],
        'priority_topological_score_sum_tau': tau['priority_topological_score_sum'],
        'priority_topological_balance_tau': tau['priority_topological_balance'],
        'fas_weighted_balance_tau': tau['fas_weighted_balance'],
        'fas_copeland_tau': tau['fas_copeland'],
        'random_topo_tau_mean': mean(random_taus),
        'random_topo_tau_std': pstdev(random_taus),
        'random_topo_tau_best': max(random_taus),
        'random_topo_tau_worst': min(random_taus),
        'current_topo_vs_random_mean_gap': tau['greedy_fas_topological'] - mean(random_taus),
        'best_random_vs_current_gap': max(random_taus) - tau['greedy_fas_topological'],
        'ambiguous_steps': ambiguous_steps,
        'max_frontier': max_frontier,
        'original_pairwise_inconsistency': inconsistent_pre,
        'after_fas_pairwise_inconsistency': inconsistent_post,
        'inconsistency_drop': inconsistent_pre - inconsistent_post,
        'fas_removed_edges': len(removed_edges),
    }


KEYS_FOR_MEAN = [
    'score_sum_tau',
    'borda_tau',
    'greedy_fas_topological_tau',
    'lexicographic_topological_tau',
    'priority_topological_score_sum_tau',
    'priority_topological_balance_tau',
    'fas_weighted_balance_tau',
    'fas_copeland_tau',
    'random_topo_tau_mean',
    'random_topo_tau_best',
    'best_random_vs_current_gap',
    'ambiguous_steps',
    'max_frontier',
    'original_pairwise_inconsistency',
    'after_fas_pairwise_inconsistency',
    'inconsistency_drop',
    'fas_removed_edges',
]


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _summaries(rows: list[dict]) -> list[dict]:
    out = []
    for scheme in SCHEMES:
        subset = [r for r in rows if r['scheme'] == scheme]
        summary = {'scheme': scheme, 'n_runs': len(subset)}
        for key in KEYS_FOR_MEAN:
            summary[f'{key}_mean'] = mean(r[key] for r in subset)
        better_balance = sum(r['fas_weighted_balance_tau'] > r['greedy_fas_topological_tau'] for r in subset)
        better_pri = sum(r['priority_topological_score_sum_tau'] > r['greedy_fas_topological_tau'] for r in subset)
        balance_beats_borda = sum(r['fas_weighted_balance_tau'] > r['borda_tau'] for r in subset)
        pri_beats_borda = sum(r['priority_topological_score_sum_tau'] > r['borda_tau'] for r in subset)
        summary['fas_weighted_balance_beats_current_topo_runs'] = better_balance
        summary['priority_topological_score_sum_beats_current_topo_runs'] = better_pri
        summary['fas_weighted_balance_beats_borda_runs'] = balance_beats_borda
        summary['priority_topological_score_sum_beats_borda_runs'] = pri_beats_borda
        out.append(summary)
    return out


def _fmt(x: float) -> str:
    return f'{x:.4f}'


def _build_markdown(rows: list[dict], summaries: list[dict]) -> str:
    by_scheme = {r['scheme']: r for r in summaries}
    margin = by_scheme['margin']
    uniform = by_scheme['uniform']
    return f"""# METHOD_REPOSITIONING_AUDIT

## 1. What I checked

- Ranking extraction logic in `topological_ranking` and `greedy_fas`.
- Existing FAS-aware ranking variants already implemented in `scripts/run_real_experiment.py`.
- Synthetic multi-seed diagnostics at `n_items=20`, `noise=0.20`, for `margin` and `uniform` edge weights.

## 2. Core diagnosis

### Observation A — the current topological extraction is underpowered

Across 5 seeds with `margin` weights, mean Kendall τ is:
- `greedy_fas_topological`: {_fmt(margin['greedy_fas_topological_tau_mean'])}
- `lexicographic_topological`: {_fmt(margin['lexicographic_topological_tau_mean'])}
- `priority_topological_score_sum`: {_fmt(margin['priority_topological_score_sum_tau_mean'])}
- `fas_weighted_balance`: {_fmt(margin['fas_weighted_balance_tau_mean'])}
- `borda`: {_fmt(margin['borda_tau_mean'])}

Across 5 seeds with `uniform` weights, mean Kendall τ is:
- `greedy_fas_topological`: {_fmt(uniform['greedy_fas_topological_tau_mean'])}
- `lexicographic_topological`: {_fmt(uniform['lexicographic_topological_tau_mean'])}
- `priority_topological_score_sum`: {_fmt(uniform['priority_topological_score_sum_tau_mean'])}
- `fas_weighted_balance`: {_fmt(uniform['fas_weighted_balance_tau_mean'])}
- `borda`: {_fmt(uniform['borda_tau_mean'])}

### Observation B — tie-breaking/linear-extension choice clearly matters

For `margin`, the best sampled random topological order beats the current one by {_fmt(margin['best_random_vs_current_gap_mean'])} τ on average.
For `uniform`, the best sampled random topological order beats the current one by {_fmt(uniform['best_random_vs_current_gap_mean'])} τ on average.
The average number of ambiguous source-choice steps is {margin['ambiguous_steps_mean']:.1f} (`margin`) and {uniform['ambiguous_steps_mean']:.1f} (`uniform`).

### Observation C — edge-weight information is likely being discarded too aggressively

`fas_weighted_balance` beats the current topological extraction in {int(margin['fas_weighted_balance_beats_current_topo_runs'])}/5 `margin` runs and {int(uniform['fas_weighted_balance_beats_current_topo_runs'])}/5 `uniform` runs.
However, it still beats `borda` in only {int(margin['fas_weighted_balance_beats_borda_runs'])}/5 `margin` runs and {int(uniform['fas_weighted_balance_beats_borda_runs'])}/5 `uniform` runs.

### Observation D — the repair objective and the final ranking objective look misaligned

The repaired DAG reduces inconsistency by {margin['inconsistency_drop_mean']:.1f} edges on average (`margin`) and {uniform['inconsistency_drop_mean']:.1f} edges on average (`uniform`), yet the default topological ranking remains poor. This suggests the method may be optimizing graph acyclicity more than rank fidelity.

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
"""


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    rows = [_run_case(seed, scheme) for scheme in SCHEMES for seed in SEEDS]
    summaries = _summaries(rows)
    _write_csv(TABLES / 'fas_variant_diagnostics.csv', rows)
    _write_csv(TABLES / 'fas_variant_diagnostics_summary.csv', summaries)
    (DOCS / 'METHOD_REPOSITIONING_AUDIT.md').write_text(_build_markdown(rows, summaries), encoding='utf-8')
    print('Wrote docs/tables/fas_variant_diagnostics.csv')
    print('Wrote docs/tables/fas_variant_diagnostics_summary.csv')
    print('Wrote docs/METHOD_REPOSITIONING_AUDIT.md')


if __name__ == '__main__':
    main()
