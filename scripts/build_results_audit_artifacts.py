#!/usr/bin/env python
from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = REPO_ROOT / 'outputs'
DOCS = REPO_ROOT / 'docs'
TABLES = DOCS / 'tables'
FIGURES = DOCS / 'figures'


def _load_json(path: Path) -> dict:
    with path.open(encoding='utf-8') as fh:
        return json.load(fh)


def _timing_map(run_dir: Path) -> dict[str, float]:
    timing_path = run_dir / 'timings' / 'synthetic_timings.json'
    data = _load_json(timing_path)
    return {row['stage']: float(row['total_s']) for row in data.get('summary', [])}


def _safe_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _result_record(run_dir: Path, family: str, dataset: str = 'synthetic') -> dict:
    result_path = run_dir / 'synthetic_results.json'
    data = _load_json(result_path)
    config = data['config']
    graph = data['graph_summary']
    cycle = data['cycle_summary']
    eval_ = data['evaluation']
    fas = data['fas']
    timings = _timing_map(run_dir)
    kt = eval_['kendall_tau']
    nv = eval_['n_violations']
    pic = eval_['pairwise_inconsistency_count']
    best_method = max(kt, key=kt.get)
    baseline_tau = max(kt['score_sum'], kt['borda'])
    best_baseline = 'score_sum' if kt['score_sum'] >= kt['borda'] else 'borda'
    return {
        'run_dir': _safe_rel(run_dir),
        'result_path': _safe_rel(result_path),
        'timing_json_path': _safe_rel(run_dir / 'timings' / 'synthetic_timings.json'),
        'timing_csv_path': _safe_rel(run_dir / 'timings' / 'synthetic_timings.csv'),
        'experiment_family': family,
        'dataset': dataset,
        'seed': int(config['seed']),
        'weight_scheme': config['weight_scheme'],
        'n_items': int(config['n_items']),
        'noise': float(config['noise']),
        'graph_n_nodes': int(graph['n_nodes']),
        'graph_n_edges': int(graph['n_edges']),
        'graph_is_dag': bool(graph['is_dag']),
        'graph_n_sccs': int(graph['n_sccs']),
        'cycle_has_cycle': bool(cycle['has_cycle']),
        'cycle_n_non_trivial_sccs': int(cycle['n_non_trivial_sccs']),
        'score_sum_tau': float(kt['score_sum']),
        'borda_tau': float(kt['borda']),
        'greedy_fas_topological_tau': float(kt['greedy_fas_topological']),
        'score_sum_violations': int(nv['score_sum']),
        'borda_violations': int(nv['borda']),
        'greedy_fas_topological_violations': int(nv['greedy_fas_topological']),
        'original_pairwise_inconsistency': int(pic['original_graph']),
        'after_fas_pairwise_inconsistency': int(pic['after_fas_dag']),
        'fas_n_removed_edges': int(fas['n_removed_edges']),
        'fas_total_removed_weight': float(fas['total_removed_weight']),
        'runtime_total_s': float(timings['total_experiment']),
        'runtime_greedy_fas_s': float(timings['greedy_fas_solver']),
        'runtime_graph_construction_s': float(timings['graph_construction']),
        'runtime_evaluation_s': float(timings['evaluation']),
        'best_method': best_method,
        'best_tau': float(kt[best_method]),
        'best_baseline': best_baseline,
        'best_baseline_tau': float(baseline_tau),
        'greedy_gap_to_best': float(kt[best_method] - kt['greedy_fas_topological']),
        'fas_runtime_share_pct': (float(timings['greedy_fas_solver']) / float(timings['total_experiment']) * 100.0),
        'status': 'final',
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as fh:
        if not rows:
            fh.write('status,reason\n')
            return
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _fmt(x: float) -> str:
    return f'{x:.4f}'


def _fmt6(x: float) -> str:
    return f'{x:.6f}'


def _collect_existing_runs() -> list[dict]:
    runs: list[dict] = []
    for path in sorted((OUTPUTS).glob('noise_sweep_n*/synthetic_results.json')):
        runs.append(_result_record(path.parent, family='noise_sweep'))
    for path in sorted((OUTPUTS).glob('scale_sweep_n*/synthetic_results.json')):
        runs.append(_result_record(path.parent, family='scale_sweep'))
    for scheme in ('margin', 'uniform'):
        for path in sorted((OUTPUTS / f'{scheme}_multiseed_n20_noise0.20').glob('seed_*/synthetic_results.json')):
            runs.append(_result_record(path.parent, family=f'{scheme}_multiseed'))
    return runs


def _build_inventory(rows: list[dict]) -> list[dict]:
    inventory = []
    methods = 'score_sum;borda;greedy_fas_topological'
    metrics = 'kendall_tau;n_violations;pairwise_inconsistency_count;fas_n_removed_edges;fas_total_removed_weight;runtime_total_s'
    for row in rows:
        inventory.append({
            'path': row['result_path'],
            'experiment_family': row['experiment_family'],
            'dataset': row['dataset'],
            'methods_present': methods,
            'metrics_present': metrics,
            'status': row['status'],
        })
        inventory.append({
            'path': row['timing_csv_path'],
            'experiment_family': row['experiment_family'],
            'dataset': row['dataset'],
            'methods_present': 'timing_stages',
            'metrics_present': 'stage;total_s;mean_s;median_s;max_s',
            'status': 'diagnostic',
        })
        inventory.append({
            'path': row['timing_json_path'],
            'experiment_family': row['experiment_family'],
            'dataset': row['dataset'],
            'methods_present': 'timing_stages',
            'metrics_present': 'metadata;summary;records',
            'status': 'diagnostic',
        })
    inventory.append({
        'path': 'docs/RESULTS_AUDIT.md',
        'experiment_family': 'results_audit',
        'dataset': 'mixed',
        'methods_present': 'n/a',
        'metrics_present': 'audit_summary',
        'status': 'final',
    })
    return inventory


def _multiseed_summary(rows: list[dict], family: str) -> dict:
    subset = [r for r in rows if r['experiment_family'] == family]
    return {
        'experiment_family': family,
        'dataset': 'synthetic',
        'weight_scheme': subset[0]['weight_scheme'],
        'n_runs': len(subset),
        'n_items': subset[0]['n_items'],
        'noise': subset[0]['noise'],
        'score_sum_tau_mean': mean(r['score_sum_tau'] for r in subset),
        'score_sum_tau_std': pstdev(r['score_sum_tau'] for r in subset),
        'borda_tau_mean': mean(r['borda_tau'] for r in subset),
        'borda_tau_std': pstdev(r['borda_tau'] for r in subset),
        'greedy_tau_mean': mean(r['greedy_fas_topological_tau'] for r in subset),
        'greedy_tau_std': pstdev(r['greedy_fas_topological_tau'] for r in subset),
        'original_pic_mean': mean(r['original_pairwise_inconsistency'] for r in subset),
        'after_fas_pic_mean': mean(r['after_fas_pairwise_inconsistency'] for r in subset),
        'fas_removed_edges_mean': mean(r['fas_n_removed_edges'] for r in subset),
        'runtime_total_mean_s': mean(r['runtime_total_s'] for r in subset),
        'runtime_fas_mean_s': mean(r['runtime_greedy_fas_s'] for r in subset),
        'best_method_by_mean_tau': max(
            {
                'score_sum': mean(r['score_sum_tau'] for r in subset),
                'borda': mean(r['borda_tau'] for r in subset),
                'greedy_fas_topological': mean(r['greedy_fas_topological_tau'] for r in subset),
            },
            key=lambda k: {
                'score_sum': mean(r['score_sum_tau'] for r in subset),
                'borda': mean(r['borda_tau'] for r in subset),
                'greedy_fas_topological': mean(r['greedy_fas_topological_tau'] for r in subset),
            }[k],
        ),
    }


def _plot_tau_vs_noise(rows: list[dict]) -> None:
    subset = sorted([r for r in rows if r['experiment_family'] == 'noise_sweep'], key=lambda r: r['noise'])
    xs = [r['noise'] for r in subset]
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 4.5))
    for key, label in [
        ('score_sum_tau', 'score_sum'),
        ('borda_tau', 'borda'),
        ('greedy_fas_topological_tau', 'greedy_fas_topological'),
    ]:
        plt.plot(xs, [r[key] for r in subset], marker='o', label=label)
    plt.xlabel('Noise')
    plt.ylabel('Kendall tau')
    plt.title('Synthetic ranking quality vs noise')
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / 'kendall_tau_vs_noise.png', dpi=160)
    plt.close()


def _plot_tau_vs_n(rows: list[dict]) -> None:
    subset = sorted([r for r in rows if r['experiment_family'] == 'scale_sweep'], key=lambda r: r['n_items'])
    xs = [r['n_items'] for r in subset]
    plt.figure(figsize=(7, 4.5))
    for key, label in [
        ('score_sum_tau', 'score_sum'),
        ('borda_tau', 'borda'),
        ('greedy_fas_topological_tau', 'greedy_fas_topological'),
    ]:
        plt.plot(xs, [r[key] for r in subset], marker='o', label=label)
    plt.xlabel('n_items')
    plt.ylabel('Kendall tau')
    plt.title('Synthetic ranking quality vs graph size')
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / 'kendall_tau_vs_n_items.png', dpi=160)
    plt.close()


def _plot_multiseed_ablation(summary_rows: list[dict]) -> None:
    labels = [r['weight_scheme'] for r in summary_rows]
    borda = [r['borda_tau_mean'] for r in summary_rows]
    score_sum = [r['score_sum_tau_mean'] for r in summary_rows]
    greedy = [r['greedy_tau_mean'] for r in summary_rows]
    x = range(len(labels))
    width = 0.22
    plt.figure(figsize=(8, 4.8))
    plt.bar([i - width for i in x], score_sum, width=width, label='score_sum')
    plt.bar(list(x), borda, width=width, label='borda')
    plt.bar([i + width for i in x], greedy, width=width, label='greedy_fas_topological')
    plt.xticks(list(x), labels)
    plt.ylabel('Mean Kendall tau across seeds')
    plt.title('Weight-scheme ablation at n=20, noise=0.20')
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / 'multiseed_weight_ablation.png', dpi=160)
    plt.close()


def _build_markdown(rows: list[dict], inventory: list[dict], ablations: list[dict], blocker_cmd: str, blocker_err: str) -> str:
    noise = sorted([r for r in rows if r['experiment_family'] == 'noise_sweep'], key=lambda r: r['noise'])
    scale = sorted([r for r in rows if r['experiment_family'] == 'scale_sweep'], key=lambda r: r['n_items'])
    margin = next(r for r in ablations if r['weight_scheme'] == 'margin')
    uniform = next(r for r in ablations if r['weight_scheme'] == 'uniform')
    strongest = max(rows, key=lambda r: r['best_tau'])
    return f"""# RESULTS_AUDIT

_Last regenerated by `scripts/build_results_audit_artifacts.py`._

## 1. Current artifact inventory

- Machine-readable result files found: **{sum(1 for r in inventory if r['path'].endswith('.json') or r['path'].endswith('.csv'))}** inventory rows covering synthetic result JSONs, timing CSV/JSONs, and the audit outputs themselves.
- Completed experiment families: `noise_sweep`, `scale_sweep`, `margin_multiseed`, `uniform_multiseed`.
- No checked-in real-data outputs were found (`*_per_query.csv`, `*_summary.csv`, real-data timing files absent).

## 2. Completed experiments found in the repo before this audit

### Noise sweep (pre-existing)

| noise | score_sum τ | borda τ | greedy_fas_topological τ | best method |
|---|---:|---:|---:|---|
{chr(10).join(f"| {r['noise']:.2f} | {_fmt(r['score_sum_tau'])} | {_fmt(r['borda_tau'])} | {_fmt(r['greedy_fas_topological_tau'])} | {r['best_method']} |" for r in noise)}

### Scale sweep (pre-existing)

| n_items | score_sum τ | borda τ | greedy_fas_topological τ | total runtime (s) | greedy share (%) |
|---|---:|---:|---:|---:|---:|
{chr(10).join(f"| {r['n_items']} | {_fmt(r['score_sum_tau'])} | {_fmt(r['borda_tau'])} | {_fmt(r['greedy_fas_topological_tau'])} | {_fmt6(r['runtime_total_s'])} | {r['fas_runtime_share_pct']:.1f} |" for r in scale)}

## 3. Newly run during this audit

### Multi-seed replication at n=20, noise=0.20

| weight_scheme | n_runs | score_sum τ mean±std | borda τ mean±std | greedy_fas_topological τ mean±std | original PIC mean | after-FAS PIC mean |
|---|---:|---:|---:|---:|---:|---:|
| margin | {margin['n_runs']} | {_fmt(margin['score_sum_tau_mean'])}±{_fmt(margin['score_sum_tau_std'])} | {_fmt(margin['borda_tau_mean'])}±{_fmt(margin['borda_tau_std'])} | {_fmt(margin['greedy_tau_mean'])}±{_fmt(margin['greedy_tau_std'])} | {margin['original_pic_mean']:.1f} | {margin['after_fas_pic_mean']:.1f} |
| uniform | {uniform['n_runs']} | {_fmt(uniform['score_sum_tau_mean'])}±{_fmt(uniform['score_sum_tau_std'])} | {_fmt(uniform['borda_tau_mean'])}±{_fmt(uniform['borda_tau_std'])} | {_fmt(uniform['greedy_tau_mean'])}±{_fmt(uniform['greedy_tau_std'])} | {uniform['original_pic_mean']:.1f} | {uniform['after_fas_pic_mean']:.1f} |

**Finding:** on the newly run multi-seed replication, `borda` has the best mean τ under `margin`, while `score_sum` and `borda` tie under `uniform`; `greedy_fas_topological` remains clearly worse under both schemes.

## 4. Strongest evidence currently available

- Best single checked-in/run result: `{strongest['best_method']}` on `{strongest['experiment_family']}` with τ={_fmt(strongest['best_tau'])}, setting `n_items={strongest['n_items']}`, `noise={strongest['noise']}`, `weight_scheme={strongest['weight_scheme']}`, `seed={strongest['seed']}`.
- The repaired graph consistently reduces pairwise inconsistency, but the ranking induced by `greedy_fas_topological` does **not** beat simple baselines in the available synthetic evidence.
- Runtime evidence is real but synthetic-only; `greedy_fas_solver` dominates total time by the largest sizes tested.

## 5. Implemented-but-not-yet-executed paths

- Real-data pipeline: `scripts/run_real_experiment.py` can produce `*_per_query.csv`, `*_summary.csv`, and timing files, but none are present.
- Bootstrap/significance: `scripts/bootstrap_method_deltas.py` is implemented, but no per-query CSV exists yet.
- Exact ILP solver (`method="scip"`, open-source, no license required) is implemented in `src/consistency_ranker/mwfas_solver.py`; see `tests/test_exact_mwfas_scip.py`.

## 6. Blockers encountered during this audit

Attempted high-priority real-data command:

```bash
{blocker_cmd}
```

Observed blocker:

```text
{blocker_err}
```

Interpretation: this environment can run Python and plotting, but Hugging Face download access is blocked here, so real-data experiments were **not feasible** in this session.

## 7. Files to read next

- `docs/tables/main_results.csv`
- `docs/tables/ablation_results.csv`
- `docs/tables/runtime_results.csv`
- `docs/tables/bootstrap_results.csv`
- `docs/figures/kendall_tau_vs_noise.png`
- `docs/figures/runtime_vs_n_items.png`
"""


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = _collect_existing_runs()
    inventory = _build_inventory(rows)

    main_rows = []
    for r in sorted(rows, key=lambda x: (x['experiment_family'], x['noise'], x['n_items'], x['weight_scheme'], x['seed'])):
        main_rows.append({
            'experiment_family': r['experiment_family'],
            'dataset': r['dataset'],
            'run_dir': r['run_dir'],
            'seed': r['seed'],
            'weight_scheme': r['weight_scheme'],
            'n_items': r['n_items'],
            'noise': r['noise'],
            'best_method': r['best_method'],
            'best_tau': round(r['best_tau'], 6),
            'best_baseline': r['best_baseline'],
            'best_baseline_tau': round(r['best_baseline_tau'], 6),
            'score_sum_tau': round(r['score_sum_tau'], 6),
            'borda_tau': round(r['borda_tau'], 6),
            'greedy_fas_topological_tau': round(r['greedy_fas_topological_tau'], 6),
            'greedy_gap_to_best': round(r['greedy_gap_to_best'], 6),
            'original_pairwise_inconsistency': r['original_pairwise_inconsistency'],
            'after_fas_pairwise_inconsistency': r['after_fas_pairwise_inconsistency'],
            'fas_n_removed_edges': r['fas_n_removed_edges'],
            'fas_total_removed_weight': round(r['fas_total_removed_weight'], 6),
            'runtime_total_s': round(r['runtime_total_s'], 6),
            'runtime_greedy_fas_s': round(r['runtime_greedy_fas_s'], 6),
            'status': r['status'],
        })

    ablation_rows = [_multiseed_summary(rows, 'margin_multiseed'), _multiseed_summary(rows, 'uniform_multiseed')]
    ablation_rows = [{k: (round(v, 6) if isinstance(v, float) and not isinstance(v, bool) else v) for k, v in row.items()} for row in ablation_rows]

    runtime_rows = []
    for r in sorted([r for r in rows if r['experiment_family'] in {'scale_sweep', 'margin_multiseed', 'uniform_multiseed'}], key=lambda x: (x['experiment_family'], x['n_items'], x['seed'])):
        runtime_rows.append({
            'experiment_family': r['experiment_family'],
            'run_dir': r['run_dir'],
            'seed': r['seed'],
            'weight_scheme': r['weight_scheme'],
            'n_items': r['n_items'],
            'noise': r['noise'],
            'runtime_total_s': round(r['runtime_total_s'], 6),
            'runtime_greedy_fas_s': round(r['runtime_greedy_fas_s'], 6),
            'runtime_graph_construction_s': round(r['runtime_graph_construction_s'], 6),
            'runtime_evaluation_s': round(r['runtime_evaluation_s'], 6),
            'fas_runtime_share_pct': round(r['fas_runtime_share_pct'], 3),
        })

    bootstrap_rows = [{
        'status': 'blocked',
        'reason': 'No real-data per_query.csv exists in the repository, and live dataset download failed in this environment.',
        'blocked_stage': 'real_data_download_and_bootstrap',
        'attempted_command': 'python scripts/download_datasets.py --dataset hotpotqa --max-queries 20',
        'error_type': 'httpx.ProxyError',
        'error_message': '403 Forbidden',
        'next_fix': 'Restore HuggingFace access or provide prepared data/outputs/*_per_query.csv, then run scripts/bootstrap_method_deltas.py.',
    }]

    _write_csv(TABLES / 'main_results.csv', main_rows)
    _write_csv(TABLES / 'ablation_results.csv', ablation_rows)
    _write_csv(TABLES / 'runtime_results.csv', runtime_rows)
    _write_csv(TABLES / 'bootstrap_results.csv', bootstrap_rows)
    _write_csv(TABLES / 'result_inventory.csv', inventory)

    _plot_tau_vs_noise(rows)
    _plot_tau_vs_n(rows)
    _plot_multiseed_ablation(ablation_rows)

    blocker_cmd = 'python scripts/download_datasets.py --dataset hotpotqa --max-queries 20'
    blocker_err = 'httpx.ProxyError: 403 Forbidden'
    (DOCS / 'RESULTS_AUDIT.md').write_text(
        _build_markdown(rows, inventory, ablation_rows, blocker_cmd, blocker_err),
        encoding='utf-8',
    )

    print('Wrote docs/tables/main_results.csv')
    print('Wrote docs/tables/ablation_results.csv')
    print('Wrote docs/tables/runtime_results.csv')
    print('Wrote docs/tables/bootstrap_results.csv')
    print('Wrote docs/tables/result_inventory.csv')
    print('Updated docs/RESULTS_AUDIT.md')
    print('Wrote figures to docs/figures/')


if __name__ == '__main__':
    main()
