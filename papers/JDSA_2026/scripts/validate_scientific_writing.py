"""Validate an editorial rewrite against fixed scientific evidence; no experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SRC = ROOT / "manuscript"
BASE = "a9bfe54e48e600153c8d19dff91b5d1e8076ed13"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def old(name):
    return subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=REPO)


def expand(name, baseline=False):
    t = (
        old("papers/JDSA_2026/manuscript/" + name).decode()
        if baseline
        else (SRC / name).read_text()
    )
    return re.sub(r"\\input\{([^}]+)\}", lambda m: expand(m[1] + ".tex", baseline), t)


def citekeys(text):
    return {k.strip() for s in re.findall(r"\\cite\w*\{([^}]+)\}", text) for k in s.split(",")}


def numerical_tokens(text):
    text = re.sub(r"(?<!\\)%[^\n]*", "", text)
    text = re.sub(r"\\(?:seqsplit|nolinkurl|url|ref|eqref|label|cite\w*)\{[^}]*\}", "", text)
    text = re.sub(r"\\href\{[^}]*\}", "", text)
    return set(re.findall(r"(?<![A-Za-z0-9])[−+-]?\d+(?:[.,]\d+)*(?:e[−+-]?\d+)?", text))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protected-root", type=Path)
    args = parser.parse_args()
    checks = []

    def check(name, ok, detail=None):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    manifest = json.loads((ROOT / "audit/SCIENTIFIC_WRITING_MANIFEST.json").read_text())
    check("fixed scientific-writing baseline", manifest["base_main_sha"] == BASE)
    mutable = set(manifest["changed_source_files"])
    allowed = {
        "main.tex",
        "supplement.tex",
        "declarations.tex",
        "common.tex",
        "selected_worked_example.tex",
        "informative_support.tex",
        "preprint_delta.tex",
    }
    check("explicit source-edit scope", mutable == allowed)
    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", BASE], cwd=REPO, text=True
    ).splitlines()
    protected = [
        n
        for n in files
        if n.startswith("papers/JDSA_2026/manuscript/")
        and Path(n).name not in mutable
        and Path(n).suffix in {".tex", ".pdf", ".bib", ".cls", ".bst", ".sh"}
    ]
    check(
        "all other scientific inputs, bibliography and figures unchanged",
        all((REPO / n).read_bytes() == old(n) for n in protected),
        len(protected),
    )
    rights_files = [
        "COHERE_PERMISSION_ASSESSMENT.md",
        "PERMISSIONS_AND_RESOURCE_RIGHTS.md",
        "REVIEWER_ACCESS.md",
        "READINESS_RESOLUTION.md",
        "SUBMISSION_CHECKLIST.md",
    ]
    check(
        "rights classifications and unresolved submission gates unchanged",
        all((ROOT / n).read_bytes() == old("papers/JDSA_2026/" + n) for n in rights_files),
    )
    for n in mutable:
        check(
            "declared revised source identity: " + n,
            sha((SRC / n).read_bytes()) == manifest["source_sha256"][n],
        )
    for name in ["main.tex", "supplement.tex"]:
        before, after = expand(name, True), expand(name)

        def equations(t):
            return re.findall(r"\\begin\{(equation|align)\}(.*?)\\end\{\1\}", t, re.S)

        check(name + " displayed mathematics unchanged", equations(before) == equations(after))
        check(
            name + " complete citation set retained",
            citekeys(before) == citekeys(after),
            len(citekeys(after)),
        )
        labels = re.findall(r"\\label\{([^}]+)\}", after)
        check(name + " no duplicate labels", len(labels) == len(set(labels)))
        refs = re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", after)
        check(
            name + " all cross-references defined",
            set(refs) <= set(labels),
            sorted(set(refs) - set(labels)),
        )
        for prefix in ["tab:", "fig:"]:
            sequence = list(dict.fromkeys(k for k in refs if k.startswith(prefix)))
            definitions = [k for k in labels if k.startswith(prefix)]
            check(name + " consecutive first citations " + prefix, sequence == definitions)

        def tables(t):
            return re.findall(r"\\begin\{tabular(?:x|\*)?\}.*?\\end\{tabular(?:x|\*)?\}", t, re.S)

        normalized_before = before.replace("Saved outcome", "Observed outcome").replace(
            "Current scope / difference", "Present analysis / difference"
        )
        normalized_before = normalized_before.replace(
            "Evidence reuse/access", "Evidence reuse and access"
        ).replace(
            "lineage, historical limits and bundle inventory",
            "evidence reuse, historical limits and data access",
        )
        check(
            name + " all numerical table bodies retained",
            tables(normalized_before) == tables(after),
            len(tables(after)),
        )
    before = expand("main.tex", True) + expand("supplement.tex", True)
    after = expand("main.tex") + expand("supplement.tex")
    missing = numerical_tokens(before) - numerical_tokens(after)
    # File-count and archive-size logistics only; full originals retained privately.
    check(
        "every scientific numerical value retained across main and SI",
        missing <= {"219", "2.09"},
        sorted(missing),
    )
    check(
        "new narrative frequencies are rounded from original counts",
        round(100 * 143 / 180, 1) == 79.4 and round(100 * 135 / 160, 1) == 84.4,
    )
    main_text = (SRC / "main.tex").read_text()
    for needle in [
        "143/180",
        "135/160",
        r"79.4\%",
        r"84.4\%",
        "descriptive frequencies",
        "not estimates of population",
        "74",
        "213",
    ]:
        check("central descriptive framing: " + needle, needle in main_text)
    start, end = (
        r"\subsection{Evaluation and query-level inference}",
        r"\subsection{Computational methods and AI assistance}",
    )
    old_main = old("papers/JDSA_2026/manuscript/main.tex").decode()
    problem_start = r"\section{Problem Formulation}"
    problem_end = r"\section{Experimental Design}"
    original_problem = old_main[old_main.index(problem_start) : old_main.index(problem_end)]
    revised_problem = main_text[main_text.index(problem_start) : main_text.index(problem_end)]
    check(
        "complete definitions and metric contracts unchanged",
        original_problem.replace(
            "The principal extractor in the cached-judgment audit",
            "The principal extractor for cached judgments",
        )
        == revised_problem,
    )
    old_end = r"\subsection{Evidence access and AI assistance}"
    old_stats = old_main[old_main.index(start) : old_main.index(old_end)]
    new_stats = main_text[main_text.index(start) : main_text.index(end)]
    old_stats = old_stats.replace(
        "The completed correction uses", "The query-block analysis uses"
    ).replace(
        "complete saved families and correction details",
        "complete comparison families and inference details",
    )
    check("statistical procedures and estimands unchanged", old_stats == new_stats)
    for section in [
        "Introduction",
        "Related Work",
        "Problem Formulation",
        "Experimental Design",
        "Conclusion",
    ]:
        check("one main section: " + section, main_text.count(r"\section{" + section + "}") == 1)
    check(
        "no operational narrative in main scientific body",
        not any(
            x in main_text
            for x in [
                "reviewer ZIP",
                "Level~2",
                "staged-source",
                "prepared for confidential editorial disclosure",
                "this revision",
                "separately scheduled",
                "GitHub",
                "commit ",
            ]
        ),
    )
    required_limits = {
        "nonrandom selection": "nonrandom",
        "incomplete judgments": "Incomplete judgments",
        "no equivalence claim": "does not establish equivalence",
        "sign symmetry": "exchangeability",
        "deterministic interventions": "not randomly assigned",
        "sparse support": "4--99",
        "unjudged does not imply irrelevant": "does not establish irrelevance",
        "model abstentions": "1,378",
        "position preference": "2,591",
        "invalidity": "148",
        "no cyclic-positive strict case": "no cyclic-positive",
        "shallow pools": "shallow candidate pools",
        "six-graph generalizability": "six eight-node graphs",
        "historical reconstruction": "incompletely pinned",
        "external access incomplete": "independent reviewer access",
        "sharing not cleared": "not cleared for distribution",
        "pointwise intervals": "pointwise",
    }
    for label, needle in required_limits.items():
        check("limitation retained: " + label, needle in after)
    abstract = re.search(r"\\abstract\{(.*?)\}\n\\keywords", main_text, re.S)[1]
    check("abstract 150–250 words", 150 <= len(abstract.split()) <= 250, len(abstract.split()))
    check("six keywords", len(re.search(r"\\keywords\{([^}]+)", main_text)[1].split(",")) == 6)
    check("Springer two-column main retained", "pdflatex,iicol,sn-basic,Numbered" in main_text)
    ack = (
        "The author gratefully acknowledges Professor Ioannis Koutis "
        "for his academic guidance and support."
    )
    check("exact requested acknowledgment retained", ack in main_text)
    bibliography = (SRC / "references.bib").read_text()
    keys = set(re.findall(r"@\w+\{([^,]+)", bibliography))
    check("all cited references have bibliography records", citekeys(after) <= keys)
    check(
        "all 35 statistical table rows unchanged",
        (SRC / "corrected35.tex").read_bytes()
        == old("papers/JDSA_2026/manuscript/corrected35.tex"),
    )
    figures = ["Fig2.pdf", "Fig3.pdf", "ESM_Fig1.pdf", "ESM_Fig2.pdf", "ESM_Fig3.pdf"]
    for figure in figures:
        check(
            "original figure bytes: " + figure,
            (SRC / figure).read_bytes() == old("papers/JDSA_2026/manuscript/" + figure),
        )
    if args.protected_root:
        ledger = json.loads((ROOT / "audit/IJIT_SOURCE_SHA256.json").read_text())
        matches = sum(
            (args.protected_root / n).is_file() and sha((args.protected_root / n).read_bytes()) == h
            for n, h in ledger.items()
        )
        check(
            "historical protected files unchanged",
            matches == len(ledger),
            {"matched": matches, "total": len(ledger)},
        )
    pdfs = {}
    for name in ["main", "supplement", "main_anonymous", "supplement_anonymous"]:
        path = SRC / "build" / (name + ".pdf")
        info = subprocess.check_output(["pdfinfo", str(path)], text=True)
        text = subprocess.check_output(["pdftotext", str(path), "-"], text=True)
        pages = int(re.search(r"Pages:\s*(\d+)", info)[1])
        log = (SRC / "build" / (name + ".log")).read_text()
        check(
            name + " references and layout compile cleanly",
            not re.search(r"undefined|multiply defined|Overfull \\hbox|Overfull \\vbox", log),
        )
        bbl = (SRC / "build" / (name + ".bbl")).read_text()
        refs = len(re.findall(r"\\bibitem", bbl))
        check(name + " reference count", refs == (36 if name.startswith("main") else 12), refs)
        if "anonymous" in name:
            check(
                name + " advisor and identity suppressed",
                "Ioannis Koutis" not in text
                and "sv96@njit.edu" not in text
                and "0000-0003-1934-6282" not in text,
            )
        pdfs[name] = {"pages": pages, "sha256": sha(path.read_bytes()), "references": refs}
    check(
        "root canonical matches identified build",
        (REPO / "LATEST_MANUSCRIPT.pdf").read_bytes() == (SRC / "build/main.pdf").read_bytes(),
    )
    check(
        "canonical manifest identity",
        sha((REPO / "LATEST_MANUSCRIPT.pdf").read_bytes()) == manifest["canonical_sha256"],
    )
    archive_manifest = json.loads((ROOT / "audit/PACKAGE_MANIFEST.json").read_text())
    with zipfile.ZipFile(ROOT / "packages/JDSA_sources.zip") as z:
        check(
            "source archive complete and flat",
            set(z.namelist()) == set(archive_manifest) and all("/" not in n for n in z.namelist()),
        )
        check(
            "source archive hashes match",
            all(sha(z.read(n)) == h for n, h in archive_manifest.items()),
        )
        check(
            "source archive excludes compiled documents and restricted inputs",
            not any(n in z.namelist() for n in ["main.pdf", "supplement.pdf", "ESM_1.pdf"])
            and not any(n.endswith((".json", ".jsonl", ".csv", ".parquet")) for n in z.namelist()),
        )
    all_pdfs = [n for n in files if n.lower().endswith(".pdf")]
    check(
        "99 supporting PDFs unchanged",
        len(all_pdfs) == 100
        and all(
            (REPO / n).read_bytes() == old(n) for n in all_pdfs if n != "LATEST_MANUSCRIPT.pdf"
        ),
    )
    report = {
        "status": "PASS" if all(c["passed"] for c in checks) else "FAIL",
        "base_main_sha": BASE,
        "passed": sum(c["passed"] for c in checks),
        "total": len(checks),
        "checks": checks,
        "pdfs": pdfs,
        "numerical_results_changed": False,
        "statistical_methods_changed": False,
        "new_experiments": False,
        "new_statistical_tests": False,
    }
    (ROOT / "audit/SCIENTIFIC_WRITING_VALIDATION.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in report.items() if k not in ("checks", "pdfs")}, indent=2))
    for c in checks:
        if not c["passed"]:
            print("FAIL:", c["check"], c["detail"])
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
