"""Descriptive composition of authentic saved rankings; no inference or optimization.

Supply a rights-cleared numeric-profile projection with original query identity,
dataset, provider-availability (2 or 4), and cyclicity metadata. Inputs and
query-level output are private; only aggregate TeX tables and a minimal observed
case description are intended for manuscript inclusion. See the schema guide.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

from verify_relevance_profiles import reconstruct

DATASETS = ("scidocs", "fiqa", "bright", "hotpotqa")
NAMES = {"scidocs": "SciDocs", "fiqa": "FiQA", "bright": "BRIGHT", "hotpotqa": "HotpotQA"}
REPAIRS = ("greedy", "scip_exact")
COUNT_FIELDS = (
    "queries",
    "positive_pool",
    "cyclic",
    "cyclic_positive",
    "ranking_unchanged",
    "ranking_changed",
    "changed_equal_profile",
    "changed_zero_positive",
    "changed_positive_equal_profile",
    "changed_profile_zero_metric",
    "utility_changed",
    "improvements",
    "deteriorations",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compute(units):
    seen, results = set(), []
    if len({u["unit"] for u in units}) != len(units):
        raise ValueError("Duplicate numeric linkage unit")
    for unit in units:
        identity = (unit["dataset"], unit["query_id"])
        if identity in seen or not isinstance(identity[1], str) or not identity[1]:
            raise ValueError("Duplicate or absent original dataset/query identity")
        seen.add(identity)
        if unit["dataset"] not in DATASETS or unit["providers"] not in (2, 4):
            raise ValueError("Undeclared dataset or provider-availability stratum")
        if type(unit["cyclic"]) is not bool:
            raise ValueError("Cyclicity must come from the saved graph record")
        if any(not math.isfinite(g) for g in unit["full_ideal_top10"]):
            raise ValueError("Nonfinite full-query ideal grade")
        for row in reconstruct(unit):
            results.append(
                {
                    **row,
                    "dataset": unit["dataset"],
                    "query_id": unit["query_id"],
                    "providers": unit["providers"],
                    "cyclic": unit["cyclic"],
                }
            )
    return results


def aggregate(rows):
    if len({(r["dataset"], r["query_id"]) for r in rows}) != len(rows):
        raise ValueError("A summary must contain one repair record per distinct query")
    out = {name: 0 for name in COUNT_FIELDS}
    for row in rows:
        changed = row["ranking_changed"]
        positive = row["positive_in_pool"] > 0
        zero = abs(row["saved_delta_ndcg10"]) <= 1e-12
        equal = row["identical_top10_grade_sequence"]
        out["queries"] += 1
        out["positive_pool"] += positive
        out["cyclic"] += row["cyclic"]
        out["cyclic_positive"] += row["cyclic"] and positive
        out["ranking_unchanged"] += not changed
        out["ranking_changed"] += changed
        out["changed_equal_profile"] += changed and equal
        out["changed_zero_positive"] += changed and not positive and zero
        out["changed_positive_equal_profile"] += changed and positive and equal and zero
        out["changed_profile_zero_metric"] += changed and positive and not equal and zero
        out["utility_changed"] += not zero
        out["improvements"] += row["saved_delta_ndcg10"] > 1e-12
        out["deteriorations"] += row["saved_delta_ndcg10"] < -1e-12
        if not changed and not zero:
            raise ValueError("Unchanged ranking cannot have changed metric")
    if out["ranking_changed"] + out["ranking_unchanged"] != out["queries"]:
        raise ValueError("Ranking partition failed")
    if out["utility_changed"] != out["improvements"] + out["deteriorations"]:
        raise ValueError("Metric sign partition failed")
    if (
        sum(
            out[k]
            for k in (
                "ranking_unchanged",
                "changed_zero_positive",
                "changed_positive_equal_profile",
                "changed_profile_zero_metric",
                "utility_changed",
            )
        )
        != out["queries"]
    ):
        raise ValueError("Opportunity partition failed")
    return out


def summarize(rows):
    def pair(selected):
        return {
            repair: aggregate([r for r in selected if r["repair"] == repair]) for repair in REPAIRS
        }

    result = {
        "all": pair(rows),
        "dataset": {d: pair([r for r in rows if r["dataset"] == d]) for d in DATASETS},
        "availability": {str(p): pair([r for r in rows if r["providers"] == p]) for p in (2, 4)},
        "positive_availability": {
            str(p): pair([r for r in rows if (r["positive_in_pool"] > 0) == p])
            for p in (False, True)
        },
        "intersections": [],
    }
    # Fixed complete cross-tabulation includes empty cells; no outcome selects a stratum.
    for dataset, providers, positive in itertools.product(DATASETS, (2, 4), (False, True)):
        selected = [
            r
            for r in rows
            if r["dataset"] == dataset
            and r["providers"] == providers
            and (r["positive_in_pool"] > 0) == positive
        ]
        result["intersections"].append(
            {
                "dataset": dataset,
                "providers": providers,
                "positive": positive,
                "counts": pair(selected),
            }
        )
    for repair in REPAIRS:
        total = result["all"][repair]
        for grouping in (
            result["dataset"].values(),
            result["availability"].values(),
            result["positive_availability"].values(),
            [x["counts"] for x in result["intersections"]],
        ):
            for field in COUNT_FIELDS:
                if sum(cell[repair][field] for cell in grouping) != total[field]:
                    raise ValueError(f"Non-additive {repair}/{field} marginal")
    return result


def historical_contract(summary):
    expected = {
        "greedy": {
            "queries": 213,
            "positive_pool": 134,
            "cyclic": 191,
            "ranking_changed": 180,
            "ranking_unchanged": 33,
            "changed_zero_positive": 69,
            "changed_positive_equal_profile": 74,
            "utility_changed": 37,
            "improvements": 15,
            "deteriorations": 22,
            "changed_profile_zero_metric": 0,
        },
        "scip_exact": {
            "queries": 213,
            "positive_pool": 134,
            "cyclic": 191,
            "ranking_changed": 160,
            "ranking_unchanged": 53,
            "changed_zero_positive": 61,
            "changed_positive_equal_profile": 74,
            "utility_changed": 25,
            "improvements": 16,
            "deteriorations": 9,
            "changed_profile_zero_metric": 0,
        },
    }
    for repair, counts in expected.items():
        for name, value in counts.items():
            if summary["all"][repair][name] != value:
                raise ValueError(
                    f"Historical discrepancy: {repair}/{name}; investigate input linkage"
                )
    for dataset, n in zip(DATASETS, (77, 76, 42, 18), strict=True):
        if any(summary["dataset"][dataset][b]["queries"] != n for b in REPAIRS):
            raise ValueError("Historical dataset roster changed")
    for providers, n in (("2", 110), ("4", 103)):
        if any(summary["availability"][providers][b]["queries"] != n for b in REPAIRS):
            raise ValueError("Historical availability roster changed")


def worked_example(units, rows):
    lookup = {u["unit"]: u for u in units}
    candidates = []
    for row in rows:
        if (
            row["repair"] != "greedy"
            or row["descriptive_class"] != "positive_pool_identical_top10_grade_sequence"
        ):
            continue
        if row["moved_documents"] != row["moved_unjudged"]:
            continue
        unit = lookup[row["unit"]]
        moved = [
            i + 1
            for i, (a, b) in enumerate(
                zip(unit["rankings"]["none"], unit["rankings"]["greedy"], strict=True)
            )
            if a != b
        ]
        if not any(i <= 10 for i in moved):
            continue
        candidates.append((len(moved), row["dataset"], row["query_id"], row, moved))
    if not candidates:
        raise ValueError("No authentic worked case satisfying the declared illustration rule")
    _, _, _, row, moved = min(candidates, key=lambda c: c[:3])
    unit = lookup[row["unit"]]
    public = {
        "case": "C1",
        "dataset": row["dataset"],
        "providers": row["providers"],
        "repair": "greedy",
        "moved_positions": moved,
        "top10_grades": [unit["grades"][d] for d in unit["rankings"]["none"][:10]],
        "baseline_ndcg10": row["baseline_ndcg10"],
        "repaired_ndcg10": row["ndcg10"],
        "delta": row["saved_delta_ndcg10"],
        "moved_all_unjudged": True,
    }
    private = {"unit": row["unit"], "dataset": row["dataset"], "query_id": row["query_id"]}
    return public, private


def render(summary, example, destination):
    destination.mkdir(parents=True, exist_ok=True)
    fields = (
        "ranking_unchanged",
        "ranking_changed",
        "changed_positive_equal_profile",
        "utility_changed",
        "improvements",
        "deteriorations",
    )

    def pairs(cell, names):
        return [f"{cell['greedy'][k]}/{cell['scip_exact'][k]}" for k in names]

    lines = [
        r"\begin{table*}[t]",
        (
            "\\caption{Composition of the 213 selected queries. $P+$ counts pools "
            "with a judged-positive candidate. Paired entries are greedy/exact "
            "(G/E) counts on the same queries. Same/changed refer to full "
            "rankings; Eq.$+$ counts changed-ranking, positive-pool cases with the "
            "same evaluated top-ten grade profile and zero metric change. $\\Delta "
            "U$ counts measured utility changes. Dataset and availability panels "
            "are overlapping descriptions, not independent samples.}"
        ),
        r"\label{tab:selected-composition}\papertable",
        r"\begin{tabularx}{\linewidth}{@{}Yrrrrrrrr@{}}\toprule",
        (
            "Group & $N$ & $P+$ & Same G/E & Changed G/E & Eq.$+$ G/E & $\\Delta U$ "
            "G/E & Gains G/E & Harms G/E\\\\\\midrule"
        ),
    ]
    groups = [(NAMES[d], summary["dataset"][d]) for d in DATASETS]
    groups += [
        ("Two-provider", summary["availability"]["2"]),
        ("Four-provider", summary["availability"]["4"]),
        ("All queries", summary["all"]),
    ]
    for index, (label, cell) in enumerate(groups):
        if index in (4, 6):
            lines.append(r"\midrule")
        lines.append(
            " & ".join(
                [label, str(cell["greedy"]["queries"]), str(cell["greedy"]["positive_pool"])]
                + pairs(cell, fields)
            )
            + r"\\"
        )
    lines += [r"\bottomrule\end{tabularx}", r"\end{table*}"]
    (destination / "selected_composition_main.tex").write_text("\n".join(lines) + "\n")
    lines = [
        r"\begin{supplementtable}\papertable\setlength{\tabcolsep}{3pt}",
        (
            r"\caption{Complete dataset $\times$ provider-availability $\times$ "
            "judged-positive-availability decomposition. $P+$ is yes/no positive pool; "
            "$C$ counts cyclic graphs (cyclic-positive cases in yes rows). "
            "Same/changed count full rankings; Equal counts changed rankings with "
            "identical evaluated grade profiles, including zero-positive cases. "
            "The last six columns contain paired greedy/exact counts. "
            "Empty cells have $N=0$; they are not estimates of population behavior.}"
            r"\label{tab:selected-composition-detail}"
        ),
        r"\begin{tabular}{@{}lllrrrrrrrr@{}}\toprule",
        (
            r"Dataset & Prov. & $P+$ & $N$ & $C$ & Same & Changed & Equal & "
            r"$\Delta U$ & Gain & Harm\\\midrule"
        ),
    ]
    detail_fields = (
        "ranking_unchanged",
        "ranking_changed",
        "changed_equal_profile",
        "utility_changed",
        "improvements",
        "deteriorations",
    )
    for index, group in enumerate(summary["intersections"]):
        cell = group["counts"]
        if index and index % 4 == 0:
            lines.append(r"\addlinespace[3pt]")
        lines.append(
            " & ".join(
                [
                    NAMES[group["dataset"]],
                    str(group["providers"]),
                    "yes" if group["positive"] else "no",
                    str(cell["greedy"]["queries"]),
                    str(cell["greedy"]["cyclic"]),
                ]
                + pairs(cell, detail_fields)
            )
            + r"\\"
        )
    lines += [r"\bottomrule\end{tabular}\end{supplementtable}"]
    (destination / "selected_composition_detail.tex").write_text("\n".join(lines) + "\n")
    grades = ",".join(
        str(int(g)) if float(g).is_integer() else str(g) for g in example["top10_grades"]
    )
    moved = " and ".join(map(str, example["moved_positions"]))
    action = (
        "exchanges the documents at ranks"
        if len(example["moved_positions"]) == 2
        else "moves documents occupying ranks"
    )
    text = (
        r"\paragraph{Observed fixed-profile case (C1).} "
        + f"In an authentic {NAMES[example['dataset']]} {example['providers']}-provider "
        + f"selected-cache record, greedy repair {action} {moved}. "
        + "All moved documents are unjudged. The evaluated top-ten grade vector remains "
        + "$({"
        + grades
        + "})$, and full-query nDCG@10 remains "
        + f"{example['baseline_ndcg10']:.6f} (change zero at $10^{{-12}}$ tolerance). "
        + (
            "This is an observed saved-ranking case, not a synthetic permutation; "
            "its source linkage is preserved privately. "
        )
        + "Unjudged is an evaluation status, not proven irrelevance. "
        + (
            "Section~\\ref{sec:optimum-choice} gives the contrasting observed case "
            "in which an optimal-repair choice changes a positive document's rank "
            "and measured utility."
        )
        + "\n"
    )
    (destination / "selected_worked_example.tex").write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--render-dir", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    data = json.loads(args.input.read_text())
    if data["schema"] != "selected-composition-inputs-v1":
        raise ValueError("Unrecognized input schema")
    rows = compute(data["units"])
    (args.output / "COMPUTED_BEFORE_REFERENCE.json").write_text(json.dumps(rows, indent=2) + "\n")
    reference = json.loads(args.reference.read_text())
    expected = {(r["unit"], r["repair"]): r for r in reference}
    if len(rows) != len(reference) or len(expected) != len(reference):
        raise ValueError("Reference identity count mismatch")
    checks, maximum = 0, 0.0
    for row in rows:
        saved = expected[(row["unit"], row["repair"])]
        for name, value in saved.items():
            if type(value) is float:
                error = abs(row[name] - value)
                maximum = max(maximum, error)
                if not math.isfinite(error) or error > 1e-12:
                    raise ValueError(f"Saved arithmetic discrepancy in {row['unit']}/{name}")
            elif row[name] != value:
                raise ValueError(f"Saved indicator discrepancy in {row['unit']}/{name}")
            checks += 1
    summary = summarize(rows)
    historical_contract(summary)
    example, identity = worked_example(data["units"], rows)
    (args.output / "WORKED_EXAMPLE_IDENTITY_PRIVATE.json").write_text(
        json.dumps(identity, indent=2) + "\n"
    )
    report = {
        "status": "PASS",
        "query_units": len(data["units"]),
        "branch_records": len(rows),
        "input_sha256": sha(args.input),
        "reference_sha256": sha(args.reference),
        "reference_fields_checked": checks,
        "maximum_reference_error": maximum,
        "summary": summary,
        "worked_example": example,
        "new_significance_tests": 0,
        "original_measurements_changed": False,
        "input_access": "PRIVATE; sharing and confidential reviewer delivery unresolved",
    }
    (args.output / "COMPOSITION_VALIDATION.json").write_text(json.dumps(report, indent=2) + "\n")
    if args.render_dir:
        render(summary, example, args.render_dir)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
