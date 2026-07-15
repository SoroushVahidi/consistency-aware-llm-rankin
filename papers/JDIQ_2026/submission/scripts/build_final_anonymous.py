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

# Defense-in-depth identity scrub, applied to every text file this script copies
# (in addition to excluding whole documents known to discuss author-identifying
# correspondence, e.g. Task 6's report -- see below). Matches are replaced with
# a visible placeholder rather than deleted, so a leftover match is easy to spot
# by eye or a follow-up grep rather than silently vanishing into odd phrasing.
IDENTITY_PATTERNS = [
    re.compile(r"soroush", re.IGNORECASE),
    re.compile(r"vahidi", re.IGNORECASE),
    re.compile(r"\bsv96@njit\.edu\b", re.IGNORECASE),
    re.compile(r"\bkoutis\b", re.IGNORECASE),
    re.compile(r"\bnjit\.edu\b", re.IGNORECASE),
]


def scrub_text(text: str) -> str:
    text = ABS_PATH_RE.sub("", text)
    for pattern in IDENTITY_PATTERNS:
        text = pattern.sub("[REDACTED-FOR-ANONYMITY]", text)
    return text


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
    # Task 8 split the manuscript into main.tex (<=~39 pages) plus a
    # standalone supplement.tex/supplement.pdf carrying the robustness detail
    # moved out of the main text; both compile from the same directory
    # (they share figure1.png/figure3.png/figure5.png and figures_v2/*.pdf),
    # so supplement.tex is copied alongside main.tex, not into a separate
    # folder, to remain independently rebuildable.
    copy_file(MANUSCRIPT / "supplement.tex", man_out / "supplement.tex")
    copy_file(MANUSCRIPT / "supplement.pdf", man_out / "supplement.pdf")
    for preserved in ("figure1.png", "figure3.png", "figure5.png"):
        copy_file(MANUSCRIPT / preserved, man_out / preserved)

    # main.tex uses fig2/fig7 directly; supplement.tex uses fig4/fig6/fig8/fig9/fig10.
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

    # --- 3b. Tasks 1-6 final-revision report directories (added in Task 7 to fix
    #     staleness: this package previously only carried the three pre-Task-1
    #     report dirs above and did not reflect the 10-task JDIQ revision sequence's
    #     own outputs, even though the manuscript explicitly names files from them,
    #     e.g. result_to_dq_mapping.csv from Task 5). For each final_revision_task*
    #     dir: include FINAL_REPORT.md, the validation/ directory (claim-to-evidence
    #     audits), the claim_to_evidence_audit*.py script, and every tables/*.csv
    #     under a 5 MB size cap -- large enough for every genuine aggregate/summary
    #     table found across Tasks 1-6 (largest included file is 2.2 MB), small
    #     enough to exclude the three multi-hundred-MB raw per-query intermediate
    #     dumps in Task 1's tables/ directory (243 MB and 65 MB pool_cutoff_*_metrics.csv,
    #     6.6 MB pool_cutoff_exact_pair_metrics.csv), which are exactly the
    #     "enormous unnecessary intermediate trees" this package must not ship.
    MAX_TABLE_BYTES = 5 * 1024 * 1024
    # Task 6 ("literature_rejection_audit") is deliberately excluded: its
    # FINAL_REPORT.md documents a Gmail-based prior-rejection-history audit and
    # necessarily quotes the author's real email address and a named advisor --
    # appropriate for the private working repository, never for a reviewer-facing
    # anonymous artifact. It also is not itself reproducible experimental
    # evidence (it is a literature/writing-quality audit), so omitting it does
    # not remove any result a reviewer would need to verify.
    #
    # The anonymous review bundle keeps the scientific revision-task reports
    # needed to trace the released evidence (Tasks 1-5). Later task reports
    # are policy/compression/peer-review freeze audits for the private
    # submission workflow rather than reproducibility evidence, and they
    # contain internal review-history language that does not belong in the
    # reviewer-facing artifact.
    task_report_dirs = sorted(
        d
        for d in (REPO_ROOT / "reports").glob("final_revision_task*_20260715")
        if re.match(r"final_revision_task[1-5]_", d.name)
    )
    for task_dir in task_report_dirs:
        label = task_dir.name
        final_report = task_dir / "FINAL_REPORT.md"
        if final_report.exists():
            copy_scrubbed_text(final_report, supp / "task_reports" / label / "FINAL_REPORT.md")
        validation_dir = task_dir / "validation"
        if validation_dir.exists():
            for vf in sorted(validation_dir.rglob("*")):
                if vf.is_file():
                    copy_scrubbed_text(vf, supp / "task_reports" / label / "validation" / vf.name)
        for audit_script in sorted(task_dir.glob("scripts/claim_to_evidence_audit*.py")):
            copy_scrubbed_text(
                audit_script, supp / "task_reports" / label / "scripts" / audit_script.name
            )
        tables_dir = task_dir / "tables"
        if tables_dir.exists():
            for csv_file in sorted(tables_dir.glob("*.csv")):
                if csv_file.stat().st_size <= MAX_TABLE_BYTES:
                    copy_scrubbed_text(
                        csv_file, supp / "task_reports" / label / "tables" / csv_file.name
                    )

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
    # main.tex's Data Availability section explicitly claims "the review artifact
    # includes a dependency list (requirements.txt)"; this was not actually true
    # before Task 7 (the file existed at the repo root but was never copied in).
    copy_file(REPO_ROOT / "requirements.txt", OUT / "requirements.txt")

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
