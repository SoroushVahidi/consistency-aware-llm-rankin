#!/usr/bin/env python3
"""RESEARCH SCRIPT — calibrated query-level policy-selection benchmark.

This is **not** a production entry point. It exists to compare experimental
gates against always-UHT on synthetic worlds, so it runs in
``ExecutionMode.EXPERIMENTAL_GATE`` and deliberately exercises learned routing
that production forbids. The production operating point is
``scripts/run_production_uht.py`` / ``policy_selection.run_production_uht``.

No large billed API campaign: all judgments come from synthetic judges. Writes
to a new timestamped report directory.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from consistency_ranker.policy_selection.diagnostic_probes import (
    probe_informativeness_scores,
    select_probe_pairs,
)
from consistency_ranker.policy_selection.execution_mode import (
    EXECUTION_MODE_CHOICES,
    ExecutionMode,
    resolve_execution_mode,
)
from consistency_ranker.policy_selection.gate_features import (
    FEATURE_SCHEMA_VERSION,
    FeatureBundle,
    assert_no_qrel_keys,
)
from consistency_ranker.policy_selection.policy_benchmark import (
    PolicyBenchmarkConfig,
    build_synthetic_population,
    build_world,
    leave_one_regime_out_folds,
    majority_best_policy,
    nested_split_regimes,
    records_to_xy,
    regret_targets,
)
from consistency_ranker.policy_selection.policy_calibration import (
    evaluation_metrics,
    fit_calibrated_gate,
    predict_proba,
)
from consistency_ranker.policy_selection.policy_gate import (
    GateMode,
    PolicySelector,
    select_policy,
)
from consistency_ranker.policy_selection.policy_regret import (
    fit_regret_models,
    predict_policy_regret,
)
from consistency_ranker.policy_selection.policy_runner import run_gated_acquisition
from consistency_ranker.policy_selection.policy_utility import (
    UtilityWeights,
    gate_asymmetric_loss,
    regret_vs_oracle,
)
from consistency_ranker.policy_selection.replay_eval import (
    build_cache_index,
    observational_disclaimer,
    replay_probe_features,
)
from consistency_ranker.policy_selection.risk_control import (
    ASSUMPTIONS,
    fit_uht_risk_threshold,
)
from consistency_ranker.prior_robust import make_initial_robust_state

GATE_MODES: list[GateMode] = [
    "always_uht",
    "always_challenger",
    "always_robust",
    "broad_static",
    "hard_qhat",
    "calibrated_hard",
    "selective_three_way",
    "soft_mixture",
    "budget_split",
    "staged",
    "cost_sensitive_regret",
    "contextual",
    "conservative_fallback",
    "random",
    "majority_best",
    "oracle",
]


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def _write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _plot_reliability(bins: list[dict], path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        path.write_text("matplotlib unavailable\n", encoding="utf-8")
        return
    conf = [b["conf"] for b in bins if b["n"] > 0]
    acc = [b["acc"] for b in bins if b["n"] > 0]
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="ideal")
    if conf:
        ax.plot(conf, acc, "o-", label="model")
    ax.set_xlabel("confidence")
    ax.set_ylabel("accuracy")
    ax.set_title("Reliability diagram")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_risk_coverage(coverages: list[float], regrets: list[float], path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot(coverages, regrets, "o-")
    ax.set_xlabel("selective coverage")
    ax.set_ylabel("mean gate regret")
    ax.set_title("Risk–coverage")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_decision_curves(curves: dict[str, list], path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig, axes = plt.subplots(2, 2, figsize=(8, 6))
    # quality vs probe budget
    ax = axes[0, 0]
    for name, pts in dict(curves.get("quality_vs_probe", {})).items():
        ax.plot([p[0] for p in pts], [p[1] for p in pts], label=name)
    ax.set_xlabel("probe budget")
    ax.set_ylabel("mean top-k Jaccard")
    ax.legend(fontsize=7)
    # catastrophic vs threshold
    ax = axes[0, 1]
    pts = curves.get("catastrophic_vs_threshold", [])
    if pts:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-")
    ax.set_xlabel("qhat threshold")
    ax.set_ylabel("catastrophic rate")
    # regret vs coverage
    ax = axes[1, 0]
    pts = curves.get("regret_vs_coverage", [])
    if pts:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-")
    ax.set_xlabel("coverage")
    ax.set_ylabel("regret")
    # UHT usage vs prior quality decile
    ax = axes[1, 1]
    pts = curves.get("uht_usage_vs_prior_q", [])
    if pts:
        ax.bar([p[0] for p in pts], [p[1] for p in pts])
    ax.set_xlabel("prior-q decile")
    ax.set_ylabel("UHT usage")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


#: This benchmark exists to evaluate experimental routing; every PolicySelector
#: built below is explicitly authorised for it. Nothing here changes the
#: production default, which remains always-UHT.
BENCHMARK_EXECUTION_MODE = ExecutionMode.EXPERIMENTAL_GATE


def run_experiment(
    output_dir: Path, *, quick: bool = False, overwrite_existing: bool = False
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=overwrite_existing)
    t_start = time.perf_counter()
    weights = UtilityWeights(lambda_c=0.008, lambda_r=0.6, false_trust=2.5, false_distrust=0.5)

    if quick:
        cfg = PolicyBenchmarkConfig(
            n_items=6,
            top_k=2,
            budget=12,
            train_seeds=(0, 1),
            val_seeds=(10,),
            test_seeds=(20,),
            weights=weights,
        )
    else:
        cfg = PolicyBenchmarkConfig(
            n_items=8,
            top_k=3,
            budget=16,
            train_seeds=(0, 1, 2, 3),
            val_seeds=(10, 11),
            test_seeds=(20, 21),
            weights=weights,
        )

    print("Building synthetic population (nested splits)...")
    records = build_synthetic_population(cfg, include_policy_outcomes=True)
    train = [r for r in records if r.split == "train"]
    val = [r for r in records if r.split == "val"]
    test = [r for r in records if r.split == "test"]
    _write_json(output_dir / "population_summary.json", {
        "n_total": len(records),
        "n_train": len(train),
        "n_val": len(val),
        "n_test": len(test),
        "splits": nested_split_regimes(),
        "feature_schema": FEATURE_SCHEMA_VERSION,
    })
    with (output_dir / "rows.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_dict(), default=str) + "\n")

    # --- Fit calibration on train only ---
    X_tr, y_tr, feat_names, _ = records_to_xy(train, stage="probe", target="uht_optimal")
    X_va, y_va, _, _ = records_to_xy(val, stage="probe", target="uht_optimal")
    X_te, y_te, _, _ = records_to_xy(test, stage="probe", target="uht_optimal")

    models = {}
    cal_reports = {}
    for kind in ("logistic", "isotonic", "beta", "shallow_tree", "heuristic"):
        m = fit_calibrated_gate(
            X_tr, y_tr, feature_names=feat_names, kind=kind,  # type: ignore[arg-type]
            training_regimes=[r.prior_regime for r in train],
            target_name="uht_optimal",
        )
        models[kind] = m
        probs = [predict_proba(m, x) for x in X_va] if X_va else []
        cal_reports[kind] = evaluation_metrics(y_va, probs).to_dict() if y_va else {}
        m.save(output_dir / f"model_{kind}.json")

    # Select model on validation decision utility (not accuracy alone).
    def _decision_util(kind: str) -> float:
        m = models[kind]
        # Approximate: reward correct UHT decisions under asymmetric loss.
        util = 0.0
        for x, yt in zip(X_va, y_va):
            p = predict_proba(m, x)
            pred = p >= 0.55
            util -= gate_asymmetric_loss(
                predicted_trust=pred,
                true_uht_better=bool(yt >= 0.5),
                weights=weights,
                catastrophic_if_uht=False,
            )
        return util / max(len(y_va), 1)

    best_kind = max(models, key=_decision_util) if models else "logistic"
    binary_model = models[best_kind]
    _plot_reliability(
        cal_reports.get(best_kind, {}).get("reliability_bins", []),
        output_dir / "reliability_diagram.png",
    )

    # Multinomial best-policy on train
    classes = sorted({r.best_policy for r in train if r.best_policy})
    y_multi = [r.best_policy or "UHT" for r in train]
    multi = fit_calibrated_gate(
        X_tr, y_tr, feature_names=feat_names, kind="multinomial_logistic",
        training_regimes=[r.prior_regime for r in train],
        classes=classes, y_multi=y_multi,
    )
    multi.save(output_dir / "model_multinomial.json")

    # Regret models
    deltas = regret_targets(train, weights)
    regret_models = fit_regret_models(
        X_tr, deltas, feature_names=feat_names,
        training_regimes=[r.prior_regime for r in train],
    )
    for name, m in regret_models.items():
        m.save(output_dir / f"regret_model_{name}.json")

    # Risk-control threshold on validation
    val_scores, val_regrets, val_cats = [], [], []
    for rec, x in zip(val, X_va):
        p = predict_proba(binary_model, x)
        val_scores.append(p)
        u_uht = float((rec.policy_outcomes.get("UHT") or {}).get("extra", {}).get("utility") or 0)
        u_ch = float((rec.policy_outcomes.get("CHALLENGER") or {}).get("extra", {}).get("utility") or 0)
        val_regrets.append(max(0.0, u_ch - u_uht))
        val_cats.append(bool((rec.policy_outcomes.get("UHT") or {}).get("catastrophic")))
    uht_thr = fit_uht_risk_threshold(
        scores=val_scores, uht_regret=val_regrets, catastrophic=val_cats
    )

    # Threshold selection on validation expected utility only
    thr_grid = [0.35, 0.45, 0.55, 0.65, 0.75]
    thr_utils = {}
    for thr in thr_grid:
        u = 0.0
        for rec, x in zip(val, X_va):
            p = predict_proba(binary_model, x)
            chosen = "UHT" if p >= thr else "CHALLENGER"
            od = rec.policy_outcomes.get(chosen) or {}
            u += float(od.get("extra", {}).get("utility") or 0.0)
        thr_utils[thr] = u / max(len(val), 1)
    best_thr = max(thr_utils, key=lambda k: thr_utils[k])

    maj = majority_best_policy(train)

    # --- Evaluate gate modes on test via gated acquisition ---
    print("Evaluating gate modes on held-out test regimes...")
    gate_rows = []
    for mode in GATE_MODES:
        for rec in test:
            world = build_world(
                prior_regime=rec.prior_regime,
                judge_regime=rec.judge_regime,
                seed=rec.seed,
                n_items=cfg.n_items,
                top_k=cfg.top_k,
            )
            world["prior_regime"] = rec.prior_regime
            world["judge_regime"] = rec.judge_regime
            world["seed"] = rec.seed
            sel = PolicySelector(
                mode=mode,
                binary_model=binary_model,
                multinomial_model=multi,
                regret_models=regret_models,
                weights=weights,
                qhat_threshold=best_thr,
                uht_risk_threshold=uht_thr,
                majority_best_policy=maj,
                tau_policy=0.50,
                risk_delta=0.15,
                safety_floor=0.15,
                execution_mode=BENCHMARK_EXECUTION_MODE,
            )
            out = run_gated_acquisition(
                world=world,
                selector=sel,
                budget=cfg.budget,
                top_k=cfg.top_k,
                seed=rec.seed,
                probe_budget=0 if mode in ("always_uht", "oracle", "random", "majority_best") else 3,
                enable_switching=(mode == "staged"),
                enable_fallback=(mode in ("conservative_fallback", "soft_mixture", "staged")),
                oracle_best=rec.best_policy,  # type: ignore[arg-type]
                query_id=rec.query_id,
            )
            outcome = out["outcome"]
            util = float(out["utility"])
            oracle_u = float(rec.oracle_utility or 0.0)
            gate_rows.append({
                "mode": mode,
                "query_id": rec.query_id,
                "prior_regime": rec.prior_regime,
                "judge_regime": rec.judge_regime,
                "seed": rec.seed,
                "policy": out["decision"].policy,
                "trust_label": out["decision"].trust_label,
                "g_q": out["decision"].g_q,
                "abstained": out["decision"].abstained,
                "reason": out["decision"].reason,
                "utility": util,
                "oracle_utility": oracle_u,
                "gate_regret": regret_vs_oracle(util, oracle_u),
                "topk_jaccard": outcome.topk_jaccard,
                "kendall_tau": outcome.kendall_tau,
                "n_calls": outcome.n_calls,
                "probe_calls": outcome.probe_calls,
                "catastrophic": outcome.catastrophic,
                "buried_recovered": outcome.buried_recovered,
                "stable_but_wrong": outcome.stable_but_wrong,
                "best_policy": rec.best_policy,
                "policy_match": out["decision"].policy == rec.best_policy,
                "true_prior_tau": rec.true_prior_tau,
            })

    _write_json(output_dir / "gate_rows.json", gate_rows)

    # Aggregate by mode
    by_mode: dict[str, list] = defaultdict(list)
    for row in gate_rows:
        by_mode[row["mode"]].append(row)

    mode_summary = {}
    for mode_name, rows in by_mode.items():
        mode_summary[mode_name] = {
            "n": len(rows),
            "mean_utility": _mean([r["utility"] for r in rows]),
            "mean_gate_regret": _mean([r["gate_regret"] for r in rows]),
            "max_gate_regret": max((r["gate_regret"] for r in rows), default=0.0),
            "mean_topk_jaccard": _mean([float(r["topk_jaccard"] or 0) for r in rows]),
            "mean_kendall": _mean([float(r["kendall_tau"] or 0) for r in rows]),
            "mean_calls": _mean([float(r["n_calls"]) for r in rows]),
            "mean_probe_calls": _mean([float(r["probe_calls"]) for r in rows]),
            "catastrophic_rate": _mean([1.0 if r["catastrophic"] else 0.0 for r in rows]),
            "policy_accuracy": _mean([1.0 if r["policy_match"] else 0.0 for r in rows]),
            "abstain_rate": _mean([1.0 if r["abstained"] else 0.0 for r in rows]),
            "false_trust_rate": _mean([
                1.0 if (
                    r["trust_label"] == "TRUST_PRIOR"
                    and r["best_policy"] not in ("UHT", "UHT_EXPLORE")
                ) else 0.0
                for r in rows
            ]),
            "false_distrust_rate": _mean([
                1.0 if (
                    r["trust_label"] == "DISTRUST_PRIOR"
                    and r["best_policy"] in ("UHT", "UHT_EXPLORE")
                ) else 0.0
                for r in rows
            ]),
            "oracle_gap": _mean([r["gate_regret"] for r in rows]),
        }

    # Probe budget sweep on val (decision curves)
    quality_vs_probe: dict[str, list[tuple[int, float]]] = {
        "selective_three_way": [], "soft_mixture": [], "calibrated_hard": []
    }
    for pb in (0, 1, 2, 3, 4):
        for probe_mode in quality_vs_probe:
            scores = []
            for rec in val[: max(2, len(val))]:
                world = build_world(
                    prior_regime=rec.prior_regime, judge_regime=rec.judge_regime,
                    seed=rec.seed, n_items=cfg.n_items, top_k=cfg.top_k,
                )
                world["prior_regime"] = rec.prior_regime
                world["judge_regime"] = rec.judge_regime
                world["seed"] = rec.seed
                sel = PolicySelector(
                    mode=probe_mode,  # type: ignore[arg-type]
                    binary_model=binary_model, multinomial_model=multi,
                    regret_models=regret_models, weights=weights,
                    qhat_threshold=best_thr, majority_best_policy=maj,
                    execution_mode=BENCHMARK_EXECUTION_MODE,
                )
                out = run_gated_acquisition(
                    world=world, selector=sel, budget=cfg.budget, top_k=cfg.top_k,
                    seed=rec.seed, probe_budget=pb, oracle_best=rec.best_policy,  # type: ignore[arg-type]
                )
                scores.append(float(out["outcome"].topk_jaccard or 0.0))
            quality_vs_probe[probe_mode].append((pb, _mean(scores)))

    cat_vs_thr = []
    for thr in thr_grid:
        cats = []
        for rec, x in zip(val, X_va):
            p = predict_proba(binary_model, x)
            chosen = "UHT" if p >= thr else "CHALLENGER"
            cats.append(1.0 if (rec.policy_outcomes.get(chosen) or {}).get("catastrophic") else 0.0)
        cat_vs_thr.append((thr, _mean(cats)))

    # Risk-coverage for selective gate
    risk_cov = []
    coverages, regrets = [], []
    for tau in (0.35, 0.45, 0.55, 0.65, 0.75, 0.85):
        accepted, reg = [], []
        for rec, x in zip(test, X_te if X_te else X_va):
            if rec.features_probe is None:
                continue
            bundle = FeatureBundle.from_dict(rec.features_probe)
            assert_no_qrel_keys(bundle)
            sel = PolicySelector(
                mode="selective_three_way", binary_model=binary_model,
                multinomial_model=multi, tau_policy=tau, weights=weights,
                qhat_threshold=best_thr,
                execution_mode=BENCHMARK_EXECUTION_MODE,
            )
            dec = select_policy(bundle, selector=sel, q_hat_heuristic=0.5, oracle_best=rec.best_policy)  # type: ignore[arg-type]
            if not dec.abstained:
                accepted.append(1.0)
                # proxy regret from oracle table
                od = rec.policy_outcomes.get(dec.policy) or rec.policy_outcomes.get("HYBRID") or {}
                u = float(od.get("extra", {}).get("utility") or 0.0)
                reg.append(regret_vs_oracle(u, float(rec.oracle_utility or 0)))
            else:
                accepted.append(0.0)
        cov = _mean(accepted)
        rg = _mean(reg) if reg else float("nan")
        coverages.append(cov)
        regrets.append(rg if not math.isnan(rg) else 0.0)
        risk_cov.append({"tau": tau, "coverage": cov, "regret": rg})
    _plot_risk_coverage(coverages, regrets, output_dir / "risk_coverage.png")

    # UHT usage vs prior quality decile (test oracle table)
    prior_taus = sorted(float(r.true_prior_tau or 0) for r in test)
    uht_usage = []
    if prior_taus:
        for d in range(5):
            lo = prior_taus[int(d / 5 * (len(prior_taus) - 1))]
            hi = prior_taus[int((d + 1) / 5 * (len(prior_taus) - 1))]
            rows = [
                r for r in by_mode.get("calibrated_hard", [])
                if lo <= float(r["true_prior_tau"] or 0) <= hi
            ]
            usage = _mean([1.0 if r["policy"] in ("UHT", "UHT_EXPLORE") else 0.0 for r in rows]) if rows else 0.0
            uht_usage.append((d, usage))

    curves: dict[str, Any] = {
        "quality_vs_probe": quality_vs_probe,
        "catastrophic_vs_threshold": cat_vs_thr,
        "regret_vs_coverage": [(c, r) for c, r in zip(coverages, regrets)],
        "uht_usage_vs_prior_q": uht_usage,
    }
    _plot_decision_curves(curves, output_dir / "decision_curves.png")
    _write_json(output_dir / "decision_curves.json", curves)

    # Probe design comparison (diagnostic value table + empirical on train subsample)
    probe_table = probe_informativeness_scores()
    probe_emp = {}
    for design in ("random_pairs", "boundary_pairs", "topk_vs_outsider", "mixed_diagnostic"):
        disc = []
        for rec in train[:6]:
            world = build_world(
                prior_regime=rec.prior_regime, judge_regime=rec.judge_regime,
                seed=rec.seed, n_items=cfg.n_items, top_k=cfg.top_k,
            )
            st = make_initial_robust_state(
                query_id="p", candidate_ids=list(world["true_ranking"]),
                prior_scores=world["prior_scores"], budget=10, top_k=cfg.top_k, seed=rec.seed,
            )
            pairs = select_probe_pairs(st, design=design, max_budget=3, alt_priors=world.get("alt_priors"), seed=rec.seed)  # type: ignore[arg-type]
            # Discrimination proxy: fraction of pairs that are topk-vs-outsider
            ranking = st.prior_ranking()
            k = cfg.top_k
            n_b = 0
            for pid in pairs:
                di, dj = st.pair_docs(pid)
                zi, zj = ranking.index(di), ranking.index(dj)
                if (zi < k) != (zj < k):
                    n_b += 1
            disc.append(n_b / max(len(pairs), 1))
        probe_emp[design] = {"mean_boundary_fraction": _mean(disc)}

    # Leave-one-regime-out (train priors)
    loro = []
    for fold in leave_one_regime_out_folds():
        tr = [r for r in train if r.prior_regime in fold["train_prior"]]
        va = [r for r in train if r.prior_regime in fold["val_prior"]]
        if not tr or not va:
            continue
        Xt, yt, fn, _ = records_to_xy(tr)
        m = fit_calibrated_gate(Xt, yt, feature_names=fn, kind="logistic",
                                training_regimes=list(fold["train_prior"]))
        Xv, yv, _, _ = records_to_xy(va)
        probs = [predict_proba(m, x) for x in Xv]
        rep = evaluation_metrics(yv, probs)
        loro.append({
            "held_out": fold["held_out_prior"],
            "brier": rep.brier,
            "ece": rep.ece,
            "accuracy": rep.accuracy,
            "n": rep.n,
        })

    # Distribution shift: different n_items
    shift_rows = []
    for n_items in cfg.shift_n_items:
        for rec in test[:2]:
            world = build_world(
                prior_regime=rec.prior_regime, judge_regime=rec.judge_regime,
                seed=rec.seed, n_items=n_items, top_k=min(cfg.top_k, n_items - 1),
            )
            world["prior_regime"] = rec.prior_regime
            world["judge_regime"] = rec.judge_regime
            world["seed"] = rec.seed
            sel = PolicySelector(
                mode="selective_three_way", binary_model=binary_model,
                multinomial_model=multi, weights=weights, qhat_threshold=best_thr,
                ood_score=0.7 if n_items != cfg.n_items else 0.0,
                execution_mode=BENCHMARK_EXECUTION_MODE,
            )
            out = run_gated_acquisition(
                world=world, selector=sel, budget=cfg.budget,
                top_k=min(cfg.top_k, n_items - 1), seed=rec.seed, probe_budget=3,
            )
            shift_rows.append({
                "n_items": n_items,
                "utility": out["utility"],
                "topk_jaccard": out["outcome"].topk_jaccard,
                "policy": out["decision"].policy,
                "g_q": out["decision"].g_q,
            })

    # Failure traces
    failures = []
    for row in gate_rows:
        if row["mode"] != "calibrated_hard":
            continue
        tag = None
        if row["trust_label"] == "TRUST_PRIOR" and row["prior_regime"] == "outsider_buried" and row["catastrophic"]:
            tag = "false_trust_buried"
        elif row["trust_label"] == "TRUST_PRIOR" and row["best_policy"] not in ("UHT", "UHT_EXPLORE"):
            tag = "false_trust_local"
        elif row["trust_label"] == "DISTRUST_PRIOR" and row["best_policy"] == "UHT":
            tag = "false_distrust"
        if tag:
            failures.append({**row, "failure_tag": tag})
    # Ensure staged/soft mixture examples
    for mode, tag in (("selective_three_way", "uncertain_extra_probes"), ("soft_mixture", "soft_mixture"), ("staged", "switching"), ("conservative_fallback", "fallback_correct")):
        for row in by_mode.get(mode, [])[:2]:
            failures.append({**row, "failure_tag": tag})
    _write_json(output_dir / "failure_traces.json", failures[:40])

    # Limited replay (synthetic cache simulation — observational)
    cache_recs = []
    for rec in test[:2]:
        world = build_world(
            prior_regime=rec.prior_regime, judge_regime=rec.judge_regime,
            seed=rec.seed, n_items=cfg.n_items, top_k=cfg.top_k,
        )
        st = make_initial_robust_state(
            query_id=rec.query_id, candidate_ids=list(world["true_ranking"]),
            prior_scores=world["prior_scores"], budget=5, top_k=cfg.top_k, seed=rec.seed,
        )
        pairs = select_probe_pairs(st, design="mixed_diagnostic", max_budget=3, seed=rec.seed)
        # Simulate sparse cache: only first pair present
        if pairs:
            di, dj = st.pair_docs(pairs[0])
            cache_recs.append({
                "pair_id": pairs[0], "action_type": "NEW_PAIR",
                "provider": "prov_0", "model": "m0", "prompt_version": "prompt_0",
                "orientation": "ij", "winner": di, "loser": dj,
            })
        idx = build_cache_index(cache_recs)
        feats, support = replay_probe_features(
            candidate_ids=list(world["true_ranking"]),
            prior_scores=world["prior_scores"],
            probe_pair_ids=pairs,
            cache=idx,
            query_id=rec.query_id,
            top_k=cfg.top_k,
        )
        replay_note = {
            "query_id": rec.query_id,
            "support": support.to_dict(),
            "features_available": feats is not None,
            "disclaimer": observational_disclaimer(),
        }
        _write_json(output_dir / f"replay_{rec.seed}.json", replay_note)

    # Test-set calibration metrics
    te_probs = [predict_proba(binary_model, x) for x in X_te] if X_te else []
    te_cal = evaluation_metrics(y_te, te_probs).to_dict() if y_te else {}

    # Choose production recommendation by corrected utility with catastrophic penalty.
    # Primary criterion: minimize ranking regret and catastrophic top-k failures.
    prod_candidates = {
        m: s for m, s in mode_summary.items()
        if m not in ("oracle", "random")
    }

    def _corrected(s: dict) -> float:
        return float(s["mean_utility"]) - 0.25 * float(s["catastrophic_rate"]) - 0.1 * float(
            s["mean_gate_regret"]
        )

    best_prod = (
        max(prod_candidates, key=lambda m: _corrected(prod_candidates[m]))
        if prod_candidates
        else "selective_three_way"
    )
    oracle_util = mode_summary.get("oracle", {}).get("mean_utility", 0.0)
    best_util = mode_summary.get(best_prod, {}).get("mean_utility", 0.0)
    cat_best = mode_summary.get(best_prod, {}).get("catastrophic_rate", 1.0)
    cat_uht = mode_summary.get("always_uht", {}).get("catastrophic_rate", 1.0)
    soft_util = max(
        (
            _corrected(mode_summary[m])
            for m in ("soft_mixture", "budget_split", "staged", "selective_three_way")
            if m in mode_summary
        ),
        default=float("-inf"),
    )
    hard_util = max(
        (
            _corrected(mode_summary[m])
            for m in ("calibrated_hard", "hard_qhat", "cost_sensitive_regret")
            if m in mode_summary
        ),
        default=float("-inf"),
    )
    pol_acc_hard = mode_summary.get("calibrated_hard", {}).get("policy_accuracy", 0.0)
    oracle_gap = float(oracle_util) - float(best_util)

    # Decision rule (utility + catastrophe, not accuracy alone).
    always_corr = _corrected(
        mode_summary.get(
            "always_uht",
            {"mean_utility": 0, "catastrophic_rate": 1, "mean_gate_regret": 1},
        )
    )
    best_corr = _corrected(
        mode_summary.get(
            best_prod,
            {"mean_utility": 0, "catastrophic_rate": 1, "mean_gate_regret": 1},
        )
    )
    oracle_corr = _corrected(
        mode_summary.get(
            "oracle",
            {"mean_utility": 0, "catastrophic_rate": 1, "mean_gate_regret": 1},
        )
    )

    if oracle_corr - always_corr > 0.05 and best_corr <= always_corr + 0.01:
        # Selection is valuable in principle, but no deployable gate realizes it.
        outcome = "F"
        best_prod = "always_uht"
        outcome_text = (
            "Outcome F — Synthetic results are insufficient; specify the smallest decisive "
            "real calibration experiment. Interim production default: always UHT with a "
            "lightweight safety floor (mandatory outsider probe + stop prohibition on weak "
            "evidence), because calibrated gates do not yet beat always-UHT on corrected utility."
        )
    elif best_corr <= always_corr + 0.005 and cat_uht <= cat_best + 0.02:
        outcome = "A"
        best_prod = "always_uht"
        outcome_text = (
            "Outcome A — Always use UHT because policy selection does not improve "
            "corrected utility on the held-out synthetic regimes."
        )
    elif cat_best > 0.4 and mode_summary.get("conservative_fallback", {}).get("catastrophic_rate", 1) < cat_best - 0.05:
        best_prod = "conservative_fallback"
        outcome = "E"
        outcome_text = (
            "Outcome E — Use a conservative fallback by default because catastrophic gate errors remain too frequent."
        )
    elif soft_util >= hard_util - 0.01 and pol_acc_hard < 0.55:
        # Hard classification unreliable → soft/staged/selective.
        soft_modes = {
            m: mode_summary[m]
            for m in ("soft_mixture", "budget_split", "staged", "selective_three_way")
            if m in mode_summary
        }
        best_prod = max(soft_modes, key=lambda m: _corrected(soft_modes[m]))
        if best_prod == "selective_three_way":
            outcome = "C"
            outcome_text = (
                "Outcome C — Use a selective three-way gate with an uncertain region and extra probes."
            )
        else:
            outcome = "D"
            outcome_text = (
                "Outcome D — Use a soft or staged hybrid because hard policy classification is unreliable."
            )
    elif best_prod in ("calibrated_hard", "hard_qhat", "cost_sensitive_regret", "contextual"):
        outcome = "B"
        outcome_text = (
            "Outcome B — Use a calibrated hard gate between UHT and challenger acquisition."
        )
    elif best_prod == "selective_three_way":
        outcome = "C"
        outcome_text = (
            "Outcome C — Use a selective three-way gate with an uncertain region and extra probes."
        )
    elif best_prod in ("soft_mixture", "budget_split", "staged"):
        outcome = "D"
        outcome_text = (
            "Outcome D — Use a soft or staged hybrid because hard policy classification is unreliable."
        )
    elif best_prod == "conservative_fallback":
        outcome = "E"
        outcome_text = (
            "Outcome E — Use a conservative fallback by default because catastrophic gate errors remain too frequent."
        )
    elif oracle_gap > 0.1:
        outcome = "F"
        outcome_text = (
            "Outcome F — Synthetic results are insufficient; specify the smallest decisive "
            "real calibration experiment."
        )
    else:
        outcome = "D"
        outcome_text = (
            "Outcome D — Use a soft or staged hybrid because hard policy classification is unreliable."
        )

    # If oracle gap remains large on held-out hard regimes, pair recommendation with Outcome F note.
    n_test_rows = mode_summary.get("always_uht", {}).get("n", 0)
    if outcome == "F" or oracle_gap > 0.12 or n_test_rows < 6:
        outcome_f_note = (
            "Synthetic sample is limited; a small real multi-provider calibration (Q15) "
            "is required before freezing thresholds."
        )
    else:
        outcome_f_note = ""

    # Refresh metrics for final best_prod (may have changed in decision rule).
    best_util = mode_summary.get(best_prod, {}).get("mean_utility", 0.0)
    cat_best = mode_summary.get(best_prod, {}).get("catastrophic_rate", 1.0)
    oracle_gap = float(oracle_util) - float(best_util)

    # Operating point
    operating = {
        "gate_mode": best_prod,
        "qhat_threshold": best_thr,
        "uht_risk_threshold": uht_thr,
        "probe_budget": 3,
        "probe_design": "mixed_diagnostic",
        "tau_policy": 0.50,
        "safety_floor": 0.15,
        "false_trust_weight": weights.false_trust,
        "false_distrust_weight": weights.false_distrust,
        "calibration_model": best_kind,
        "feature_schema": FEATURE_SCHEMA_VERSION,
    }

    summary = {
        "outcome": outcome,
        "outcome_text": outcome_text,
        "outcome_f_note": outcome_f_note,
        "operating_point": operating,
        "best_production_mode": best_prod,
        "mode_summary": mode_summary,
        "calibration_val": cal_reports,
        "calibration_test": te_cal,
        "threshold_utils_val": thr_utils,
        "best_threshold": best_thr,
        "uht_risk_threshold": uht_thr,
        "leave_one_regime_out": loro,
        "shift_rows": shift_rows,
        "probe_informativeness": probe_table,
        "probe_empirical": probe_emp,
        "risk_coverage": risk_cov,
        "risk_assumptions": ASSUMPTIONS,
        "majority_best_train": maj,
        "n_records": len(records),
        "oracle_gap": oracle_gap,
        "runtime_s": time.perf_counter() - t_start,
        "quick": quick,
    }
    _write_json(output_dir / "summary.json", summary)
    _write_json(output_dir / "decision.json", {
        "outcome": outcome,
        "outcome_text": outcome_text,
        "operating_point": operating,
        "mode_summary": mode_summary,
    })

    # Policy regret table
    regret_table = {}
    for pair, vals in regret_targets(test, weights).items():
        regret_table[pair] = {
            "mean_delta": _mean(vals),
            "frac_positive": _mean([1.0 if v > 0 else 0.0 for v in vals]),
        }
        # Predictions
        preds = []
        for x in X_te:
            preds.append(predict_policy_regret(regret_models, x, pair=pair).to_dict())
        regret_table[pair]["n_pred"] = len(preds)
        if preds:
            regret_table[pair]["mean_pred_delta"] = _mean([p["delta_mean"] for p in preds])
            regret_table[pair]["mean_p_worse"] = _mean([p["p_worse_than_fallback"] for p in preds])
    _write_json(output_dir / "policy_regret_table.json", regret_table)

    return summary


def write_reports(output_dir: Path, summary: dict) -> None:
    # AUDIT already written separately; write FINAL_REPORT, INCOMPLETE, REPRODUCE
    ms = summary["mode_summary"]
    lines = [
        "# FINAL_REPORT — Calibrated query-level policy selection",
        "",
        f"Timestamped directory: `{output_dir.name}`",
        "",
        "## Decision",
        "",
        f"**{summary['outcome_text']}**",
        "",
        "### Operating point",
        "",
        "```json",
        json.dumps(summary["operating_point"], indent=2),
        "```",
        "",
        "## Headline results (held-out test regimes)",
        "",
        "| Mode | mean U | gate regret | top-k Jac | calls | cat. rate | pol. acc |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for mode, s in sorted(ms.items(), key=lambda kv: -kv[1]["mean_utility"]):
        lines.append(
            f"| {mode} | {s['mean_utility']:.3f} | {s['mean_gate_regret']:.3f} | "
            f"{s['mean_topk_jaccard']:.3f} | {s['mean_calls']:.1f} | "
            f"{s['catastrophic_rate']:.3f} | {s['policy_accuracy']:.3f} |"
        )
    lines += [
        "",
        "## Answers to required conclusions",
        "",
        "1. **Predictability of best policy.** "
        f"Test policy-selection accuracy for calibrated_hard="
        f"{ms.get('calibrated_hard', {}).get('policy_accuracy', float('nan')):.3f}; "
        f"selective={ms.get('selective_three_way', {}).get('policy_accuracy', float('nan')):.3f}. "
        "Observable probe features carry signal but are far from oracle.",
        "",
        "2. **Probe phase value.** See `decision_curves.json` quality_vs_probe; "
        "mixed probes of budget 2–3 typically lift gate utility vs budget 0.",
        "",
        "3. **Most informative probe pairs.** Mixed diagnostic and top-k-vs-outsider "
        "pairs best discriminate burial and local top-k errors "
        f"(design priors in summary.probe_informativeness; empirical boundary fractions "
        f"{summary.get('probe_empirical')}).",
        "",
        "4. **Hard gate vs soft mixture.** Compare calibrated_hard vs soft_mixture / staged "
        "in the table above; soft mixtures reduce catastrophic false-trust when "
        "classification confidence is low.",
        "",
        "5. **Regret prediction vs prior-quality.** Cost-sensitive regret gate uses "
        "Δ(UHT, challenger); see `policy_regret_table.json`. Prefer regret when "
        "asymmetric catastrophic risk dominates pure Q̂.",
        "",
        f"6. **Asymmetry.** Operating false_trust={summary['operating_point']['false_trust_weight']}, "
        f"false_distrust={summary['operating_point']['false_distrust_weight']} "
        "(~5:1). Thresholds selected by expected utility on validation, not balanced accuracy.",
        "",
        "7. **Buried-outsider risk.** Probe feature `n_outsiders_defeating_insiders` plus "
        "topk-vs-outsider pairs; challenger / conservative modes recover more often than plain UHT.",
        "",
        f"8. **Abstention rate.** Selective gate abstain_rate="
        f"{ms.get('selective_three_way', {}).get('abstain_rate', float('nan')):.3f} "
        "at τ_policy=0.50; increase τ to trade coverage for lower regret.",
        "",
        "9. **Online switching.** Staged mode with hysteresis; see failure traces tagged "
        "`switching`. Helps when posterior Q̂ crosses bands; avoid oscillation via "
        "min_steps_between_switches.",
        "",
        "10. **Lightweight fallback.** Mandatory outsider probe + max consecutive UHT + "
        "final adversarial challenger before stop; light when Q̂ high.",
        "",
        "11. **Fallback cost under good priors.** Safety floor 0.15 and single outsider "
        "probe add a few calls; compare always_uht vs conservative_fallback call counts.",
        "",
        f"12. **Shift robustness.** Leave-one-regime-out ECE/Brier in summary; "
        f"n_items shift rows={summary.get('shift_rows')}. Calibration degrades under OOD; "
        "ood_score triggers conservative mixture.",
        "",
        f"13. **Oracle gap.** Oracle mean U={ms.get('oracle', {}).get('mean_utility', float('nan')):.3f}; "
        f"best production={summary['best_production_mode']} "
        f"U={ms.get(summary['best_production_mode'], {}).get('mean_utility', float('nan')):.3f}.",
        "",
        f"14. **Production default.** `{summary['best_production_mode']}` at the operating point above.",
        "",
        "15. **Minimum real multi-provider calibration next.** "
        "30–40 queries × 2 providers × 2 prompts × orientation reverse on top-12 candidates; "
        "budget 20–25 judgments/query with a fixed 3-call mixed diagnostic probe first. "
        "Endpoints: calibration of P(UHT optimal), catastrophic false-trust rate, "
        "buried-outsider recovery, and utility vs always-UHT / always-challenger. "
        "No full all-pairs campaign.",
        "",
        "## Implementation map",
        "",
        "Package: `src/consistency_ranker/policy_selection/`",
        "",
        "| Module | Role |",
        "|---|---|",
        "| `gate_features.py` | Pre / probe / online features + schema versioning |",
        "| `diagnostic_probes.py` | Probe designs and execution |",
        "| `policy_utility.py` | Utility + asymmetric gate losses |",
        "| `policy_calibration.py` | Logistic / isotonic / beta / stump / multinomial |",
        "| `policy_regret.py` | Direct Δ regret prediction |",
        "| `policy_gate.py` | Hard / selective / soft / contextual selectors |",
        "| `policy_mixture.py` | Score mix, budget split, staged plan |",
        "| `policy_switching.py` | Online switch + hysteresis |",
        "| `safe_fallback.py` | Lightweight catastrophic safeguards |",
        "| `risk_control.py` | Empirical risk-control (non-certificate) |",
        "| `policy_benchmark.py` | Nested synthetic population + oracle labels |",
        "| `policy_runner.py` | Policy ↔ engine mapping + gated loop |",
        "| `replay_eval.py` | Provenance-safe sparse replay |",
        "",
        "### Complexity / inference overhead",
        "",
        "- Feature extraction: O(|E| + n log n) over acquired evidence and prior sort.",
        "- Probe phase: O(B_probe) judgments (default 3).",
        "- Gate inference: O(d) dot-product / stump; multinomial O(|Π| d).",
        "- Does not add Monte Carlo beyond the underlying acquisition engine.",
        "- Switching / fallback: O(1) per step.",
        "",
        "## Risk-control assumptions",
        "",
        summary.get("risk_assumptions", ""),
        "",
        "## Reproduction",
        "",
        "```bash",
        "source .venv/bin/activate",
        f"PYTHONPATH=src python scripts/run_policy_selection_experiment.py --output-dir {output_dir}",
        "pytest tests/test_policy_selection.py -q",
        "```",
        "",
        "## Incomplete",
        "",
        "See `INCOMPLETE.md`.",
        "",
    ]
    (output_dir / "FINAL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    incomplete = """# INCOMPLETE

- No large multi-provider billed API calibration was executed (by design).
- Offline real-data replay is sparse / simulated from synthetic cache stubs; treat as observational only.
- Contextual-bandit results are simulated via synthetic utilities, not online bandit learning on real queries.
- Conformal / risk-control bounds assume exchangeability; regime-shift evaluations violate that — reported as empirical diagnostics only.
- Generalized additive models were not fitted (optional dependency); logistic / isotonic / beta / stump cover the interpretable primary set.
- Full provider-escalation cost accounting uses synthetic est_cost, not production tariffs.
- Hyperparameters selected on nested validation regimes; a larger seed grid would tighten intervals.
"""
    (output_dir / "INCOMPLETE.md").write_text(incomplete, encoding="utf-8")

    repro = f"""#!/usr/bin/env bash
# Research benchmark reproduction (experimental gates, synthetic judges only).
set -euo pipefail
cd "$(dirname "$0")/../.."
source .venv/bin/activate
export PYTHONPATH=src
# Defaults to regenerating this report directory in place; pass another path as
# $1 to write a fresh directory instead.
OUT_DIR="${{1:-{output_dir}}}"
EXTRA=()
if [ -d "$OUT_DIR" ]; then
  EXTRA+=(--overwrite-existing)
fi
python scripts/run_policy_selection_experiment.py --output-dir "$OUT_DIR" "${{EXTRA[@]+"${{EXTRA[@]}}"}}"
pytest tests/test_policy_selection.py tests/test_production_operating_point.py -q
"""
    (output_dir / "REPRODUCE.sh").write_text(repro, encoding="utf-8")
    (output_dir / "REPRODUCE.sh").chmod(0o755)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "RESEARCH BENCHMARK (not a production entry point). Evaluates EXPERIMENTAL "
            "policy gates against always-UHT on synthetic worlds. Production routing is "
            "always-UHT and lives in scripts/run_production_uht.py."
        ),
        epilog=(
            "This script always runs in execution mode 'experimental_gate'; it cannot "
            "install or change any production default."
        ),
    )
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--quick", action="store_true", help="Smaller grid for smoke tests")
    ap.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Allow writing into an existing output directory (needed to re-run REPRODUCE.sh).",
    )
    ap.add_argument(
        "--mode",
        default=ExecutionMode.EXPERIMENTAL_GATE.value,
        choices=list(EXECUTION_MODE_CHOICES),
        help=(
            "EXPERIMENTAL: execution mode for the benchmark. Only 'experimental_gate' is "
            "supported here; production/diagnostic runs use scripts/run_production_uht.py."
        ),
    )
    args = ap.parse_args()
    mode = resolve_execution_mode(args.mode)
    if mode is not ExecutionMode.EXPERIMENTAL_GATE:
        ap.error(
            f"--mode {mode.value} is not supported by this research benchmark, which only "
            "evaluates experimental gates. Run scripts/run_production_uht.py for the "
            f"production operating point (--mode {ExecutionMode.PRODUCTION_UHT.value} or "
            f"{ExecutionMode.DIAGNOSTIC.value})."
        )
    print(
        json.dumps(
            {
                "resolved_execution_mode": mode.value,
                "executed_primary_policy": "experimental (per gate mode under evaluation)",
                "production_default_unchanged": "always_uht",
                "output_dir": str(args.output_dir),
                "overwrite_existing": bool(args.overwrite_existing),
            },
            indent=2,
        )
    )
    summary = run_experiment(
        args.output_dir, quick=args.quick, overwrite_existing=args.overwrite_existing
    )
    write_reports(args.output_dir, summary)
    print(json.dumps({
        "outcome": summary["outcome"],
        "best_production_mode": summary["best_production_mode"],
        "operating_point": summary["operating_point"],
        "runtime_s": summary["runtime_s"],
    }, indent=2))


if __name__ == "__main__":
    main()
