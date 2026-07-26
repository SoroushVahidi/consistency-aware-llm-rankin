"""Limited provenance-safe offline replay for gate features / policy support.

Does not impute missing judgments from qrels. Reports coverage and skips
unevaluable policy choices. Two-query pilots are observational only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReplaySupport:
    n_cached_actions: int = 0
    n_requested: int = 0
    n_hits: int = 0
    coverage: float = 0.0
    unevaluable_policies: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_cached_actions": self.n_cached_actions,
            "n_requested": self.n_requested,
            "n_hits": self.n_hits,
            "coverage": self.coverage,
            "unevaluable_policies": list(self.unevaluable_policies),
            "notes": list(self.notes),
        }


def action_key(action: dict[str, Any]) -> str:
    return "|".join(
        str(action.get(k, ""))
        for k in ("pair_id", "action_type", "provider", "model", "prompt_version", "orientation")
    )


def build_cache_index(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index provenance-safe cached judgments by action key."""
    idx: dict[str, dict[str, Any]] = {}
    for rec in records:
        # Accept either NormalizedEvidence-like dicts or action+outcome rows.
        if "pair_id" in rec:
            key = action_key(rec)
            idx[key] = rec
        elif "action" in rec and isinstance(rec["action"], dict):
            key = action_key(rec["action"])
            idx[key] = rec
    return idx


def replay_probe_features(
    *,
    candidate_ids: list[str],
    prior_scores: dict[str, float],
    probe_pair_ids: list[str],
    cache: dict[str, dict[str, Any]],
    query_id: str = "replay_q",
    top_k: int = 3,
    budget: int = 20,
    seed: int = 0,
) -> tuple[dict[str, Any] | None, ReplaySupport]:
    """Build probe-stage features using only cache hits. No qrel imputation."""
    from consistency_ranker.policy_selection.gate_features import extract_features
    from consistency_ranker.prior_robust import make_initial_robust_state
    from consistency_ranker.reliability_repair.pair_evidence import preference_from_simple

    support = ReplaySupport(n_cached_actions=len(cache), n_requested=len(probe_pair_ids))
    st = make_initial_robust_state(
        query_id=query_id,
        candidate_ids=candidate_ids,
        prior_scores=prior_scores,
        budget=budget,
        top_k=top_k,
        seed=seed,
    )
    for pid in probe_pair_ids:
        # Find any cache entry for this pair (provider/prompt may vary).
        hits = [v for k, v in cache.items() if k.startswith(pid + "|") or v.get("pair_id") == pid]
        if not hits:
            support.notes.append(f"missing_probe:{pid}")
            continue
        hit = hits[0]
        support.n_hits += 1
        # Reconstruct minimal evidence if winner/loser present.
        winner = hit.get("winner") or hit.get("preferred")
        loser = hit.get("loser")
        if winner and loser:
            st.add_evidence(
                [
                    preference_from_simple(
                        query_id=query_id, winner=str(winner), loser=str(loser)
                    )
                ]
            )
            st.remaining_budget -= 1
        else:
            support.notes.append(f"incomplete_cache:{pid}")
    support.coverage = support.n_hits / max(support.n_requested, 1)
    if support.n_hits == 0:
        support.notes.append("no_probe_support; gate features pre-only")
        feats = extract_features(st, stage="pre")
        return feats.to_dict(), support
    feats = extract_features(st, stage="probe")
    return feats.to_dict(), support


def evaluate_policy_under_replay(
    *,
    policy: str,
    requested_actions: list[dict[str, Any]],
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Check whether a policy's action sequence is supported by the cache."""
    hits = misses = 0
    for a in requested_actions:
        if action_key(a) in cache:
            hits += 1
        else:
            # pair-level soft match
            pid = a.get("pair_id")
            if pid and any(k.startswith(str(pid) + "|") for k in cache):
                hits += 1
            else:
                misses += 1
    total = hits + misses
    return {
        "policy": policy,
        "n_requested": total,
        "n_hits": hits,
        "n_misses": misses,
        "coverage": hits / total if total else 0.0,
        "evaluable": misses == 0 and total > 0,
        "note": "observational_only_if_sparse",
    }


def observational_disclaimer() -> str:
    return (
        "Provenance-safe replay with few queries is observational only. "
        "Do not claim real-world gate accuracy from two-query pilots. "
        "Missing actions are never imputed from qrels."
    )


__all__ = [
    "ReplaySupport",
    "action_key",
    "build_cache_index",
    "replay_probe_features",
    "evaluate_policy_under_replay",
    "observational_disclaimer",
]
