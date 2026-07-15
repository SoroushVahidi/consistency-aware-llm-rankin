"""
Tests for the normalization/threshold protocol machinery in
reports/full_calibrated_core/scripts/full_calibration_utils.py and
run_full_calibrated_core.py -- the canonical engine behind every committed
JDIQ manuscript number (not the general-purpose src/consistency_ranker
package, which has its own, separately-tested primitives).

These scripts are not part of the installable "consistency-ranker" package,
so this file inserts them onto sys.path the same way the scripts' own
cross-imports already do (see e.g. validate_scip_vs_bruteforce.py).

Run just this file:

    pytest tests/test_normalization_protocols.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FULL_CAL_SCRIPTS = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
for _p in (REPO_ROOT, REPO_ROOT / "src", FULL_CAL_SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from full_calibration_utils import (  # noqa: E402
    ProtocolSpec,
    ThresholdConfig,
    _parse_quantile_independent_mode,
    build_query_vote_artifacts,
    calibrate_query_ranker_scores,
    choose_threshold_config,
)

pytestmark = pytest.mark.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# ProtocolSpec: validation and round-tripping.
# ---------------------------------------------------------------------------


class TestProtocolSpec:
    def test_valid_spec_constructs(self):
        spec = ProtocolSpec(
            protocol_id="x",
            calibration="minmax_query_ranker",
            threshold_mode="quantile_independent_q0p5",
            label="test",
            kind="independent",
        )
        assert spec.is_raw_reference_matched is False

    def test_retention_matched_is_raw_reference_matched(self):
        spec = ProtocolSpec(
            protocol_id="x",
            calibration="minmax_query_ranker",
            threshold_mode="retention_matched",
            label="t",
            kind="primary",
        )
        assert spec.is_raw_reference_matched is True

    def test_unknown_calibration_rejected(self):
        with pytest.raises(ValueError, match="Unknown calibration"):
            ProtocolSpec(
                protocol_id="bad",
                calibration="not_a_calibration",
                threshold_mode="retention_matched",
                label="x",
                kind="primary",
            )

    def test_unknown_threshold_mode_rejected(self):
        with pytest.raises(ValueError, match="Unknown threshold_mode"):
            ProtocolSpec(
                protocol_id="bad",
                calibration="raw",
                threshold_mode="not_a_mode",
                label="x",
                kind="ablation",
            )

    def test_out_of_range_quantile_rejected(self):
        with pytest.raises(ValueError, match="in \\(0, 1\\)"):
            ProtocolSpec(
                protocol_id="bad",
                calibration="raw",
                threshold_mode="quantile_independent_q1p5",
                label="x",
                kind="ablation",
            )

    def test_unknown_kind_rejected(self):
        with pytest.raises(ValueError, match="Unknown protocol kind"):
            ProtocolSpec(
                protocol_id="bad",
                calibration="raw",
                threshold_mode="fixed_numeric",
                label="x",
                kind="not_a_kind",
            )

    def test_empty_protocol_id_rejected(self):
        with pytest.raises(ValueError):
            ProtocolSpec(
                protocol_id="",
                calibration="raw",
                threshold_mode="fixed_numeric",
                label="x",
                kind="ablation",
            )

    def test_round_trip_via_dict(self):
        spec = ProtocolSpec(
            protocol_id="independent_minmax_quantile_q0p5",
            calibration="minmax_query_ranker",
            threshold_mode="quantile_independent_q0p5",
            label="minmax + independent quantile (q=0.5)",
            kind="independent",
        )
        payload = spec.to_dict()
        restored = ProtocolSpec.from_dict(payload)
        assert restored == spec

    def test_round_trip_via_json(self):
        import json

        spec = ProtocolSpec(
            protocol_id="ablation_raw_fixed",
            calibration="raw",
            threshold_mode="fixed_numeric",
            label="raw + fixed",
            kind="ablation",
        )
        blob = json.dumps(spec.to_dict())
        restored = ProtocolSpec.from_dict(json.loads(blob))
        assert restored == spec

    def test_full_registry_validates(self):
        """Every protocol actually registered in run_full_calibrated_core's
        PROTOCOL_SPECS (the source of every committed manuscript number, plus
        the new independently-defined protocols) must construct a valid
        ProtocolSpec -- this is the "validation of protocol names and
        parameters" requirement, exercised against the real registry rather
        than only synthetic examples."""
        from run_full_calibrated_core import PROTOCOL_REGISTRY, PROTOCOL_SPECS

        assert len(PROTOCOL_REGISTRY) == len(PROTOCOL_SPECS)
        for protocol_id, spec_cfg in PROTOCOL_SPECS.items():
            spec = PROTOCOL_REGISTRY[protocol_id]
            assert spec.protocol_id == protocol_id
            assert spec.calibration == spec_cfg["calibration"]
            assert spec.threshold_mode == spec_cfg["threshold_mode"]

    def test_canonical_name_aliases_resolve_to_valid_protocols(self):
        from run_full_calibrated_core import CANONICAL_NAME_ALIASES, PROTOCOL_REGISTRY

        expected = {"raw_fixed", "minmax_raw_matched", "minmax_quantile", "rank_percentile"}
        assert set(CANONICAL_NAME_ALIASES) == expected
        for canonical_name, protocol_id in CANONICAL_NAME_ALIASES.items():
            assert protocol_id in PROTOCOL_REGISTRY, (
                f"{canonical_name!r} -> {protocol_id!r} not in registry"
            )


def test_parse_quantile_independent_mode():
    assert _parse_quantile_independent_mode("quantile_independent_q0p5") == pytest.approx(0.5)
    assert _parse_quantile_independent_mode("quantile_independent_q0p3") == pytest.approx(0.3)
    assert _parse_quantile_independent_mode("quantile_independent_q0p7") == pytest.approx(0.7)
    assert _parse_quantile_independent_mode("retention_matched") is None
    assert _parse_quantile_independent_mode("fixed_numeric") is None
    with pytest.raises(ValueError):
        _parse_quantile_independent_mode("quantile_independent_q1p2")
    with pytest.raises(ValueError):
        _parse_quantile_independent_mode("quantile_independent_q0p0")


# ---------------------------------------------------------------------------
# No-qrels-leakage guard.
# ---------------------------------------------------------------------------


def test_choose_threshold_config_signature_has_no_qrels_or_relevance_parameter():
    """Structural guard against reintroducing qrels into threshold
    selection: choose_threshold_config's parameter names must never include
    anything relevance/qrels-shaped. This fails loudly (a clear assertion,
    not a silent pass) if a future edit adds such a parameter."""
    import inspect

    params = set(inspect.signature(choose_threshold_config).parameters)
    forbidden_substrings = ("qrel", "relevance", "ndcg", "rel_map", "gain")
    for param in params:
        for bad in forbidden_substrings:
            assert bad not in param.lower(), (
                f"choose_threshold_config gained a qrels/relevance-shaped parameter: {param!r}"
            )


def test_quantile_independent_threshold_ignores_raw_baseline_even_if_supplied():
    """Even when raw baseline_vote_rates/baseline_edge_count are passed in
    (the call signature always receives them, since the dispatcher is
    shared with retention_matched), the quantile_independent policy must
    produce byte-identical results regardless of their values -- proving
    the independence is real, not just documented."""
    margins = {"bm25": [0.1, 0.2, 0.3, 0.4, 0.5], "tfidf": [0.2] * 10, "minilm": []}
    cfg_a = choose_threshold_config(
        dataset="d",
        regime="ms1",
        calibration="minmax_query_ranker",
        threshold_mode="quantile_independent_q0p5",
        baseline_vote_rates={"bm25": 0.1, "tfidf": 0.9, "minilm": 0.5},
        baseline_edge_count=10,
        calibration_pair_margins=margins,
        per_query_inputs=[],
    )
    cfg_b = choose_threshold_config(
        dataset="d",
        regime="ms1",
        calibration="minmax_query_ranker",
        threshold_mode="quantile_independent_q0p5",
        baseline_vote_rates={"bm25": 0.99, "tfidf": 0.01, "minilm": 0.5},
        baseline_edge_count=999999,
        calibration_pair_margins=margins,
        per_query_inputs=[],
    )
    assert cfg_a.vote_thresholds == cfg_b.vote_thresholds
    assert cfg_a.aggregate_threshold == cfg_b.aggregate_threshold == 0.0
    assert cfg_a.target_vote_rates is None
    assert cfg_a.target_edge_count is None


# ---------------------------------------------------------------------------
# Normalization invariances / non-invariances (task requirement 6).
# ---------------------------------------------------------------------------


class TestMinMaxInvariances:
    def test_invariant_to_positive_affine_transform(self):
        """min-max normalization must be invariant to x -> a*x + b, a > 0:
        the same document gets the same normalized score either way."""
        raw = {"a": 1.0, "b": 5.0, "c": 3.0, "d": -2.0}
        transformed = {k: 2.5 * v + 7.0 for k, v in raw.items()}
        norm_raw, _ = calibrate_query_ranker_scores(raw, calibration="minmax_query_ranker")
        norm_transformed, _ = calibrate_query_ranker_scores(
            transformed, calibration="minmax_query_ranker"
        )
        for doc in raw:
            assert norm_raw[doc] == pytest.approx(norm_transformed[doc], abs=1e-9)

    def test_not_invariant_to_negative_affine_transform_direction_flip(self):
        """A *negative* affine transform (a < 0) reverses ranking order --
        min-max is only invariant to positive affine transforms, not affine
        transforms in general. This documents the boundary of the
        invariance rather than a bug."""
        raw = {"a": 1.0, "b": 5.0, "c": 3.0}
        flipped = {k: -1.0 * v for k, v in raw.items()}
        norm_raw, _ = calibrate_query_ranker_scores(raw, calibration="minmax_query_ranker")
        norm_flipped, _ = calibrate_query_ranker_scores(flipped, calibration="minmax_query_ranker")
        # "b" is the max under raw (normalized 1.0) but the min under the
        # negated scores (normalized 0.0) -- ranking order is reversed.
        assert norm_raw["b"] == pytest.approx(1.0)
        assert norm_flipped["b"] == pytest.approx(0.0)

    def test_sensitive_to_one_extreme_score(self):
        """A single extreme outlier compresses every other document's
        min-max spread toward the low end -- this is a documented weakness,
        not a bug, and this test demonstrates it exists."""
        without_outlier = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}
        with_outlier = {**without_outlier, "z": 10_000.0}
        norm_without, _ = calibrate_query_ranker_scores(
            without_outlier, calibration="minmax_query_ranker"
        )
        norm_with, _ = calibrate_query_ranker_scores(
            with_outlier, calibration="minmax_query_ranker"
        )
        spread_without = max(norm_without.values()) - min(norm_without.values())
        spread_with = max(v for k, v in norm_with.items() if k != "z") - min(
            v for k, v in norm_with.items() if k != "z"
        )
        assert spread_without == pytest.approx(1.0)
        assert spread_with < 0.01  # compressed by more than 100x by the single outlier

    def test_fully_constant_scores_flagged_zero_variance(self):
        constant = {"a": 5.0, "b": 5.0, "c": 5.0}
        _norm, meta = calibrate_query_ranker_scores(constant, calibration="minmax_query_ranker")
        assert meta["zero_variance"] is True

    def test_fully_constant_scores_contribute_no_directional_margin(self):
        """Constant ranker scores must abstain on every pair (no vote),
        not silently cast a spurious directional vote."""
        raw_scores = {"bm25": {"a": 5.0, "b": 5.0, "c": 5.0}}
        pool = ["a", "b", "c"]
        tc = ThresholdConfig(
            vote_thresholds={"bm25": 0.0},
            aggregate_threshold=0.0,
            min_support=1,
            postprocess_drop_mutual=False,
            target_vote_rates=None,
            target_edge_count=None,
            notes="t",
        )
        artifacts = build_query_vote_artifacts(
            query_id="q",
            raw_scores_by_ranker=raw_scores,
            candidate_pool=pool,
            calibration="minmax_query_ranker",
            threshold_config=tc,
        )
        assert artifacts["rows"] == []
        assert artifacts["retained_vote_counts"].get("bm25", 0) == 0

    def test_near_constant_scores_not_flagged_but_hugely_amplified(self):
        """A near-degenerate (tiny nonzero range) score vector is NOT
        flagged zero_variance, but min-max still stretches that tiny range
        to fill [0, 1] -- amplifying what may be numerical noise into an
        apparently-confident full-strength margin. This is the documented
        weakness distinguishing "near-constant" from "fully constant"."""
        near_constant = {"a": 1.0, "b": 1.0 + 1e-10, "c": 1.0 + 2e-10}
        norm, meta = calibrate_query_ranker_scores(near_constant, calibration="minmax_query_ranker")
        assert meta["zero_variance"] is False
        assert max(norm.values()) - min(norm.values()) == pytest.approx(
            1.0
        )  # stretched to fill [0, 1]

    def test_no_nan_or_inf_from_near_constant_scores(self):
        near_constant = {"a": 1.0, "b": 1.0 + 1e-10}
        norm, _ = calibrate_query_ranker_scores(near_constant, calibration="minmax_query_ranker")
        import math

        assert all(math.isfinite(v) for v in norm.values())

    def test_sensitive_to_candidate_pool_changes_nonlocal(self):
        """min-max is a *non-local* transform: adding an unrelated
        document's score to the pool changes the normalized margin between
        two OTHER documents that did not themselves change, because the
        [0, 1] range is defined by the whole pool's min/max. Raw margins,
        by contrast, do not depend on unrelated documents at all."""
        small_pool = {"a": 1.0, "b": 2.0}
        larger_pool = {"a": 1.0, "b": 2.0, "z": 100.0}  # "z" unrelated to the a-vs-b comparison
        norm_small, _ = calibrate_query_ranker_scores(small_pool, calibration="minmax_query_ranker")
        norm_large, _ = calibrate_query_ranker_scores(
            larger_pool, calibration="minmax_query_ranker"
        )
        margin_small = abs(norm_small["a"] - norm_small["b"])
        margin_large = abs(norm_large["a"] - norm_large["b"])
        assert margin_small == pytest.approx(1.0)
        assert margin_large < 0.02  # a and b are now both near the bottom of a much wider range
        # Raw margin between a and b is completely unaffected by "z".
        assert abs(small_pool["a"] - small_pool["b"]) == abs(larger_pool["a"] - larger_pool["b"])


class TestRankPercentileInvariances:
    def test_invariant_to_strictly_increasing_monotone_transform(self):
        """rank-percentile depends only on the *order* of scores, so it must
        be invariant to any strictly increasing transform (not just affine
        ones) -- e.g. x -> x**3 or x -> exp(x)."""
        import math

        raw = {"a": 1.0, "b": 5.0, "c": 3.0, "d": -2.0}
        cubed = {k: v**3 for k, v in raw.items()}
        exp_transformed = {k: math.exp(v) for k, v in raw.items()}
        norm_raw, _ = calibrate_query_ranker_scores(raw, calibration="rank_percentile")
        norm_cubed, _ = calibrate_query_ranker_scores(cubed, calibration="rank_percentile")
        norm_exp, _ = calibrate_query_ranker_scores(exp_transformed, calibration="rank_percentile")
        for doc in raw:
            assert norm_raw[doc] == pytest.approx(norm_cubed[doc])
            assert norm_raw[doc] == pytest.approx(norm_exp[doc])

    def test_not_invariant_to_decreasing_transform(self):
        raw = {"a": 1.0, "b": 5.0, "c": 3.0}
        negated = {k: -v for k, v in raw.items()}
        norm_raw, _ = calibrate_query_ranker_scores(raw, calibration="rank_percentile")
        norm_negated, _ = calibrate_query_ranker_scores(negated, calibration="rank_percentile")
        assert norm_raw["b"] == pytest.approx(1.0)
        assert norm_negated["b"] == pytest.approx(0.0)


def test_raw_margins_not_invariant_to_scaling():
    """Raw (uncalibrated) margins must scale linearly with the score scale
    -- they are explicitly NOT invariant, which is exactly the
    scale-comparability problem the paper's normalization step exists to
    fix. This test documents that raw is the *non-invariant baseline*, not
    a bug in the raw path."""
    raw = {"a": 1.0, "b": 3.0}
    scaled = {k: 1000.0 * v for k, v in raw.items()}
    norm_raw, _ = calibrate_query_ranker_scores(raw, calibration="raw")
    norm_scaled, _ = calibrate_query_ranker_scores(scaled, calibration="raw")
    margin_raw = abs(norm_raw["a"] - norm_raw["b"])
    margin_scaled = abs(norm_scaled["a"] - norm_scaled["b"])
    assert margin_scaled == pytest.approx(1000.0 * margin_raw)
    assert margin_scaled != pytest.approx(margin_raw)


def test_missing_score_never_imputed():
    """A ranker that did not score a document must contribute no vote for
    any pair involving that document -- never a silently-imputed value
    (e.g. 0.0), for any calibration."""
    raw_scores = {"bm25": {"a": 1.0, "b": 2.0}}  # "c" never scored by bm25
    pool = ["a", "b", "c"]
    tc = ThresholdConfig(
        vote_thresholds={"bm25": 0.0},
        aggregate_threshold=0.0,
        min_support=1,
        postprocess_drop_mutual=False,
        target_vote_rates=None,
        target_edge_count=None,
        notes="t",
    )
    for calibration in (
        "raw",
        "minmax_query_ranker",
        "zscore_query_ranker",
        "rank_percentile",
        "rank_percentile_independent",
        "unit_vote",
    ):
        artifacts = build_query_vote_artifacts(
            query_id="q",
            raw_scores_by_ranker=raw_scores,
            candidate_pool=pool,
            calibration=calibration,
            threshold_config=tc,
        )
        for row in artifacts["rows"]:
            assert "c" not in (row["winner_doc_id"], row["loser_doc_id"]), (
                f"calibration={calibration!r} produced a vote involving "
                f"unscored document 'c': {row}"
            )
