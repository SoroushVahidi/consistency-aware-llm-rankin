"""Acquisition action space and eligible-action generation.

An action is richer than "compare pair (i, j)": it names the target pair, the
judge (provider / model / prompt / decoding), the display orientation, a cost
proxy, an expected reliability, and a human-readable reason. Every action has a
*billing signature* so the engine can guarantee it never issues a duplicate
billed judgment after a restart.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from consistency_ranker.adaptive_acquisition.acquisition_state import AcquisitionState

ActionType = str

ACTION_TYPES: tuple[str, ...] = (
    "NEW_PAIR",
    "REPEAT_SAME",
    "REVERSE_ORIENTATION",
    "ALTERNATE_PROMPT",
    "ALTERNATE_MODEL",
    "STRONG_MODEL_ADJUDICATION",
    "NO_ACTION",
)


@dataclass(frozen=True)
class JudgeProfile:
    """A declared, addressable judge configuration (provider/model/prompt/decoding).

    ``cost`` is a token-/price-cost proxy (relative units). ``reliability`` is a
    prior expected reliability in ``[0, 1]``. ``strong`` marks escalation judges.
    Uses only identifiers supplied by the caller (no invented model names/prices).
    """

    name: str
    provider: str
    model: str
    prompt_version: str
    temperature: float = 0.0
    top_p: float | None = None
    max_tokens: int = 32
    cost: float = 1.0
    reliability: float = 0.7
    strong: bool = False

    def key(self) -> tuple[str, str, str]:
        return (self.provider, self.model, self.prompt_version)


@dataclass
class Action:
    action_type: ActionType
    pair_id: str
    doc_i: str
    doc_j: str
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    orientation: str = "ab"
    repetition_index: int = 0
    temperature: float = 0.0
    top_p: float | None = None
    max_tokens: int = 32
    est_cost: float = 1.0
    expected_reliability: float = 0.7
    reason: str = ""
    score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)

    def billing_signature(self) -> tuple[str, str, str, str, str, int]:
        return (
            self.pair_id,
            str(self.provider),
            str(self.model),
            str(self.prompt_version),
            str(self.orientation),
            int(self.repetition_index),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _next_repetition_index(
    state: AcquisitionState, pair_id: str, profile: JudgeProfile, orientation: str
) -> int:
    reps = [
        e.repetition_index
        for e in state.evidence_for_pair(pair_id)
        if e.provider == profile.provider
        and e.model == profile.model
        and e.prompt_version == profile.prompt_version
        and e.displayed_orientation == orientation
    ]
    return (max(reps) + 1) if reps else 0


def _pair_profiles_used(state: AcquisitionState, pair_id: str) -> set[tuple[str, str, str]]:
    return {
        (str(e.provider), str(e.model), str(e.prompt_version))
        for e in state.evidence_for_pair(pair_id)
    }


def _dominant_orientation(state: AcquisitionState, pair_id: str, profile: JudgeProfile) -> str:
    """Orientation most used so far for this pair+profile (default 'ab')."""
    counts = {"ab": 0, "ba": 0}
    for e in state.evidence_for_pair(pair_id):
        if e.provider == profile.provider and e.model == profile.model:
            o = str(e.displayed_orientation)
            if o in counts:
                counts[o] += 1
    return "ab" if counts["ab"] >= counts["ba"] else "ba"


def generate_eligible_actions(
    state: AcquisitionState,
    profiles: list[JudgeProfile],
    *,
    strong_profiles: list[JudgeProfile] | None = None,
    include_no_action: bool = True,
    max_repeats_per_signature: int = 3,
) -> list[Action]:
    """Enumerate eligible actions for every pair, deduping billed judgments.

    An action is emitted only if its billing signature has not already been
    executed. REPEAT_SAME advances the repetition index; a signature is capped
    at ``max_repeats_per_signature`` to avoid unbounded repetition.
    """
    if not profiles:
        raise ValueError("At least one JudgeProfile is required")
    default = profiles[0]
    strong_profiles = strong_profiles or [p for p in profiles if p.strong]
    sigs = state.evidence_signatures()
    actions: list[Action] = []

    def _sig_count(pair_id: str, prof: JudgeProfile, orient: str) -> int:
        return sum(
            1
            for (pid, pv, md, pr, o, _rep) in sigs
            if pid == pair_id
            and pv == prof.provider
            and md == prof.model
            and pr == prof.prompt_version
            and o == orient
        )

    for pid in state.all_pair_ids():
        doc_i, doc_j = state.pair_docs(pid)
        ev = state.evidence_for_pair(pid)
        used_profiles = _pair_profiles_used(state, pid)

        if not ev:
            # NEW_PAIR with the cheapest / default judge, both orientations offered.
            for orient in ("ab", "ba"):
                actions.append(
                    _mk(
                        "NEW_PAIR", pid, doc_i, doc_j, default, orient, 0,
                        reason="unqueried_pair",
                    )
                )
            continue

        # REPEAT_SAME on the default (or first used) profile.
        base = default if default.key() in used_profiles else profiles[0]
        base_orient = _dominant_orientation(state, pid, base)
        if _sig_count(pid, base, base_orient) < max_repeats_per_signature:
            rep = _next_repetition_index(state, pid, base, base_orient)
            actions.append(
                _mk("REPEAT_SAME", pid, doc_i, doc_j, base, base_orient, rep,
                    reason="repeat_same_judge")
            )

        # REVERSE_ORIENTATION (opposite of dominant) for each used profile.
        for prof in profiles:
            if prof.key() not in used_profiles:
                continue
            dom = _dominant_orientation(state, pid, prof)
            rev = "ba" if dom == "ab" else "ab"
            rep = _next_repetition_index(state, pid, prof, rev)
            actions.append(
                _mk("REVERSE_ORIENTATION", pid, doc_i, doc_j, prof, rev, rep,
                    reason="check_position_bias")
            )

        # ALTERNATE_PROMPT: same provider/model, a prompt not yet used.
        seen_pm_prompts = {(p, m): set() for (p, m, _pr) in used_profiles}
        for (p, m, pr) in used_profiles:
            seen_pm_prompts.setdefault((p, m), set()).add(pr)
        for prof in profiles:
            pm = (prof.provider, prof.model)
            if pm in seen_pm_prompts and prof.prompt_version not in seen_pm_prompts[pm]:
                actions.append(
                    _mk("ALTERNATE_PROMPT", pid, doc_i, doc_j, prof, "ab", 0,
                        reason="cross_prompt_check")
                )

        # ALTERNATE_MODEL: a provider/model not yet used on this pair.
        used_pm = {(p, m) for (p, m, _pr) in used_profiles}
        for prof in profiles:
            if (prof.provider, prof.model) not in used_pm and not prof.strong:
                actions.append(
                    _mk("ALTERNATE_MODEL", pid, doc_i, doc_j, prof, "ab", 0,
                        reason="cross_model_check")
                )

        # STRONG_MODEL_ADJUDICATION: escalate to a strong judge not yet used.
        for prof in strong_profiles:
            if (prof.provider, prof.model) not in used_pm:
                actions.append(
                    _mk("STRONG_MODEL_ADJUDICATION", pid, doc_i, doc_j, prof, "ab", 0,
                        reason="escalate_disputed_pair")
                )

    if include_no_action:
        actions.append(
            Action(
                action_type="NO_ACTION",
                pair_id="",
                doc_i="",
                doc_j="",
                est_cost=0.0,
                expected_reliability=0.0,
                reason="stop_or_skip",
            )
        )

    # Final dedup by billing signature against already-collected evidence.
    out: list[Action] = []
    seen: set[tuple[str, str, str, str, str, int]] = set()
    for a in actions:
        if a.action_type == "NO_ACTION":
            out.append(a)
            continue
        sig = a.billing_signature()
        if sig in sigs or sig in seen:
            continue
        seen.add(sig)
        out.append(a)
    return out


def _mk(
    action_type: str,
    pair_id: str,
    doc_i: str,
    doc_j: str,
    profile: JudgeProfile,
    orientation: str,
    rep: int,
    *,
    reason: str,
) -> Action:
    return Action(
        action_type=action_type,
        pair_id=pair_id,
        doc_i=doc_i,
        doc_j=doc_j,
        provider=profile.provider,
        model=profile.model,
        prompt_version=profile.prompt_version,
        orientation=orientation,
        repetition_index=rep,
        temperature=profile.temperature,
        top_p=profile.top_p,
        max_tokens=profile.max_tokens,
        est_cost=profile.cost,
        expected_reliability=profile.reliability,
        reason=reason,
    )


__all__ = [
    "Action",
    "ActionType",
    "ACTION_TYPES",
    "JudgeProfile",
    "generate_eligible_actions",
]
