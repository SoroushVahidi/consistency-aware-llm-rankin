#!/usr/bin/env python3
"""JDIQ Task 3, section 8: custom TF-IDF validation and raw
score-distribution summaries for BM25/TF-IDF/MiniLM.

Reproduces the custom TF-IDF ranker (scripts/generate_score_file.py
TfidfRanker) with an independent reference implementation (scikit-learn's
TfidfVectorizer, configured to match: sublinear term frequency, smoothed
IDF, L2-normalized cosine, and the SAME tokenizer regex/lowercasing/
title+text document representation) on a deterministic sample of queries
per dataset, fit on the full document corpus exactly as the original
score-generation run was. Does NOT replace the stored canonical TF-IDF
scores used anywhere in the manuscript pipeline -- this is a read-only
validation.
"""

from __future__ import annotations

import importlib
import json
import time
from typing import Any

import numpy as np
import task3_common as t3
from scipy.stats import kendalltau
from sklearn.feature_extraction.text import TfidfVectorizer

from consistency_ranker.data.unified_loader import load_dataset_splits

SAMPLE_QUERIES_PER_DATASET = 5
TOKEN_PATTERN = r"[A-Za-z0-9]+"

sys_path_scripts = str(t3.REPO_ROOT / "scripts")
import sys  # noqa: E402

if sys_path_scripts not in sys.path:
    sys.path.insert(0, sys_path_scripts)
gsf = importlib.import_module("generate_score_file")


def _document_text(doc) -> str:
    return f"{doc.title}\n{doc.text}" if doc.title else doc.text


def validate_dataset(dataset: str) -> dict[str, Any]:
    t0 = time.time()
    queries, documents, _qrels = load_dataset_splits(dataset)
    query_by_id = {q.query_id: q for q in queries}

    dataset_inputs = t3.dataset_inputs_for_pool(dataset, t3.CANONICAL_POOL[dataset])
    usable_ids = sorted(dataset_inputs["analysis_query_ids"])[:SAMPLE_QUERIES_PER_DATASET]

    custom_ranker = gsf.TfidfRanker(documents)
    doc_texts = [_document_text(d) for d in documents]
    doc_ids = [d.doc_id for d in documents]

    vectorizer = TfidfVectorizer(
        token_pattern=TOKEN_PATTERN,
        lowercase=True,
        sublinear_tf=True,
        smooth_idf=True,
        norm="l2",
        use_idf=True,
    )
    doc_matrix = vectorizer.fit_transform(doc_texts)
    build_time = time.time() - t0

    depth = t3.LARGER_POOL[dataset]
    query_rows: list[dict[str, Any]] = []
    for qid in usable_ids:
        query_text = query_by_id[qid].text
        custom_top = custom_ranker.top_docs(query_text, depth)
        custom_map = dict(custom_top)

        q_vec = vectorizer.transform([query_text])
        sklearn_scores = np.asarray((doc_matrix @ q_vec.T).todense()).ravel()
        order = np.argsort(-sklearn_scores, kind="stable")
        sklearn_ranked = [(doc_ids[i], float(sklearn_scores[i])) for i in order[:depth]]
        sklearn_map = dict(sklearn_ranked)

        custom_docs = [d for d, _s in custom_top]
        sklearn_docs = [d for d, _s in sklearn_ranked]
        common = sorted(set(custom_docs) & set(sklearn_docs))
        jac = (
            len(set(custom_docs) & set(sklearn_docs)) / len(set(custom_docs) | set(sklearn_docs))
            if (custom_docs or sklearn_docs)
            else None
        )

        # score correlation restricted to docs present in BOTH top lists
        if len(common) >= 2:
            v_custom = [custom_map[d] for d in common]
            v_sklearn = [sklearn_map[d] for d in common]
            tau, _p = kendalltau(v_custom, v_sklearn)
            corr = (
                float(np.corrcoef(v_custom, v_sklearn)[0, 1])
                if np.std(v_custom) > 0 and np.std(v_sklearn) > 0
                else None
            )
        else:
            tau, corr = None, None

        # directional agreement on pairs within the custom top-depth doc set,
        # scored by BOTH implementations (sklearn score computed for every doc
        # in the corpus, so restrict to docs custom actually returned)
        sklearn_full_map = {doc_ids[i]: float(sklearn_scores[i]) for i in range(len(doc_ids))}
        agree = disagree = 0
        for i in range(len(custom_docs)):
            for j in range(i + 1, len(custom_docs)):
                a, b = custom_docs[i], custom_docs[j]
                ca, cb = custom_map[a], custom_map[b]
                sa, sb = sklearn_full_map[a], sklearn_full_map[b]
                if ca == cb or sa == sb:
                    continue
                if (ca > cb) == (sa > sb):
                    agree += 1
                else:
                    disagree += 1
        nontied = agree + disagree
        query_rows.append(
            {
                "dataset": dataset,
                "query_id": qid,
                "depth": depth,
                "custom_top_n": len(custom_docs),
                "sklearn_top_n": len(sklearn_docs),
                "topk_jaccard": jac,
                "n_common_docs": len(common),
                "score_pearson_on_common": corr,
                "score_kendall_tau_on_common": tau,
                "directional_agreement_rate": (agree / nontied) if nontied else None,
                "nontied_pairs_checked": nontied,
                "custom_score_min": float(min(v for _d, v in custom_top)) if custom_top else None,
                "custom_score_max": float(max(v for _d, v in custom_top)) if custom_top else None,
                "sklearn_score_min": float(min(sklearn_scores)) if len(sklearn_scores) else None,
                "sklearn_score_max": float(max(sklearn_scores)) if len(sklearn_scores) else None,
            }
        )

    return {
        "dataset": dataset,
        "n_documents": len(documents),
        "n_queries_sampled": len(usable_ids),
        "sampled_query_ids": usable_ids,
        "index_build_time_seconds": build_time,
        "query_rows": query_rows,
    }


def raw_score_distribution_summaries() -> list[dict[str, Any]]:
    """min/max/mean/median/std/IQR and per-query range for BM25/TF-IDF/
    MiniLM, and pairwise-margin distribution, over the canonical
    candidate-pool scores actually used by the manuscript pipeline."""
    rows: list[dict[str, Any]] = []
    for dataset in t3.DATASETS:
        dataset_inputs = t3.dataset_inputs_for_pool(dataset, t3.CANONICAL_POOL[dataset])
        for ranker in t3.RANKERS:
            all_scores: list[float] = []
            per_query_ranges: list[float] = []
            margins: list[float] = []
            for item in dataset_inputs["per_query_inputs"]:
                score_map = item["raw_scores_by_ranker"].get(ranker, {})
                pool_scores = [score_map[d] for d in item["candidate_pool"] if d in score_map]
                if not pool_scores:
                    continue
                all_scores.extend(pool_scores)
                per_query_ranges.append(max(pool_scores) - min(pool_scores))
                for a, b in t3.unordered_pairs(item["candidate_pool"]):
                    if a in score_map and b in score_map:
                        margins.append(abs(score_map[a] - score_map[b]))
            if not all_scores:
                continue
            arr = np.asarray(all_scores, dtype=float)
            q25, q75 = np.quantile(arr, [0.25, 0.75])
            rows.append(
                {
                    "dataset": dataset,
                    "ranker": ranker,
                    "n_scores": len(all_scores),
                    "min": float(arr.min()),
                    "max": float(arr.max()),
                    "mean": float(arr.mean()),
                    "median": float(np.median(arr)),
                    "std": float(arr.std()),
                    "iqr": float(q75 - q25),
                    "mean_per_query_range": float(np.mean(per_query_ranges))
                    if per_query_ranges
                    else None,
                    "mean_pairwise_margin": float(np.mean(margins)) if margins else None,
                    "median_pairwise_margin": float(np.median(margins)) if margins else None,
                }
            )
    return rows


def main() -> int:
    t0 = time.time()
    all_query_rows: list[dict[str, Any]] = []
    dataset_manifests: dict[str, Any] = {}
    for dataset in t3.DATASETS:
        print(f"[tfidf validation] {dataset}", flush=True)
        result = validate_dataset(dataset)
        all_query_rows.extend(result["query_rows"])
        dataset_manifests[dataset] = {
            "n_documents": result["n_documents"],
            "n_queries_sampled": result["n_queries_sampled"],
            "sampled_query_ids": result["sampled_query_ids"],
            "index_build_time_seconds": result["index_build_time_seconds"],
        }
    t3.write_csv(t3.TABLES_DIR / "tfidf_validation_per_query.csv", all_query_rows)

    print("[score distributions]", flush=True)
    dist_rows = raw_score_distribution_summaries()
    t3.write_csv(t3.TABLES_DIR / "raw_score_distribution_summary.csv", dist_rows)

    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sample_queries_per_dataset": SAMPLE_QUERIES_PER_DATASET,
        "token_pattern": TOKEN_PATTERN,
        "reference_config": (
            "sklearn.TfidfVectorizer(sublinear_tf=True, smooth_idf=True, norm='l2', "
            "use_idf=True, token_pattern=r'[A-Za-z0-9]+', lowercase=True)"
        ),
        "dataset_manifests": dataset_manifests,
        "elapsed_seconds": time.time() - t0,
        "custom_formulation": {
            "tokenization": (
                "regex [A-Za-z0-9]+ on lowercased text; document text = "
                "title + '\\n' + text if title else text"
            ),
            "term_frequency": (
                "raw count per doc/query, then sublinear weight w = (1 + ln(tf)) applied per term"
            ),
            "idf_formula": (
                "smoothed: idf = ln((n_docs + 1) / (df + 1)) + 1.0 (matches "
                "scikit-learn's smooth_idf=True convention exactly)"
            ),
            "cosine": "dot(query_weights, doc_weights) / (||doc||_2 * ||query||_2)",
            "zero_vector_handling": (
                "doc or query with zero sum-of-squares gets norm=1.0 fallback "
                "(score stays 0 rather than dividing by zero)"
            ),
            "empty_query_fallback": (
                "if query tokenizes to nothing, returns zero-padded fallback "
                "(real-hit-first then ascending doc_id) rather than an empty list"
            ),
        },
    }
    t3.write_json(t3.MANIFESTS_DIR / "tfidf_validation_run_summary.json", manifest)
    print(json.dumps(manifest, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
