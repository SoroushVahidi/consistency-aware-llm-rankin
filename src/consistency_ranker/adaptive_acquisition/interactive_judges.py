"""Interactive synthetic judge for fair evaluation of adaptive policies.

Crucially, a judgment is produced **only** when the policy requests a specific
action (pair + orientation + provider/model/prompt + repetition). The policy can
never observe the outcome of an action it did not select, so adaptive and static
policies are compared on equal footing.

Supported effects: latent ground-truth strengths (Bradley–Terry pair
probabilities), non-transitivity, position/prompt bias, per-provider accuracy,
per-model calibration, correlated repeat errors, item/pair/top-k-boundary
difficulty, ties, abstentions, invalid outputs, missing providers, and per-judge
cost.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field

from consistency_ranker.reliability_repair.pair_evidence import NormalizedEvidence


def _hash_seed(*parts: object) -> int:
    h = hashlib.sha256("::".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:12], 16)


@dataclass
class InteractiveJudgeConfig:
    n_items: int = 8
    beta: float = 1.2  # BT sharpness on latent strengths
    base_accuracy: float = 0.8
    position_bias: float = 0.08
    prompt_bias: dict[str, float] = field(default_factory=dict)
    provider_accuracy: dict[str, float] = field(default_factory=dict)
    model_calibration: dict[str, float] = field(default_factory=dict)
    systematic_error_rate: float = 0.05  # correlated per (pair,provider,model,prompt)
    tie_rate: float = 0.04
    abstain_rate: float = 0.02
    invalid_rate: float = 0.02
    topk_harder: int = 3
    topk_difficulty_penalty: float = 0.12
    available_providers: tuple[str, ...] | None = None  # None = all available
    strong_provider: str = "strong"
    strong_accuracy: float = 0.95
    non_transitivity: float = 0.0  # prob a pair's truth is locally flipped
    seed: int = 0


@dataclass
class InteractiveJudge:
    latent_strength: dict[str, float]
    config: InteractiveJudgeConfig
    true_ranking: list[str] = field(default_factory=list)
    calls: int = 0
    total_cost: float = 0.0

    def __post_init__(self) -> None:
        if not self.true_ranking:
            self.true_ranking = sorted(
                self.latent_strength, key=lambda d: (-self.latent_strength[d], d)
            )
        self._true_rank = {d: i + 1 for i, d in enumerate(self.true_ranking)}

    # ---- probability model -------------------------------------------
    def _bt_prob_i_beats_j(self, doc_i: str, doc_j: str) -> float:
        si = self.latent_strength.get(doc_i, 0.0)
        sj = self.latent_strength.get(doc_j, 0.0)
        return 1.0 / (1.0 + math.exp(-self.config.beta * (si - sj)))

    def _accuracy(self, provider: str | None, model: str | None, doc_i: str, doc_j: str) -> float:
        cfg = self.config
        if provider == cfg.strong_provider:
            acc = cfg.strong_accuracy
        else:
            acc = cfg.base_accuracy
            acc *= cfg.provider_accuracy.get(str(provider), 1.0)
            acc *= cfg.model_calibration.get(str(model), 1.0)
        ri = self._true_rank.get(doc_i, 99)
        rj = self._true_rank.get(doc_j, 99)
        hard = ri <= cfg.topk_harder or rj <= cfg.topk_harder
        if hard:
            acc -= cfg.topk_difficulty_penalty
        return float(max(0.5, min(0.999, acc)))

    def available(self, action) -> bool:
        """Whether this judge can execute ``action`` (provider reachable)."""
        cfg = self.config
        if getattr(action, "action_type", None) == "NO_ACTION":
            return False
        provider = action.provider
        if (
            cfg.available_providers is not None
            and provider not in cfg.available_providers
            and provider != cfg.strong_provider
        ):
            return False
        return True

    # ---- main entry ---------------------------------------------------
    def judge(self, action) -> NormalizedEvidence | None:
        """Return a normalized judgment for ``action`` or ``None`` if unavailable."""
        cfg = self.config
        if action.action_type == "NO_ACTION":
            return None
        provider = action.provider
        if (
            cfg.available_providers is not None
            and provider not in cfg.available_providers
            and provider != cfg.strong_provider
        ):
            return None  # missing provider

        doc_i, doc_j = action.doc_i, action.doc_j
        # canonical ordering guaranteed by action generation (doc_i < doc_j)
        rng_call = random.Random(
            _hash_seed(
                cfg.seed, action.pair_id, provider, action.model,
                action.prompt_version, action.orientation, action.repetition_index,
            )
        )
        # systematic (correlated) component shared across repeats/orientations
        rng_sys = random.Random(
            _hash_seed(
                cfg.seed, "sys", action.pair_id, provider,
                action.model, action.prompt_version,
            )
        )
        self.calls += 1
        self.total_cost += float(action.est_cost)

        # invalid / abstain draws
        if rng_call.random() < cfg.invalid_rate:
            return self._record(action, z=0, subtype="invalid", valid=False, raw="INVALID")
        if rng_call.random() < (cfg.tie_rate + cfg.abstain_rate):
            sub = "tie" if rng_call.random() < 0.5 else "insufficient_information"
            return self._record(action, z=0, subtype=sub, valid=True, raw="TIE")

        p_i = self._bt_prob_i_beats_j(doc_i, doc_j)
        # non-transitivity: occasionally the local truth is flipped
        if cfg.non_transitivity > 0 and rng_sys.random() < cfg.non_transitivity:
            p_i = 1.0 - p_i
        acc = self._accuracy(provider, action.model, doc_i, doc_j)
        # sharpen/soften belief toward accuracy
        p_correct_dir = p_i * acc + (1 - p_i) * (1 - acc)

        # systematic error: this judge consistently biased on this pair
        systematic_flip = rng_sys.random() < cfg.systematic_error_rate

        # decide winner (doc_i preferred?)
        prefer_i = rng_call.random() < p_correct_dir
        if systematic_flip:
            prefer_i = not prefer_i

        # position bias: prob prefer the displayed-A document
        prompt_pb = cfg.prompt_bias.get(str(action.prompt_version), 0.0)
        pb = cfg.position_bias + prompt_pb
        if pb > 0 and rng_call.random() < pb:
            shown_a_is_i = action.orientation == "ab"
            prefer_i = shown_a_is_i

        z = 1 if prefer_i else -1
        return self._record(action, z=z, subtype="none", valid=True, raw="A")

    def _record(self, action, *, z, subtype, valid, raw) -> NormalizedEvidence:
        return NormalizedEvidence(
            query_id=action.pair_id.split("::")[0],
            canonical_pair_id=action.pair_id,
            doc_i=action.doc_i,
            doc_j=action.doc_j,
            displayed_orientation=action.orientation,
            z=z,
            abstention_subtype=subtype,
            provider=action.provider,
            model=action.model,
            prompt_version=action.prompt_version,
            repetition_index=action.repetition_index,
            temperature=action.temperature,
            valid=bool(valid),
            raw_choice=raw,
            extra={"synthetic_interactive": True},
        )


def make_interactive_judge(
    *,
    n_items: int = 8,
    config: InteractiveJudgeConfig | None = None,
    seed: int = 0,
) -> InteractiveJudge:
    """Build a judge with latent strengths for ``item_00 ≻ item_01 ≻ …``."""
    cfg = config or InteractiveJudgeConfig(n_items=n_items, seed=seed)
    cfg.n_items = n_items
    items = [f"item_{i:02d}" for i in range(n_items)]
    # descending latent strengths with small jitter (keeps ties rare)
    rng = random.Random(seed)
    strengths = {}
    for i, d in enumerate(items):
        strengths[d] = float(n_items - i) + rng.uniform(-0.15, 0.15)
    return InteractiveJudge(latent_strength=strengths, config=cfg, true_ranking=items)


__all__ = [
    "InteractiveJudge",
    "InteractiveJudgeConfig",
    "make_interactive_judge",
]
