#!/usr/bin/env python3
"""Validate final JDIQ submission materials."""

from __future__ import annotations

import json
import hashlib
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
FINAL_MATERIALS = REPO_ROOT / "papers/JDIQ_2026/submission/final_submission_materials"
SUPP_DIR = FINAL_MATERIALS / "anonymous_supplementary"
SUPP_ZIP = FINAL_MATERIALS / "anonymous_supplementary.zip"
HIGHLIGHTS = FINAL_MATERIALS / "highlights.pdf"
COVER_LETTER = FINAL_MATERIALS / "cover_letter.pdf"

IDENTITY_PATTERN = re.compile(
    r"soroush|vahidi|\bsv96\b|\bnjit\b|github\.com/SoroushVahidi|researchsquare|rs-\d{4,}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|/home/soroush",
    re.IGNORECASE,
)
SECRET_PATTERN = re.compile(
    (
        r"api[_-]?key\s*[:=]\s*['\"][^'\"]{12,}['\"]|"
        r"secret[_-]?key\s*[:=]\s*['\"][^'\"]{12,}['\"]|"
        r"password\s*[:=]\s*['\"][^'\"]{8,}['\"]|"
        r"BEGIN (RSA|OPENSSH|PGP)|AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{20,}"
    ),
    re.IGNORECASE,
)
TEXT_SUFFIXES = {
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
ALLOWED_IDENTITY_PATTERNS = [
    re.compile(r"Soroush\s+Vosoughi", re.IGNORECASE),
    re.compile(r"permissions@acm\.org", re.IGNORECASE),
]
ALLOWED_SECRET_PATTERNS = [
    re.compile(r"sk-super-secret-not-real"),
    re.compile(r"test-cohere-key"),
]


def check(results: list[tuple[str, bool, str]], name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))


def pdfinfo(path: Path) -> str:
    return subprocess.run(
        ["pdfinfo", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def pdf_text(path: Path) -> str:
    return subprocess.run(
        ["pdftotext", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def text_leaks(root: Path, pattern: re.Pattern[str]) -> list[str]:
    leaks: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.suffix.lower() in TEXT_SUFFIXES:
                text = path.read_text(errors="ignore")
            elif path.suffix.lower() == ".pdf":
                text = pdf_text(path)
            else:
                continue
        except Exception:
            continue
        for allowed in ALLOWED_IDENTITY_PATTERNS:
            text = allowed.sub("SAFEIDENTITY", text)
        for allowed in ALLOWED_SECRET_PATTERNS:
            text = allowed.sub("SAFEKEY", text)
        if pattern.search(text):
            leaks.append(str(path.relative_to(root)))
    return leaks


def verify_checksums(root: Path) -> tuple[bool, str]:
    checksum_file = root / "metadata/CHECKSUMS.sha256.txt"
    listed = 0
    bad: list[str] = []
    for line in checksum_file.read_text().splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        file = root / rel
        listed += 1
        if not file.exists():
            bad.append(f"missing:{rel}")
            continue
        actual = hashlib.sha256(file.read_bytes()).hexdigest()
        if actual != digest:
            bad.append(rel)
    return (not bad, f"verified={listed}" if not bad else f"bad={bad}")


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    check(results, "supplementary_dir_exists", SUPP_DIR.exists(), str(SUPP_DIR))
    check(results, "supplementary_zip_exists", SUPP_ZIP.exists(), str(SUPP_ZIP))
    check(results, "highlights_pdf_exists", HIGHLIGHTS.exists(), str(HIGHLIGHTS))
    check(results, "cover_letter_pdf_exists", COVER_LETTER.exists(), str(COVER_LETTER))

    required = [
        SUPP_DIR / "README.md",
        SUPP_DIR / "manuscript/main.pdf",
        SUPP_DIR / "manuscript/supplement.pdf",
        SUPP_DIR / "src/consistency_ranker/graph_construction.py",
        SUPP_DIR / "src/consistency_ranker/statistical_inference.py",
        SUPP_DIR / "scripts/run_real_experiment.py",
        SUPP_DIR / "tests/test_exact_mwfas_scip.py",
        SUPP_DIR / "supplemental/REPRODUCIBILITY.md",
        SUPP_DIR / "metadata/PACKAGE_METADATA.json",
    ]
    missing = [str(path.relative_to(SUPP_DIR)) for path in required if not path.exists()]
    check(
        results,
        "required_files_present",
        not missing,
        "present" if not missing else f"missing={missing}",
    )

    title_text = (SUPP_DIR / "README.md").read_text() if (SUPP_DIR / "README.md").exists() else ""
    final_title = (
        "Data Quality for Derived Preference Graphs: Construction Sensitivity "
        "and Repair Outcomes in Multi-Ranker Retrieval"
    )
    normalized_title = " ".join(title_text.split())
    check(
        results,
        "readme_uses_final_title",
        final_title in normalized_title,
        "final title present" if final_title in normalized_title else "title mismatch",
    )
    repro_path = SUPP_DIR / "supplemental/REPRODUCIBILITY.md"
    repro_text = repro_path.read_text() if repro_path.exists() else ""
    check(
        results,
        "repro_uses_current_test_count",
        "617 passed" in repro_text,
        "617 stated" if "617 passed" in repro_text else "stale test count",
    )
    package_metadata = SUPP_DIR / "metadata/PACKAGE_METADATA.json"
    freeze_manifest = SUPP_DIR / "supplemental/SUBMISSION_FREEZE_MANIFEST.json"
    manifest_ok = False
    manifest_detail = "manifest missing"
    if package_metadata.exists() and freeze_manifest.exists():
        package_payload = json.loads(package_metadata.read_text())
        freeze_payload = json.loads(freeze_manifest.read_text())
        manifest_ok = package_payload.get("git_commit") == freeze_payload.get("git_commit")
        manifest_detail = (
            "git commit aligned"
            if manifest_ok
            else "git commit mismatch between package metadata and freeze manifest"
        )
    check(
        results,
        "freeze_manifest_matches_package_metadata",
        manifest_ok,
        manifest_detail,
    )

    identity_leaks = text_leaks(SUPP_DIR, IDENTITY_PATTERN)
    secret_leaks = text_leaks(SUPP_DIR, SECRET_PATTERN)
    check(
        results,
        "supplementary_identity_scan",
        not identity_leaks,
        "clean" if not identity_leaks else f"leaks={identity_leaks}",
    )
    check(
        results,
        "supplementary_secrets_scan",
        not secret_leaks,
        "clean" if not secret_leaks else f"leaks={secret_leaks}",
    )

    info = ""
    for pdf in (SUPP_DIR / "manuscript/main.pdf", SUPP_DIR / "manuscript/supplement.pdf"):
        if pdf.exists():
            info += pdfinfo(pdf) + "\n"
    check(
        results,
        "supplementary_pdf_metadata_clean",
        bool(info) and not IDENTITY_PATTERN.search(info),
        (
            "clean"
            if info and not IDENTITY_PATTERN.search(info)
            else "missing PDF or identity token found in PDF metadata"
        ),
    )
    for pdf in (HIGHLIGHTS, COVER_LETTER):
        info = pdfinfo(pdf) if pdf.exists() else ""
        check(
            results,
            f"{pdf.stem}_pdf_metadata_clean",
            bool(info) and not IDENTITY_PATTERN.search(info),
            (
                "clean"
                if info and not IDENTITY_PATTERN.search(info)
                else "missing PDF or identity token found in PDF metadata"
            ),
        )

    zip_ok = False
    zip_detail = "missing"
    zip_path_ok = False
    if SUPP_ZIP.exists():
        with zipfile.ZipFile(SUPP_ZIP) as zf:
            zip_ok = zf.testzip() is None
            bad_names = [
                name
                for name in zf.namelist()
                if IDENTITY_PATTERN.search(name) or name.startswith("/")
            ]
            zip_path_ok = not bad_names
            zip_detail = "clean" if zip_ok else "corrupt"
    check(results, "supplementary_zip_integrity", zip_ok, zip_detail)
    check(
        results,
        "supplementary_zip_paths_clean",
        zip_path_ok,
        "clean" if zip_path_ok else "identity or absolute path in zip names",
    )

    if SUPP_ZIP.exists():
        with tempfile.TemporaryDirectory(prefix="jdiq_submission_") as tmp:
            extract_root = Path(tmp)
            with zipfile.ZipFile(SUPP_ZIP) as zf:
                zf.extractall(extract_root)
            extracted = extract_root / "anonymous_supplementary"
            diffs = subprocess.run(
                ["diff", "-rq", str(SUPP_DIR), str(extracted)],
                capture_output=True,
                text=True,
            )
            check(
                results,
                "zip_extraction_matches_directory",
                diffs.returncode == 0,
                "match" if diffs.returncode == 0 else diffs.stdout[:400],
            )
    else:
        check(
            results,
            "zip_extraction_matches_directory",
            False,
            "supplementary zip missing",
        )

    checksum_ok, checksum_detail = (
        verify_checksums(SUPP_DIR)
        if (SUPP_DIR / "metadata/CHECKSUMS.sha256.txt").exists()
        else (False, "checksum file missing")
    )
    check(results, "supplementary_checksums_verify", checksum_ok, checksum_detail)

    ok = all(cond for _, cond, _ in results)
    for name, cond, detail in results:
        print(f"[{'OK' if cond else 'FAIL'}] {name}: {detail}")
    print(f"\n{sum(1 for _, cond, _ in results if cond)}/{len(results)} checks passed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
