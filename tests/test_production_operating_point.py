"""Contract tests for the interim production operating point (post Outcome F).

Every test here fails on the pre-remediation implementation, in which
``PolicySelector`` defaulted to ``selective_three_way`` and the "safety floor"
could rewrite UHT into HYBRID/CHALLENGER. No billed API calls: all judgments
come from local synthetic judges.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from consistency_ranker.policy_selection.execution_mode import (
    ExecutionMode,
    resolve_execution_mode,
)
from consistency_ranker.policy_selection.gate_features import extract_features
from consistency_ranker.policy_selection.policy_benchmark import build_world
from consistency_ranker.policy_selection.policy_calibration import fit_calibrated_gate
from consistency_ranker.policy_selection.policy_gate import (
    PolicySelector,
    resolve_gate_mode,
    select_policy,
)
from consistency_ranker.policy_selection.policy_runner import run_gated_acquisition
from consistency_ranker.policy_selection.production_config import (
    PRODUCTION_OPERATING_POINT,
    ProductionPolicyConfig,
)
from consistency_ranker.policy_selection.production_runner import (
    ProductionSafeguards,
    run_production_uht,
)
from consistency_ranker.policy_selection.safe_fallback import (
    NON_ROUTING_ACTIONS,
    apply_experimental_escalation,
    evaluate_safeguards,
    production_safety_actions,
)
from consistency_ranker.prior_robust import make_initial_robust_state

REPO_ROOT = Path(__file__).resolve().parents[1]


def _world(prior="outsider_buried", judge="clean", seed=0, n=8, top_k=3):
    return build_world(
        prior_regime=prior, judge_regime=judge, seed=seed, n_items=n, top_k=top_k
    )


def _feats(world, budget=10, top_k=3, seed=0):
    st = make_initial_robust_state(
        query_id="q",
        candidate_ids=list(world["true_ranking"]),
        prior_scores=world["prior_scores"],
        budget=budget,
        top_k=top_k,
        seed=seed,
    )
    return extract_features(st, stage="pre", alt_priors=world.get("alt_priors"))


# --------------------------------------------------------------------------
# Defaults
# --------------------------------------------------------------------------


def test_default_selector_is_production_uht():
    sel = PolicySelector()
    assert sel.mode == "always_uht"
    assert sel.execution_mode is ExecutionMode.PRODUCTION_UHT
    assert sel.allows_learned_routing is False
    assert sel.safety_floor == 0.15


def test_default_select_policy_executes_uht():
    dec = select_policy(_feats(_world()))
    assert dec.policy == "UHT"
    assert dec.executed_policy == "UHT"
    assert dec.experimental_policy is None
    assert dec.execution_mode is ExecutionMode.PRODUCTION_UHT


def test_no_omitted_argument_enables_selective_three_way():
    with pytest.raises(ValueError, match="selective_three_way"):
        PolicySelector(mode="selective_three_way")
    # Only an explicit experimental opt-in unlocks it.
    sel = PolicySelector(
        mode="selective_three_way", execution_mode=ExecutionMode.EXPERIMENTAL_GATE
    )
    assert sel.allows_learned_routing is True


def test_attaching_calibration_model_in_production_is_rejected():
    model = fit_calibrated_gate(
        [[0.0], [1.0]], [0.0, 1.0], feature_names=["x"], kind="logistic"
    )
    with pytest.raises(ValueError, match="Calibration models cannot be attached"):
        PolicySelector(binary_model=model)


def test_unknown_modes_are_rejected_not_mapped():
    with pytest.raises(ValueError, match="Unknown gate mode"):
        resolve_gate_mode("super_gate")
    with pytest.raises(ValueError, match="Unknown execution mode"):
        resolve_execution_mode("experimental")  # near-miss must not resolve
    with pytest.raises(ValueError):
        PolicySelector(execution_mode="turbo")
    # Missing configuration fails closed to production, never to experimental.
    assert resolve_execution_mode(None) is ExecutionMode.PRODUCTION_UHT
    assert resolve_gate_mode(None) == "always_uht"


def test_environment_variables_cannot_enable_learned_routing(monkeypatch):
    monkeypatch.setenv("CONSISTENCY_RANKER_GATE_MODE", "calibrated_hard")
    monkeypatch.setenv("EXECUTION_MODE", "experimental_gate")
    sel = PolicySelector()
    assert sel.mode == "always_uht"
    assert sel.execution_mode is ExecutionMode.PRODUCTION_UHT


def test_production_config_is_frozen_and_locked_to_uht():
    assert PRODUCTION_OPERATING_POINT.primary_policy == "UHT"
    assert PRODUCTION_OPERATING_POINT.safety_floor == 0.15
    assert PRODUCTION_OPERATING_POINT.probe_design == "mixed_diagnostic"
    assert PRODUCTION_OPERATING_POINT.probe_budget == 3
    with pytest.raises(AttributeError):
        PRODUCTION_OPERATING_POINT.primary_policy = "CHALLENGER"  # type: ignore[misc]
    with pytest.raises(ValueError):
        ProductionPolicyConfig(primary_policy="CHALLENGER")


# --------------------------------------------------------------------------
# Safety-floor semantics
# --------------------------------------------------------------------------


def test_safety_floor_does_not_rewrite_uht_in_production():
    # The exact condition that used to reroute: an outsider defeated an insider.
    feats = _feats(_world())
    feats.values["n_outsiders_defeating_insiders"] = 1.0
    dec = select_policy(feats)
    assert dec.policy == "UHT"

    _, actions = evaluate_safeguards(
        step=0,
        q_hat=0.4,
        contradiction_rate=0.4,
        evidence_fraction=0.0,
        remaining_budget=5,
        intending_stop=True,
    )
    assert "mandatory_outsider_probe" in actions
    kept = production_safety_actions(actions)
    assert set(kept) <= NON_ROUTING_ACTIONS
    assert "force_non_local" not in kept


def test_same_condition_may_reroute_only_under_experimental_mode():
    feats = _feats(_world())
    feats.values["n_outsiders_defeating_insiders"] = 1.0
    dec = select_policy(
        feats,
        selector=PolicySelector(execution_mode=ExecutionMode.EXPERIMENTAL_GATE),
        q_hat_heuristic=0.2,
    )
    # always_uht under experimental mode still escalates via the old path.
    assert dec.policy in ("CHALLENGER", "HYBRID")
    assert apply_experimental_escalation("UHT", ["mandatory_outsider_probe"], q_hat=0.9) == (
        "HYBRID"
    )


def test_threshold_equality_at_safety_floor_boundary():
    # Budget 20 * 0.15 == 3.0 exactly: the reservation is the exact 3 calls, and
    # never fewer than the two mandatory safeguard actions.
    cfg = PRODUCTION_OPERATING_POINT
    assert cfg.reserved_safety_calls(20) == 3
    assert cfg.reserved_safety_calls(13) == 2  # ceil(1.95) = 2
    assert cfg.reserved_safety_calls(4) == 2  # floor below the 2 mandatory actions
    assert cfg.reserved_safety_calls(0) == 0


def test_weak_evidence_threshold_equality_is_documented_and_tested():
    """Exactly at the threshold the stop is allowed: the check is strict `<`."""

    class FixedCoverage(ProductionSafeguards):
        def __init__(self, frac):
            super().__init__()
            self._frac = frac

        def evidence_fraction(self, state):
            return self._frac

    world = _world()
    st = make_initial_robust_state(
        query_id="q",
        candidate_ids=list(world["true_ranking"]),
        prior_scores=world["prior_scores"],
        budget=5,
        top_k=3,
        seed=0,
    )
    thr = PRODUCTION_OPERATING_POINT.min_evidence_fraction_to_stop
    assert FixedCoverage(thr).check_weak_evidence_stop(st) is False
    assert FixedCoverage(thr - 1e-9).check_weak_evidence_stop(st) is True
    # No budget left => nothing to gain by blocking the stop.
    st.remaining_budget = 0
    assert FixedCoverage(0.0).check_weak_evidence_stop(st) is False


def test_malformed_calibration_artifact_cannot_activate_learned_gating(tmp_path: Path):
    from consistency_ranker.policy_selection.policy_calibration import CalibratedModel

    bad = tmp_path / "model_logistic.json"
    bad.write_text('{"schema_version": "corrupt", "kind": "logistic"}', encoding="utf-8")
    with pytest.raises(ValueError):
        CalibratedModel.from_dict(__import__("json").loads(bad.read_text(encoding="utf-8")))
    # And a production run never consults such a file in the first place.
    res = run_production_uht(world=_world(), budget=8, top_k=3, seed=0)
    assert res.executed_policy == "UHT"
    assert res.decision.policy_probs == {"UHT": 1.0}


def test_malformed_safety_data_fails_closed_to_uht():
    class BrokenSafeguards(ProductionSafeguards):
        def check_weak_evidence_stop(self, state):
            raise RuntimeError("corrupt safety state")

        def run_outsider_probe(self, *a, **k):
            raise RuntimeError("corrupt probe artifact")

    res = run_production_uht(
        world=_world(),
        budget=10,
        top_k=3,
        seed=0,
        safeguards=BrokenSafeguards(),
    )
    assert res.executed_policy == "UHT"
    assert len(res.safeguards.errors) == 2
    assert res.ranking


# --------------------------------------------------------------------------
# Safeguard execution (spies, not labels)
# --------------------------------------------------------------------------


class SpySafeguards(ProductionSafeguards):
    def __init__(self, cfg=None, force_weak_stop: bool | None = None):
        super().__init__(cfg)
        self.calls: list[str] = []
        self.force_weak_stop = force_weak_stop

    def run_outsider_probe(self, *a, **k):
        self.calls.append("run_outsider_probe")
        return super().run_outsider_probe(*a, **k)

    def check_weak_evidence_stop(self, state):
        self.calls.append("check_weak_evidence_stop")
        if self.force_weak_stop is not None:
            return self.force_weak_stop
        return super().check_weak_evidence_stop(state)

    def gather_additional_evidence(self, *a, **k):
        self.calls.append("gather_additional_evidence")
        return super().gather_additional_evidence(*a, **k)

    def run_final_challenger(self, *a, **k):
        self.calls.append("run_final_challenger")
        return super().run_final_challenger(*a, **k)


def test_all_safeguards_actually_execute():
    spy = SpySafeguards(force_weak_stop=True)
    res = run_production_uht(world=_world(), budget=16, top_k=3, seed=0, safeguards=spy)
    assert "run_outsider_probe" in spy.calls
    assert "check_weak_evidence_stop" in spy.calls
    assert "gather_additional_evidence" in spy.calls
    assert "run_final_challenger" in spy.calls
    assert res.safeguards.outsider_probe_executed is True
    assert res.safeguards.weak_evidence_stop_blocked is True
    assert res.safeguards.final_challenger_executed is True
    assert res.safeguards.errors == []


def test_weak_evidence_stop_is_rejected_and_adds_evidence():
    spy = SpySafeguards(force_weak_stop=True)
    res = run_production_uht(world=_world(), budget=16, top_k=3, seed=0, safeguards=spy)
    assert res.safeguards.weak_evidence_stop_blocked is True
    assert res.safeguards.extra_evidence_calls >= 1
    # Blocking the stop must buy evidence, not a different policy.
    assert res.executed_policy == "UHT"


def test_final_challenger_runs_even_when_stop_is_not_blocked():
    spy = SpySafeguards(force_weak_stop=False)
    res = run_production_uht(world=_world(), budget=16, top_k=3, seed=0, safeguards=spy)
    assert spy.calls.count("run_final_challenger") == 1
    assert res.safeguards.weak_evidence_stop_blocked is False
    assert res.safeguards.final_challenger_executed is True


def test_safeguards_are_not_executed_twice():
    spy = SpySafeguards(force_weak_stop=True)
    run_production_uht(world=_world(), budget=16, top_k=3, seed=0, safeguards=spy)
    assert spy.calls.count("run_outsider_probe") == 1
    assert spy.calls.count("run_final_challenger") == 1
    assert spy.calls.count("gather_additional_evidence") == 1


def test_safeguard_exception_still_returns_uht_ranking():
    class ExplodingFinal(SpySafeguards):
        def run_final_challenger(self, *a, **k):
            self.calls.append("run_final_challenger")
            raise RuntimeError("challenger judge unavailable")

    spy = ExplodingFinal()
    res = run_production_uht(world=_world(), budget=12, top_k=3, seed=1, safeguards=spy)
    assert "run_final_challenger" in spy.calls
    assert res.executed_policy == "UHT"
    assert any("final_challenger" in e for e in res.safeguards.errors)
    assert len(res.ranking) == len(_world()["true_ranking"])


def test_production_runner_refuses_experimental_mode():
    with pytest.raises(ValueError, match="never performs experimental routing"):
        run_production_uht(
            world=_world(),
            budget=8,
            top_k=3,
            seed=0,
            execution_mode=ExecutionMode.EXPERIMENTAL_GATE,
        )


def test_gated_runner_requires_explicit_experimental_opt_in():
    with pytest.raises(ValueError, match="EXPERIMENTAL_GATE"):
        run_gated_acquisition(
            world=_world(), selector=PolicySelector(), budget=8, top_k=3, seed=0
        )


# --------------------------------------------------------------------------
# Diagnostic isolation
# --------------------------------------------------------------------------


def test_diagnostic_recommendation_does_not_alter_executed_policy():
    res = run_production_uht(
        world=_world(),
        budget=16,
        top_k=3,
        seed=0,
        execution_mode=ExecutionMode.DIAGNOSTIC,
        selector=PolicySelector(
            mode="calibrated_hard", execution_mode=ExecutionMode.DIAGNOSTIC
        ),
    )
    assert res.executed_policy == "UHT"
    assert res.experimental_policy is None
    assert res.probe is not None
    assert res.probe["design"] == "mixed_diagnostic"
    assert res.probe["n_executed"] <= 3


def test_strong_challenger_preference_still_executes_uht():
    feats = _feats(_world())
    feats.values["n_outsiders_defeating_insiders"] = 1.0
    sel = PolicySelector(mode="calibrated_hard", execution_mode=ExecutionMode.DIAGNOSTIC)
    dec = select_policy(feats, selector=sel, q_hat_heuristic=0.01)
    assert dec.diagnostic_recommendation == "CHALLENGER"
    assert dec.policy == "UHT"
    assert dec.executed_policy == "UHT"
    assert dec.experimental_policy is None


def test_result_fields_keep_the_three_meanings_separate():
    dec = select_policy(
        _feats(_world()),
        selector=PolicySelector(mode="always_challenger", execution_mode=ExecutionMode.DIAGNOSTIC),
    )
    d = dec.to_dict()
    assert d["executed_policy"] == "UHT"
    assert d["diagnostic_recommendation"] == "CHALLENGER"
    assert d["experimental_policy"] is None
    assert d["execution_mode"] == "diagnostic"


def test_replay_keeps_diagnostic_and_executed_outputs_separate():
    res = run_production_uht(
        world=_world(),
        budget=14,
        top_k=3,
        seed=2,
        execution_mode=ExecutionMode.DIAGNOSTIC,
        selector=PolicySelector(
            mode="selective_three_way", execution_mode=ExecutionMode.DIAGNOSTIC
        ),
    )
    payload = res.to_dict()
    assert payload["executed_policy"] == "UHT"
    assert payload["experimental_policy"] is None
    assert payload["decision"]["executed_policy"] == "UHT"
    # A recommendation is recorded and is allowed to disagree with what ran.
    assert payload["decision"]["diagnostic_recommendation"] is not None


# --------------------------------------------------------------------------
# CLI / configuration
# --------------------------------------------------------------------------


def _run_cli(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": "src", "HOME": str(REPO_ROOT)},
        timeout=300,
    )


def test_production_cli_defaults_to_production_uht():
    proc = _run_cli("run_production_uht.py", "--budget", "8", "--n-items", "6", "--top-k", "2")
    assert proc.returncode == 0, proc.stderr
    assert '"resolved_execution_mode": "production_uht"' in proc.stdout
    assert '"executed_primary_policy": "UHT"' in proc.stdout
    assert '"learned_gate_active": false' in proc.stdout


def test_production_cli_rejects_experimental_gate():
    proc = _run_cli("run_production_uht.py", "--mode", "experimental_gate")
    assert proc.returncode != 0
    assert "invalid choice" in proc.stderr


def test_production_cli_help_labels_experimental_and_diagnostic():
    proc = _run_cli("run_production_uht.py", "--help")
    assert proc.returncode == 0
    assert "EXPERIMENTAL" in proc.stdout
    assert "does NOT alter routing" in proc.stdout


def test_research_cli_help_labels_itself_as_research():
    proc = _run_cli("run_policy_selection_experiment.py", "--help")
    assert proc.returncode == 0
    assert "RESEARCH BENCHMARK" in proc.stdout
    assert "EXPERIMENTAL" in proc.stdout
    assert "--overwrite-existing" in proc.stdout


def test_research_cli_rejects_conflicting_mode(tmp_path: Path):
    proc = _run_cli(
        "run_policy_selection_experiment.py",
        "--output-dir",
        str(tmp_path / "out"),
        "--mode",
        "production_uht",
    )
    assert proc.returncode != 0
    assert "run_production_uht.py" in proc.stderr
    assert not (tmp_path / "out").exists()


# --------------------------------------------------------------------------
# End-to-end (release critical)
# --------------------------------------------------------------------------


def test_end_to_end_production_operating_point():
    """Release-critical: resolved config → final result under production defaults."""
    spy = SpySafeguards()
    world = _world(prior="outsider_buried", judge="nontransitive", seed=3, n=10, top_k=3)
    res = run_production_uht(
        world=world,
        budget=20,
        top_k=3,
        seed=3,
        config=PRODUCTION_OPERATING_POINT,
        safeguards=spy,
    )

    # 1. Executed policy is UHT and no learned selector controlled routing.
    assert res.executed_policy == "UHT"
    assert res.decision.policy == "UHT"
    assert res.decision.mode == "always_uht"
    assert res.execution_mode is ExecutionMode.PRODUCTION_UHT
    assert res.experimental_policy is None
    assert res.decision.diagnostic_recommendation is None

    # 2. Safeguards ran, in code, exactly once each.
    assert spy.calls.count("run_outsider_probe") == 1
    assert spy.calls.count("check_weak_evidence_stop") == 1
    assert spy.calls.count("run_final_challenger") == 1
    assert res.safeguards.outsider_probe_executed is True
    assert res.safeguards.outsider_probe_pair is not None
    assert res.safeguards.weak_evidence_stop_checked is True
    assert res.safeguards.final_challenger_executed is True

    # 3. The safety floor reserved budget and stayed within it.
    assert res.safeguards.reserved_calls == 3
    assert res.n_calls <= 20
    assert res.safeguards.errors == []

    # 4. Result is a usable ranking over the candidate set.
    assert sorted(res.ranking) == sorted(world["true_ranking"])


def test_production_run_is_deterministic():
    a = run_production_uht(world=_world(seed=5), budget=12, top_k=3, seed=5)
    b = run_production_uht(world=_world(seed=5), budget=12, top_k=3, seed=5)
    assert a.ranking == b.ranking
    assert a.utility == b.utility
    assert a.safeguards.to_dict() == b.safeguards.to_dict()
