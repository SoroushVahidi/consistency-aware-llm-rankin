"""
Tests for scripts/run_cloud_validation.py.

Expensive subprocesses (venv creation, pip install, pytest runs) are mocked
in unit tests; one lightweight end-to-end smoke test exercises the real
Runner/subprocess plumbing against trivial shell commands in a temporary
directory (not a full venv build, which belongs to the manual/scheduled
full validation run, not the fast test suite).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import scripts.run_cloud_validation as rcv


def test_module_imports():
    import scripts.run_cloud_validation  # noqa: F401


def test_repo_validators_bundle_includes_repo_clarity(tmp_path, monkeypatch):
    """Regression test: validate_repo_clarity.py was added after
    run_repo_validators() was first written and had to be wired in
    separately -- guard against it silently dropping out of the bundle
    again on a future refactor."""
    calls = []

    class FakeRunner:
        def run(self, name, cmd, **kwargs):
            calls.append(name)
            return rcv.StepResult(name, cmd, str(tmp_path), 0, 0.01, f"{name}.log", "PASS")

    rcv.run_repo_validators(FakeRunner(), "fake_python")
    assert "validate_repo_clarity" in calls


def test_packaging_steps_install_build_backend_before_building(tmp_path, monkeypatch):
    """Regression test: an earlier version called `python -m build` without
    ever installing the `build` package into the tier venv first, which
    failed with 'No module named build' on every real run. The build
    backend must be installed before the build step runs."""
    calls = []

    class FakeRunner:
        def run(self, name, cmd, **kwargs):
            calls.append(name)
            return rcv.StepResult(name, cmd, str(tmp_path), 0, 0.01, f"{name}.log", "PASS")

    monkeypatch.setattr(rcv, "make_venv", lambda path: str(path / "bin" / "python"))
    # Simulate a wheel appearing after the (mocked) build step.
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "consistency_ranker-0.1.0-py3-none-any.whl").touch()

    rcv.run_packaging_steps(FakeRunner(), "fake_python", tmp_path)

    assert "install_build_backend" in calls
    assert "package_build_sdist_wheel" in calls
    assert calls.index("install_build_backend") < calls.index("package_build_sdist_wheel")


# ---------------------------------------------------------------------------
# Runner / command construction / failure propagation
# ---------------------------------------------------------------------------


def test_runner_records_pass_status_for_zero_exit(tmp_path):
    runner = rcv.Runner(tmp_path)
    result = runner.run("echo_ok", ["python3", "-c", "print('hi')"])
    assert result.status == "PASS"
    assert result.returncode == 0
    assert (tmp_path / result.log_path).exists()
    assert "hi" in (tmp_path / result.log_path).read_text()


def test_runner_records_fail_status_for_nonzero_exit(tmp_path):
    runner = rcv.Runner(tmp_path)
    result = runner.run("fail_cmd", ["python3", "-c", "import sys; sys.exit(1)"])
    assert result.status == "FAIL"
    assert result.returncode == 1


def test_runner_records_error_status_on_timeout(tmp_path):
    runner = rcv.Runner(tmp_path)
    result = runner.run("slow_cmd", ["python3", "-c", "import time; time.sleep(5)"], timeout=0.1)
    assert result.status == "ERROR"
    assert result.returncode is None
    assert "timed out" in result.note


def test_runner_records_error_status_on_missing_command(tmp_path):
    runner = rcv.Runner(tmp_path)
    result = runner.run("missing_cmd", ["definitely_not_a_real_binary_xyz"])
    assert result.status == "ERROR"
    assert "not found" in result.note


def test_runner_never_leaks_raw_stdout_into_step_result(tmp_path):
    """The StepResult dataclass itself must not carry a command's raw
    stdout/output -- only the log file path. The printed value below goes to
    the log file on disk (fine, inspectable there) but must never appear in
    the structured StepResult that later gets embedded in summary.json."""
    import dataclasses

    # The secret-shaped value is assembled at runtime (via chr() codes), not
    # spelled out in the command's own argv, so a leak into the structured
    # result would have to come from captured *output*, not the input command.
    secret = "".join(chr(c) for c in (68, 73, 83, 84, 95, 57, 102, 56, 101, 55, 100))
    runner = rcv.Runner(tmp_path)
    result = runner.run(
        "secret_like_output",
        ["python3", "-c", f"print(''.join(chr(c) for c in {[ord(ch) for ch in secret]}))"],
    )
    as_dict = dataclasses.asdict(result)
    assert secret not in json.dumps(as_dict)
    # It IS expected on disk in the per-command log file (that's the point
    # of a log file: full detail, kept out of the structured summary).
    assert secret in (tmp_path / result.log_path).read_text()


# ---------------------------------------------------------------------------
# Tier report aggregation
# ---------------------------------------------------------------------------


def test_tier_report_overall_status_pass_when_all_steps_pass():
    steps = [
        rcv.StepResult("a", [], ".", 0, 0.1, "a.log", "PASS"),
        rcv.StepResult("b", [], ".", 0, 0.1, "b.log", "PASS"),
    ]
    report = rcv.TierReport(tier="core", steps=steps)
    assert report.overall_status == "PASS"


def test_tier_report_overall_status_fail_when_any_step_fails():
    steps = [
        rcv.StepResult("a", [], ".", 0, 0.1, "a.log", "PASS"),
        rcv.StepResult("b", [], ".", 1, 0.1, "b.log", "FAIL"),
    ]
    report = rcv.TierReport(tier="core", steps=steps)
    assert report.overall_status == "FAIL"


def test_tier_report_skipped_when_reason_set():
    report = rcv.TierReport(tier="real-data", skipped_reason="datasets not prepared")
    assert report.overall_status == "SKIPPED"


def test_tier_report_not_run_when_no_steps_and_no_skip_reason():
    report = rcv.TierReport(tier="solver")
    assert report.overall_status == "NOT_RUN"


# ---------------------------------------------------------------------------
# Gurobi detection: availability, redaction, missing-package behavior
# ---------------------------------------------------------------------------


def test_gurobi_smoke_reports_package_unavailable():
    """A python with no gurobipy installed must be classified
    package_unavailable, not crash or hang."""

    class FakeProc:
        stdout = "__GUROBI_SMOKE__" + json.dumps(
            {"available": False, "reason": "package_unavailable"}
        )

    with patch("subprocess.run", return_value=FakeProc()):
        result = rcv.gurobi_smoke("irrelevant_python")
    assert result == {"available": False, "reason": "package_unavailable"}


def test_gurobi_smoke_reports_license_failure_distinct_from_missing_package():
    class FakeProc:
        stdout = "__GUROBI_SMOKE__" + json.dumps(
            {
                "available": False,
                "reason": "license_or_runtime_failure",
                "error_type": "GurobiError",
            }
        )

    with patch("subprocess.run", return_value=FakeProc()):
        result = rcv.gurobi_smoke("irrelevant_python")
    assert result["reason"] == "license_or_runtime_failure"
    assert result["reason"] != "package_unavailable"


def test_gurobi_smoke_redacts_everything_except_whitelisted_fields(tmp_path, monkeypatch):
    """Even if the underlying process printed something secret-shaped, only
    the whitelisted keys (available/version/optimize_status/reason/error_type)
    ever make it into the returned dict."""

    class FakeProc:
        stdout = (
            "Set parameter WLSAccessID\n"
            "Set parameter WLSSecret\n"
            "__GUROBI_SMOKE__"
            + json.dumps({"available": True, "version": [13, 0, 2], "optimize_status": 2})
        )

    with patch("subprocess.run", return_value=FakeProc()):
        result = rcv.gurobi_smoke("irrelevant_python")

    assert set(result.keys()) <= {"available", "version", "optimize_status", "reason", "error_type"}
    assert result["available"] is True
    assert result["version"] == [13, 0, 2]
    dumped = json.dumps(result)
    assert "WLSSecret" not in dumped
    assert "WLSAccessID" not in dumped


def test_gurobi_smoke_handles_unparseable_output():
    class FakeProc:
        stdout = "some unrelated banner text with no marker\n"

    with patch("subprocess.run", return_value=FakeProc()):
        result = rcv.gurobi_smoke("irrelevant_python")
    assert result == {"available": False, "reason": "unparseable_output"}


# ---------------------------------------------------------------------------
# Dataset detection (real_data tier gating)
# ---------------------------------------------------------------------------


def test_dataset_prepared_false_when_files_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(rcv, "REPO_ROOT", tmp_path)
    assert rcv.dataset_prepared("scidocs") is False


def test_dataset_prepared_true_when_files_present(tmp_path, monkeypatch):
    monkeypatch.setattr(rcv, "REPO_ROOT", tmp_path)
    base = tmp_path / "data" / "processed" / "beir" / "scidocs"
    base.mkdir(parents=True)
    (base / "queries.jsonl").write_text("{}\n")
    (base / "documents.jsonl").write_text("{}\n")
    assert rcv.dataset_prepared("scidocs") is True


def test_real_data_tier_skips_explicitly_when_not_prepared_and_not_requested(tmp_path, monkeypatch):
    monkeypatch.setattr(rcv, "REPO_ROOT", tmp_path)
    runner = rcv.Runner(tmp_path)
    report = rcv.run_real_data_tier(runner, tmp_path, prepare=False)
    assert report.overall_status == "SKIPPED"
    assert report.skipped_reason  # never a silent/empty skip


# ---------------------------------------------------------------------------
# Summary generation / schema determinism
# ---------------------------------------------------------------------------


def test_write_summary_produces_expected_schema(tmp_path):
    steps = [rcv.StepResult("a", ["echo"], ".", 0, 0.1, "a.log", "PASS")]
    tiers = [rcv.TierReport(tier="core", steps=steps)]
    summary = rcv.write_summary(
        tmp_path,
        "20260101T000000Z",
        "abc123",
        False,
        "main",
        {"python_version": "3.12.3"},
        tiers,
        False,
    )
    assert summary["overall_status"] == "PASS"
    assert summary["commit_sha"] == "abc123"
    assert summary["dirty_worktree"] is False
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "environment.json").exists()
    assert (tmp_path / "commands.json").exists()
    assert (tmp_path / "SUMMARY.md").exists()

    reloaded = json.loads((tmp_path / "summary.json").read_text())
    assert reloaded == summary


def test_write_summary_overall_fail_when_any_tier_fails(tmp_path):
    pass_steps = [rcv.StepResult("a", [], ".", 0, 0.1, "a.log", "PASS")]
    fail_steps = [rcv.StepResult("b", [], ".", 1, 0.1, "b.log", "FAIL")]
    tiers = [
        rcv.TierReport(tier="core", steps=pass_steps),
        rcv.TierReport(tier="solver", steps=fail_steps),
    ]
    summary = rcv.write_summary(tmp_path, "run1", "sha", False, "main", {}, tiers, False)
    assert summary["overall_status"] == "FAIL"


def test_write_summary_never_includes_full_env_var_dump(tmp_path):
    tiers = [
        rcv.TierReport(tier="core", steps=[rcv.StepResult("a", [], ".", 0, 0.1, "a.log", "PASS")])
    ]
    env_meta = {"python_version": "3.12.3", "cpu_count": 20}
    summary = rcv.write_summary(tmp_path, "run1", "sha", False, "main", env_meta, tiers, False)
    assert summary["environment"] == env_meta
    assert "environ" not in summary


# ---------------------------------------------------------------------------
# verify-run integrity check
# ---------------------------------------------------------------------------


def test_verify_run_fails_on_missing_summary(tmp_path):
    assert rcv.verify_run(tmp_path) == 1


def test_verify_run_passes_on_consistent_summary(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "a.log").write_text("ok\n")
    summary = {
        "tiers": [
            {
                "tier": "core",
                "overall_status": "PASS",
                "skipped_reason": "",
                "steps": [{"name": "a", "log_path": "logs/a.log", "status": "PASS"}],
            }
        ]
    }
    (tmp_path / "summary.json").write_text(json.dumps(summary))
    assert rcv.verify_run(tmp_path) == 0


def test_verify_run_detects_status_mismatch(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "a.log").write_text("ok\n")
    summary = {
        "tiers": [
            {
                "tier": "core",
                "overall_status": "PASS",  # inconsistent: step below is FAIL
                "skipped_reason": "",
                "steps": [{"name": "a", "log_path": "logs/a.log", "status": "FAIL"}],
            }
        ]
    }
    (tmp_path / "summary.json").write_text(json.dumps(summary))
    assert rcv.verify_run(tmp_path) == 1


def test_verify_run_detects_missing_log_file(tmp_path):
    summary = {
        "tiers": [
            {
                "tier": "core",
                "overall_status": "PASS",
                "skipped_reason": "",
                "steps": [{"name": "a", "log_path": "logs/missing.log", "status": "PASS"}],
            }
        ]
    }
    (tmp_path / "summary.json").write_text(json.dumps(summary))
    assert rcv.verify_run(tmp_path) == 1


# ---------------------------------------------------------------------------
# CLI: tier selection, dirty-worktree refusal, tmux command, exit codes
# ---------------------------------------------------------------------------


def test_main_refuses_dirty_worktree_without_allow_dirty(monkeypatch):
    monkeypatch.setattr(rcv, "git_state", lambda: ("deadbeef", True, "main"))
    monkeypatch.setattr(rcv.sys, "argv", ["run_cloud_validation.py", "--tier", "core"])
    assert rcv.main() == 1


def test_main_print_tmux_command_contains_session_and_log(monkeypatch, capsys):
    monkeypatch.setattr(
        rcv.sys, "argv", ["run_cloud_validation.py", "--print-tmux-command", "--tier", "solver"]
    )
    exit_code = rcv.main()
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "tmux new-session -d -s cloud_validation_solver_" in out
    assert "tee .cloud_validation_runs/" in out
    assert "EXIT_CODE=$?" in out
    assert "--tier solver" in out


def test_main_verify_run_short_circuits_before_git_checks(monkeypatch, tmp_path):
    """--verify-run must not require a clean worktree or touch git state at all."""
    called = {"git_state": False}

    def fake_git_state():
        called["git_state"] = True
        return ("deadbeef", True, "main")

    monkeypatch.setattr(rcv, "git_state", fake_git_state)
    monkeypatch.setattr(rcv.sys, "argv", ["run_cloud_validation.py", "--verify-run", str(tmp_path)])
    rcv.main()
    assert called["git_state"] is False


def test_main_exits_nonzero_when_a_tier_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(rcv, "git_state", lambda: ("deadbeef", False, "main"))
    monkeypatch.setattr(rcv, "RUNS_ROOT", tmp_path / ".cloud_validation_runs")

    def fake_core_tier(runner, work_dir):
        return rcv.TierReport(
            tier="core", steps=[rcv.StepResult("x", [], ".", 1, 0.1, "x.log", "FAIL")]
        )

    monkeypatch.setattr(rcv, "run_core_tier", fake_core_tier)
    monkeypatch.setattr(rcv.sys, "argv", ["run_cloud_validation.py", "--tier", "core"])
    assert rcv.main() == 1


def test_main_exits_zero_when_tier_passes(monkeypatch, tmp_path):
    monkeypatch.setattr(rcv, "git_state", lambda: ("deadbeef", False, "main"))
    monkeypatch.setattr(rcv, "RUNS_ROOT", tmp_path / ".cloud_validation_runs")

    def fake_core_tier(runner, work_dir):
        return rcv.TierReport(
            tier="core", steps=[rcv.StepResult("x", [], ".", 0, 0.1, "x.log", "PASS")]
        )

    monkeypatch.setattr(rcv, "run_core_tier", fake_core_tier)
    monkeypatch.setattr(rcv.sys, "argv", ["run_cloud_validation.py", "--tier", "core"])
    assert rcv.main() == 0


# ---------------------------------------------------------------------------
# Lightweight end-to-end smoke test (real subprocess plumbing, trivial commands)
# ---------------------------------------------------------------------------


def test_end_to_end_smoke_with_trivial_commands(tmp_path):
    """Exercises the real Runner -> StepResult -> TierReport -> write_summary
    pipeline against real (but trivial, fast) subprocess calls -- not mocked
    -- to catch integration bugs the mocked unit tests above can't."""
    runner = rcv.Runner(tmp_path)
    steps = [
        runner.run("step_one", ["python3", "-c", "print('one')"]),
        runner.run("step_two", ["python3", "-c", "print('two')"]),
    ]
    report = rcv.TierReport(tier="smoke", steps=steps)
    assert report.overall_status == "PASS"

    summary = rcv.write_summary(
        tmp_path,
        "smoke_run",
        "deadbeef",
        False,
        "main",
        rcv.collect_environment_metadata(),
        [report],
        False,
    )
    assert summary["overall_status"] == "PASS"
    assert rcv.verify_run(tmp_path) == 0
