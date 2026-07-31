#!/usr/bin/env python3
"""Prior-robust adaptive ranking experiments (synthetic + optional replay).

No large billed API campaign. Writes to a new timestamped report directory.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from consistency_ranker.adaptive_acquisition import synthetic_roster
from consistency_ranker.experiment_cli import (
    ensure_output_dir,
    utc_stamp,
    write_run_manifest,
)
from consistency_ranker.prior_robust import (
    AdversarialScenario,
    RobustEngineConfig,
    make_adversarial_world,
    make_initial_robust_state,
    run_robust_acquisition,
)
from consistency_ranker.prior_robust.exploration_guards import ExplorationConfig
from consistency_ranker.statistical_inference import holm_adjust, sign_flip_pvalue

PRIOR_REGIMES = [
    "accurate",
    "noisy",
    "reversed_topk",
    "outsider_buried",
    "block_permute_topk",
    "overconfident_wrong",
]
JUDGE_REGIMES = [
    "clean",
    "shared_position_bias",
    "stable_wrong_consensus",
]

POLICIES = [
    ("plain_uht", {"plain_baseline": True, "score_mode": "uncertainty_x_topk_impact"}),
    ("uht_epsilon", {
        "score_mode": "uncertainty_x_topk_impact_epsilon",
        "exploration": ExplorationConfig(
            epsilon=0.15, enable_scheduled=False, enable_coverage=False,
            enable_challenger=False, enable_sentinel=False, enable_epsilon=True,
        ),
    }),
    ("uht_scheduled_probes", {
        "score_mode": "uncertainty_x_topk_impact",
        "exploration": ExplorationConfig(
            epsilon=0.0, enable_epsilon=False, enable_scheduled=True,
            scheduled_probe_every=4, enable_coverage=True, enable_challenger=True,
            enable_sentinel=True, n_sentinel_probes=1,
        ),
    }),
    ("uht_guarded", {
        "score_mode": "uncertainty_x_topk_impact",
        "prior_mode": "adaptive",
        "use_robust_stopping": True,
    }),
    ("evidence_stability", {"score_mode": "evidence_stability_gain"}),
    ("prior_dep_reduction", {"score_mode": "prior_dependence_reduction"}),
    ("challenger_focused", {"score_mode": "challenger_resolution"}),
    ("robust_combined", {"score_mode": "robust_combined"}),
    ("no_prior", {"score_mode": "no_prior", "prior_mode": "none"}),
    ("quality_gated", {"score_mode": "uncertainty_x_topk_impact"}),  # meta-policy via name
]


def _cfg_from(base: dict, budget: int, seed: int, top_k: int) -> RobustEngineConfig:
    kwargs = dict(base)
    explor = kwargs.pop("exploration", None)
    cfg = RobustEngineConfig(
        budget=budget,
        seed=seed,
        top_k=top_k,
        score_mode=kwargs.get("score_mode", "uncertainty_x_topk_impact"),
        prior_mode=kwargs.get("prior_mode", "adaptive"),
        plain_baseline=bool(kwargs.get("plain_baseline", False)),
        use_robust_stopping=bool(kwargs.get("use_robust_stopping", True)),
    )
    if explor is not None:
        cfg.exploration = explor
    return cfg


def _true_prior_kendall(true_ranking: list[str], prior: dict[str, float]) -> float:
    from consistency_ranker.evaluation import kendall_tau

    prior_rank = sorted(prior, key=lambda d: (-float(prior[d]), d))
    return float(kendall_tau(true_ranking, prior_rank))


def run_cell(
    *,
    prior_regime: str,
    judge_regime: str,
    policy_name: str,
    policy_kwargs: dict,
    seed: int,
    budget: int,
    n_items: int,
    top_k: int,
) -> dict:
    sc = AdversarialScenario(
        name=f"{prior_regime}|{judge_regime}",
        prior_regime=prior_regime,  # type: ignore[arg-type]
        judge_regime=judge_regime,  # type: ignore[arg-type]
        n_items=n_items,
        top_k=top_k,
        seed=seed,
    )
    world = make_adversarial_world(sc)
    profiles = synthetic_roster(n_models=3, n_prompts=2)
    st = make_initial_robust_state(
        query_id=f"q_{seed}",
        candidate_ids=list(world["true_ranking"]),
        prior_scores=world["prior_scores"],
        budget=budget,
        top_k=top_k,
        seed=seed,
    )
    cfg = _cfg_from(policy_kwargs, budget=budget, seed=seed, top_k=top_k)
    t0 = time.perf_counter()
    res = run_robust_acquisition(
        st,
        profiles,
        world["judge"],
        cfg=cfg,
        alt_priors=world["alt_priors"],
        true_ranking=world["true_ranking"],
        true_prior_quality=_true_prior_kendall(world["true_ranking"], world["prior_scores"]),
        policy_name=policy_name,
    )
    runtime = time.perf_counter() - t0
    final = res.trace.final()
    q_hat = res.lambda_state.q_hat
    true_q = _true_prior_kendall(world["true_ranking"], world["prior_scores"])
    # Stable-but-wrong: high ordinary stability but wrong top-k.
    stable = float(final.get("topk_jaccard_min") or 0.0) >= 0.9
    topk_wrong = float(final.get("topk_jaccard_truth") or 0.0) < 1.0
    # Outsider recall for buried regime.
    buried = world["true_ranking"][0]
    recovered = buried in res.state.ranking[:top_k]
    return {
        "prior_regime": prior_regime,
        "judge_regime": judge_regime,
        "policy": policy_name,
        "seed": seed,
        "budget": budget,
        "n_calls": res.n_calls,
        "total_cost": res.total_cost,
        "runtime_s": runtime,
        "stopping_reason": res.stopping_reason,
        "category": res.report.category,
        "kendall_tau_truth": final.get("kendall_tau_truth"),
        "topk_jaccard_truth": final.get("topk_jaccard_truth"),
        "topk_set_acc": 1.0 if float(final.get("topk_jaccard_truth") or 0) >= 0.999 else 0.0,
        "s_total": res.report.evidence_only_stability,  # filled below
        "s_evidence": res.report.evidence_only_stability,
        "g_prior": res.report.prior_dependence_gap,
        "q_hat": q_hat,
        "true_prior_tau": true_q,
        "q_err": abs(q_hat - max(0.0, (true_q + 1) / 2)),
        "lambda_q": res.lambda_state.lambda_q,
        "stable_but_wrong": bool(stable and topk_wrong),
        "outsider_recovered": recovered if prior_regime == "outsider_buried" else None,
        "n_exploration": res.report.n_exploration_probes,
        "action_counts": res.action_counts,
        "failure_trace": res.failure_trace if (stable and topk_wrong) else None,
    }


def paired_delta(rows: list[dict], policy_a: str, policy_b: str, metric: str) -> dict:
    """Matched-seed paired comparison within the same regime cell."""
    by_key: dict[tuple, dict[str, float]] = defaultdict(dict)
    for r in rows:
        key = (r["prior_regime"], r["judge_regime"], r["seed"], r["budget"])
        if r["policy"] in (policy_a, policy_b) and r.get(metric) is not None:
            by_key[key][r["policy"]] = float(r[metric])
    diffs = []
    for key, m in by_key.items():
        if policy_a in m and policy_b in m:
            diffs.append(m[policy_a] - m[policy_b])
    if not diffs:
        return {"n": 0, "mean_delta": None, "p": None}
    mean = sum(diffs) / len(diffs)
    sf = sign_flip_pvalue(diffs, reps=2000, seed=0)
    p = float(sf.pvalue) if sf.pvalue is not None else None
    return {"n": len(diffs), "mean_delta": mean, "p": p}


def summarize(rows: list[dict]) -> dict:
    out: dict = {"by_policy_regime": {}, "overall_policy": {}}
    for pol in sorted({r["policy"] for r in rows}):
        subset = [r for r in rows if r["policy"] == pol]
        out["overall_policy"][pol] = {
            "n": len(subset),
            "mean_tau": _mean([r["kendall_tau_truth"] for r in subset]),
            "mean_topk_j": _mean([r["topk_jaccard_truth"] for r in subset]),
            "mean_calls": _mean([r["n_calls"] for r in subset]),
            "frac_stable_but_wrong": _mean([1.0 if r["stable_but_wrong"] else 0.0 for r in subset]),
            "mean_g_prior": _mean([r["g_prior"] for r in subset]),
            "mean_q_err": _mean([r["q_err"] for r in subset]),
        }
        for pr in PRIOR_REGIMES:
            ss = [r for r in subset if r["prior_regime"] == pr]
            if not ss:
                continue
            out["by_policy_regime"][f"{pol}|{pr}"] = {
                "n": len(ss),
                "mean_tau": _mean([r["kendall_tau_truth"] for r in ss]),
                "mean_topk_j": _mean([r["topk_jaccard_truth"] for r in ss]),
                "mean_calls": _mean([r["n_calls"] for r in ss]),
                "frac_sbw": _mean([1.0 if r["stable_but_wrong"] else 0.0 for r in ss]),
                "outsider_recall": _mean(
                    [
                        1.0 if r["outsider_recovered"] else 0.0
                        for r in ss
                        if r["outsider_recovered"] is not None
                    ]
                ),
            }
    return out


def _mean(xs):
    xs = [float(x) for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def write_report(out_dir: Path, rows: list[dict], summary: dict, comparisons: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "rows.jsonl").write_text(
        "\n".join(json.dumps(r, default=str) for r in rows) + "\n"
    )
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    (out_dir / "comparisons.json").write_text(json.dumps(comparisons, indent=2, default=str))

    # Decision logic
    ov = summary["overall_policy"]
    plain = ov.get("plain_uht", {})
    guarded = ov.get("uht_guarded", {})
    robust = ov.get("robust_combined", {})
    qg = ov.get("quality_gated", {})
    bad_regs = ["reversed_topk", "outsider_buried", "overconfident_wrong"]
    def regime_tau(pol, reg):
        return (summary["by_policy_regime"].get(f"{pol}|{reg}") or {}).get("mean_tau")

    guarded_bad = _mean([regime_tau("uht_guarded", r) for r in bad_regs])
    plain_bad = _mean([regime_tau("plain_uht", r) for r in bad_regs])
    qg_bad = _mean([regime_tau("quality_gated", r) for r in bad_regs])
    guarded_good = regime_tau("uht_guarded", "accurate")
    plain_good = regime_tau("plain_uht", "accurate")
    qg_good = regime_tau("quality_gated", "accurate")
    sbw_g = guarded.get("frac_stable_but_wrong")
    sbw_p = plain.get("frac_stable_but_wrong")
    outsider_qg = (summary["by_policy_regime"].get("quality_gated|outsider_buried") or {}).get(
        "outsider_recall"
    )
    outsider_plain = (summary["by_policy_regime"].get("plain_uht|outsider_buried") or {}).get(
        "outsider_recall"
    )

    # Prefer Outcome D when quality-gated retains good-prior efficiency and
    # improves recovery under corrupted priors.
    if (
        qg_good is not None
        and plain_good is not None
        and qg_good >= plain_good - 0.08
        and (
            (qg_bad is not None and plain_bad is not None and qg_bad >= plain_bad - 0.02)
            or (
                outsider_qg is not None
                and outsider_plain is not None
                and outsider_qg > outsider_plain + 0.1
            )
        )
    ):
        decision = "D"
        decision_text = (
            "Outcome D — Use adaptive acquisition (uncertainty_x_topk_impact) when "
            "prior-quality diagnostics pass after exploration probes; otherwise fall "
            "back to robust_combined with challenger expansion."
        )
    elif (
        guarded_bad is not None
        and plain_bad is not None
        and guarded_bad > plain_bad + 0.03
        and (plain_good is None or guarded_good is None or guarded_good >= plain_good - 0.08)
    ):
        decision = "B"
        decision_text = (
            "Outcome B — Adopt guarded uncertainty_x_topk_impact with exploration, "
            "prior-quality λ_q, and robust stopping safeguards."
        )
    elif (
        robust.get("frac_stable_but_wrong") is not None
        and plain.get("frac_stable_but_wrong") is not None
        and robust["frac_stable_but_wrong"] < plain["frac_stable_but_wrong"] - 0.1
        and (robust.get("mean_tau") or 0) >= (plain.get("mean_tau") or 0) - 0.05
    ):
        decision = "C"
        decision_text = (
            "Outcome C — Prefer robust_combined acquisition as default."
        )
    elif guarded_good is not None and plain_good is not None and guarded_good < plain_good - 0.15:
        decision = "D"
        decision_text = (
            "Outcome D — Use adaptive acquisition only when prior-quality diagnostics pass; "
            "always-on guards regress under accurate priors."
        )
    else:
        decision = "D"
        decision_text = (
            "Outcome D — Gate adaptive UHT on prior-quality diagnostics; fall back to "
            "robust/challenger acquisition when Q_hat is low."
        )

    failure_traces = [r["failure_trace"] for r in rows if r.get("failure_trace")][:12]
    (out_dir / "failure_traces.json").write_text(
        json.dumps(failure_traces, indent=2, default=str)
    )

    auto = {
        "decision": decision,
        "text": decision_text,
        "plain": plain,
        "guarded": guarded,
        "robust": robust,
        "quality_gated": qg,
        "guarded_bad_tau": guarded_bad,
        "plain_bad_tau": plain_bad,
        "qg_bad_tau": qg_bad,
        "guarded_good_tau": guarded_good,
        "plain_good_tau": plain_good,
        "qg_good_tau": qg_good,
        "outsider_recall_plain": outsider_plain,
        "outsider_recall_qg": outsider_qg,
        "sbw_plain": sbw_p,
        "sbw_guarded": sbw_g,
        "sbw_qg": qg.get("frac_stable_but_wrong"),
    }
    (out_dir / "decision.json").write_text(json.dumps(auto, indent=2, default=str))
    auto_md = "\n".join(
        [
            f"# Auto summary — {out_dir.name}",
            "",
            f"**Decision:** {decision_text}",
            "",
            "See curated `FINAL_REPORT.md` for full answers to Q1–Q18.",
            "Machine-readable metrics: `summary.json`, `comparisons.json`, `decision.json`.",
            "",
            "## Reproduction",
            "",
            "```bash",
            "source .venv/bin/activate",
            f"PYTHONPATH=src python scripts/run_prior_robust_experiment.py --output-dir {out_dir}",
            "```",
            "",
        ]
    )
    (out_dir / "FINAL_REPORT_AUTO.md").write_text(auto_md)
    if not (out_dir / "FINAL_REPORT.md").exists():
        (out_dir / "FINAL_REPORT.md").write_text(auto_md)
    (out_dir / "REPRODUCE.sh").write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'cd "$(dirname "$0")/../.."\n'
        "source .venv/bin/activate\n"
        'PYTHONPATH=src python scripts/run_prior_robust_experiment.py '
        '--output-dir "$(dirname "$0")" --overwrite\n'
    )
    if not (out_dir / "INCOMPLETE.md").exists():
        (out_dir / "INCOMPLETE.md").write_text(
            "# INCOMPLETE\n\n"
            "* See curated notes in the report directory after the first full run.\n"
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Report directory (default: reports/prior_robust_<UTC>).",
    )
    ap.add_argument("--n-seeds", type=int, default=8)
    ap.add_argument("--budget", type=int, default=24)
    ap.add_argument("--n-items", type=int, default=8)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into a non-empty --output-dir.",
    )
    args = ap.parse_args()

    stamp = utc_stamp()
    out_dir = ensure_output_dir(
        (args.output_dir or Path("reports") / f"prior_robust_{stamp}").resolve(),
        overwrite=args.overwrite,
    )

    seeds = list(range(args.n_seeds))
    if args.quick:
        seeds = list(range(2))
        prior_regimes = ["accurate", "reversed_topk", "outsider_buried"]
        judge_regimes = ["clean"]
        policies = [
            p
            for p in POLICIES
            if p[0]
            in {
                "plain_uht",
                "uht_guarded",
                "uht_epsilon",
                "robust_combined",
                "challenger_focused",
                "quality_gated",
            }
        ]
        n_items = min(args.n_items, 6)
        budget = min(args.budget, 8)
        top_k = min(args.top_k, 3)
    else:
        prior_regimes = PRIOR_REGIMES
        judge_regimes = JUDGE_REGIMES
        policies = POLICIES
        n_items = args.n_items
        budget = args.budget
        top_k = args.top_k

    rows = []
    t0 = time.perf_counter()
    for pr in prior_regimes:
        for jr in judge_regimes:
            for pname, pkw in policies:
                for seed in seeds:
                    rows.append(
                        run_cell(
                            prior_regime=pr,
                            judge_regime=jr,
                            policy_name=pname,
                            policy_kwargs=pkw,
                            seed=seed,
                            budget=budget,
                            n_items=n_items,
                            top_k=top_k,
                        )
                    )
    print(f"ran {len(rows)} cells in {time.perf_counter()-t0:.1f}s")

    summary = summarize(rows)
    # Paired comparisons vs plain
    comparisons = {}
    for pname, _ in policies:
        if pname == "plain_uht":
            continue
        for metric in ("kendall_tau_truth", "topk_jaccard_truth", "g_prior"):
            key = f"{pname}_vs_plain_{metric}"
            comparisons[key] = paired_delta(rows, pname, "plain_uht", metric)
        # Holm over regimes for tau
        ps = []
        labels = []
        for pr in prior_regimes:
            sub = [r for r in rows if r["prior_regime"] == pr]
            d = paired_delta(sub, pname, "plain_uht", "kendall_tau_truth")
            if d["p"] is not None:
                ps.append(d["p"])
                labels.append(pr)
                comparisons[f"{pname}_vs_plain_tau|{pr}"] = d
        if ps:
            adj = holm_adjust(ps)
            comparisons[f"{pname}_holm_tau"] = dict(zip(labels, adj))

    config = {
        "n_seeds": len(seeds),
        "seeds": seeds,
        "budget": budget,
        "n_items": n_items,
        "top_k": top_k,
        "prior_regimes": prior_regimes,
        "judge_regimes": judge_regimes,
        "policies": [p[0] for p in policies],
        "quick": bool(args.quick),
        "offline": True,
        "paid_api_calls": 0,
        "timestamp": stamp,
    }
    (out_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    write_run_manifest(
        out_dir,
        script="scripts/run_prior_robust_experiment.py",
        config=config,
        repo_root=Path(__file__).resolve().parents[1],
    )
    write_report(out_dir, rows, summary, comparisons)
    print("wrote", out_dir)
    print("decision", json.loads((out_dir / "decision.json").read_text())["decision"])


if __name__ == "__main__":
    main()
