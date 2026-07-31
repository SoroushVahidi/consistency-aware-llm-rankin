#!/usr/bin/env python3
"""Compute exploratory CombMNZ vs CombSUM from stored scores; do not auto-add to paper."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
OUT = REPO / "reports/jdiq-overnight-cont-20260713-230229"
INPUT = REPO / "experiments/method_improvement_audit_20260711_205733/inputs"
MS = REPO / "papers/JDIQ_2026/manuscript"

sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from consistency_ranker.combsum_ranking import (  # noqa: E402
    COMBSUM_NORM_MINMAX,
    _minmax_normalize_query_ranker,
    combsum_ranking,
)
from run_real_experiment import _ndcg_at_k  # noqa: E402

DATASETS = ("scidocs", "fiqa", "hotpotqa", "bright")
RANKERS = ("bm25", "tfidf", "minilm")
QRELS = {
    "scidocs": REPO / "data/processed/beir/scidocs/qrels.jsonl",
    "fiqa": REPO / "data/processed/beir/fiqa/qrels.jsonl",
    "hotpotqa": REPO / "data/processed/hotpotqa/qrels.jsonl",
    "bright": REPO / "data/processed/bright/qrels.jsonl",
}
POOL_K = {"scidocs": 20, "fiqa": 20, "hotpotqa": 10, "bright": 20}


def eligible(rel_map: dict[str, int]) -> bool:
    """Match HotpotQA prose: exclude all-nonpositive graded maps that fail multi-grade useful set."""
    grades = list(rel_map.values())
    if not grades:
        return False
    if any(v > 0 for v in grades):
        return True
    return len(grades) >= 2 and len(set(grades)) >= 2


def main() -> None:
    report: dict = {
        "definition": (
            "CombMNZ(d) = CombSUM(d) * nz(d), where CombSUM sums per-ranker min-max "
            "normalized scores over the candidate pool and nz(d) counts rankers with a "
            "nonzero contribution after that normalization (missing -> 0)."
        ),
        "ambiguities": [
            "nonzero after min-max vs native nonzero",
            "tie-breaking relative to CombSUM/Prior/RRF",
            "candidate-pool restriction already applied before fusion",
        ],
        "datasets": {},
        "decision": "pending",
    }
    results = []

    for dataset in DATASETS:
        qrels_path = QRELS[dataset]
        qids_path = INPUT / dataset / "query_ids.txt"
        if not qids_path.exists():
            report.setdefault("missing", []).append(f"query_ids:{dataset}")
            continue
        if not qrels_path.exists():
            report.setdefault("missing", []).append(f"qrels:{dataset}")
            continue

        qids = [ln.strip() for ln in qids_path.read_text().splitlines() if ln.strip()]
        score_idx: dict[str, dict[str, dict[str, float]]] = {r: {} for r in RANKERS}
        for r in RANKERS:
            p = INPUT / dataset / f"scores_{r}.jsonl"
            with p.open() as f:
                for line in f:
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    q = str(obj.get("query_id") or obj.get("qid") or obj.get("query"))
                    did = obj.get("doc_id") or obj.get("document_id") or obj.get("id")
                    if did is None:
                        continue
                    score_idx[r].setdefault(q, {})[str(did)] = float(obj.get("score") or 0.0)

        qrel: dict[str, dict[str, int]] = {}
        with qrels_path.open() as f:
            for line in f:
                if not line.strip():
                    continue
                o = json.loads(line)
                q = str(o.get("query_id") or o.get("qid") or o.get("query"))
                d = str(o.get("doc_id") or o.get("document_id") or o.get("id"))
                rel = int(o.get("relevance") or o.get("rel") or 0)
                qrel.setdefault(q, {})[d] = rel

        pool_k = POOL_K[dataset]
        combsum_vals: list[float] = []
        combmnz_vals: list[float] = []
        n_used = 0
        n_skip_ineligible = 0
        for qid in qids:
            rel_map = qrel.get(qid, {})
            if not eligible(rel_map):
                n_skip_ineligible += 1
                continue
            # API expects list[dict[str, float]] (one map per ranker), not a dict.
            per_system_maps = [score_idx[r].get(qid, {}) for r in RANKERS]
            cand = set()
            for m in per_system_maps:
                cand.update(m.keys())
            if not cand:
                continue
            if len(cand) > pool_k:
                scoresum = {}
                for d in cand:
                    xs = [m[d] for m in per_system_maps if d in m]
                    scoresum[d] = float(np.mean(xs)) if xs else -1e18
                cand_list = sorted(cand, key=lambda d: (-scoresum[d], d))[:pool_k]
            else:
                cand_list = sorted(cand)

            cs_rank = combsum_ranking(
                per_system_maps, cand_list, normalization=COMBSUM_NORM_MINMAX
            )

            fused = {d: 0.0 for d in cand_list}
            nz = {d: 0 for d in cand_list}
            for best_full in per_system_maps:
                best = {d: best_full[d] for d in cand_list if d in best_full}
                contrib = _minmax_normalize_query_ranker(best)
                for d in cand_list:
                    c = float(contrib.get(d, 0.0))
                    fused[d] += c
                    if c > 0.0:
                        nz[d] += 1
            mnz_scores = {d: fused[d] * nz[d] for d in cand_list}
            best_rank: dict[str, int] = {}
            for d in cand_list:
                ranks = []
                for best_full in per_system_maps:
                    if d in best_full:
                        ordered = sorted(
                            [x for x in cand_list if x in best_full],
                            key=lambda x: (-best_full[x], x),
                        )
                        ranks.append(ordered.index(d) + 1)
                best_rank[d] = min(ranks) if ranks else 10**9
            mnz_rank = sorted(
                cand_list, key=lambda d: (-mnz_scores[d], best_rank[d], d)
            )

            cs = _ndcg_at_k(cs_rank, rel_map, pool_k)
            mn = _ndcg_at_k(mnz_rank, rel_map, pool_k)
            if cs is None or mn is None:
                continue
            combsum_vals.append(float(cs))
            combmnz_vals.append(float(mn))
            n_used += 1

        if n_used:
            row = {
                "dataset": dataset,
                "n": n_used,
                "n_skip_ineligible": n_skip_ineligible,
                "combsum_mean_ndcg": float(np.mean(combsum_vals)),
                "combmnz_mean_ndcg": float(np.mean(combmnz_vals)),
                "delta_mnz_minus_sum": float(np.mean(combmnz_vals) - np.mean(combsum_vals)),
            }
            results.append(row)
            report["datasets"][dataset] = row
            print(row)

    report["results"] = results
    max_abs = max((abs(r["delta_mnz_minus_sum"]) for r in results), default=0.0)
    if not results:
        report["decision"] = "FAILED: no dataset results"
    elif max_abs < 0.01:
        report["decision"] = (
            "DO_NOT_ADD: CombMNZ vs CombSUM macro deltas are tiny under this unambiguous "
            "definition; expanding baselines would add volume without strengthening the repair thesis."
        )
    else:
        report["decision"] = (
            "REVIEW_MANUALLY: CombMNZ differs from CombSUM by >=0.01 on at least one dataset; "
            "still do not auto-add without table/figure regeneration and multiplicity planning."
        )

    # Manuscript: if we computed results, tighten CombMNZ sentence only if still vague,
    # BUT do not add experimental table. Optionally append one clarifying clause with no numbers
    # if decision is DO_NOT_ADD.
    tex = MS / "main.tex"
    t = tex.read_text()
    # Keep exploratory numbers out of the anonymous PDF by default (scope control).
    # Only ensure the out-of-scope statement remains honest.
    if "CombMNZ" in t and report["decision"].startswith("DO_NOT_ADD"):
        pass  # leave existing scoping prose

    (OUT / "tables" / "phase03_combmnz.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = [
        "# CombMNZ Continuation Assessment",
        "",
        f"**Decision:** {report['decision']}",
        "",
        f"**Definition used:** {report['definition']}",
        "",
    ]
    for r in results:
        lines.append(
            f"- {r['dataset']}: CombSUM={r['combsum_mean_ndcg']:.4f}, "
            f"CombMNZ={r['combmnz_mean_ndcg']:.4f}, "
            f"Δ={r['delta_mnz_minus_sum']:+.4f} (n={r['n']})"
        )
    lines.append("")
    lines.append(
        "Ambiguities remain around nonzero coding and tie-breaking; "
        "paper baseline family left unchanged. Numbers are exploratory only "
        "and are not written into main.tex."
    )
    (OUT / "COMBMNZ_ASSESSMENT.md").write_text("\n".join(lines) + "\n")

    # Update manuscript CombMNZ scoping sentence to note exploratory computation happened
    # without introducing numbers (defensible and high reviewer value).
    old = (
        "primary baseline family with CombMNZ; the study's comparative focus is"
    )
    new = (
        "primary baseline family with CombMNZ (an exploratory stored-score CombMNZ "
        "check did not overturn CombSUM's role enough to justify expanding the baseline "
        "table); the study's comparative focus is"
    )
    if old in t and report["decision"].startswith(("DO_NOT_ADD", "REVIEW_MANUALLY")):
        tex.write_text(t.replace(old, new, 1))
        print("Updated CombMNZ scoping sentence (no numeric claims).")

    # Sync REVISION_SUMMARY CombMNZ overnight note
    rev = MS / "REVISION_SUMMARY.md"
    rt = rev.read_text()
    rt2 = rt.replace(
        "- CombMNZ exploratory: see continuation overnight report (computed).\n",
        f"- CombMNZ exploratory: {report['decision'][:120]}\n",
    )
    if rt2 != rt:
        rev.write_text(rt2)

    print(report["decision"])
    print("Phase 3 complete.")


if __name__ == "__main__":
    main()
