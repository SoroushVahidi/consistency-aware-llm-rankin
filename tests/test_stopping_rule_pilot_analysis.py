"""Tests for the stopping-rule pilot CLI's analysis-layer fixes:

- severe-harm / premature-stop rate confidence intervals use a valid
  binomial-proportion interval (Wilson by default) instead of a
  nonparametric bootstrap that degenerates to a zero-width interval when
  the observed count is 0 or n.
- capped (censored, non-triggering) walks are surfaced as explicit,
  machine-readable counts (``run_status``), distinct from and never
  relabeled as triggered stops.
- ``analyze`` refuses to silently treat a truncated ``simulate`` output as
  complete.

Uses purely synthetic rows / fixture directories -- no real oracle or
simulation is required for these specific code paths.
"""

from __future__ import annotations

import json

import pytest

from scripts.run_stopping_rule_pilot import (
    STATISTICAL_ANALYSIS_SCHEMA_VERSION,
    _statistical_analysis,
    run_analyze,
)

TEST_IDS = {"q1", "q2", "q3", "q4", "q5"}
CONFIG = {"frozen_setting_name": "primary", "max_simulated_budget_fraction": 0.6}


def _row(method, qid, *, stopped, severe_harm=False, prem_qrel=False, prem_free=False):
    return dict(
        order="random",
        method=method,
        query_id=qid,
        ndcg=0.9,
        budget_frac=0.3,
        stopped=stopped,
        severe_harm=severe_harm,
        premature_stop_qrel_label=prem_qrel,
        premature_instability_qrelfree=prem_free,
    )


def _synthetic_rows():
    rows = []
    # counterfactual_primary: 3 stopped, 2 capped, 0/5 severe harm.
    stopped_flags = {"q1": True, "q2": True, "q3": False, "q4": True, "q5": False}
    for qid, stopped in stopped_flags.items():
        rows.append(_row("counterfactual_primary", qid, stopped=stopped))
    # fixed-budget probes are always "stopped=True" by construction (not an
    # adaptive rule); include one severe-harm event to exercise a nonzero
    # (but not 0 or n) proportion too.
    for qid in TEST_IDS:
        rows.append(_row("fixed_0.10", qid, stopped=True, severe_harm=(qid == "q1")))
        rows.append(_row("fixed_0.20", qid, stopped=True))
        rows.append(_row("simple_recent_stability", qid, stopped=True))
    return rows


def test_severe_harm_ci_is_nondegenerate_for_zero_events():
    result = _statistical_analysis(_synthetic_rows(), TEST_IDS, CONFIG)
    sev = result["severe_harm"]["counterfactual_primary"]
    assert sev["n"] == 5
    assert sev["rate"] == 0.0
    assert sev["ci_method"] == "wilson"
    assert sev["ci95_lower"] == pytest.approx(0.0, abs=1e-9)
    # The regression this guards against: a bootstrap of an all-zero sample
    # gives ci95_upper == 0.0 exactly, falsely implying certainty.
    assert sev["ci95_upper"] > 0.0


def test_severe_harm_ci_is_nondegenerate_for_interior_rate():
    result = _statistical_analysis(_synthetic_rows(), TEST_IDS, CONFIG)
    sev = result["severe_harm"]["fixed_0.10"]
    assert sev["n"] == 5
    assert sev["rate"] == pytest.approx(0.2)
    assert 0.0 < sev["ci95_lower"] < sev["rate"] < sev["ci95_upper"] < 1.0


def test_run_status_distinguishes_stopped_from_capped():
    result = _statistical_analysis(_synthetic_rows(), TEST_IDS, CONFIG)
    status = result["run_status"]["counterfactual_primary"]
    assert status["n_total_runs"] == 5
    assert status["n_stopped"] == 3
    assert status["n_capped"] == 2
    assert status["n_failed"] == 0
    assert status["stopped_rate"] == pytest.approx(0.6)
    assert status["capped_rate"] == pytest.approx(0.4)
    assert status["capped_runs_included_in_headline_aggregates"] is True
    assert status["cap_budget_fraction"] == CONFIG["max_simulated_budget_fraction"]
    # Capped walks must never be silently folded into "stopped".
    assert status["n_stopped"] + status["n_capped"] == status["n_total_runs"]


def test_run_status_capped_count_is_zero_for_fixed_budget_probes():
    # Fixed-budget rows are always emitted with stopped=True (they are not
    # an adaptive rule, so "capped" does not apply) -- confirm this is
    # represented as n_capped=0, not omitted or conflated.
    result = _statistical_analysis(_synthetic_rows(), TEST_IDS, CONFIG)
    for method in ("fixed_0.10", "fixed_0.20", "simple_recent_stability"):
        status = result["run_status"][method]
        assert status["n_capped"] == 0
        assert status["n_stopped"] == status["n_total_runs"]


def test_statistical_analysis_result_is_schema_versioned():
    result = _statistical_analysis(_synthetic_rows(), TEST_IDS, CONFIG)
    assert result["schema_version"] == STATISTICAL_ANALYSIS_SCHEMA_VERSION


def _write_manifest(sim_dir, *, dev_ids, test_ids, n_pairs=105):
    manifest = dict(
        protocol="stopping_rule_pilot_v1",
        input_judgments_sha256="deadbeef",
        n_queries=len(dev_ids) + len(test_ids),
        dev_query_ids=sorted(dev_ids),
        test_query_ids=sorted(test_ids),
        cap_budget=63,
        n_pairs_per_query=n_pairs,
        seed=42,
        frozen_schedule="linear_decay",
    )
    (sim_dir / "MANIFEST.json").write_text(json.dumps(manifest))
    return manifest


def _write_raw_histories(sim_dir, keys):
    lines = []
    for order, qid in keys:
        lines.append(json.dumps(dict(order=order, query_id=qid, history=[])))
    (sim_dir / "raw_stopping_histories.jsonl").write_text("\n".join(lines) + "\n")


def test_run_analyze_refuses_truncated_simulate_output(tmp_path):
    sim_dir = tmp_path / "simulate"
    sim_dir.mkdir()
    dev_ids, test_ids = {"d1"}, {"t1", "t2"}
    _write_manifest(sim_dir, dev_ids=dev_ids, test_ids=test_ids)
    # Missing the static_adjacent/t2 walk that would be expected.
    complete_keys = {("random", "d1"), ("random", "t1"), ("random", "t2")}
    complete_keys |= {("static_adjacent", "t1")}  # t2's static_adjacent walk is missing
    _write_raw_histories(sim_dir, complete_keys)

    config = dict(CONFIG, primary_cutoff_k=10)
    with pytest.raises(RuntimeError, match="incomplete simulate run"):
        run_analyze(sim_dir, tmp_path / "analyze_out", config)


def test_run_analyze_refuses_unexpected_extra_walks(tmp_path):
    sim_dir = tmp_path / "simulate"
    sim_dir.mkdir()
    dev_ids, test_ids = {"d1"}, {"t1"}
    _write_manifest(sim_dir, dev_ids=dev_ids, test_ids=test_ids)
    complete_keys = {("random", "d1"), ("random", "t1"), ("static_adjacent", "t1")}
    complete_keys.add(("random", "not_in_split"))  # unexpected extra walk
    _write_raw_histories(sim_dir, complete_keys)

    config = dict(CONFIG, primary_cutoff_k=10)
    with pytest.raises(RuntimeError, match="not in the expected work set"):
        run_analyze(sim_dir, tmp_path / "analyze_out", config)
