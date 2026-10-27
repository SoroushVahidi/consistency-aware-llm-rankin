"""Validate the scientific revision against its fixed JDSA baseline.

Reorganization and new descriptive analyses are intentional. Protect individual
original tables, figure bytes and statistical methods, rather than requiring the
old prose/result-section ordering to remain unchanged. No model/solver executes.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "manuscript"
AUDIT = ROOT / "audit"
BASE = "2c69f331fa4add10ce577c17516afb997b630dfe"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def expanded(name, seen=None):
    seen = set() if seen is None else seen
    if name in seen:
        raise ValueError(f"Repeated or recursive input: {name}")
    seen.add(name)
    text = (SRC / name).read_text()
    return re.sub(
        r"\\input\{([^}]+)\}",
        lambda m: expanded(m[1] + ".tex", seen),
        text,
    )


def citations(text):
    return {k.strip() for m in re.findall(r"\\cite\w*\{([^}]+)\}", text) for k in m.split(",")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protected-root", type=Path)
    args = parser.parse_args()
    checks = []

    def check(name, ok, detail=None):
        checks.append(dict(check=name, passed=bool(ok), detail=detail))

    repo = ROOT.parents[1]

    def original(path):
        return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=repo)

    baseline = json.loads((AUDIT / "SCIENTIFIC_REVISION_BASELINE.json").read_text())
    check("fixed baseline commit", baseline["base_commit"] == BASE)
    protected = []
    for relative, saved_hash in baseline["files"].items():
        p = Path(relative)
        if p.parent.name != "manuscript":
            continue
        if p.suffix not in (".tex", ".pdf", ".cls", ".bst"):
            continue
        if p.name in {
            "main.tex",
            "supplement.tex",
            "authors.tex",
            "declarations.tex",
            "main.pdf",
            "supplement.pdf",
            "ESM_1.pdf",
            "main_anonymous.pdf",
            "supplement_anonymous.pdf",
        }:
            continue
        protected.append(relative)
        check("unchanged baseline asset: " + p.name, digest((repo / p).read_bytes()) == saved_hash)
    main_text = (SRC / "main.tex").read_text()
    si = (SRC / "supplement.tex").read_text()
    old_main = original("papers/JDSA_2026/manuscript/main.tex").decode()

    def tables(s):
        return collections.Counter(re.findall(r"\\begin\{tabularx\}.*?\\end\{tabularx\}", s, re.S))

    check("all six original main table bodies preserved", tables(main_text) == tables(old_main))
    start = r"\subsection{Evaluation and query-level inference}"
    end = r"\subsection{Evidence access and AI assistance}"

    def block(s):
        return s[s.index(start) : s.index(end)]

    check(
        "original statistical estimands and methods preserved", block(main_text) == block(old_main)
    )
    abstract = re.search(r"\\abstract\{(.*?)\}\n\\keywords", main_text, re.S)[1]
    check("abstract 150 to 250 words", 150 <= len(abstract.split()) <= 250, len(abstract.split()))
    check("six keywords", len(re.search(r"\\keywords\{([^}]+)", main_text)[1].split(",")) == 6)
    check(
        "Springer two-column main format retained", "pdflatex,iicol,sn-basic,Numbered" in main_text
    )
    check(
        "three wording corrections",
        all(
            t not in main_text + si
            for t in (
                "Exact-cost controls retain no corrected general retrieval advantage",
                "It excludes restricted optional inputs",
                "without rerunning extraction or scoring",
            )
        ),
    )
    bib = (SRC / "references.bib").read_text()
    bib_keys = re.findall(r"@\w+\s*\{\s*([^,]+),", bib)
    check("unique bibliography keys", len(bib_keys) == len(set(bib_keys)))
    pdf_summary = {}
    for name in ("main", "supplement"):
        text = expanded(name + ".tex")
        keys = citations(text)
        labels = re.findall(r"\\label\{([^}]+)\}", text)
        refs = re.findall(r"\\(?:eqref|ref)\{([^}]+)\}", text)
        check(
            name + " source references resolved",
            set(refs) <= set(labels),
            sorted(set(refs) - set(labels)),
        )
        check(name + " unique labels", len(labels) == len(set(labels)))
        check(name + " citation metadata present", keys <= set(bib_keys))
        old_keys = citations(original(f"papers/JDSA_2026/manuscript/{name}.tex").decode())
        check(name + " prior citations retained", old_keys <= keys)
        for suffix in ("", "_anonymous"):
            doc = name + suffix
            log = (SRC / "build" / (doc + ".log")).read_text()
            check(
                doc + " clean final LaTeX log",
                not re.search(
                    r"! |Overfull|undefined|multiply defined|There were undefined|Rerun to get", log
                ),
                {"underfull_notices": log.count("Underfull")},
            )
            bbl = (SRC / "build" / (doc + ".bbl")).read_text()
            found = set(re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", bbl))
            check(doc + " bibliography matches cited keys", found == keys, len(found))
            pdf = SRC / "build" / (doc + ".pdf")
            info = subprocess.check_output(["pdfinfo", str(pdf)], text=True)
            body = subprocess.check_output(["pdftotext", str(pdf), "-"], text=True)
            check(doc + " no unresolved PDF markers", "??" not in body)
            author = re.search(r"^Author:[ \t]*(.*)$", info, re.M)
            if suffix:
                check(
                    doc + " direct identifiers and acknowledgment withheld",
                    all(
                        x not in body
                        for x in (
                            "sv96@njit.edu",
                            "0000-0003-1934-6282",
                            "SoroushVahidi/",
                            "New Jersey Institute of Technology",
                            "Ioannis Koutis",
                        )
                    )
                    and (not author or not author[1].strip()),
                )
            else:
                check(
                    doc + " identified author details",
                    all(
                        x in body
                        for x in (
                            "Soroush Vahidi",
                            "sv96@njit.edu",
                            "0000-0003-1934-6282",
                        )
                    )
                    and author
                    and "Soroush Vahidi" in author[1],
                )
                if name == "main":
                    check(
                        "requested advisor acknowledgment",
                        "Professor Ioannis Koutis" in " ".join(body.split()),
                    )
            pdf_summary[doc] = dict(
                pages=int(re.search(r"^Pages:\s+(\d+)", info, re.M)[1]),
                sha256=digest(pdf.read_bytes()),
                references=len(found),
            )
    receipt = json.loads((AUDIT / "SCIENTIFIC_REVISION_EVIDENCE.json").read_text())
    comp = receipt["composition"]
    from stratify_selected_cache import historical_contract, render

    historical_contract(comp["summary"])
    check(
        "213-query 426-branch reconstruction",
        comp["query_units"] == 213 and comp["branch_records"] == 426,
    )
    check(
        "original 219 source hashes verified",
        receipt["composition_source_receipt"]["original_sources_verified"] == 219,
    )
    check(
        "6816 attribution fields reproduce",
        comp["reference_fields_checked"] == 6816 and comp["maximum_reference_error"] <= 1e-12,
    )
    check("no added inferential family", comp["new_significance_tests"] == 0)
    # Compare generated files in a temporary directory; manuscript sources stay untouched.
    import tempfile

    with tempfile.TemporaryDirectory() as temp:
        render(comp["summary"], comp["worked_example"], Path(temp))
        check(
            "generated tables and observed case match validated receipt",
            all(f.read_bytes() == (SRC / f.name).read_bytes() for f in Path(temp).iterdir()),
        )
    corrected = receipt["corrected35_saved_endpoints"]
    display = (SRC / "informative_support.tex").read_text().splitlines()
    display_ok = True
    for test_id, label in (
        ("EVG35-013", "Copeland E--G"),
        ("EVG35-028", "Priority-topological E--G"),
    ):
        saved = next(r for r in corrected if r["test_id"] == test_id)
        line = next(t for t in display if t.startswith(label + " &"))
        display_ok &= all(
            f"{float(saved[k]):.6f}" in line
            for k in (
                "corrected_mean_delta",
                "cluster_percentile_ci_low",
                "cluster_percentile_ci_high",
            )
        )
        display_ok &= str(int(saved["query_positive"]) + int(saved["query_negative"])) in line
    for saved in receipt["selected_saved_endpoints"]:
        if saved["cohort"] == "pool8_complete":
            label = "G/E--U, primary aggregate"
        else:
            label = "G--U" if saved["repair"] == "greedy" else "E--U"
            label += ", two-provider" if saved["n_queries"] == 110 else ", four-provider"
        line = next(t for t in display if t.startswith(label + " &"))
        display_ok &= f"{saved['mean_delta']:.6f}" in line
        display_ok &= all((f"{v:.6f}" if v else "0") in line for v in saved["ci95"])
    check("new main uncertainty display matches saved endpoint values", display_ok)
    support = collections.Counter(int(r["independent_query_units"]) for r in corrected)
    nonzero = [int(r["query_positive"]) + int(r["query_negative"]) for r in corrected]
    check(
        "35 comparisons, 342/290 supports, zero Holm rejections",
        len(corrected) == 35
        and support == {342: 28, 290: 7}
        and all(float(r["cluster_signflip_holm_p"]) > 0.05 for r in corrected),
    )
    check("4--99 nonzero support range", min(nonzero) == 4 and max(nonzero) == 99)
    invariant = json.loads((AUDIT / "SAVED_INVARIANTS.json").read_text())
    check(
        "1025 graph records and six diagnostics retained",
        all(
            invariant[k] == v
            for k, v in {
                "structural_records": 1025,
                "acyclic": 646,
                "cyclic": 379,
                "envelope_graphs": 6,
            }.items()
        ),
    )
    manifest = json.loads((AUDIT / "PACKAGE_MANIFEST.json").read_text())
    with zipfile.ZipFile(ROOT / "packages/JDSA_sources.zip") as archive:
        check(
            "source archive is flat and complete",
            set(archive.namelist()) == set(manifest)
            and all("/" not in n for n in archive.namelist()),
        )
        check(
            "source archive hashes match",
            all(digest(archive.read(n)) == h for n, h in manifest.items()),
        )
        check(
            "no private payload or editorial documents in archive",
            all(
                not n.endswith((".json", ".jsonl", ".csv", ".parquet"))
                and "PRIVATE" not in n
                and "editorial" not in n
                for n in archive.namelist()
            ),
        )
        required = {
            p.name for p in SRC.iterdir() if p.suffix in {".tex", ".cls", ".bst", ".bib", ".sh"}
        }
        required |= {
            "Fig2.pdf",
            "Fig3.pdf",
            "ESM_Fig1.pdf",
            "ESM_Fig2.pdf",
            "ESM_Fig3.pdf",
            "main.bbl",
            "supplement.bbl",
            "verify_relevance_profiles.py",
            "verify_optimum_envelope.py",
            "stratify_selected_cache.py",
            "test_selected_composition.py",
            "OFFLINE_VERIFICATION.md",
            "STRATIFIED_ATTRIBUTION.md",
            "LICENSE_VERIFICATION_CODE.txt",
        }
        check(
            "every source input and data-free procedure packaged",
            required == set(archive.namelist()),
        )
    if args.protected_root:
        ledger = json.loads((AUDIT / "IJIT_SOURCE_SHA256.json").read_text())
        matches = sum(
            (args.protected_root / p).is_file()
            and digest((args.protected_root / p).read_bytes()) == h
            for p, h in ledger.items()
        )
        check(
            "all protected historical files unchanged",
            matches == len(ledger),
            {"matched": matches, "total": len(ledger)},
        )
    integration = json.loads((AUDIT / "MAIN_INTEGRATION_MANIFEST.json").read_text())
    canonical = repo / "LATEST_MANUSCRIPT.pdf"
    check(
        "canonical PDF is the exact approved revision artifact",
        digest(canonical.read_bytes()) == integration["canonical_sha256"],
    )
    check("identified main rebuild has 20 pages", pdf_summary["main"]["pages"] == 20)
    check("identified supplement rebuild has 38 pages", pdf_summary["supplement"]["pages"] == 38)
    canonical_text = subprocess.check_output(["pdftotext", str(canonical), "-"], text=True)
    rebuilt_text = subprocess.check_output(
        ["pdftotext", str(SRC / "build/main.pdf"), "-"], text=True
    )
    check("canonical and rebuilt manuscript text match", canonical_text == rebuilt_text)
    check(
        "README begins with canonical download link",
        (repo / "README.md")
        .read_text()
        .startswith(
            "# Latest Manuscript\n\n[Download the latest JDSA manuscript](LATEST_MANUSCRIPT.pdf)"
        ),
    )
    for item in integration["source_pdf_inventory"]:
        path = repo / item["path"]
        if item["action"] == "retain":
            check(
                "retained supporting PDF: " + item["path"],
                path.is_file() and digest(path.read_bytes()) == item["sha256"],
            )
        else:
            check("superseded output absent: " + item["path"], not path.exists())
    tracked = subprocess.check_output(["git", "ls-files"], cwd=repo, text=True).splitlines()
    pdf_paths = [p for p in tracked if p.lower().endswith(".pdf")]
    check(
        "one canonical manuscript and expected supporting PDFs",
        len(pdf_paths) == integration["expected_final_pdf_count"]
        and "LATEST_MANUSCRIPT.pdf" in pdf_paths
        and not set(pdf_paths).intersection(integration["removed_pdf_paths"]),
    )
    # All scientific TeX, bibliography, numeric evidence and analysis stay at af03da5.
    source = integration["source_revision_sha"]
    source_paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", source, "papers/JDSA_2026"], cwd=repo, text=True
    ).splitlines()
    scientific = [
        p
        for p in source_paths
        if Path(p).suffix in (".tex", ".bib", ".cls", ".bst")
        or p.endswith(
            (
                "stratify_selected_cache.py",
                "verify_relevance_profiles.py",
                "verify_optimum_envelope.py",
                "SCIENTIFIC_REVISION_EVIDENCE.json",
            )
        )
    ]
    check(
        "all revision scientific sources and evidence byte-identical",
        all(
            (repo / p).read_bytes()
            == subprocess.check_output(["git", "show", f"{source}:{p}"], cwd=repo)
            for p in scientific
        ),
        len(scientific),
    )
    result = dict(
        status="PASS" if all(c["passed"] for c in checks) else "FAIL",
        passed=sum(c["passed"] for c in checks),
        total=len(checks),
        checks=checks,
        baseline_commit=BASE,
        pdfs=pdf_summary,
        new_experiments_performed=False,
        scientific_scope="Existing-record descriptive arithmetic; original measurements preserved",
    )
    (AUDIT / "MAIN_INTEGRATION_DOCUMENT_VALIDATION.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in result.items() if k not in ("checks", "pdfs")}, indent=2))
    for c in checks:
        if not c["passed"]:
            print("FAIL:", c)
    raise SystemExit(result["status"] != "PASS")


if __name__ == "__main__":
    main()
