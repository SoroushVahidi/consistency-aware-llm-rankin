#!/usr/bin/env python3
"""
run_cloud_validation.py
========================
Canonical, repo-native release-validation entry point. Replaces reliance on
GitHub-hosted Actions (currently blocked by an account billing/spending-limit
issue unrelated to code correctness -- see docs/PROJECT_STATUS.md) with a
reproducible validation that runs entirely on this machine (or any Linux
cloud host with this repo cloned).

Never relies on the caller's active virtual environment: every tier creates
its own fresh, isolated venv under the run directory and invokes that venv's
python/pip explicitly.

Tiers (mapped 1:1 onto .github/workflows/ci.yml's two jobs, plus two new
local-only tiers that job never covered):

- core:      mirrors ci.yml's `tests` job exactly -- installs `.[dev,llm]`
             (no `[exact]`, no gurobipy), runs the architecture/portability
             checkers, then bare `pytest`. SCIP-dependent tests are EXPECTED
             to skip in this tier (ci.yml's own comment says so); the gate
             is "no failures/errors", not zero-skip. Also runs packaging
             (sdist/wheel build + wheel-only install into a separate venv +
             import/CLI smoke) and the quick-start example, and the maintained
             repo validators (evidence/claims/links/secrets/ruff) that
             `make repo-ready` runs but ci.yml's `tests` job does not.
- solver:    mirrors ci.yml's `tests-solver-enabled` job -- installs
             `.[dev,exact,llm]` + gurobipy, reports PySCIPOpt/SCIP version,
             runs `make verify-env` equivalent, a dedicated Gurobi smoke test
             (safe: never prints credential values, only version + optimize
             status), then `make test-full` equivalent (pytest -q, REQUIRES
             zero skipped). This is the tier that produces the "1307 passed,
             64 deselected, 0 skipped, 0 failed" contract documented in
             docs/EXPERIMENTS.md and docs/PROJECT_STATUS.md.
- real-data: prepares BEIR/HotpotQA/BRIGHT datasets (network, ~3GB, resumable
             -- download_datasets.py/prepare_datasets.py already skip
             existing files unless --force) and runs the `real_data`-marked
             pytest tier (~64 tests). Never run implicitly by `all` unless
             datasets are already present and valid.
- all:       core, then solver, then real-data IF ALREADY PREPARED (report
             explicitly, never silently skip it without saying so).

Usage
-----
    python scripts/run_cloud_validation.py --tier core
    python scripts/run_cloud_validation.py --tier solver
    python scripts/run_cloud_validation.py --tier real-data
    python scripts/run_cloud_validation.py --tier all
    python scripts/run_cloud_validation.py --verify-run .cloud_validation_runs/<run_id>
    python scripts/run_cloud_validation.py --print-tmux-command --tier all

For any tier expected to exceed ~5 minutes (solver, real-data, all), run
under tmux -- use --print-tmux-command to get the exact command, or see
docs/EXPERIMENTS.md "Cloud validation".
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_ROOT = REPO_ROOT / ".cloud_validation_runs"

CORE_EXTRAS = "dev,llm"
SOLVER_EXTRAS = "dev,exact,llm"

REQUIRED_DATASETS = ("scidocs", "fiqa", "hotpotqa", "bright")


# ---------------------------------------------------------------------------
# Structured result types
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    name: str
    command: list[str]
    cwd: str
    returncode: int | None
    duration_s: float
    log_path: str
    status: str  # PASS | FAIL | ERROR | SKIPPED
    note: str = ""


@dataclass
class TierReport:
    tier: str
    steps: list[StepResult] = field(default_factory=list)
    skipped_reason: str = ""

    @property
    def overall_status(self) -> str:
        if self.skipped_reason:
            return "SKIPPED"
        if not self.steps:
            return "NOT_RUN"
        if any(s.status in ("FAIL", "ERROR") for s in self.steps):
            return "FAIL"
        return "PASS"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


class Runner:
    """Executes commands, logging each to its own file under the run dir.
    Never lets a command's raw stdout/stderr into the JSON summary --
    only curated, explicitly-extracted fields go there."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.logs_dir = run_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        name: str,
        cmd: list[str],
        *,
        cwd: Path | None = None,
        env: dict | None = None,
        timeout: float | None = None,
    ) -> StepResult:
        log_path = self.logs_dir / f"{name}.log"
        cwd = cwd or REPO_ROOT
        t0 = time.time()
        rc: int | None
        note = ""
        with log_path.open("w") as fh:
            fh.write(f"$ {' '.join(cmd)}\n(cwd={cwd})\n\n")
            fh.flush()
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(cwd),
                    env=env,
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                )
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                rc = None
                note = f"timed out after {timeout}s"
                fh.write(f"\n[run_cloud_validation] {note}\n")
            except FileNotFoundError as exc:
                rc = None
                note = f"command not found: {exc}"
                fh.write(f"\n[run_cloud_validation] {note}\n")
        duration = time.time() - t0
        status = "PASS" if rc == 0 else ("ERROR" if rc is None else "FAIL")
        result = StepResult(
            name=name,
            command=cmd,
            cwd=str(cwd),
            returncode=rc,
            duration_s=round(duration, 2),
            log_path=str(log_path.relative_to(self.run_dir)),
            status=status,
            note=note,
        )
        print(f"  [{status}] {name} ({result.duration_s}s)")
        return result


def make_venv(path: Path) -> str:
    subprocess.run([sys.executable, "-m", "venv", str(path)], check=True)
    return str(path / "bin" / "python")


def git_state() -> tuple[str, bool, str]:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout
    dirty = bool(status.strip())
    return sha, dirty, branch


def collect_environment_metadata() -> dict:
    du = shutil.disk_usage(REPO_ROOT)
    mem_total_gb = None
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    mem_total_gb = round(int(line.split()[1]) / 1e6, 1)
                    break
    except FileNotFoundError:
        pass
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "mem_total_gb": mem_total_gb,
        "disk_free_gb": round(du.free / 1e9, 1),
        "disk_total_gb": round(du.total / 1e9, 1),
    }


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def gurobi_smoke(python_exe: str) -> dict:
    """Never prints or returns credential values -- only package availability,
    version, and a tiny optimize-call status code."""
    script = (
        "import json, sys\n"
        "try:\n"
        "    import gurobipy as gp\n"
        "except ImportError:\n"
        "    r = {'available': False, 'reason': 'package_unavailable'}\n"
        "    print('__GUROBI_SMOKE__' + json.dumps(r))\n"
        "    sys.exit(0)\n"
        "try:\n"
        "    env = gp.Env(params={})\n"
        "    env.setParam('OutputFlag', 0)\n"
        "    m = gp.Model(env=env)\n"
        "    x = m.addVar(vtype='B')\n"
        "    m.setObjective(x, gp.GRB.MAXIMIZE)\n"
        "    m.optimize()\n"
        "    result = {'available': True, 'version': list(gp.gurobi.version()), "
        "'optimize_status': m.Status}\n"
        "    env.dispose()\n"
        "    print('__GUROBI_SMOKE__' + json.dumps(result))\n"
        "except Exception as e:\n"
        "    print('__GUROBI_SMOKE__' + json.dumps({'available': False, "
        "'reason': 'license_or_runtime_failure', 'error_type': type(e).__name__}))\n"
    )
    proc = subprocess.run([python_exe, "-c", script], capture_output=True, text=True, timeout=60)
    for line in proc.stdout.splitlines():
        if line.startswith("__GUROBI_SMOKE__"):
            try:
                return json.loads(line[len("__GUROBI_SMOKE__") :])
            except json.JSONDecodeError:
                pass
    return {"available": False, "reason": "unparseable_output"}


def dataset_prepared(name: str) -> bool:
    base = (
        REPO_ROOT / "data" / "processed" / "beir" / name
        if name in ("scidocs", "fiqa")
        else REPO_ROOT / "data" / "processed" / name
    )
    return (base / "queries.jsonl").exists() and (base / "documents.jsonl").exists()


def all_datasets_prepared() -> bool:
    return all(dataset_prepared(d) for d in REQUIRED_DATASETS)


# ---------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------


def run_packaging_steps(runner: Runner, source_python: str, work_dir: Path) -> list[StepResult]:
    """sdist+wheel build from the source venv, then install the built wheel
    into a brand-new, separate venv and smoke-test import + CLI entry point."""
    steps = []
    dist_dir = work_dir / "dist"
    steps.append(
        runner.run(
            "install_build_backend", [source_python, "-m", "pip", "install", "--quiet", "build"]
        )
    )
    steps.append(
        runner.run(
            "package_build_sdist_wheel",
            [source_python, "-m", "build", "--outdir", str(dist_dir)],
        )
    )
    wheel_venv_python = make_venv(work_dir / "venv_wheel_check")
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        steps.append(
            StepResult(
                "package_install_wheel",
                [],
                str(work_dir),
                1,
                0.0,
                "",
                "FAIL",
                note="no wheel found after build step",
            )
        )
        return steps
    wheel = wheels[-1]
    steps.append(
        runner.run(
            "package_install_wheel",
            [wheel_venv_python, "-m", "pip", "install", "--quiet", str(wheel)],
        )
    )
    steps.append(
        runner.run(
            "package_import_smoke",
            [
                wheel_venv_python,
                "-c",
                "import consistency_ranker; "
                "from consistency_ranker.mwfas_solver import solve; "
                "print('import OK')",
            ],
        )
    )
    steps.append(
        runner.run(
            "package_cli_smoke",
            [str(work_dir / "venv_wheel_check" / "bin" / "run-synthetic"), "--help"],
        )
    )
    return steps


def run_repo_validators(runner: Runner, python_exe: str) -> list[StepResult]:
    steps = [
        runner.run(
            "check_architecture_boundaries",
            [python_exe, "scripts/check_architecture_boundaries.py"],
        ),
        runner.run("check_active_portability", [python_exe, "scripts/check_active_portability.py"]),
        runner.run(
            "validate_canonical_evidence_manifest",
            [python_exe, "scripts/validate_canonical_evidence_manifest.py"],
        ),
        runner.run(
            "validate_claim_evidence_registry",
            [python_exe, "scripts/validate_claim_evidence_registry.py"],
        ),
        runner.run("validate_repo_clarity", [python_exe, "scripts/validate_repo_clarity.py"]),
        runner.run("validate_report_links", [python_exe, "scripts/validate_report_links.py"]),
        runner.run("secret_scan", [python_exe, "scripts/run_secret_scan.py"]),
    ]
    ruff_exe = python_exe.replace("/python", "/ruff")
    maintained_paths = [
        "scripts/check_active_portability.py",
        "scripts/check_architecture_boundaries.py",
        "scripts/check_repo_ready.py",
        "scripts/run_real_llm_clustered_reanalysis.py",
        "scripts/run_secret_scan.py",
        "scripts/validate_canonical_evidence_manifest.py",
        "scripts/validate_report_links.py",
        "src/consistency_ranker/experiment_cli.py",
        "src/consistency_ranker/provenance.py",
        "src/consistency_ranker/real_llm_reanalysis/population.py",
        "tests/test_active_portability.py",
        "tests/test_check_architecture_boundaries.py",
        "tests/test_check_repo_ready.py",
        "tests/test_cli_validation.py",
        "tests/test_experiment_cli.py",
        "tests/test_offline_validation_scripts.py",
        "tests/test_provenance.py",
        "tests/test_real_llm_clustered_reanalysis.py",
        "tests/test_secret_scan.py",
    ]
    steps.append(runner.run("ruff_maintained_scope", [ruff_exe, "check", *maintained_paths]))
    return steps


def run_core_tier(runner: Runner, work_dir: Path) -> TierReport:
    print("=== core tier (mirrors ci.yml 'tests' job) ===")
    report = TierReport(tier="core")
    venv_python = make_venv(work_dir / "venv_core")
    report.steps.append(
        runner.run(
            "pip_upgrade", [venv_python, "-m", "pip", "install", "--upgrade", "pip", "--quiet"]
        )
    )
    report.steps.append(
        runner.run(
            "install_requirements",
            [venv_python, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
        )
    )
    report.steps.append(
        runner.run(
            "install_editable_core",
            [venv_python, "-m", "pip", "install", "-e", f".[{CORE_EXTRAS}]", "--quiet"],
        )
    )
    report.steps.extend(run_repo_validators(runner, venv_python))
    report.steps.extend(run_packaging_steps(runner, venv_python, work_dir))
    smoke_out = work_dir / "quickstart_smoke_output"
    report.steps.append(
        runner.run(
            "quickstart_synthetic_example",
            [
                venv_python,
                "scripts/run_synthetic.py",
                "--n-items",
                "20",
                "--noise",
                "0.2",
                "--seed",
                "42",
                "--output-dir",
                str(smoke_out),
            ],
        )
    )
    # Bare `pytest`, exactly like ci.yml's `tests` job. SCIP-dependent tests
    # are EXPECTED to skip here (no [exact] extra installed) -- the gate is
    # "no failures/errors", checked by the caller via step.status, not skip
    # count.
    report.steps.append(runner.run("pytest_core", [venv_python, "-m", "pytest"], timeout=1800))
    return report


def run_solver_tier(runner: Runner, work_dir: Path) -> TierReport:
    print("=== solver tier (mirrors ci.yml 'tests-solver-enabled' job) ===")
    report = TierReport(tier="solver")
    venv_python = make_venv(work_dir / "venv_solver")
    report.steps.append(
        runner.run(
            "pip_upgrade", [venv_python, "-m", "pip", "install", "--upgrade", "pip", "--quiet"]
        )
    )
    report.steps.append(
        runner.run(
            "install_requirements",
            [venv_python, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
        )
    )
    report.steps.append(
        runner.run(
            "install_editable_solver",
            [venv_python, "-m", "pip", "install", "-e", f".[{SOLVER_EXTRAS}]", "--quiet"],
        )
    )
    report.steps.append(
        runner.run("install_gurobipy", [venv_python, "-m", "pip", "install", "gurobipy", "--quiet"])
    )
    report.steps.append(
        runner.run(
            "verify_env_solver_version",
            [
                venv_python,
                "-c",
                "from consistency_ranker.mwfas_solver import "
                "verify_canonical_solver_version as v; print('PySCIPOpt', v())",
            ],
        )
    )
    report.steps.extend(run_repo_validators(runner, venv_python))

    gurobi_info = gurobi_smoke(venv_python)
    gurobi_status = (
        "PASS"
        if gurobi_info.get("available") and gurobi_info.get("optimize_status") == 2
        else "FAIL"
    )
    report.steps.append(
        StepResult(
            "gurobi_smoke",
            [venv_python, "-c", "<gurobi smoke, see docstring>"],
            str(work_dir),
            0 if gurobi_status == "PASS" else 1,
            0.0,
            "",
            gurobi_status,
            note=json.dumps(gurobi_info),
        )
    )
    print(f"  [{gurobi_status}] gurobi_smoke ({json.dumps(gurobi_info)})")

    # `make test-full` equivalent: pytest -q, must show zero skipped.
    result = runner.run("pytest_solver_full", [venv_python, "-m", "pytest", "-q"], timeout=1800)
    log_text = (work_dir / "logs" / "pytest_solver_full.log").read_text(errors="replace")
    skipped = 0
    for line in log_text.splitlines():
        if " skipped" in line and ("passed" in line or "failed" in line):
            m = re.search(r"(\d+) skipped", line)
            if m:
                skipped = int(m.group(1))
    if result.status == "PASS" and skipped != 0:
        result.status = "FAIL"
        result.note = f"{skipped} test(s) skipped -- zero-skip contract violated"
    report.steps.append(result)
    return report


def run_real_data_tier(runner: Runner, work_dir: Path, *, prepare: bool) -> TierReport:
    print("=== real-data tier ===")
    report = TierReport(tier="real-data")
    if not prepare and not all_datasets_prepared():
        report.skipped_reason = (
            "datasets not already prepared under data/processed/ and --prepare-real-data "
            "was not passed; real-data tier explicitly NOT RUN (not a hidden skip)"
        )
        print(f"  SKIPPED: {report.skipped_reason}")
        return report

    venv_python = make_venv(work_dir / "venv_realdata")
    report.steps.append(
        runner.run(
            "pip_upgrade", [venv_python, "-m", "pip", "install", "--upgrade", "pip", "--quiet"]
        )
    )
    report.steps.append(
        runner.run(
            "install_requirements",
            [venv_python, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
        )
    )
    report.steps.append(
        runner.run(
            "install_editable_realdata",
            [venv_python, "-m", "pip", "install", "-e", f".[{CORE_EXTRAS}]", "--quiet"],
        )
    )

    if not all_datasets_prepared():
        report.steps.append(
            runner.run(
                "download_datasets",
                [venv_python, "scripts/download_datasets.py", "--dataset", "all"],
                timeout=3600,
            )
        )
        report.steps.append(
            runner.run(
                "prepare_datasets",
                [venv_python, "scripts/prepare_datasets.py", "--dataset", "all"],
                timeout=3600,
            )
        )

    disk_usage = {}
    for name in REQUIRED_DATASETS:
        base = (
            REPO_ROOT
            / "data"
            / "processed"
            / ("beir/" + name if name in ("scidocs", "fiqa") else name)
        )
        if base.exists():
            total = sum(f.stat().st_size for f in base.rglob("*") if f.is_file())
            disk_usage[name] = round(total / 1e6, 1)
    (work_dir / "real_data_disk_usage_mb.json").write_text(json.dumps(disk_usage, indent=2))

    report.steps.append(
        runner.run(
            "pytest_real_data", [venv_python, "-m", "pytest", "-q", "-m", "real_data"], timeout=1800
        )
    )
    return report


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def write_summary(
    run_dir: Path,
    run_id: str,
    sha: str,
    dirty: bool,
    branch: str,
    env_meta: dict,
    tiers: list[TierReport],
    allow_dirty: bool,
) -> dict:
    summary = {
        "run_id": run_id,
        "commit_sha": sha,
        "branch": branch,
        "dirty_worktree": dirty,
        "allow_dirty_used": allow_dirty,
        "environment": env_meta,
        "tiers": [
            {
                "tier": t.tier,
                "overall_status": t.overall_status,
                "skipped_reason": t.skipped_reason,
                "steps": [dataclasses.asdict(s) for s in t.steps],
            }
            for t in tiers
        ],
    }
    statuses = [t.overall_status for t in tiers if t.overall_status != "SKIPPED"]
    summary["overall_status"] = (
        "PASS"
        if statuses and all(s == "PASS" for s in statuses)
        else ("FAIL" if any(s == "FAIL" for s in statuses) else "NOT_RUN")
    )
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    (run_dir / "environment.json").write_text(json.dumps(env_meta, indent=2))
    (run_dir / "commands.json").write_text(
        json.dumps([dataclasses.asdict(s) for t in tiers for s in t.steps], indent=2)
    )

    lines = [
        f"# Cloud Validation Run {run_id}",
        "",
        f"- Commit: `{sha}` (branch `{branch}`, dirty={dirty})",
        f"- Overall status: **{summary['overall_status']}**",
        f"- Python: {env_meta.get('python_version')}, CPUs: {env_meta.get('cpu_count')}, "
        f"Mem: {env_meta.get('mem_total_gb')}GB, Disk free: {env_meta.get('disk_free_gb')}GB",
        "",
    ]
    for t in tiers:
        lines.append(f"## Tier: {t.tier} -- {t.overall_status}")
        if t.skipped_reason:
            lines.append(f"_{t.skipped_reason}_")
        for s in t.steps:
            lines.append(
                f"- `{s.status}` **{s.name}** ({s.duration_s}s) -- `{s.log_path}`"
                + (f" -- {s.note}" if s.note else "")
            )
        lines.append("")
    (run_dir / "SUMMARY.md").write_text("\n".join(lines))
    return summary


def verify_run(run_dir: Path) -> int:
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        print(f"FAIL: {summary_path} not found")
        return 1
    summary = json.loads(summary_path.read_text())
    problems = []
    for tier in summary.get("tiers", []):
        for step in tier.get("steps", []):
            log_path = run_dir / step["log_path"] if step["log_path"] else None
            if log_path and not log_path.exists():
                problems.append(f"{tier['tier']}/{step['name']}: log file missing: {log_path}")
        recomputed = (
            "SKIPPED"
            if tier.get("skipped_reason")
            else (
                "NOT_RUN"
                if not tier.get("steps")
                else (
                    "FAIL"
                    if any(s["status"] in ("FAIL", "ERROR") for s in tier["steps"])
                    else "PASS"
                )
            )
        )
        if recomputed != tier["overall_status"]:
            problems.append(
                f"{tier['tier']}: recorded overall_status={tier['overall_status']!r} "
                f"does not match recomputed={recomputed!r}"
            )
    if problems:
        print(f"FAIL: {len(problems)} integrity problem(s) in {run_dir}:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK: {run_dir} is internally consistent ({len(summary.get('tiers', []))} tier(s))")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--tier", choices=["core", "solver", "real-data", "all"], default="core")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Diagnostic override: run even with a dirty worktree",
    )
    parser.add_argument(
        "--prepare-real-data",
        action="store_true",
        help="For --tier real-data/all: download+prepare datasets if not already present",
    )
    parser.add_argument(
        "--verify-run",
        type=str,
        default=None,
        help="Verify an existing run directory's integrity and exit",
    )
    parser.add_argument(
        "--print-tmux-command",
        action="store_true",
        help="Print the recommended tmux command for this invocation and exit",
    )
    args = parser.parse_args()

    if args.verify_run:
        return verify_run(Path(args.verify_run))

    if args.print_tmux_command:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        session = f"cloud_validation_{args.tier}_{ts}"
        log = f".cloud_validation_runs/tmux_{session}.log"
        cmd = (
            f"tmux new-session -d -s {session} "
            f'"cd {REPO_ROOT} && source .venv/bin/activate 2>/dev/null; '
            f"python scripts/run_cloud_validation.py --tier {args.tier}"
            f"{' --prepare-real-data' if args.prepare_real_data else ''} "
            f'2>&1 | tee {log}; echo EXIT_CODE=$? >> {log}"'
        )
        print(cmd)
        return 0

    sha, dirty, branch = git_state()
    if dirty and not args.allow_dirty:
        print(
            "REFUSING to run release-mode validation on a dirty worktree.\n"
            "Commit or stash changes first, or pass --allow-dirty for a diagnostic run."
        )
        return 1

    RUNS_ROOT.mkdir(exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(parents=True)
    runner = Runner(run_dir)
    env_meta = collect_environment_metadata()

    print(f"Cloud validation run {run_id} -- commit {sha[:12]} (dirty={dirty}) -- tier={args.tier}")
    print(f"Run directory: {run_dir}")

    tiers: list[TierReport] = []
    if args.tier in ("core", "all"):
        tiers.append(run_core_tier(runner, run_dir))
    if args.tier in ("solver", "all"):
        tiers.append(run_solver_tier(runner, run_dir))
    if args.tier == "real-data":
        tiers.append(run_real_data_tier(runner, run_dir, prepare=args.prepare_real_data))
    elif args.tier == "all":
        tiers.append(run_real_data_tier(runner, run_dir, prepare=args.prepare_real_data))

    summary = write_summary(run_dir, run_id, sha, dirty, branch, env_meta, tiers, args.allow_dirty)
    print(f"\nOverall status: {summary['overall_status']}")
    print(f"Full report: {run_dir / 'SUMMARY.md'}")
    return 0 if summary["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
