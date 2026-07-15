#!/usr/bin/env python3
"""Final page-limit freeze audit for the compressed JDIQ submission."""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MANUSCRIPT = REPO / "papers/JDIQ_2026/manuscript"
SUBMISSION = REPO / "papers/JDIQ_2026/submission"
ARTIFACT = SUBMISSION / "final_anonymous"

MAIN_TEX = MANUSCRIPT / "main.tex"
SUPP_TEX = MANUSCRIPT / "supplement.tex"
MAIN_PDF = MANUSCRIPT / "main.pdf"
SUPP_PDF = MANUSCRIPT / "supplement.pdf"

REQUIRED_MAIN_PATTERNS = {
    "bm25_scale_dominance": r"0\.988.*0\.512",
    "canonical_holm_null": r"0/20.*canonical",
    "larger_pool_holm_null": r"0/110.*larger-pool",
    "exact_repair_coverage": r"1\{,\}025/1\{,\}025",
    "membership_change_rate": r"10\.6\\%.*mean rate",
    "equivalence_margin_small": r"13/110",
    "equivalence_margin_large": r"32/110",
}


def run_text(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def pdf_text(path: Path) -> str:
    return run_text(["pdftotext", str(path), "-"])


def pdf_pages(path: Path) -> int:
    out = run_text(["pdfinfo", str(path)])
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"Pages not found in pdfinfo output for {path}")


def reference_start_page(path: Path) -> int | None:
    pages = pdf_text(path).split("\f")
    marker = re.compile(r"(^|\n)\s*REFERENCES\s*(\n|$)")
    for idx, page in enumerate(pages, start=1):
        if marker.search(page):
            return idx
    return None


def check(results: list[tuple[str, bool, str]], name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))


def labels_are_referenced(tex: str, prefix: str) -> tuple[bool, str]:
    labels = re.findall(rf"\\label\{{({prefix}:[^}}]+)\}}", tex)
    missing = []
    for label in labels:
        if not re.search(rf"\\(auto)?ref\{{{re.escape(label)}\}}", tex):
            missing.append(label)
    return (not missing, "all referenced" if not missing else f"missing={missing}")


def count_equations(tex: str) -> tuple[int, int]:
    equations = len(re.findall(r"\\begin\{equation\}", tex))
    labels = len(re.findall(r"\\label\{eq:[^}]+\}", tex))
    return equations, labels


def artifact_leaks() -> list[str]:
    leak_pattern = re.compile(
        r"vahidi|sv96@njit\.edu|koutis|/home/soroush|njit\.edu",
        re.IGNORECASE,
    )
    leaks: list[str] = []
    for file in ARTIFACT.rglob("*"):
        if not file.is_file():
            continue
        try:
            text = file.read_text(errors="ignore")
        except Exception:
            continue
        if leak_pattern.search(text):
            leaks.append(str(file.relative_to(ARTIFACT)))
    return leaks


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    main_tex = MAIN_TEX.read_text()
    supp_tex = SUPP_TEX.read_text()
    main_text = pdf_text(MAIN_PDF)
    supp_text = pdf_text(SUPP_PDF)
    main_log_path = MANUSCRIPT / "main.log"
    supp_log_path = MANUSCRIPT / "supplement.log"
    main_log = main_log_path.read_text(errors="ignore") if main_log_path.exists() else ""
    supp_log = supp_log_path.read_text(errors="ignore") if supp_log_path.exists() else ""

    main_pages = pdf_pages(MAIN_PDF)
    supp_pages = pdf_pages(SUPP_PDF)
    ref_start = reference_start_page(MAIN_PDF)
    body_pages = ref_start - 1 if ref_start else main_pages

    check(
        results,
        "ai_disclosure_once_in_main",
        main_tex.count("Generative AI tools were used") == 1,
        f"count={main_tex.count('Generative AI tools were used')}",
    )
    check(
        results,
        "ai_disclosure_absent_from_supplement",
        "Generative AI tools were used" not in supp_tex,
        "absent" if "Generative AI tools were used" not in supp_tex else "present",
    )
    check(
        results,
        "main_body_pages_leq_23",
        body_pages <= 23,
        f"body_pages={body_pages}, references_start={ref_start}, total_pages={main_pages}",
    )
    check(results, "supplement_pdf_present", supp_pages >= 1, f"pages={supp_pages}")
    check(
        results,
        "main_pdf_no_broken_ref_glyphs",
        "??" not in main_text and "⁇" not in main_text,
        "clean" if "??" not in main_text and "⁇" not in main_text else "broken glyph found",
    )
    check(
        results,
        "supplement_pdf_no_broken_ref_glyphs",
        "??" not in supp_text and "⁇" not in supp_text,
        "clean" if "??" not in supp_text and "⁇" not in supp_text else "broken glyph found",
    )
    missing_phrases = [
        name
        for name, pattern in REQUIRED_MAIN_PATTERNS.items()
        if not re.search(pattern, main_tex, flags=re.IGNORECASE | re.DOTALL)
    ]
    check(
        results,
        "main_preserves_decisive_claims",
        not missing_phrases,
        "all present" if not missing_phrases else f"missing={missing_phrases}",
    )
    eq_count, eq_labels = count_equations(main_tex)
    check(
        results,
        "equations_numbered",
        eq_count == eq_labels,
        f"equations={eq_count}, labels={eq_labels}",
    )
    label_sets = (
        ("main_figures", main_tex),
        ("main_tables", main_tex),
        ("supp_figures", supp_tex),
        ("supp_tables", supp_tex),
    )
    for name, tex in label_sets:
        prefix = "fig" if "figures" in name else "tab"
        ok, detail = labels_are_referenced(tex, prefix)
        check(results, f"{name}_referenced", ok, detail)
    undefined_patterns = [
        "Citation",
        "Reference",
        "undefined references",
        "undefined citation",
    ]
    if main_log_path.exists():
        bad_main_log = any(term in main_log for term in undefined_patterns)
        check(
            results,
            "main_log_no_undefined_refs",
            not bad_main_log,
            "clean" if not bad_main_log else "undefined ref/cite text present",
        )
    else:
        check(
            results,
            "main_log_no_undefined_refs",
            True,
            "log not retained; relied on rendered-PDF scan",
        )
    if supp_log_path.exists():
        bad_supp_log = any(term in supp_log for term in undefined_patterns)
        check(
            results,
            "supp_log_no_undefined_refs",
            not bad_supp_log,
            "clean" if not bad_supp_log else "undefined ref/cite text present",
        )
    else:
        check(
            results,
            "supp_log_no_undefined_refs",
            True,
            "log not retained; relied on rendered-PDF scan",
        )

    artifact_files = [
        ARTIFACT / "manuscript/main.tex",
        ARTIFACT / "manuscript/main.pdf",
        ARTIFACT / "manuscript/supplement.tex",
        ARTIFACT / "manuscript/supplement.pdf",
        SUBMISSION / "final_anonymous.zip",
    ]
    check(
        results,
        "artifact_core_files_present",
        all(path.exists() for path in artifact_files),
        (
            "present"
            if all(path.exists() for path in artifact_files)
            else f"missing={[str(p) for p in artifact_files if not p.exists()]}"
        ),
    )
    leaks = artifact_leaks()
    check(
        results,
        "artifact_no_identity_or_absolute_path_leaks",
        not leaks,
        "clean" if not leaks else f"leaks={leaks}",
    )

    zip_path = SUBMISSION / "final_anonymous.zip"
    zip_ok = False
    zip_detail = "missing"
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            bad_name = zf.testzip()
            zip_ok = bad_name is None
            zip_detail = "clean" if zip_ok else f"first_bad={bad_name}"
    check(results, "final_anonymous_zip_integrity", zip_ok, zip_detail)

    ok = all(cond for _, cond, _ in results)
    for name, cond, detail in results:
        print(f"[{'OK' if cond else 'FAIL'}] {name}: {detail}")
    print(f"\n{sum(1 for _, cond, _ in results if cond)}/{len(results)} checks passed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
