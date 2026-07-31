"""
run_offline_validation_workflow.py
=====================================
Repo Stage 4 (2026-07-30): the single canonical offline reproduction
workflow for this repository. Runs entirely from data already committed to
the repository -- makes NO external API calls, requires NO network access,
and never modifies any committed canonical output (all reproduction runs
write to a fresh temporary directory, compared against but never written
over the committed canonical directory; see
canonical_output_protection_report.md).

Full run (`--only` omitted) executes, in order:
  1. verify-env      -- Python + PySCIPOpt version check (mirrors `make verify-env`)
  2. input-availability -- confirm every source directory both canonical
     workflows read from actually exists
  3. reproduce-ir-audit -- re-run scripts/run_ir_evidence_audit.py into a
     temp dir, diff its deterministic outputs against the committed
     reports/ir_evidence_audit_20260729T182949Z/
  4. reproduce-real-llm-reanalysis -- re-run
     scripts/run_real_llm_clustered_reanalysis.py into a temp dir, diff
     against reports/real_llm_clustered_reanalysis_20260730T023745Z/
  5. regression-tests -- `.venv/bin/pytest -q` (skip with --skip-tests for
     fast iteration; full run takes ~3 minutes)
  6. evidence-manifest-validation -- scripts/validate_canonical_evidence_manifest.py
  7. report-link-validation -- scripts/validate_report_links.py
  8. final readiness summary

`--only {ir-audit,real-llm}` restricts the run to steps 1-2 plus the one
named reproduction step (used by `make reproduce-ir-audit` /
`make reproduce-real-llm-reanalysis`).
"""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from consistency_ranker.mwfas_solver import (  # noqa: E402
    UnsupportedSolverVersionError,
    verify_canonical_solver_version,
)
from consistency_ranker.real_llm_reanalysis import population as llm_population  # noqa: E402
from scripts import (  # noqa: E402
    run_ir_evidence_audit,
    run_real_llm_clustered_reanalysis,
    validate_canonical_evidence_manifest,
    validate_report_links,
)

IR_AUDIT_CANONICAL_DIR = _REPO_ROOT / "reports/ir_evidence_audit_20260729T182949Z"
IR_AUDIT_COMPARE_FILES = [
    "unified_configuration_results.csv",
    "structure_utility_associations.csv",
    "baseline_verification.csv",
    "cutoff_robustness.csv",
    "tables/publication_table_structure_vs_utility.csv",
    "tables/publication_table_structure_vs_utility.md",
]

REAL_LLM_CANONICAL_DIR = _REPO_ROOT / "reports/real_llm_clustered_reanalysis_20260730T023745Z"
REAL_LLM_COMPARE_FILES = [
    "analysis_population_manifest.csv",
    "query_level_aggregates.csv",
    "repair_frontier_clustered_results.csv",
    "repair_frontier_clustered_summary.json",
    "extraction_clustered_results.csv",
    "repair_diagnostic_clustered_results.csv",
    "repair_diagnostic_overall_delta.json",
    "repair_diagnostic_grouped_cv_status.json",
    "multiple_comparison_families.csv",
    "per_query_effects.csv",
    "frontier_reconstruction_verification.json",
]

IR_AUDIT_SOURCE_DIRS = [
    run_ir_evidence_audit.CALIBRATED_CORE,
    run_ir_evidence_audit.HEADROOM_419,
    run_ir_evidence_audit.EXACT_ILP,
    run_ir_evidence_audit.POOL_CUTOFF,
    run_ir_evidence_audit.BASELINE_FAIRNESS,
    run_ir_evidence_audit.REPAIR_FRONTIER_DIR,
    run_ir_evidence_audit.EXTRACTION_DIR,
    run_ir_evidence_audit.REPAIR_DIAGNOSTIC_DIR,
]

REAL_LLM_SOURCE_DIRS = [
    llm_population.FRONTIER_DIR,
    llm_population.EXTRACTION_DIR,
    llm_population.DIAGNOSTIC_DIR,
]


def step_verify_env() -> dict:
    result = {"step": "verify-env", "python_version": sys.version}
    try:
        result["solver_version"] = verify_canonical_solver_version()
        result["status"] = "PASS"
    except UnsupportedSolverVersionError as exc:
        result["solver_version"] = "MISMATCH_OR_MISSING"
        result["detail"] = str(exc)
        result["status"] = "FAIL"
    return result


def step_input_availability(source_dirs: list[Path], label: str) -> dict:
    checked = [{"path": str(p.relative_to(_REPO_ROOT)), "exists": p.exists()} for p in source_dirs]
    n_missing = sum(1 for c in checked if not c["exists"])
    return {
        "step": f"input-availability:{label}",
        "status": "PASS" if n_missing == 0 else "FAIL",
        "n_missing": n_missing,
        "checked": checked,
    }


def _compare_files(canonical_dir: Path, reproduced_dir: Path, relative_files: list[str]) -> dict:
    comparisons = []
    for rel in relative_files:
        canonical_file = canonical_dir / rel
        reproduced_file = reproduced_dir / rel
        if not canonical_file.exists() or not reproduced_file.exists():
            comparisons.append({
                "file": rel,
                "match": False,
                "reason": "one or both files missing",
                "canonical_exists": canonical_file.exists(),
                "reproduced_exists": reproduced_file.exists(),
            })
            continue
        match = filecmp.cmp(canonical_file, reproduced_file, shallow=False)
        comparisons.append({"file": rel, "match": match})
    n_mismatch = sum(1 for c in comparisons if not c["match"])
    return {
        "status": "PASS" if n_mismatch == 0 else "FAIL",
        "n_files_compared": len(comparisons),
        "n_mismatches": n_mismatch,
        "comparisons": [c for c in comparisons if not c["match"]] if n_mismatch else [],
    }


def step_reproduce_ir_audit(keep_temp: bool) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="offline_validation_ir_audit_"))
    try:
        run_ir_evidence_audit.run(tmp, allow_overwrite=True)
        comparison = _compare_files(IR_AUDIT_CANONICAL_DIR, tmp, IR_AUDIT_COMPARE_FILES)
        comparison["step"] = "reproduce-ir-audit"
        comparison["temp_dir"] = str(tmp) if keep_temp else None
        return comparison
    finally:
        if not keep_temp:
            shutil.rmtree(tmp, ignore_errors=True)


def step_reproduce_real_llm(keep_temp: bool) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="offline_validation_real_llm_"))
    try:
        run_real_llm_clustered_reanalysis.run(tmp, allow_overwrite=True)
        comparison = _compare_files(REAL_LLM_CANONICAL_DIR, tmp, REAL_LLM_COMPARE_FILES)
        comparison["step"] = "reproduce-real-llm-reanalysis"
        comparison["temp_dir"] = str(tmp) if keep_temp else None
        return comparison
    finally:
        if not keep_temp:
            shutil.rmtree(tmp, ignore_errors=True)


def step_regression_tests() -> dict:
    proc = subprocess.run(
        [str(_REPO_ROOT / ".venv/bin/pytest"), "-q"],
        cwd=_REPO_ROOT, capture_output=True, text=True,
    )
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    return {
        "step": "regression-tests",
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "summary_line": tail,
        "returncode": proc.returncode,
    }


def step_evidence_manifest_validation() -> dict:
    result = validate_canonical_evidence_manifest.run()
    return {
        "step": "evidence-manifest-validation",
        "status": result["overall_status"],
        "detail": result,
    }


def step_report_link_validation() -> dict:
    result = validate_report_links.run(validate_report_links.DEFAULT_FILES)
    return {"step": "report-link-validation", "status": result["overall_status"], "detail": result}


def run_only(which: str, keep_temp: bool) -> dict:
    steps = [step_verify_env()]
    if which == "ir-audit":
        steps.append(step_input_availability(IR_AUDIT_SOURCE_DIRS, "ir-audit"))
        steps.append(step_reproduce_ir_audit(keep_temp))
    elif which == "real-llm":
        steps.append(step_input_availability(REAL_LLM_SOURCE_DIRS, "real-llm"))
        steps.append(step_reproduce_real_llm(keep_temp))
    else:
        raise ValueError(f"Unknown --only value: {which}")
    overall = "PASS" if all(s["status"] == "PASS" for s in steps) else "FAIL"
    return {"overall_status": overall, "steps": steps}


def run_full(keep_temp: bool, skip_tests: bool) -> dict:
    steps = [
        step_verify_env(),
        step_input_availability(IR_AUDIT_SOURCE_DIRS, "ir-audit"),
        step_input_availability(REAL_LLM_SOURCE_DIRS, "real-llm"),
        step_reproduce_ir_audit(keep_temp),
        step_reproduce_real_llm(keep_temp),
    ]
    if skip_tests:
        steps.append({
            "step": "regression-tests", "status": "SKIPPED", "reason": "--skip-tests passed",
        })
    else:
        steps.append(step_regression_tests())
    steps.append(step_evidence_manifest_validation())
    steps.append(step_report_link_validation())

    hard_statuses = [s["status"] for s in steps if s["status"] != "SKIPPED"]
    overall = "PASS" if all(s == "PASS" for s in hard_statuses) else "FAIL"
    return {"overall_status": overall, "steps": steps}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["ir-audit", "real-llm"], default=None)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument(
        "--keep-temp", action="store_true",
        help="Keep the temporary reproduction directories instead of deleting them.",
    )
    args = parser.parse_args()

    if args.only:
        outcome = run_only(args.only, args.keep_temp)
    else:
        outcome = run_full(args.keep_temp, args.skip_tests)

    print(json.dumps(outcome, indent=2, default=str))
    sys.exit(0 if outcome["overall_status"] == "PASS" else 1)
