#!/usr/bin/env python3
"""Assemble papers/JDIQ_2026/submission/final_anonymous/ from frozen canonical
outputs and zip it. Re-run to rebuild after any manuscript/table change; this
script performs the file selection and path-scrubbing decisions recorded in
ANONYMITY_AUDIT.md rather than requiring them to be repeated by hand.
"""

import hashlib
import re
import shutil
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MANUSCRIPT = REPO_ROOT / "papers/JDIQ_2026/manuscript"
SUBMISSION = REPO_ROOT / "papers/JDIQ_2026/submission"
TEMPLATES = SUBMISSION / "scripts" / "templates"
OUT = SUBMISSION / "final_anonymous"

ABS_PATH_RE = re.compile(re.escape(str(REPO_ROOT)) + r"/?")


def scrub_text(text: str) -> str:
    return ABS_PATH_RE.sub("", text)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_scrubbed_text(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(scrub_text(src.read_text()))


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # --- 1. Manuscript source, PDF, preserved figures, active generated figures ---
    man_out = OUT / "manuscript"
    copy_file(MANUSCRIPT / "main.tex", man_out / "main.tex")
    copy_file(MANUSCRIPT / "references.bib", man_out / "references.bib")
    copy_file(MANUSCRIPT / "main.pdf", man_out / "main.pdf")
    for preserved in ("figure1.png", "figure3.png", "figure5.png"):
        copy_file(MANUSCRIPT / preserved, man_out / preserved)

    active_figs = [
        "fig2_bm25_share.pdf",
        "fig4_raw_vs_calibrated_structure.pdf",
        "fig6_normalized_fas_removed.pdf",
        "fig7_bootstrap_forest.pdf",
        "fig8_influence.pdf",
        "fig9_sign_change_heatmap.pdf",
        "fig10_baseline_comparison.pdf",
    ]
    for fig in active_figs:
        copy_file(MANUSCRIPT / "figures_v2" / fig, man_out / "figures_v2" / fig)
    for script in ("generate_figures.py", "style.py"):
        copy_file(MANUSCRIPT / "figures_v2" / script, man_out / "figures_v2" / script)

    # --- 2. Supplemental docs (authored templates + carried-over reports) ---
    supp = OUT / "supplemental"
    copy_file(TEMPLATES / "REPRODUCIBILITY.md", supp / "REPRODUCIBILITY.md")
    copy_file(TEMPLATES / "DATA_AVAILABILITY.md", supp / "DATA_AVAILABILITY.md")
    for name in (
        "FIGURE_INVENTORY.md",
        "FIGURE_DATA_VERIFICATION_REPORT.md",
        "SUBMISSION_FREEZE_MANIFEST.json",
    ):
        copy_file(SUBMISSION / name, supp / name)
    copy_file(
        SUBMISSION / "scripts" / "verify_figure_data.py", supp / "scripts" / "verify_figure_data.py"
    )
    copy_file(
        SUBMISSION / "scripts" / "build_freeze_manifest.py",
        supp / "scripts" / "build_freeze_manifest.py",
    )

    # --- 3. Aggregate tables (path-scrubbing every CSV; only query_exclusion_audit.csv
    #     is known to contain an absolute-path column, but every file is scrubbed
    #     defensively rather than only the known offender) ---
    table_dirs = {
        "full_calibrated_core": REPO_ROOT / "reports/full_calibrated_core/tables",
        "normalization_protocol_audit": REPO_ROOT
        / "reports/normalization_protocol_audit_20260714/tables",
        "candidate_pool_conditional_audit": REPO_ROOT
        / "reports/candidate_pool_conditional_audit_20260714/tables",
        "exact_ilp_repair_investigation": REPO_ROOT
        / "reports/exact_open_source_ilp_repair_investigation/tables",
    }
    for label, src_dir in table_dirs.items():
        for csv_file in sorted(src_dir.glob("*.csv")):
            copy_scrubbed_text(csv_file, supp / "tables" / label / csv_file.name)

    # --- 4. Driver scripts (already verified clean of author-identifying strings) ---
    driver_scripts = {
        "full_calibrated_core": [
            "run_full_calibrated_core.py",
            "full_calibration_utils.py",
            "candidate_pool_policies.py",
            "conditional_subsets.py",
        ],
        "normalization_protocol_audit_20260714": [
            "run_independent_protocols.py",
            "analyze_protocol_robustness.py",
        ],
        "candidate_pool_conditional_audit_20260714": [
            "run_pool_robustness.py",
            "run_conditional_and_failure_analysis.py",
            "run_baseline_comparison.py",
        ],
    }
    for report_dir, files in driver_scripts.items():
        for fname in files:
            src = REPO_ROOT / "reports" / report_dir / "scripts" / fname
            copy_scrubbed_text(src, supp / "scripts" / report_dir / fname)

    # --- 5. Top-level docs ---
    copy_file(TEMPLATES / "README.md", OUT / "README.md")
    copy_file(SUBMISSION / "SUBMISSION_CHECKLIST.md", OUT / "SUBMISSION_CHECKLIST.md")

    # --- 6. Source manifest + checksums over every file now in the package ---
    all_files = sorted(p for p in OUT.rglob("*") if p.is_file())
    manifest_lines = [
        "# Source Manifest (final_anonymous/)",
        "",
        "Every file in this package, generated at zip time.",
        "",
    ]
    checksum_lines = []
    for f in all_files:
        rel = f.relative_to(OUT)
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        manifest_lines.append(f"- `{rel}`")
        checksum_lines.append(f"{digest}  {rel}")
    (OUT / "SOURCE_MANIFEST.md").write_text("\n".join(manifest_lines) + "\n")
    (OUT / "CHECKSUMS.sha256.txt").write_text("\n".join(checksum_lines) + "\n")

    # --- 7. Zip the whole package (excluding the manifest files' own re-hash issue:
    #     CHECKSUMS covers everything present at the time it was written, which
    #     does not include itself or SOURCE_MANIFEST.md; that is expected). ---
    zip_path = SUBMISSION / "final_anonymous.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(OUT.rglob("*")):
            if f.is_file():
                zf.write(f, arcname=f.relative_to(OUT.parent))

    zip_digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print("final_anonymous/ assembled at", OUT)
    print("zip:", zip_path, "sha256:", zip_digest)
    print(
        "total files:", len(all_files) + 2
    )  # +2 for SOURCE_MANIFEST.md and CHECKSUMS.sha256.txt themselves


if __name__ == "__main__":
    main()
