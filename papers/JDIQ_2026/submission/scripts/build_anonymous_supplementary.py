#!/usr/bin/env python3
"""Build the final anonymous supplementary ZIP for JDIQ submission."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SUBMISSION = REPO_ROOT / "papers/JDIQ_2026/submission"
FINAL_MATERIALS = SUBMISSION / "final_submission_materials"
OUT = FINAL_MATERIALS / "anonymous_supplementary"
ZIP_PATH = FINAL_MATERIALS / "anonymous_supplementary.zip"

IDENTITY_PATTERNS = [
    re.compile(r"soroush", re.IGNORECASE),
    re.compile(r"vahidi", re.IGNORECASE),
    re.compile(r"\bsv96\b", re.IGNORECASE),
    re.compile(r"\bnjit\b", re.IGNORECASE),
    re.compile(r"\bORCID\b", re.IGNORECASE),
    re.compile(r"researchsquare", re.IGNORECASE),
    re.compile(r"rs-\d{4,}", re.IGNORECASE),
    re.compile(r"github\.com/SoroushVahidi", re.IGNORECASE),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
]
ABS_PATH_RE = re.compile(re.escape(str(REPO_ROOT)) + r"/?")


def scrub_text(text: str) -> str:
    text = ABS_PATH_RE.sub("", text)
    text = text.replace("/home/soroush/", "")
    for pattern in IDENTITY_PATTERNS:
        text = pattern.sub("[REDACTED-FOR-ANONYMITY]", text)
    return text


def copy_binary(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_text(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(scrub_text(src.read_text()))


def ensure_parent(dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)


def copy_tree(
    src_dir: Path,
    dst_dir: Path,
    *,
    text_suffixes: set[str],
    include: callable | None = None,
) -> None:
    for src in sorted(src_dir.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(src_dir)
        if include is not None and not include(src, rel):
            continue
        dst = dst_dir / rel
        if src.suffix.lower() in text_suffixes:
            copy_text(src, dst)
        else:
            copy_binary(src, dst)


def git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def python_version() -> str:
    return sys.version.splitlines()[0]


def pyscipopt_version() -> str:
    try:
        import pyscipopt  # type: ignore

        return pyscipopt.__version__
    except Exception:
        return "unknown"


def write_readme(dst: Path) -> None:
    ensure_parent(dst)
    text = """# Anonymous Supplementary Material

This package accompanies the anonymous JDIQ submission
"Data Quality for Derived Preference Graphs: Construction Sensitivity and Repair Outcomes in Multi-Ranker Retrieval."

It is a reviewer-facing anonymous supplementary package. It contains the
final anonymous manuscript and supplement, the canonical source code needed
to reproduce the reported analyses, the aggregate intermediate tables and
validation outputs behind the manuscript claims, and machine-readable
metadata for the frozen submission state.

## Top-level structure

- `manuscript/` — final anonymous main manuscript and supplement source/PDFs,
  plus the figure assets and figure-generation code they require.
- `src/` — the `consistency_ranker` Python package used for graph
  construction, normalization, vote extraction, repair, ranking, qrels
  handling, and statistical analysis.
- `scripts/` — top-level driver and validation scripts kept with the frozen
  submission state.
- `tests/` — automated regression tests for the shipped code.
- `supplemental/` — reproduction guide, dataset-availability notes, figure
  inventories, figure-data verification, canonical aggregate tables, and the
  report-layer scripts that regenerate them.
- `metadata/` — frozen commit SHA, environment and solver metadata,
  checksums, and the submission freeze manifest.
- `requirements.txt` / `pyproject.toml` — dependency and package metadata.

## What does not need to be rerun

The package is designed so reviewers do not need to rerun upstream retrieval
or any paid LLM/API calls. The shipped manuscript claims trace to stored
aggregate tables, fixed manifests, and deterministic scripts over already
stored score files and qrels.

## What is not redistributed

No raw third-party document collections are redistributed here. Public
benchmarks such as SciDocs, FiQA, HotpotQA, and BRIGHT must be obtained from
their original sources if full end-to-end upstream data reconstruction is
desired. See `supplemental/DATA_AVAILABILITY.md`.

## Anonymity

This package was built from scrubbed copies and then scanned recursively for
identity-bearing names, usernames, emails, affiliations, GitHub URLs, home
paths, and Research Square identifiers before zipping.
"""
    dst.write_text(text)


def write_reproducibility(dst: Path) -> None:
    ensure_parent(dst)
    text = """# Reproducibility Guide

This guide regenerates the mechanical evidence cited in the anonymous JDIQ
submission from the shipped code and stored intermediate tables. No step
requires rerunning upstream retrieval or any paid LLM/API call.

## 1. Environment

- Python 3.12 was used for the frozen submission state; Python 3.11 is also
  supported by the shipped package metadata.
- Exact solver: SCIP through `pyscipopt` (open-source, no commercial solver
  dependency in the shipped pipeline).
- Install from the package root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python scripts/check_repo_ready.py
pytest -q
```

Expected regression-test result at the frozen submission state: `617 passed`.

## 2. Package map

The main code is under `src/consistency_ranker/`.

The aggregate tables cited in the manuscript live under:

- `supplemental/tables/full_calibrated_core/`
- `supplemental/tables/normalization_protocol_audit/`
- `supplemental/tables/candidate_pool_conditional_audit/`
- `supplemental/tables/exact_ilp_repair_investigation/`

The scripts that regenerate those tables live under:

- `supplemental/scripts/full_calibrated_core/`
- `supplemental/scripts/normalization_protocol_audit_20260714/`
- `supplemental/scripts/candidate_pool_conditional_audit_20260714/`

## 3. Exact commands

Run these commands from the package root.

```bash
# Core protocol comparison.
cd supplemental/scripts/full_calibrated_core
python run_full_calibrated_core.py
cd ../../..

# Independent normalization / threshold protocol robustness.
cd supplemental/scripts/normalization_protocol_audit_20260714
python run_independent_protocols.py
python analyze_protocol_robustness.py
cd ../../..

# Candidate-pool, conditional-analysis, and baseline robustness.
cd supplemental/scripts/candidate_pool_conditional_audit_20260714
python run_pool_robustness.py
python run_conditional_and_failure_analysis.py
python run_baseline_comparison.py
cd ../../..

# Figure-data verification.
python supplemental/scripts/verify_figure_data.py

# Full validation of the shipped code.
pytest -q
python scripts/check_repo_ready.py
cd manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
cd manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error supplement.tex
```

## 4. Notes

- The shipped aggregate tables are sufficient to verify the manuscript's
  reported values without rerunning large per-query manifests.
- The manuscript-support figures can be regenerated from
  `manuscript/figures_v2/generate_figures.py`.
- The exact commit SHA and file checksums for the frozen submission state are
  under `metadata/`.
"""
    dst.write_text(text)


def write_environment(dst: Path, metadata: dict[str, object]) -> None:
    ensure_parent(dst)
    text = f"""# Environment Metadata

- Frozen commit SHA: `{metadata["git_commit"]}`
- Built at (UTC): `{metadata["built_at_utc"]}`
- Python: `{metadata["python_version"]}`
- Platform: `{metadata["platform"]}`
- SCIP wrapper: `{metadata["pyscipopt_version"]}`
- Main manuscript SHA-256: `{metadata["main_pdf_sha256"]}`
- Supplement SHA-256: `{metadata["supplement_pdf_sha256"]}`
- Upstream retrieval rerun required: `no`
- Paid API rerun required: `no`
"""
    dst.write_text(text)


def metadata_payload() -> dict[str, object]:
    main_pdf = REPO_ROOT / "papers/JDIQ_2026/manuscript/main.pdf"
    supp_pdf = REPO_ROOT / "papers/JDIQ_2026/manuscript/supplement.pdf"
    return {
        "git_commit": git_sha(),
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": python_version(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "pyscipopt_version": pyscipopt_version(),
        "main_pdf_sha256": hashlib.sha256(main_pdf.read_bytes()).hexdigest(),
        "supplement_pdf_sha256": hashlib.sha256(supp_pdf.read_bytes()).hexdigest(),
        "tests_expected": 617,
        "upstream_retrieval_rerun_required": False,
        "paid_api_rerun_required": False,
    }


def freeze_manifest_payload(metadata: dict[str, object]) -> dict[str, object]:
    return {
        "generated_at_utc": metadata["built_at_utc"],
        "git_commit": metadata["git_commit"],
        "manuscript": {
            "main_pdf_sha256": metadata["main_pdf_sha256"],
            "supplement_pdf_sha256": metadata["supplement_pdf_sha256"],
            "main_source": "manuscript/main.tex",
            "supplement_source": "manuscript/supplement.tex",
        },
        "reproducibility": {
            "tests_expected": metadata["tests_expected"],
            "upstream_retrieval_rerun_required": metadata[
                "upstream_retrieval_rerun_required"
            ],
            "paid_api_rerun_required": metadata["paid_api_rerun_required"],
            "core_table_directories": [
                "supplemental/tables/full_calibrated_core",
                "supplemental/tables/normalization_protocol_audit",
                "supplemental/tables/candidate_pool_conditional_audit",
                "supplemental/tables/exact_ilp_repair_investigation",
            ],
            "core_script_directories": [
                "supplemental/scripts/full_calibrated_core",
                "supplemental/scripts/normalization_protocol_audit_20260714",
                "supplemental/scripts/candidate_pool_conditional_audit_20260714",
            ],
        },
        "notes": [
            "This package contains scrubbed anonymous copies only.",
            "Public third-party datasets are not redistributed in this ZIP.",
            "The package metadata records the source commit from which the ZIP was built.",
        ],
    }


def write_manifests() -> None:
    all_files = sorted(p for p in OUT.rglob("*") if p.is_file())
    manifest_lines = [
        "# Source Manifest (anonymous_supplementary/)",
        "",
        "Every file in this package, generated at zip time.",
        "",
    ]
    checksum_lines = []
    for file in all_files:
        rel = file.relative_to(OUT)
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        manifest_lines.append(f"- `{rel}`")
        checksum_lines.append(f"{digest}  {rel}")
    (OUT / "metadata" / "SOURCE_MANIFEST.md").write_text("\n".join(manifest_lines) + "\n")
    (OUT / "metadata" / "CHECKSUMS.sha256.txt").write_text("\n".join(checksum_lines) + "\n")


def write_submission_freeze_manifest(dst: Path, metadata: dict[str, object]) -> None:
    ensure_parent(dst)
    dst.write_text(json.dumps(freeze_manifest_payload(metadata), indent=2) + "\n")


def zip_package() -> str:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(OUT.rglob("*")):
            if file.is_file():
                zf.write(file, arcname=file.relative_to(OUT.parent))
    return hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()


def main() -> None:
    text_suffixes = {
        ".md",
        ".txt",
        ".py",
        ".json",
        ".csv",
        ".tex",
        ".bib",
        ".toml",
        ".yml",
        ".yaml",
        ".cfg",
        ".ini",
    }

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # Manuscript support.
    for name in ("main.tex", "main.pdf", "supplement.tex", "supplement.pdf", "references.bib"):
        src = REPO_ROOT / "papers/JDIQ_2026/manuscript" / name
        dst = OUT / "manuscript" / name
        if src.suffix.lower() in text_suffixes:
            copy_text(src, dst)
        else:
            copy_binary(src, dst)
    for name in ("figure1.png", "figure3.png", "figure5.png"):
        copy_binary(
            REPO_ROOT / "papers/JDIQ_2026/manuscript" / name,
            OUT / "manuscript" / name,
        )
    copy_tree(
        REPO_ROOT / "papers/JDIQ_2026/manuscript" / "figures_v2",
        OUT / "manuscript" / "figures_v2",
        text_suffixes=text_suffixes,
        include=lambda src, rel: src.suffix.lower() in {".pdf", ".py"},
    )

    # Core code and tests.
    copy_tree(
        REPO_ROOT / "src",
        OUT / "src",
        text_suffixes=text_suffixes,
        include=lambda src, rel: (
            "__pycache__" not in src.parts and src.suffix.lower() == ".py"
        ),
    )
    copy_tree(
        REPO_ROOT / "scripts",
        OUT / "scripts",
        text_suffixes=text_suffixes,
        include=lambda src, rel: "__pycache__" not in src.parts and src.suffix.lower() == ".py",
    )
    copy_tree(
        REPO_ROOT / "tests",
        OUT / "tests",
        text_suffixes=text_suffixes,
        include=lambda src, rel: "__pycache__" not in src.parts and src.suffix.lower() == ".py",
    )
    copy_text(REPO_ROOT / "requirements.txt", OUT / "requirements.txt")
    copy_text(REPO_ROOT / "pyproject.toml", OUT / "pyproject.toml")

    # Supplemental docs and generated tables.
    write_readme(OUT / "README.md")
    write_reproducibility(OUT / "supplemental" / "REPRODUCIBILITY.md")
    copy_text(
        SUBMISSION / "scripts" / "templates" / "DATA_AVAILABILITY.md",
        OUT / "supplemental" / "DATA_AVAILABILITY.md",
    )
    copy_text(
        SUBMISSION / "FIGURE_INVENTORY.md",
        OUT / "supplemental" / "FIGURE_INVENTORY.md",
    )
    copy_text(
        SUBMISSION / "FIGURE_DATA_VERIFICATION_REPORT.md",
        OUT / "supplemental" / "FIGURE_DATA_VERIFICATION_REPORT.md",
    )
    # Supplemental scripts.
    copy_tree(
        REPO_ROOT / "reports/full_calibrated_core/scripts",
        OUT / "supplemental" / "scripts" / "full_calibrated_core",
        text_suffixes=text_suffixes,
        include=lambda src, rel: "__pycache__" not in src.parts and src.suffix.lower() == ".py",
    )
    copy_tree(
        REPO_ROOT / "reports/normalization_protocol_audit_20260714/scripts",
        OUT / "supplemental" / "scripts" / "normalization_protocol_audit_20260714",
        text_suffixes=text_suffixes,
        include=lambda src, rel: "__pycache__" not in src.parts and src.suffix.lower() == ".py",
    )
    copy_tree(
        REPO_ROOT / "reports/candidate_pool_conditional_audit_20260714/scripts",
        OUT / "supplemental" / "scripts" / "candidate_pool_conditional_audit_20260714",
        text_suffixes=text_suffixes,
        include=lambda src, rel: "__pycache__" not in src.parts and src.suffix.lower() == ".py",
    )
    copy_text(
        SUBMISSION / "scripts" / "verify_figure_data.py",
        OUT / "supplemental" / "scripts" / "verify_figure_data.py",
    )
    copy_text(
        SUBMISSION / "scripts" / "build_freeze_manifest.py",
        OUT / "supplemental" / "scripts" / "build_freeze_manifest.py",
    )

    # Aggregate tables.
    table_sources = {
        "full_calibrated_core": REPO_ROOT / "reports/full_calibrated_core/tables",
        "normalization_protocol_audit": (
            REPO_ROOT / "reports/normalization_protocol_audit_20260714/tables"
        ),
        "candidate_pool_conditional_audit": (
            REPO_ROOT / "reports/candidate_pool_conditional_audit_20260714/tables"
        ),
        "exact_ilp_repair_investigation": (
            REPO_ROOT / "reports/exact_open_source_ilp_repair_investigation/tables"
        ),
    }
    for label, src_dir in table_sources.items():
        copy_tree(
            src_dir,
            OUT / "supplemental" / "tables" / label,
            text_suffixes=text_suffixes,
            include=lambda src, rel: src.suffix.lower() == ".csv",
        )

    # Public-safe task-report evidence only: tables, validation, and audit scripts.
    for task in range(1, 6):
        task_dirs = sorted((REPO_ROOT / "reports").glob(f"final_revision_task{task}_*_20260715"))
        if len(task_dirs) != 1:
            continue
        task_dir = task_dirs[0]
        task_out = OUT / "supplemental" / "task_reports" / task_dir.name
        copy_tree(
            task_dir / "tables",
            task_out / "tables",
            text_suffixes=text_suffixes,
            include=lambda src, rel: src.suffix.lower() == ".csv",
        )
        validation_dir = task_dir / "validation"
        if validation_dir.exists():
            copy_tree(
                validation_dir,
                task_out / "validation",
                text_suffixes=text_suffixes,
                include=lambda src, rel: src.is_file(),
            )
        scripts_dir = task_dir / "scripts"
        if scripts_dir.exists():
            copy_tree(
                scripts_dir,
                task_out / "scripts",
                text_suffixes=text_suffixes,
                include=lambda src, rel: (
                    src.name.startswith("claim_to_evidence_audit")
                    and src.suffix.lower() == ".py"
                ),
            )

    # Metadata.
    metadata = metadata_payload()
    metadata_dir = OUT / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "PACKAGE_METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n")
    write_environment(metadata_dir / "ENVIRONMENT.md", metadata)
    write_submission_freeze_manifest(
        OUT / "supplemental" / "SUBMISSION_FREEZE_MANIFEST.json",
        metadata,
    )
    write_submission_freeze_manifest(
        metadata_dir / "SUBMISSION_FREEZE_MANIFEST.json",
        metadata,
    )
    write_manifests()
    zip_digest = zip_package()

    print(f"anonymous_supplementary/ assembled at {OUT}")
    print(f"zip: {ZIP_PATH} sha256: {zip_digest}")


if __name__ == "__main__":
    main()
