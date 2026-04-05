#!/usr/bin/env python
"""
Stronger selective policy: learned selector vs fixed thresholds.

Trains a lightweight classifier (logistic regression or decision tree) on
(bew_before, disagreement, n_sccs, cyclic) to predict whether FAS will improve
over RRF. Uses 60/20/20 train/val/test split. Conservative: avoid overfitting.

Compares: never, always, best_fixed (BEW p75), learned_selector
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from consistency_ranker.data.dataset_registry import get_config
from consistency_ranker.data.unified_loader import load_dataset_splits, load_multi_scorer_rankings

# Import run_query_full from paper_ready
sys.path.insert(0, str(REPO / "scripts"))
from run_paper_ready_experiments import run_query_full  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="fiqa")
    parser.add_argument("--scorers", default="bm25,dense")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--max-queries", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/learned_selector"))
    args = parser.parse_args()

    random.seed(args.seed)
    scorer_names = [s.strip() for s in args.scorers.split(",") if s.strip()]
    if len(scorer_names) < 2:
        print("ERROR: need at least 2 scorers")
        sys.exit(1)

    cfg = get_config(args.dataset)
    scorer_paths = {n: cfg.processed_path / "scores" / f"{n}.jsonl" for n in scorer_names}
    multi = load_multi_scorer_rankings(scorer_paths)
    missing = [n for n in scorer_names if n not in multi]
    if missing:
        print(f"ERROR: missing scorers: {missing}")
        sys.exit(1)

    queries, _, qrels = load_dataset_splits(args.dataset)
    qrels_by_q = {}
    for e in qrels:
        qrels_by_q.setdefault(e.query_id, []).append(e)

    qids = [
        q.query_id
        for q in queries
        if all(q.query_id in multi[n] for n in scorer_names) and q.query_id in qrels_by_q
    ][: args.max_queries]

    random.shuffle(qids)
    n_train = int(len(qids) * 0.6)
    n_val = int(len(qids) * 0.2)
    train_qids = set(qids[: n_train])
    val_qids = set(qids[n_train : n_train + n_val])
    test_qids = qids[n_train + n_val :]

    per_query: list[dict] = []
    for i, qid in enumerate(qids):
        if (i + 1) % 25 == 0 or i == 0:
            print(f"  Query {i + 1}/{len(qids)}...")
        sr = {n: multi[n][qid] for n in scorer_names}
        relevance_map = {e.doc_id: e.relevance for e in qrels_by_q[qid]}
        relevant_ids = {e.doc_id for e in qrels_by_q[qid] if e.relevance > 0}
        row = run_query_full(qid, sr, scorer_names, args.top_k, "summed_margin", relevance_map, relevant_ids)
        row["split"] = "train" if qid in train_qids else ("val" if qid in val_qids else "test")
        per_query.append(row)

    train_rows = [r for r in per_query if r["split"] == "train"]
    val_rows = [r for r in per_query if r["split"] == "val"]
    test_rows = [r for r in per_query if r["split"] == "test"]

    def feats(r: dict) -> list[float]:
        return [
            float(r["bew_before"]),
            float(r["disagreement"]),
            float(r.get("n_sccs", 0)),
            1.0 if r.get("cyclic") in (True, "True") else 0.0,
        ]

    X_train = [feats(r) for r in train_rows]
    y_train = [1 if r["fas_helps"] else 0 for r in train_rows]
    X_test = [feats(r) for r in test_rows]

    # Best fixed threshold on validation
    bew_vals = sorted(r["bew_before"] for r in per_query)
    p75 = bew_vals[len(bew_vals) * 3 // 4] if bew_vals else 0
    best_fixed_ndcg = sum(
        r["ndcg_greedy_fas_topological"] if r["bew_before"] >= p75 else r["ndcg_rrf_fusion"]
        for r in val_rows
    ) / len(val_rows) if val_rows else 0

    # Learned selector
    dt_pred = None
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.tree import DecisionTreeClassifier
        clf = LogisticRegression(max_iter=500, random_state=args.seed, C=0.5)
        clf.fit(X_train, y_train)
        learned_pred = [bool(pred) for pred in clf.predict(X_test)]
        dt = DecisionTreeClassifier(max_depth=3, random_state=args.seed)
        dt.fit(X_train, y_train)
        dt_pred = [bool(pred) for pred in dt.predict(X_test)]
    except ImportError:
        print("sklearn not installed; using best_fixed only")
        learned_pred = [r["bew_before"] >= p75 for r in test_rows]

    n_test = len(test_rows)
    ndcg_never = sum(r["ndcg_rrf_fusion"] for r in test_rows) / n_test
    ndcg_always = sum(r["ndcg_greedy_fas_topological"] for r in test_rows) / n_test
    ndcg_best_fixed = sum(
        r["ndcg_greedy_fas_topological"] if r["bew_before"] >= p75 else r["ndcg_rrf_fusion"]
        for r in test_rows
    ) / n_test
    ndcg_learned = sum(
        r["ndcg_greedy_fas_topological"] if learned_pred[i] else r["ndcg_rrf_fusion"]
        for i, r in enumerate(test_rows)
    ) / n_test
    ndcg_dt = (
        sum(
            r["ndcg_greedy_fas_topological"] if dt_pred[i] else r["ndcg_rrf_fusion"]
            for i, r in enumerate(test_rows)
        )
        / n_test
        if dt_pred is not None
        else 0
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    scorers_str = "_".join(scorer_names)

    print("\n" + "=" * 60)
    print(f"LEARNED SELECTOR: {args.dataset} {scorers_str}")
    print("=" * 60)
    print(f"  Train={len(train_rows)} Val={len(val_rows)} Test={len(test_rows)}")
    print("-" * 60)
    print(f"  never (RRF):        NDCG@10 = {ndcg_never:.4f}")
    print(f"  always (FAS):      NDCG@10 = {ndcg_always:.4f}")
    print(f"  best_fixed (BEW≥p75): NDCG@10 = {ndcg_best_fixed:.4f}")
    print(f"  learned (logreg):   NDCG@10 = {ndcg_learned:.4f}")
    if dt_pred is not None:
        print(f"  learned (tree):     NDCG@10 = {ndcg_dt:.4f}")

    out_csv = args.output_dir / f"{args.dataset}_{scorers_str}_learned_selector.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["policy", "ndcg_at_10"])
        w.writerow(["never", round(ndcg_never, 4)])
        w.writerow(["always", round(ndcg_always, 4)])
        w.writerow(["best_fixed_bew75", round(ndcg_best_fixed, 4)])
        w.writerow(["learned_logreg", round(ndcg_learned, 4)])
        if dt_pred is not None:
            w.writerow(["learned_tree", round(ndcg_dt, 4)])
    print(f"\nWrote {out_csv}")


if __name__ == "__main__":
    main()
