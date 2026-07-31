"""Observable bias diagnostics and counter-bias action suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from consistency_ranker.adaptive_acquisition.acquisition_actions import Action, JudgeProfile
from consistency_ranker.prior_robust.shared_bias import effective_judge_count

if TYPE_CHECKING:
    from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState


@dataclass
class BiasDiagnostic:
    position_bias_score: float
    orientation_disagreement_rate: float
    prompt_disagreement_rate: float
    model_disagreement_rate: float
    n_effective_judges: float
    n_judges: int
    suspected: list[str]
    detail: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_bias_score": self.position_bias_score,
            "orientation_disagreement_rate": self.orientation_disagreement_rate,
            "prompt_disagreement_rate": self.prompt_disagreement_rate,
            "model_disagreement_rate": self.model_disagreement_rate,
            "n_effective_judges": self.n_effective_judges,
            "n_judges": self.n_judges,
            "suspected": list(self.suspected),
            "detail": dict(self.detail),
        }


def diagnose_bias(state: "AcquisitionState") -> BiasDiagnostic:
    """Estimate bias signals from acquired evidence only (no qrels)."""
    # Position bias: among oriented judgments, fraction preferring displayed A.
    prefer_a = total_orient = 0
    for e in state.evidence:
        if e.z == 0 or not e.displayed_orientation:
            continue
        total_orient += 1
        # z=+1 means canonical doc_i preferred. Map to displayed A preference.
        # orientation ab: A=doc_i (if doc order matches display) — we approximate:
        # if orientation=='ab', displayed A is the first shown; without raw display
        # ids we use: ab → prefer lower-id when z=+1 as 'A preference' proxy via
        # whether z matches orientation convention from normalization.
        # Prefer displayed A if (orient=='ab' and z=+1) or (orient=='ba' and z=-1)
        # under canonical doc_i < doc_j with ab showing doc_i as A.
        if e.displayed_orientation == "ab" and e.z == 1:
            prefer_a += 1
        elif e.displayed_orientation == "ba" and e.z == -1:
            prefer_a += 1
    pos = (prefer_a / total_orient) if total_orient else 0.5
    # Deviation from 0.5 indicates position bias.
    pos_score = float(abs(pos - 0.5) * 2.0)

    orient_dis = prompt_dis = model_dis = 0
    n_pairs = 0
    for pid, agg in state.aggregates.items():
        if agg.n_valid_directional < 2:
            continue
        n_pairs += 1
        f = agg.features
        if float(f.get("orientation_agreement", 1.0)) < 0.999:
            orient_dis += 1
        if float(f.get("prompt_agreement", 1.0)) < 0.999:
            prompt_dis += 1
        if float(f.get("model_agreement", 1.0)) < 0.999:
            model_dis += 1
    denom = max(n_pairs, 1)
    eff = effective_judge_count(state.evidence)

    suspected = []
    if pos_score >= 0.4 and total_orient >= 6:
        suspected.append("position_bias")
    if orient_dis / denom >= 0.5 and n_pairs >= 3:
        suspected.append("orientation_inconsistency")
    if (
        eff["n_effective"] < max(1.5, 0.5 * eff["n_judges"])
        and eff["n_judges"] >= 3
        and eff.get("n_corr_pairs", 0) >= 2
    ):
        suspected.append("correlated_judges")
    if prompt_dis / denom >= 0.5 and n_pairs >= 3:
        suspected.append("prompt_bias")

    return BiasDiagnostic(
        position_bias_score=pos_score,
        orientation_disagreement_rate=orient_dis / denom,
        prompt_disagreement_rate=prompt_dis / denom,
        model_disagreement_rate=model_dis / denom,
        n_effective_judges=float(eff["n_effective"]),
        n_judges=int(eff["n_judges"]),
        suspected=suspected,
        detail={"prefer_displayed_a_rate": pos, "eff": eff},
    )


def suggest_counter_bias_actions(
    state: "AcquisitionState",
    diagnostic: BiasDiagnostic,
    eligible: list[Action],
    profiles: list[JudgeProfile],
) -> list[tuple[Action, str]]:
    """Pick counter-bias actions from the eligible set with motivating hypotheses."""
    out: list[tuple[Action, str]] = []
    if (
        "position_bias" in diagnostic.suspected
        or "orientation_inconsistency" in diagnostic.suspected
    ):
        for a in eligible:
            if a.action_type == "REVERSE_ORIENTATION":
                out.append((a, "test_position_bias"))
                break
    if "prompt_bias" in diagnostic.suspected:
        for a in eligible:
            if a.action_type == "ALTERNATE_PROMPT":
                out.append((a, "test_prompt_bias"))
                break
    if "correlated_judges" in diagnostic.suspected:
        for a in eligible:
            if a.action_type in ("ALTERNATE_MODEL", "STRONG_MODEL_ADJUDICATION"):
                out.append((a, "diversify_provider_family"))
                break
    return out


__all__ = ["BiasDiagnostic", "diagnose_bias", "suggest_counter_bias_actions"]
