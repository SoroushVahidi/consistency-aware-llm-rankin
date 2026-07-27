"""Focused CLI / integration tests for Outcome B–D experiment drivers.

Tiny fixtures only. No paid provider calls.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from consistency_ranker.experiment_cli import (
    assert_offline_or_allowed,
    ensure_output_dir,
    write_run_manifest,
)

REPO = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
DRIVERS = [
    "scripts/run_adaptive_acquisition_experiment.py",
    "scripts/run_prior_robust_experiment.py",
    "scripts/run_reliability_aware_repair_experiment.py",
    "scripts/run_linear_extension_extraction_experiment.py",
    "scripts/run_multi_provider_llm_robustness.py",
]


def _run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [PYTHON, *args],
        cwd=str(cwd or REPO),
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.mark.parametrize("driver", DRIVERS)
def test_driver_help_exits_zero(driver: str) -> None:
    proc = _run([driver, "--help"])
    assert proc.returncode == 0, proc.stderr
    assert "usage:" in proc.stdout.lower() or "Usage:" in proc.stdout


def test_ensure_output_dir_refuses_nonempty(tmp_path: Path) -> None:
    d = tmp_path / "out"
    d.mkdir()
    (d / "marker.txt").write_text("x")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        ensure_output_dir(d, overwrite=False)
    ensure_output_dir(d, overwrite=True)


def test_write_run_manifest(tmp_path: Path) -> None:
    out = ensure_output_dir(tmp_path / "fresh")
    path = write_run_manifest(
        out,
        script="scripts/example.py",
        config={"seed": 1},
        repo_root=REPO,
        argv=["scripts/example.py", "--seed", "1"],
    )
    payload = json.loads(path.read_text())
    assert payload["script"] == "scripts/example.py"
    assert payload["config"]["seed"] == 1
    assert "argv" in payload


def test_assert_offline_or_allowed_fail_closed() -> None:
    with pytest.raises(SystemExit, match="Refusing to run"):
        assert_offline_or_allowed(
            allow_provider_calls=False, dry_run=False, cache_only=False
        )
    assert assert_offline_or_allowed(
        allow_provider_calls=False, dry_run=True, cache_only=False
    ) == "dry_run"
    assert assert_offline_or_allowed(
        allow_provider_calls=False, dry_run=False, cache_only=True
    ) == "cache_only"
    assert assert_offline_or_allowed(
        allow_provider_calls=True, dry_run=False, cache_only=False
    ) == "live"
    with pytest.raises(SystemExit, match="Invalid mode"):
        assert_offline_or_allowed(
            allow_provider_calls=True, dry_run=True, cache_only=False
        )


def test_multi_provider_requires_explicit_mode(tmp_path: Path) -> None:
    proc = _run(
        [
            "scripts/run_multi_provider_llm_robustness.py",
            "--stage",
            "0",
            "--output-dir",
            str(tmp_path / "mp"),
        ]
    )
    assert proc.returncode != 0
    assert "Refusing to run" in proc.stderr or "Refusing to run" in proc.stdout


def test_multi_provider_cache_only_stage0(tmp_path: Path) -> None:
    out = tmp_path / "mp_cache"
    proc = _run(
        [
            "scripts/run_multi_provider_llm_robustness.py",
            "--stage",
            "0",
            "--cache-only",
            "--output-dir",
            str(out),
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    smoke = json.loads((out / "STAGE0_SMOKE_RESULTS.json").read_text())
    assert smoke
    assert all(s.get("category") == "cache_only_skipped" for s in smoke)
    manifest = json.loads((out / "run_manifest.json").read_text())
    assert manifest["config"]["mode"] == "cache_only"
    assert manifest["config"]["paid_api_calls_allowed"] is False


def test_multi_provider_overwrite_protection(tmp_path: Path) -> None:
    out = tmp_path / "mp_ow"
    out.mkdir()
    (out / "keep.txt").write_text("x")
    proc = _run(
        [
            "scripts/run_multi_provider_llm_robustness.py",
            "--stage",
            "0",
            "--cache-only",
            "--output-dir",
            str(out),
        ]
    )
    assert proc.returncode != 0
    assert "Refusing to overwrite" in (proc.stderr + proc.stdout)


def test_prior_robust_quick_smoke(tmp_path: Path) -> None:
    out = tmp_path / "prior_q"
    proc = _run(
        [
            "scripts/run_prior_robust_experiment.py",
            "--quick",
            "--output-dir",
            str(out),
            "--budget",
            "6",
            "--n-items",
            "5",
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (out / "rows.jsonl").exists()
    assert (out / "decision.json").exists()
    assert (out / "run_manifest.json").exists()
    assert (out / "config.json").exists()
    cfg = json.loads((out / "config.json").read_text())
    assert cfg["offline"] is True
    assert cfg["paid_api_calls"] == 0


def test_adaptive_quick_smoke(tmp_path: Path) -> None:
    out = tmp_path / "adapt_q"
    proc = _run(
        [
            "scripts/run_adaptive_acquisition_experiment.py",
            "--quick",
            "--output-dir",
            str(out),
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (out / "final_results.csv").exists()
    assert (out / "run_manifest.json").exists()
    cfg = json.loads((out / "config.json").read_text())
    assert cfg["paid_api_calls"] == 0
    assert cfg["offline"] is True


def test_reliability_quick_smoke(tmp_path: Path) -> None:
    out = tmp_path / "rel_q"
    proc = _run(
        [
            "scripts/run_reliability_aware_repair_experiment.py",
            "--quick",
            "--output-dir",
            str(out),
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (out / "synthetic_results.csv").exists()
    assert (out / "run_manifest.json").exists()


def test_linear_extension_quick_smoke(tmp_path: Path) -> None:
    out = tmp_path / "lin_q"
    proc = _run(
        [
            "scripts/run_linear_extension_extraction_experiment.py",
            "--quick",
            "--output-dir",
            str(out),
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (out / "per_instance_method_metrics.csv").exists()
    assert (out / "run_manifest.json").exists()
    assert (out / "AUDIT.md").exists()
    audit = (out / "AUDIT.md").read_text()
    assert "Method audit" in audit
    cfg = json.loads((out / "config.json").read_text())
    assert cfg["skip_real"] is True
    assert cfg["paid_api_calls"] == 0


def test_adaptive_unknown_policy_fails(tmp_path: Path) -> None:
    proc = _run(
        [
            "scripts/run_adaptive_acquisition_experiment.py",
            "--quick",
            "--policies",
            "not_a_real_policy",
            "--output-dir",
            str(tmp_path / "bad"),
        ]
    )
    assert proc.returncode != 0
    assert "Unknown policies" in (proc.stderr + proc.stdout)
