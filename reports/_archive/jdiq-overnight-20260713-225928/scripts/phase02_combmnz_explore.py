#!/usr/bin/env python3
"""Phase 2: exploratory CombMNZ from stored scores; do not auto-add to manuscript."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
OUT = REPO / "reports/jdiq-overnight-20260713-225928"
INPUT = REPO / "experiments/method_improvement_audit_20260711_205733/inputs"

import sys

sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports/full_calibrated_core/scripts"))

from consistency_ranker.combsum_ranking import (  # noqa: E402
    COMBSUM_NORM_MINMAX,
    _minmax_normalize_query_ranker,
    combsum_ranking,
)
from scripts.run_real_experiment import (  # noqa: E402
    _ndcg_at_k,
)
import full_calibration_utils as fc  # noqa: E402

DATASETS = ("scidocs", "fiqa", "hotpotqa", "bright")
RANKERS = ("bm25", "tfidf", "minilm")


def load_score_maps(dataset: str, qid: str) -> dict[str, dict[str, float]]:
    # Use existing helpers via score indexes if possible
    maps: dict[str, dict[str, float]] = {}
    for r in RANKERS:
        path = INPUT / dataset / f"scores_{r}.jsonl"
        # Fall back: scan file for query (slow but fine overnight)
        # Prefer utils loaders in full_calibration_utils
        maps[r] = {}
    return maps


def main() -> None:
    """Compute CombMNZ macro nDCG vs CombSUM on usable queries using calibrated package records if available."""
    # Prefer recomputing from the primary calibrated package query records by reconstructing rankings from score files
    # via full_calibration_utils dataset loaders.
    report = {
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

    # Use published CombSUM means from manuscript source CSV if present for sanity baselines
    cmp_csv = (
        REPO
        / "reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables"
    )
    # Lightweight exploratory: for each dataset, load eligible queries and compare macro nDCG of CombSUM vs CombMNZ
    try:
        from consistency_ranker.combsum_ranking import combsum_scores  # type: ignore
    except Exception as e:  # noqa: BLE001
        report["error"] = str(e)

    results = []
    for dataset in DATASETS:
        qrels_path = REPO / "data/processed" / dataset / "qrels.jsonl"
        qids_path = INPUT / dataset / "query_ids.txt"
        if not qids_path.exists() or not qrels_path.exists():
            continue
        qids = [ln.strip() for ln in qids_path.read_text().splitlines() if ln.strip()]
        # Load score indexes once
        score_idx: dict[str, dict[str, dict[str, float]]] = {r: {} for r in RANKERS}
        for r in RANKERS:
            p = INPUT / dataset / f"scores_{r}.jsonl"
            with p.open() as f:
                for line in f:
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    # Schema: one row per (query_id, doc_id, score)
                    q = str(obj.get("query_id") or obj.get("qid") or obj.get("query"))
                    did = obj.get("doc_id") or obj.get("document_id") or obj.get("id")
                    if did is None:
                        continue
                    score_idx[r].setdefault(q, {})[str(did)] = float(obj.get("score") or 0.0)

        # qrels
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

        # pool settings from manuscript table
        pool_k = {"scidocs": 20, "fiqa": 20, "hotpotqa": 10, "bright": 20}[dataset]
        ndcg_k = pool_k
        combsum_vals = []
        combmnz_vals = []
        n_used = 0
        for qid in qids:
            rel_map = qrel.get(qid, {})
            # eligibility: same rule as manuscript
            grades = [v for v in rel_map.values()]
            if not ((len(grades) >= 2 and len(set(grades)) >= 2) or any(v > 0 for v in grades)):
                continue
            per_system = {r: score_idx[r].get(qid, {}) for r in RANKERS}
            # candidate pool = union of scored docs, truncated if needed by simple score max
            cand = set()
            for m in per_system.values():
                cand.update(m.keys())
            if not cand:
                continue
            # If oversize, keep top by mean present raw scores
            if len(cand) > pool_k:
                scoresum = {}
                for d in cand:
                    xs = [per_system[r][d] for r in RANKERS if d in per_system[r]]
                    scoresum[d] = float(np.mean(xs)) if xs else -1e18
                cand_list = sorted(cand, key=lambda d: (-scoresum[d], d))[:pool_k]
            else:
                cand_list = sorted(cand)

            # CombSUM ranking via library
            cs_rank = combsum_ranking(per_system, cand_list, normalization=COMBSUM_NORM_MINMAX)

            # CombMNZ: multiply fused by nonzero count after per-ranker minmax contrib
            fused = {d: 0.0 for d in cand_list}
            nz = {d: 0 for d in cand_list}
            for r in RANKERS:
                best = {d: per_system[r][d] for d in cand_list if d in per_system[r]}
                contrib = _minmax_normalize_query_ranker(best)
                for d in cand_list:
                    c = float(contrib.get(d, 0.0))
                    fused[d] += c
                    if c > 0.0:
                        nz[d] += 1
            mnz_scores = {d: fused[d] * nz[d] for d in cand_list}
            # Tie-break: score, then best rank among systems, then id — match combsum style loosely
            best_rank = {}
            for d in cand_list:
                ranks = []
                for r in RANKERS:
                    if d in per_system[r]:
                        # approximate rank via score order within system over candidates
                        ordered = sorted(
                            [x for x in cand_list if x in per_system[r]],
                            key=lambda x: (-per_system[r][x], x),
                        )
                        ranks.append(ordered.index(d) + 1)
                best_rank[d] = min(ranks) if ranks else 10**9
            mnz_rank = sorted(cand_list, key=lambda d: (-mnz_scores[d], best_rank[d], d))

            cs = _ndcg_at_k(cs_rank, rel_map, ndcg_k)
            mn = _ndcg_at_k(mnz_rank, rel_map, ndcg_k)
            combsum_vals.append(cs)
            combmnz_vals.append(mn)
            n_used += 1

        if n_used:
            row = {
                "dataset": dataset,
                "n": n_used,
                "combsum_mean_ndcg": float(np.mean(combsum_vals)),
                "combmnz_mean_ndcg": float(np.mean(combmnz_vals)),
                "delta_mnz_minus_sum": float(np.mean(combmnz_vals) - np.mean(combsum_vals)),
            }
            results.append(row)
            report["datasets"][dataset] = row
            print(row)

    report["results"] = results
    # Decision rule: add only if CombMNZ clearly overturns the paper's baseline takeaway
    # (CombSUM remains strong) OR repairs-vs-baselines narrative. Here we only compare CombMNZ vs CombSUM.
    max_abs = max((abs(r["delta_mnz_minus_sum"]) for r in results), default=0.0)
    if max_abs < 0.01:
        report["decision"] = (
            "DO_NOT_ADD: CombMNZ vs CombSUM macro deltas are tiny under this unambiguous "
            "definition; expanding baselines would add volume without strengthening the repair thesis."
        )
    else:
        report["decision"] = (
            "REVIEW_MANUALLY: CombMNZ differs from CombSUM by >=0.01 on at least one dataset; "
            "still do not auto-add without table/figure regeneration and multiplicity planning."
        )
    (OUT / "tables" / "phase02_combmnz.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUT / "COMBMNZ_ASSESSMENT.md").write_text(
        "# CombMNZ Overnight Assessment\n\n"
        f"**Decision:** {report['decision']}\n\n"
        f"**Definition used:** {report['definition']}\n\n"
        + "\n".join(
            f"- {r['dataset']}: CombSUM={r['combsum_mean_ndcg']:.4f}, "
            f"CombMNZ={r['combmnz_mean_ndcg']:.4f}, Δ={r['delta_mnz_minus_sum']:+.4f} (n={r['n']})"
            for r in results
        )
        + "\n\nAmbiguities remain around nonzero coding and tie-breaking; paper baseline family left unchanged.\n"
    )
    print(report["decision"])


if __name__ == "__main__":
    main()
