"""Shared multifactor evaluation contract (offline and live).

Relevance quality uses qrels only. Prior agreement is a diagnostic, never truth.
Missing qrels stay missing — never zero-filled, never replaced by the prior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from consistency_ranker.evaluation import kendall_tau, ndcg_at_k
from consistency_ranker.policy_selection.policy_utility import UtilityWeights

# Default cost-adjusted utility: U = nDCG - λ_c * calls - λ_r * catastrophic
DEFAULT_UTILITY_WEIGHTS = UtilityWeights(
    lambda_c=0.01,
    lambda_r=0.5,
    quality_metric="ndcg_at_k",
)

# Stable serialized policy ids → human-readable execution definitions.
POLICY_DEFINITIONS: dict[str, dict[str, str]] = {
    "production_uht": {
        "display_name": "Production UHT (safety floor)",
        "runner": "run_production_uht",
        "safeguards": "yes",
        "role": "primary comparison baseline for multifactor production operating point",
    },
    "plain_uht": {
        "display_name": "Plain named UHT (no production safety floor)",
        "runner": "run_robust_acquisition(policy=UHT) via multifactor harness",
        "safeguards": "no",
        "role": "ablation twin of production_uht without reserved safety actions",
    },
    "UHT": {
        "display_name": "Factorial-experiment UHT",
        "runner": "run_robust_acquisition after mixed_diagnostic probe",
        "safeguards": "no",
        "role": "factorial acquisition arm sharing the probe budget with other policies",
    },
}


@dataclass(frozen=True)
class EvaluationContract:
    """Prespecified evaluation definitions shared by every policy."""

    metric_cutoff_name: str = "effective_depth_top_k"
    relevance_metrics: tuple[str, ...] = ("ndcg_at_k", "mrr_at_k", "recall_at_k")
    agreement_diagnostics: tuple[str, ...] = (
        "prior_kendall_tau",
        "prior_full_pool_membership_jaccard",
    )
    missing_qrels_policy: str = (
        "record relevance metrics as null; exclude from relevance aggregates; "
        "keep cost/execution diagnostics; never substitute prior ranking"
    )
    utility_formula: str = (
        "ndcg_at_k - lambda_c * modeled_acquisition_calls - lambda_r * catastrophic"
    )
    call_cost_semantics: str = (
        "modeled_or_replayed_acquisition_calls_not_new_paid_api_charges"
    )
    lambda_c: float = DEFAULT_UTILITY_WEIGHTS.lambda_c
    lambda_r: float = DEFAULT_UTILITY_WEIGHTS.lambda_r

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_CONTRACT = EvaluationContract()


@dataclass
class RankingEvalResult:
    """Per-ranking evaluation under the shared contract."""

    ndcg_at_k: float | None
    mrr_at_k: float | None
    recall_at_k: float | None
    prior_topk_jaccard: float | None
    prior_kendall_tau: float | None
    relevance_topk_jaccard: float | None
    n_calls: int
    catastrophic: bool
    buried_recovered: bool | None
    utility: float | None
    has_qrels: bool
    missing_qrels_reason: str | None = None
    k: int = 0
    pool_size: int = 0
    n_relevant_in_pool: int = 0
    prior_topk_jaccard_informative: bool = False
    agreement_metric_informative: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_row_fields(self) -> dict[str, Any]:
        return {
            "ndcg_at_k": self.ndcg_at_k,
            "mrr_at_k": self.mrr_at_k,
            "recall_at_k": self.recall_at_k,
            "prior_topk_jaccard": self.prior_topk_jaccard,
            "prior_kendall_tau": self.prior_kendall_tau,
            "prior_topk_jaccard_informative": self.prior_topk_jaccard_informative,
            "agreement_metric_informative": self.agreement_metric_informative,
            # Legacy column: relevance∩top-k overlap — NOT prior agreement.
            "topk_jaccard": self.relevance_topk_jaccard,
            "n_calls": self.n_calls,
            "catastrophic": self.catastrophic if self.has_qrels else None,
            "buried_recovered": self.buried_recovered,
            "utility": self.utility,
            "has_qrels": self.has_qrels,
            "missing_qrels_reason": self.missing_qrels_reason,
            "n_relevant_in_pool": self.n_relevant_in_pool,
            "eval_k": self.k,
            "pool_size": self.pool_size,
        }


def ranking_from_prior(prior: dict[str, float]) -> list[str]:
    return sorted(prior, key=lambda d: (-float(prior[d]), d))


def topk_jaccard(a: list[str], b: list[str], k: int) -> float:
    pred, ref = set(a[:k]), set(b[:k])
    union = len(pred | ref)
    return (len(pred & ref) / union) if union else 0.0


def prior_rank_agreement(
    ranking: list[str],
    prior_ranking: list[str],
    *,
    k: int,
    pool_size: int,
) -> dict[str, Any]:
    """Prior-agreement diagnostics with an explicit informativeness flag.

    When ``k >= pool_size``, top-k set Jaccard compares the full candidate set
    to itself and is always 1.0 for any permutation. That value is *full-pool
    membership agreement*, not ranking equality. Kendall τ over the common
    candidate set remains informative whenever both rankings share the same
    items.
    """
    jacc = topk_jaccard(ranking, prior_ranking, k)
    jacc_informative = bool(pool_size > 0 and k < pool_size)
    tau: float | None = None
    tau_informative = False
    if set(ranking) == set(prior_ranking) and len(ranking) >= 2:
        tau = float(kendall_tau(list(ranking), list(prior_ranking)))
        tau_informative = True
    return {
        "prior_topk_jaccard": jacc,
        "prior_topk_jaccard_informative": jacc_informative,
        "prior_kendall_tau": tau,
        "agreement_metric_informative": bool(tau_informative or jacc_informative),
        "prior_topk_jaccard_note": (
            "full_pool_membership_only_k_ge_pool_size"
            if not jacc_informative
            else "topk_set_overlap_vs_prior"
        ),
    }


def mrr_at_k(ranking: list[str], qrels: dict[str, int], *, k: int) -> float:
    for i, doc in enumerate(ranking[:k]):
        if int(qrels.get(doc, 0)) > 0:
            return 1.0 / float(i + 1)
    return 0.0


def recall_at_k(
    ranking: list[str],
    qrels: dict[str, int],
    *,
    k: int,
    candidate_pool: list[str] | None = None,
) -> float | None:
    pool = set(candidate_pool) if candidate_pool is not None else set(ranking) | set(qrels)
    relevant = {d for d, r in qrels.items() if int(r) > 0 and d in pool}
    if not relevant:
        return None
    hit = relevant & set(ranking[:k])
    return float(len(hit) / len(relevant))


def evaluate_ranking(
    ranking: list[str],
    qrels: dict[str, int] | None,
    *,
    k: int,
    n_calls: int,
    prior_ranking: list[str] | None = None,
    candidate_pool: list[str] | None = None,
    lambda_c: float = DEFAULT_CONTRACT.lambda_c,
    lambda_r: float = DEFAULT_CONTRACT.lambda_r,
    catastrophic: bool | None = None,
    buried_recovered: bool | None = None,
) -> RankingEvalResult:
    """Evaluate one ranking under the shared contract.

    If ``qrels`` is empty/missing, relevance metrics are ``None`` (not 0.0).
    Prior-agreement fields are diagnostics only; when ``k >= pool_size``,
    ``prior_topk_jaccard`` is marked uninformative.
    """
    pool = list(candidate_pool) if candidate_pool is not None else list(ranking)
    pool_size = len(pool)
    qrels = dict(qrels or {})
    pool_set = set(pool)
    qrels_pool = {d: int(r) for d, r in qrels.items() if d in pool_set}
    rel = {d for d, r in qrels_pool.items() if r > 0}
    has_qrels = bool(rel)
    missing_reason = None if has_qrels else (
        "no_positive_qrels_in_candidate_pool" if qrels else "qrels_unavailable"
    )

    if prior_ranking is not None:
        agree = prior_rank_agreement(
            ranking, prior_ranking, k=k, pool_size=pool_size
        )
    else:
        agree = {
            "prior_topk_jaccard": None,
            "prior_topk_jaccard_informative": False,
            "prior_kendall_tau": None,
            "agreement_metric_informative": False,
            "prior_topk_jaccard_note": "prior_ranking_not_provided",
        }

    if not has_qrels:
        return RankingEvalResult(
            ndcg_at_k=None,
            mrr_at_k=None,
            recall_at_k=None,
            prior_topk_jaccard=agree["prior_topk_jaccard"],
            prior_kendall_tau=agree["prior_kendall_tau"],
            relevance_topk_jaccard=None,
            n_calls=int(n_calls),
            catastrophic=False,
            buried_recovered=None,
            utility=None,
            has_qrels=False,
            missing_qrels_reason=missing_reason,
            k=int(k),
            pool_size=pool_size,
            n_relevant_in_pool=0,
            prior_topk_jaccard_informative=bool(agree["prior_topk_jaccard_informative"]),
            agreement_metric_informative=bool(agree["agreement_metric_informative"]),
            extra={"prior_topk_jaccard_note": agree["prior_topk_jaccard_note"]},
        )

    ndcg = float(ndcg_at_k(ranking, qrels_pool, k=k))
    mrr = float(mrr_at_k(ranking, qrels_pool, k=k))
    recall = recall_at_k(ranking, qrels_pool, k=k, candidate_pool=pool)
    top = set(ranking[:k])
    rel_jacc = (len(top & rel) / len(top | rel)) if (top or rel) else 0.0
    if catastrophic is None:
        catastrophic = bool(rel) and not (top & rel) and bool(rel & pool_set)
    if buried_recovered is None and rel:
        buried_recovered = bool(top & rel)

    utility = float(
        ndcg - lambda_c * float(n_calls) - lambda_r * (1.0 if catastrophic else 0.0)
    )
    return RankingEvalResult(
        ndcg_at_k=ndcg,
        mrr_at_k=mrr,
        recall_at_k=recall,
        prior_topk_jaccard=agree["prior_topk_jaccard"],
        prior_kendall_tau=agree["prior_kendall_tau"],
        relevance_topk_jaccard=float(rel_jacc),
        n_calls=int(n_calls),
        catastrophic=bool(catastrophic),
        buried_recovered=buried_recovered,
        utility=utility,
        has_qrels=True,
        missing_qrels_reason=None,
        k=int(k),
        pool_size=pool_size,
        n_relevant_in_pool=len(rel),
        prior_topk_jaccard_informative=bool(agree["prior_topk_jaccard_informative"]),
        agreement_metric_informative=bool(agree["agreement_metric_informative"]),
        extra={
            "lambda_c": lambda_c,
            "lambda_r": lambda_r,
            "utility_formula": DEFAULT_CONTRACT.utility_formula,
            "call_cost_semantics": DEFAULT_CONTRACT.call_cost_semantics,
            "prior_topk_jaccard_note": agree["prior_topk_jaccard_note"],
        },
    )


def mean_with_denominator(values: list[float | None]) -> dict[str, float | int | None]:
    valid = [float(v) for v in values if v is not None]
    return {
        "mean": (sum(valid) / len(valid)) if valid else None,
        "n_valid": len(valid),
        "n_total": len(values),
        "n_missing": len(values) - len(valid),
    }
