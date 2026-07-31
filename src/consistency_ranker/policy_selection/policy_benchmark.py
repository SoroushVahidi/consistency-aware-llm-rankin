"""Synthetic policy-selection benchmark with nested train/val/test regimes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from consistency_ranker.policy_selection.gate_features import (
    feature_names_for_stage,
    features_to_vector,
)
from consistency_ranker.policy_selection.policy_gate import ALL_POLICIES, PolicyName
from consistency_ranker.policy_selection.policy_runner import run_named_policy
from consistency_ranker.policy_selection.policy_utility import (
    PolicyOutcome,
    UtilityWeights,
    compute_utility,
)
from consistency_ranker.prior_robust import AdversarialScenario, make_adversarial_world

SplitName = Literal["train", "val", "test"]

# Nested design: disjoint prior/judge regime sets.
# Burial / deceptive-margin failures are held out to test (not train) so
# catastrophic false-trust risk is measurable on deployment-like regimes.
TRAIN_PRIOR = ("accurate", "noisy", "reversed_topk", "block_permute_topk")
VAL_PRIOR = ("overconfident_wrong", "shared_failure_priors")
TEST_PRIOR = ("outsider_buried", "tail_ok_topk_wrong", "diverse_priors")

TRAIN_JUDGE = ("clean", "shared_position_bias")
VAL_JUDGE = ("stable_wrong_consensus",)
TEST_JUDGE = ("nontransitive", "correlated_repeats")

# Candidate policies evaluated per query for oracle / supervised targets.
EVAL_POLICIES: tuple[PolicyName, ...] = (
    "UHT",
    "UHT_EXPLORE",
    "CHALLENGER",
    "ROBUST_COMBINED",
    "BROAD_STATIC",
    "NO_PRIOR",
    "HYBRID",
)


@dataclass
class PolicyBenchmarkConfig:
    n_items: int = 8
    top_k: int = 3
    budget: int = 18
    train_seeds: tuple[int, ...] = (0, 1, 2, 3)
    val_seeds: tuple[int, ...] = (10, 11)
    test_seeds: tuple[int, ...] = (20, 21)
    weights: UtilityWeights = field(default_factory=UtilityWeights)
    # Held-out corruption / parameter ranges for shift tests.
    shift_n_items: tuple[int, ...] = (6, 10)
    shift_budgets: tuple[int, ...] = (12, 24)


@dataclass
class QueryRecord:
    query_id: str
    split: SplitName
    prior_regime: str
    judge_regime: str
    seed: int
    n_items: int
    budget: int
    world_meta: dict[str, Any]
    features_pre: dict[str, Any] | None = None
    features_probe: dict[str, Any] | None = None
    policy_outcomes: dict[str, dict[str, Any]] = field(default_factory=dict)
    best_policy: str | None = None
    oracle_utility: float | None = None
    true_prior_tau: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "split": self.split,
            "prior_regime": self.prior_regime,
            "judge_regime": self.judge_regime,
            "seed": self.seed,
            "n_items": self.n_items,
            "budget": self.budget,
            "world_meta": dict(self.world_meta),
            "features_pre": self.features_pre,
            "features_probe": self.features_probe,
            "policy_outcomes": dict(self.policy_outcomes),
            "best_policy": self.best_policy,
            "oracle_utility": self.oracle_utility,
            "true_prior_tau": self.true_prior_tau,
        }


def nested_split_regimes() -> dict[str, dict[str, tuple[str, ...]]]:
    return {
        "train": {"prior": TRAIN_PRIOR, "judge": TRAIN_JUDGE},
        "val": {"prior": VAL_PRIOR, "judge": VAL_JUDGE},
        "test": {"prior": TEST_PRIOR, "judge": TEST_JUDGE},
    }


def leave_one_regime_out_folds() -> list[dict[str, Any]]:
    """Each fold holds out one prior regime from the train set."""
    folds = []
    for held in TRAIN_PRIOR:
        folds.append(
            {
                "held_out_prior": held,
                "train_prior": tuple(p for p in TRAIN_PRIOR if p != held),
                "val_prior": (held,),
            }
        )
    return folds


def _true_prior_kendall(true_ranking: list[str], prior: dict[str, float]) -> float:
    from consistency_ranker.evaluation import kendall_tau

    prior_rank = sorted(prior, key=lambda d: (-float(prior[d]), d))
    return float(kendall_tau(true_ranking, prior_rank))


def build_world(
    *,
    prior_regime: str,
    judge_regime: str,
    seed: int,
    n_items: int,
    top_k: int,
) -> dict[str, Any]:
    sc = AdversarialScenario(
        name=f"{prior_regime}|{judge_regime}",
        prior_regime=prior_regime,  # type: ignore[arg-type]
        judge_regime=judge_regime,  # type: ignore[arg-type]
        n_items=n_items,
        top_k=top_k,
        seed=seed,
    )
    return make_adversarial_world(sc)


def evaluate_policies_on_query(
    world: dict[str, Any],
    *,
    policies: tuple[PolicyName, ...] = EVAL_POLICIES,
    budget: int,
    top_k: int,
    seed: int,
    weights: UtilityWeights | None = None,
) -> dict[str, PolicyOutcome]:
    """Run every candidate policy (fresh world clone via re-seeded judge state).

    Each policy gets an independent world rebuild so interactive judges do not
    leak outcomes across policies.
    """
    w = weights or UtilityWeights()
    out: dict[str, PolicyOutcome] = {}
    meta = {
        "prior_regime": world.get("prior_regime"),
        "judge_regime": world.get("judge_regime"),
        "true_ranking": world["true_ranking"],
        "prior_scores": world["prior_scores"],
        "alt_priors": world.get("alt_priors") or [],
        "seed": world.get("seed", seed),
        "n_items": len(world["true_ranking"]),
        "top_k": top_k,
    }
    for i, pol in enumerate(policies):
        # Rebuild world so each policy sees a fresh interactive judge.
        sc = AdversarialScenario(
            name="cell",
            prior_regime=meta["prior_regime"],  # type: ignore[arg-type]
            judge_regime=meta["judge_regime"],  # type: ignore[arg-type]
            n_items=meta["n_items"],
            top_k=top_k,
            seed=int(meta["seed"]),
        )
        wld = make_adversarial_world(sc)
        _, outcome = run_named_policy(
            policy=pol,
            world=wld,
            budget=budget,
            top_k=top_k,
            seed=seed + 17 * i,
            query_id=f"q_{seed}_{pol}",
        )
        outcome.extra["utility"] = compute_utility(outcome, w)
        out[pol] = outcome
    return out


def _attach_features(record: QueryRecord, world: dict[str, Any], top_k: int, seed: int) -> None:
    from consistency_ranker.adaptive_acquisition import synthetic_roster
    from consistency_ranker.policy_selection.diagnostic_probes import (
        ProbeConfig,
        run_diagnostic_probes,
    )
    from consistency_ranker.policy_selection.gate_features import extract_features
    from consistency_ranker.prior_robust import make_initial_robust_state

    st = make_initial_robust_state(
        query_id=record.query_id,
        candidate_ids=list(world["true_ranking"]),
        prior_scores=world["prior_scores"],
        budget=record.budget,
        top_k=top_k,
        seed=seed,
    )
    pre = extract_features(st, stage="pre", alt_priors=world.get("alt_priors"))
    record.features_pre = pre.to_dict()
    profiles = synthetic_roster(n_models=2, n_prompts=1)
    run_diagnostic_probes(
        st,
        profiles,
        world["judge"],
        cfg=ProbeConfig(design="mixed_diagnostic", max_budget=3),
        alt_priors=world.get("alt_priors"),
        seed=seed,
    )
    probe = extract_features(st, stage="probe", alt_priors=world.get("alt_priors"))
    record.features_probe = probe.to_dict()


def build_synthetic_population(
    cfg: PolicyBenchmarkConfig | None = None,
    *,
    include_policy_outcomes: bool = True,
    max_queries: int | None = None,
) -> list[QueryRecord]:
    """Generate nested train/val/test query population with oracle labels."""
    cfg = cfg or PolicyBenchmarkConfig()
    splits = nested_split_regimes()
    seed_map = {"train": cfg.train_seeds, "val": cfg.val_seeds, "test": cfg.test_seeds}
    records: list[QueryRecord] = []
    for split, regimes in splits.items():
        for prior in regimes["prior"]:
            for judge in regimes["judge"]:
                for seed in seed_map[split]:
                    if max_queries is not None and len(records) >= max_queries:
                        return records
                    world = build_world(
                        prior_regime=prior,
                        judge_regime=judge,
                        seed=seed,
                        n_items=cfg.n_items,
                        top_k=cfg.top_k,
                    )
                    world["prior_regime"] = prior
                    world["judge_regime"] = judge
                    world["seed"] = seed
                    qid = f"{split}|{prior}|{judge}|{seed}"
                    rec = QueryRecord(
                        query_id=qid,
                        split=split,  # type: ignore[arg-type]
                        prior_regime=prior,
                        judge_regime=judge,
                        seed=seed,
                        n_items=cfg.n_items,
                        budget=cfg.budget,
                        world_meta={
                            "alt_n": len(world.get("alt_priors") or []),
                        },
                        true_prior_tau=_true_prior_kendall(
                            world["true_ranking"], world["prior_scores"]
                        ),
                    )
                    _attach_features(rec, world, cfg.top_k, seed)
                    if include_policy_outcomes:
                        # Fresh world for policy eval (probe above consumed judgments).
                        world2 = build_world(
                            prior_regime=prior,
                            judge_regime=judge,
                            seed=seed,
                            n_items=cfg.n_items,
                            top_k=cfg.top_k,
                        )
                        world2["prior_regime"] = prior
                        world2["judge_regime"] = judge
                        world2["seed"] = seed
                        outcomes = evaluate_policies_on_query(
                            world2,
                            budget=cfg.budget,
                            top_k=cfg.top_k,
                            seed=seed,
                            weights=cfg.weights,
                        )
                        rec.policy_outcomes = {p: o.to_dict() for p, o in outcomes.items()}
                        utils = {
                            p: float(o.extra.get("utility", compute_utility(o, cfg.weights)))
                            for p, o in outcomes.items()
                        }
                        best = max(utils, key=lambda k: utils[k])
                        rec.best_policy = best
                        rec.oracle_utility = utils[best]
                    records.append(rec)
    return records


def records_to_xy(
    records: list[QueryRecord],
    *,
    stage: str = "probe",
    target: str = "uht_optimal",
) -> tuple[list[list[float]], list[float], list[str], list[str]]:
    """Build (X, y, feature_names, query_ids) without exposing truth features."""
    from consistency_ranker.policy_selection.gate_features import FeatureBundle

    names = feature_names_for_stage("probe")
    X, y, qids = [], [], []
    for rec in records:
        raw = rec.features_probe if stage == "probe" else rec.features_pre
        if not raw:
            continue
        bundle = FeatureBundle.from_dict(raw)
        x = features_to_vector(bundle, stage="probe")
        if len(x) < len(names):
            x = x + [0.0] * (len(names) - len(x))
        x = x[: len(names)]
        if target == "uht_optimal":
            label = 1.0 if rec.best_policy == "UHT" else 0.0
        elif target == "best_is_challenger":
            label = 1.0 if rec.best_policy == "CHALLENGER" else 0.0
        else:
            label = 1.0 if rec.best_policy == target else 0.0
        X.append(x)
        y.append(label)
        qids.append(rec.query_id)
    return X, y, names, qids


def _outcome_utility(odict: dict[str, Any], weights: UtilityWeights) -> float:
    if odict.get("extra", {}).get("utility") is not None:
        return float(odict["extra"]["utility"])
    oc = PolicyOutcome(
        policy=str(odict.get("policy", "?")),
        kendall_tau=odict.get("kendall_tau"),
        topk_jaccard=odict.get("topk_jaccard"),
        n_calls=int(odict.get("n_calls") or 0),
        total_cost=float(odict.get("total_cost") or 0.0),
        catastrophic=bool(odict.get("catastrophic")),
        stable_but_wrong=bool(odict.get("stable_but_wrong")),
    )
    return compute_utility(oc, weights)


def regret_targets(
    records: list[QueryRecord],
    weights: UtilityWeights | None = None,
) -> dict[str, list[float]]:
    w = weights or UtilityWeights()
    pairs = {
        "UHT_vs_CHALLENGER": ("UHT", "CHALLENGER"),
        "UHT_vs_HYBRID": ("UHT", "HYBRID"),
        "ROBUST_vs_BROAD": ("ROBUST_COMBINED", "BROAD_STATIC"),
    }
    out: dict[str, list[float]] = {k: [] for k in pairs}
    for rec in records:
        for name, (p1, p2) in pairs.items():
            o1 = rec.policy_outcomes.get(p1)
            o2 = rec.policy_outcomes.get(p2)
            if not o1 or not o2:
                out[name].append(0.0)
                continue
            out[name].append(_outcome_utility(o1, w) - _outcome_utility(o2, w))
    return out


def majority_best_policy(records: list[QueryRecord]) -> PolicyName:
    from collections import Counter

    c = Counter(r.best_policy for r in records if r.best_policy)
    if not c:
        return "UHT"
    return c.most_common(1)[0][0]  # type: ignore[return-value]


__all__ = [
    "PolicyBenchmarkConfig",
    "QueryRecord",
    "EVAL_POLICIES",
    "ALL_POLICIES",
    "nested_split_regimes",
    "leave_one_regime_out_folds",
    "build_world",
    "evaluate_policies_on_query",
    "build_synthetic_population",
    "records_to_xy",
    "regret_targets",
    "majority_best_policy",
]
