#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from consistency_ranker.data.query_ids import load_query_ids_file


RANKERS = ("bm25", "tfidf", "minilm")
VARIANTS = ("ms1", "ms1_drop_mutual", "ms2")
BM25_COLOR = "#9a3412"
TFIDF_COLOR = "#0f766e"
MINILM_COLOR = "#1d4ed8"
RANKER_COLORS = {
    "bm25": BM25_COLOR,
    "tfidf": TFIDF_COLOR,
    "minilm": MINILM_COLOR,
}
SCORE_QUANTILES = (0.05, 0.25, 0.75, 0.95)
PAIRWISE_QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    top_k: int
    top_n: int
    n_queries: int
    input_dir: Path
    query_ids_file: Path
    score_files: dict[str, Path]
    vote_files: dict[str, Path]


def _run(cmd: list[str], cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _safe_run(cmd: list[str], cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    text = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    if text and err:
        return f"{text}\n{err}"
    return text or err


def _float_list_stats(values: list[float], prefix: str = "") -> dict[str, float | int | None]:
    if not values:
        return {
            f"{prefix}count": 0,
            f"{prefix}min": None,
            f"{prefix}max": None,
            f"{prefix}range": None,
            f"{prefix}mean": None,
            f"{prefix}std": None,
            f"{prefix}median": None,
            f"{prefix}iqr": None,
            f"{prefix}q05": None,
            f"{prefix}q25": None,
            f"{prefix}q75": None,
            f"{prefix}q95": None,
        }
    arr = np.asarray(values, dtype=float)
    q05, q25, q75, q95 = np.quantile(arr, SCORE_QUANTILES)
    return {
        f"{prefix}count": int(arr.size),
        f"{prefix}min": float(arr.min()),
        f"{prefix}max": float(arr.max()),
        f"{prefix}range": float(arr.max() - arr.min()),
        f"{prefix}mean": float(arr.mean()),
        f"{prefix}std": float(arr.std(ddof=0)),
        f"{prefix}median": float(np.median(arr)),
        f"{prefix}iqr": float(q75 - q25),
        f"{prefix}q05": float(q05),
        f"{prefix}q25": float(q25),
        f"{prefix}q75": float(q75),
        f"{prefix}q95": float(q95),
    }


def _margin_stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "pair_count": 0,
            "total_absolute_margin": 0.0,
            "mean": None,
            "median": None,
            "std": None,
            "q05": None,
            "q25": None,
            "q50": None,
            "q75": None,
            "q95": None,
        }
    arr = np.asarray(values, dtype=float)
    q05, q25, q50, q75, q95 = np.quantile(arr, PAIRWISE_QUANTILES)
    return {
        "pair_count": int(arr.size),
        "total_absolute_margin": float(arr.sum()),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "std": float(arr.std(ddof=0)),
        "q05": float(q05),
        "q25": float(q25),
        "q50": float(q50),
        "q75": float(q75),
        "q95": float(q95),
    }


def _jsonl_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dataset_specs(canonical_manifest: dict[str, Any]) -> dict[str, DatasetSpec]:
    specs: dict[str, DatasetSpec] = {}
    subsets = canonical_manifest["canonical_query_subset"]
    score_files = canonical_manifest["score_files"]
    vote_files = canonical_manifest["vote_files"]
    for dataset, subset in subsets.items():
        input_dir = REPO_ROOT / "experiments" / "method_improvement_audit_20260711_205733" / "inputs" / dataset
        specs[dataset] = DatasetSpec(
            name=dataset,
            top_k=int(subset["top_k"]),
            top_n=int(subset["top_n"]),
            n_queries=int(subset["n_queries"]),
            input_dir=input_dir,
            query_ids_file=input_dir / "query_ids.txt",
            score_files={ranker: Path(score_files[dataset][ranker]) for ranker in RANKERS},
            vote_files={variant: Path(vote_files[dataset][variant]) for variant in VARIANTS},
        )
    return specs


def _load_score_file(path: Path) -> dict[str, dict[str, float]]:
    by_query: dict[str, dict[str, float]] = defaultdict(dict)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            qid = str(row["query_id"])
            doc_id = str(row["doc_id"])
            score = float(row["score"])
            prev = by_query[qid].get(doc_id)
            if prev is None or score > prev:
                by_query[qid][doc_id] = score
    return dict(by_query)


def _load_votes_file(path: Path) -> dict[str, list[dict[str, Any]]]:
    by_query: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            qid = str(row["query_id"])
            by_query[qid].append(
                {
                    "query_id": qid,
                    "winner_doc_id": str(row["winner_doc_id"]),
                    "loser_doc_id": str(row["loser_doc_id"]),
                    "weight": float(row["weight"]),
                    "voter": str(row["voter"]),
                }
            )
    return dict(by_query)


def _select_candidates(ranker_scores: dict[str, dict[str, float]], top_k: int) -> list[str]:
    union_docs = sorted({doc_id for scores in ranker_scores.values() for doc_id in scores})
    if len(union_docs) <= top_k:
        return union_docs
    rrf_scores: dict[str, float] = defaultdict(float)
    for ranker in sorted(ranker_scores):
        ranked = sorted(ranker_scores[ranker].items(), key=lambda x: (-x[1], x[0]))
        for rank, (doc_id, _score) in enumerate(ranked, start=1):
            rrf_scores[doc_id] += 1.0 / (60.0 + rank)
    return sorted(union_docs, key=lambda d: (-rrf_scores.get(d, 0.0), d))[:top_k]


def _reconstruct_votes_for_query(
    query_id: str,
    ranker_scores: dict[str, dict[str, float]],
    top_k: int,
    *,
    min_vote_margin: float = 0.05,
    abstain_missing: bool = True,
) -> tuple[list[str], list[dict[str, Any]], dict[str, list[float]], dict[str, dict[str, int | float]], dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float, float]]]]]:
    candidates = _select_candidates(ranker_scores, top_k=top_k)
    pairwise_margins_by_ranker: dict[str, list[float]] = {ranker: [] for ranker in RANKERS}
    retained_by_ranker: dict[str, dict[str, int | float]] = {
        ranker: {"possible_pairs": 0, "retained_votes": 0, "retained_margin": 0.0}
        for ranker in RANKERS
    }
    votes_by_pair: dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float, float]]]] = defaultdict(lambda: defaultdict(list))
    raw_vote_rows: list[dict[str, Any]] = []
    for ranker in sorted(ranker_scores):
        score_map = ranker_scores[ranker]
        for a, b in combinations(candidates, 2):
            if abstain_missing and (a not in score_map or b not in score_map):
                continue
            sa = score_map[a]
            sb = score_map[b]
            margin = abs(sa - sb)
            pairwise_margins_by_ranker[ranker].append(float(margin))
            retained_by_ranker[ranker]["possible_pairs"] = int(retained_by_ranker[ranker]["possible_pairs"]) + 1
            if margin < min_vote_margin:
                continue
            if sa > sb:
                winner, loser = a, b
            elif sb > sa:
                winner, loser = b, a
            else:
                winner, loser = (a, b) if a < b else (b, a)
            pair_key = (a, b) if a < b else (b, a)
            votes_by_pair[pair_key][(winner, loser)].append((ranker, float(margin), float(margin)))
            retained_by_ranker[ranker]["retained_votes"] = int(retained_by_ranker[ranker]["retained_votes"]) + 1
            retained_by_ranker[ranker]["retained_margin"] = float(retained_by_ranker[ranker]["retained_margin"]) + float(margin)
            raw_vote_rows.append(
                {
                    "query_id": query_id,
                    "winner_doc_id": winner,
                    "loser_doc_id": loser,
                    "weight": float(margin),
                    "voter": ranker,
                }
            )
    return candidates, raw_vote_rows, pairwise_margins_by_ranker, retained_by_ranker, votes_by_pair


def _apply_variant(
    query_id: str,
    votes_by_pair: dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float, float]]]],
    variant: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pair_key in sorted(votes_by_pair):
        dir_votes = votes_by_pair[pair_key]
        if variant == "ms1":
            min_support = 1
            min_aggregate_margin = 0.0
        elif variant == "ms2":
            min_support = 2
            min_aggregate_margin = 0.1
        elif variant == "ms1_drop_mutual":
            min_support = 1
            min_aggregate_margin = 0.0
        else:
            raise ValueError(f"Unknown variant: {variant}")
        kept_directions: dict[tuple[str, str], list[tuple[str, float, float]]] = {}
        for direction, recs in dir_votes.items():
            support = len(recs)
            margin_sum = sum(r[2] for r in recs)
            if support < min_support or margin_sum < min_aggregate_margin:
                continue
            kept_directions[direction] = recs
        if variant == "ms1_drop_mutual" and len(kept_directions) > 1:
            continue
        for (winner, loser), recs in sorted(kept_directions.items()):
            for voter, weight, _margin in recs:
                rows.append(
                    {
                        "query_id": query_id,
                        "winner_doc_id": winner,
                        "loser_doc_id": loser,
                        "weight": float(weight),
                        "voter": voter,
                    }
                )
    return rows


def _normalized_rows(rows: list[dict[str, Any]]) -> list[tuple[str, str, str, float, str]]:
    return sorted(
        (
            str(row["query_id"]),
            str(row["winner_doc_id"]),
            str(row["loser_doc_id"]),
            round(float(row["weight"]), 12),
            str(row["voter"]),
        )
        for row in rows
    )


def _graph_from_rows(rows: list[dict[str, Any]]) -> tuple[nx.DiGraph, dict[tuple[str, str], dict[str, float]], dict[tuple[str, str], set[str]], dict[tuple[str, str], int]]:
    edge_weights: dict[tuple[str, str], float] = defaultdict(float)
    edge_ranker_weights: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    edge_ranker_set: dict[tuple[str, str], set[str]] = defaultdict(set)
    edge_vote_counts: dict[tuple[str, str], int] = defaultdict(int)
    nodes: set[str] = set()
    for row in rows:
        u = str(row["winner_doc_id"])
        v = str(row["loser_doc_id"])
        w = float(row["weight"])
        r = str(row["voter"])
        edge_weights[(u, v)] += w
        edge_ranker_weights[(u, v)][r] += w
        edge_ranker_set[(u, v)].add(r)
        edge_vote_counts[(u, v)] += 1
        nodes.add(u)
        nodes.add(v)
    graph = nx.DiGraph()
    graph.add_nodes_from(sorted(nodes))
    for (u, v), w in edge_weights.items():
        graph.add_edge(u, v, weight=float(w))
    return graph, edge_ranker_weights, edge_ranker_set, edge_vote_counts


def _analyze_greedy_fas(
    graph: nx.DiGraph,
    edge_ranker_weights: dict[tuple[str, str], dict[str, float]],
) -> tuple[nx.DiGraph, list[dict[str, Any]]]:
    dag = graph.copy()
    removed_records: list[dict[str, Any]] = []
    while True:
        try:
            cycle = nx.find_cycle(dag, orientation="original")
        except nx.NetworkXNoCycle:
            break
        cycle_edges = [(u, v) for u, v, *_ in cycle]
        min_edge = min(cycle_edges, key=lambda e: dag[e[0]][e[1]].get("weight", 1.0))
        weight = float(dag[min_edge[0]][min_edge[1]].get("weight", 1.0))
        cycle_weights = [float(dag[u][v].get("weight", 1.0)) for u, v in cycle_edges]
        contrib = dict(edge_ranker_weights.get(min_edge, {}))
        dominant_ranker = None
        dominant_share = None
        if contrib:
            dominant_ranker = max(sorted(contrib), key=lambda r: contrib[r])
            dominant_share = contrib[dominant_ranker] / weight if weight > 0 else None
        removed_records.append(
            {
                "removed_u": min_edge[0],
                "removed_v": min_edge[1],
                "removed_weight": weight,
                "cycle_size": len(cycle_edges),
                "cycle_weight_min": min(cycle_weights),
                "cycle_weight_max": max(cycle_weights),
                "cycle_total_weight": sum(cycle_weights),
                "removed_ranker_weights": contrib,
                "dominant_ranker": dominant_ranker,
                "dominant_ranker_share": dominant_share,
                "cycle_edges": cycle_edges,
            }
        )
        dag.remove_edge(*min_edge)
    return dag, removed_records


def _sum_nested_weight(records: list[dict[str, Any]], key: str) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for rec in records:
        for ranker, value in rec.get(key, {}).items():
            out[ranker] += float(value)
    return dict(out)


def _format_pct(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{100.0 * value:.2f}%"


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _code_path_inventory_rows() -> list[dict[str, Any]]:
    return [
        {
            "stage": "BM25 scoring",
            "file": "scripts/generate_score_file.py",
            "function": "BM25Ranker.top_docs",
            "relevant_parameters": "k1=1.5, b=0.75, top_n from canonical subset manifest",
            "score_normalization_applied": "none",
            "query_level_normalization_applied": "none",
            "ranker_level_normalization_applied": "none",
            "notes": "Native BM25 scores written directly to scores_bm25.jsonl.",
        },
        {
            "stage": "TF-IDF scoring",
            "file": "scripts/generate_score_file.py",
            "function": "TfidfRanker.top_docs",
            "relevant_parameters": "log-tf * idf cosine-style normalization, top_n from canonical subset manifest",
            "score_normalization_applied": "document/query vector norm inside TF-IDF scorer only",
            "query_level_normalization_applied": "none after scoring",
            "ranker_level_normalization_applied": "none",
            "notes": "Stored cosine-like scores are not rescaled against BM25 or MiniLM.",
        },
        {
            "stage": "MiniLM scoring",
            "file": "scripts/generate_score_file.py",
            "function": "MiniLMRanker.top_docs",
            "relevant_parameters": "sentence-transformers/all-MiniLM-L6-v2, normalized embeddings, top_n from canonical subset manifest",
            "score_normalization_applied": "cosine similarity from normalized embeddings",
            "query_level_normalization_applied": "none after scoring",
            "ranker_level_normalization_applied": "none",
            "notes": "Stored scores are cosine similarities, typically bounded near [-1, 1].",
        },
        {
            "stage": "Candidate-score storage",
            "file": "scripts/generate_score_file.py",
            "function": "main",
            "relevant_parameters": "query_id_file, output JSONL rows {query_id, doc_id, score, ranker}",
            "score_normalization_applied": "none",
            "query_level_normalization_applied": "none",
            "ranker_level_normalization_applied": "none",
            "notes": "Exact canonical score files are under experiments/method_improvement_audit_20260711_205733/inputs/<dataset>/scores_*.jsonl.",
        },
        {
            "stage": "Candidate pool selection",
            "file": "scripts/build_votes_file.py",
            "function": "_select_candidates",
            "relevant_parameters": "top_k from canonical subset manifest, reciprocal-rank fusion with k=60",
            "score_normalization_applied": "rank-based RRF only for candidate selection",
            "query_level_normalization_applied": "none on native scores",
            "ranker_level_normalization_applied": "none",
            "notes": "Top-k candidate pool is a union ranked by RRF over native ranker orderings, not native score magnitudes.",
        },
        {
            "stage": "Pairwise margin extraction",
            "file": "scripts/build_votes_file.py",
            "function": "_votes_for_query",
            "relevant_parameters": "vote_weight_scheme='margin', abstain_missing=True",
            "score_normalization_applied": "none",
            "query_level_normalization_applied": "none",
            "ranker_level_normalization_applied": "none",
            "notes": "Per-ranker vote weight equals absolute native score margin |sa-sb|.",
        },
        {
            "stage": "Per-ranker abstention threshold",
            "file": "scripts/build_votes_file.py",
            "function": "_votes_for_query",
            "relevant_parameters": "min_vote_margin parameter; canonical value 0.05 supplied by scripts/run_publication_vote_suite.py",
            "score_normalization_applied": "none",
            "query_level_normalization_applied": "none",
            "ranker_level_normalization_applied": "none",
            "notes": "Threshold is applied to native absolute margins before any cross-ranker calibration.",
        },
        {
            "stage": "Support aggregation",
            "file": "scripts/build_votes_file.py",
            "function": "_votes_for_query",
            "relevant_parameters": "support=len(recs), canonical min_support=1 (ms1) or 2 (ms2)",
            "score_normalization_applied": "none",
            "query_level_normalization_applied": "none",
            "ranker_level_normalization_applied": "none",
            "notes": "Votes are grouped by unordered pair and direction; support counts distinct retained ranker votes.",
        },
        {
            "stage": "Aggregate margin threshold",
            "file": "scripts/build_votes_file.py",
            "function": "_votes_for_query",
            "relevant_parameters": "margin_sum=sum(native margins), canonical min_aggregate_margin=0.1 for ms2 and 0.0 for ms1",
            "score_normalization_applied": "none",
            "query_level_normalization_applied": "none",
            "ranker_level_normalization_applied": "none",
            "notes": "Threshold uses summed native margins, so large-scale rankers can satisfy it more easily.",
        },
        {
            "stage": "Mutual-pair removal",
            "file": "scripts/postprocess_votes_drop_mutual_pairs.py",
            "function": "_mutual_unordered_pairs / _filter_rows",
            "relevant_parameters": "drop both directions for unordered pairs with contradictory votes",
            "score_normalization_applied": "none",
            "query_level_normalization_applied": "none",
            "ranker_level_normalization_applied": "none",
            "notes": "ms1_drop_mutual keeps native vote weights for non-conflicting pairs.",
        },
        {
            "stage": "Edge-weight construction",
            "file": "src/consistency_ranker/graph_construction.py",
            "function": "build_graph",
            "relevant_parameters": "aggregation='sum'",
            "score_normalization_applied": "none",
            "query_level_normalization_applied": "none",
            "ranker_level_normalization_applied": "none",
            "notes": "Stored vote row weights are summed per directed edge.",
        },
        {
            "stage": "Repair objective",
            "file": "src/consistency_ranker/greedy_fas.py",
            "function": "greedy_fas",
            "relevant_parameters": "iteratively remove minimum-weight edge from each detected cycle",
            "score_normalization_applied": "none",
            "query_level_normalization_applied": "none",
            "ranker_level_normalization_applied": "none",
            "notes": "Repair directly optimizes over summed native edge weights; no calibration is introduced before edge removal.",
        },
        {
            "stage": "Canonical orchestration",
            "file": "scripts/run_publication_vote_suite.py",
            "function": "main",
            "relevant_parameters": "ms1 uses min_support=1, min_aggregate_margin=0.0; ms2 uses min_support=2, min_aggregate_margin=0.1; min_vote_margin=0.05 for both",
            "score_normalization_applied": "none",
            "query_level_normalization_applied": "none",
            "ranker_level_normalization_applied": "none",
            "notes": "Canonical four-dataset inputs in experiments/method_improvement_audit_20260711_205733/inputs were produced with these settings.",
        },
    ]


def _collect_initial_state(root: Path, canonical_manifest_path: Path, specs: dict[str, DatasetSpec]) -> dict[str, Any]:
    now_local = datetime.now().astimezone()
    branch = _run(["git", "branch", "--show-current"])
    head = _run(["git", "rev-parse", "HEAD"])
    status_short = _safe_run(["git", "status", "--short"])
    python_version = _run([str(REPO_ROOT / ".venv" / "bin" / "python"), "--version"])
    pip_freeze = _run([str(REPO_ROOT / ".venv" / "bin" / "pip"), "freeze"])
    disk = _run(["df", "-h", "."])
    state = {
        "repo_root": str(REPO_ROOT),
        "branch": branch,
        "head": head,
        "git_status_short": status_short.splitlines() if status_short else [],
        "python_version": python_version,
        "pip_freeze": pip_freeze.splitlines(),
        "disk_free": disk.splitlines(),
        "timestamp_local": now_local.isoformat(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_manifest_path": str(canonical_manifest_path),
        "dataset_inputs": {
            name: {
                "query_ids_file": str(spec.query_ids_file),
                "top_k": spec.top_k,
                "top_n": spec.top_n,
                "n_queries": spec.n_queries,
                "score_files": {ranker: str(path) for ranker, path in spec.score_files.items()},
                "vote_files": {variant: str(path) for variant, path in spec.vote_files.items()},
            }
            for name, spec in specs.items()
        },
        "scripts_involved": [
            "scripts/generate_score_file.py",
            "scripts/build_votes_file.py",
            "scripts/postprocess_votes_drop_mutual_pairs.py",
            "scripts/run_publication_vote_suite.py",
            "scripts/run_real_experiment.py",
            "src/consistency_ranker/graph_construction.py",
            "src/consistency_ranker/greedy_fas.py",
        ],
        "manuscript_artifacts_referenced": [
            "outputs/final_jis_package",
            "outputs/manuscript_artifacts",
        ],
    }

    lines = [
        "# Initial State",
        "",
        f"- Repository root: `{state['repo_root']}`",
        f"- Branch: `{branch}`",
        f"- HEAD: `{head}`",
        f"- Snapshot time (local): `{state['timestamp_local']}`",
        f"- Snapshot time (UTC): `{state['timestamp_utc']}`",
        "",
        "## Git Status",
        "",
        "```text",
        status_short or "(clean)",
        "```",
        "",
        "## Python Environment",
        "",
        f"- Python: `{python_version}`",
        "",
        "## Disk",
        "",
        "```text",
        disk,
        "```",
        "",
        "## Canonical Inputs",
        "",
    ]
    for dataset, spec in specs.items():
        lines.extend(
            [
                f"### {dataset}",
                "",
                f"- Query ids: `{spec.query_ids_file}`",
                f"- Score files: `{spec.score_files['bm25']}`, `{spec.score_files['tfidf']}`, `{spec.score_files['minilm']}`",
                f"- Vote files: `{spec.vote_files['ms1']}`, `{spec.vote_files['ms1_drop_mutual']}`, `{spec.vote_files['ms2']}`",
                f"- Canonical subset: `n_queries={spec.n_queries}`, `top_n={spec.top_n}`, `top_k={spec.top_k}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Scripts Involved",
            "",
            *[f"- `{path}`" for path in state["scripts_involved"]],
            "",
            "## Referenced Published Output Roots",
            "",
            *[f"- `{path}`" for path in state["manuscript_artifacts_referenced"]],
            "",
        ]
    )
    (root / "INITIAL_STATE.md").write_text("\n".join(lines), encoding="utf-8")
    return state


def _plot_box_from_csv(csv_path: Path, value_col: str, out_path: Path, title: str, yscale: str = "linear") -> None:
    df = pd.read_csv(csv_path)
    if df.empty:
        return
    datasets = list(dict.fromkeys(df["dataset"]))
    rankers = list(dict.fromkeys(df["ranker"]))
    positions: list[float] = []
    data: list[np.ndarray] = []
    colors: list[str] = []
    tick_pos: list[float] = []
    tick_labels: list[str] = []
    gap = len(rankers) + 1
    for di, dataset in enumerate(datasets):
        base = di * gap
        tick_pos.append(base + (len(rankers) - 1) / 2)
        tick_labels.append(dataset)
        for ri, ranker in enumerate(rankers):
            vals = df[(df["dataset"] == dataset) & (df["ranker"] == ranker)][value_col].dropna().to_numpy()
            if vals.size == 0:
                continue
            positions.append(base + ri)
            data.append(vals)
            colors.append(RANKER_COLORS.get(ranker, "#475569"))
    if not data:
        return
    fig, ax = plt.subplots(figsize=(12, 5.5))
    bp = ax.boxplot(data, positions=positions, widths=0.65, patch_artist=True, showfliers=False)
    for patch, color in zip(bp["boxes"], colors):
        patch.set(facecolor=color, alpha=0.78, edgecolor="#111827")
    for element in ("whiskers", "caps", "medians"):
        for line in bp[element]:
            line.set(color="#111827", linewidth=1.1)
    ax.set_title(title)
    ax.set_ylabel(value_col.replace("_", " "))
    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_labels)
    ax.set_yscale(yscale)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    legend_handles = [
        plt.Line2D([0], [0], color=RANKER_COLORS[r], lw=8, label=r.upper())
        for r in rankers
    ]
    ax.legend(handles=legend_handles, ncol=3, frameon=False, loc="upper right")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def _plot_stacked_share(df: pd.DataFrame, value_col: str, stage_filter: str, out_path: Path, title: str) -> None:
    sub = df[df["stage"] == stage_filter].copy()
    if sub.empty:
        return
    sub["dataset_variant"] = sub["dataset"] + ":" + sub["variant"]
    pivot = sub.pivot_table(
        index="dataset_variant",
        columns="ranker",
        values=value_col,
        aggfunc="sum",
        fill_value=0.0,
    )
    pivot = pivot[[r for r in RANKERS if r in pivot.columns]]
    if pivot.empty:
        return
    fig, ax = plt.subplots(figsize=(12.5, 5.5))
    bottom = np.zeros(len(pivot.index))
    x = np.arange(len(pivot.index))
    for ranker in pivot.columns:
        vals = pivot[ranker].to_numpy(dtype=float)
        ax.bar(x, vals, bottom=bottom, color=RANKER_COLORS[ranker], label=ranker.upper())
        bottom += vals
    ax.set_title(title)
    ax.set_ylabel(value_col.replace("_", " "))
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, rotation=25, ha="right")
    ax.set_ylim(0, 1)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(frameon=False, ncol=3, loc="upper right")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run B3 Phase 0 and Phase 1 audit.")
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT / "reports" / "b3_margin_calibration_investigation",
    )
    parser.add_argument(
        "--canonical-manifest",
        type=Path,
        default=REPO_ROOT / "experiments" / "method_improvement_audit_20260711_205733" / "phase_reports" / "canonical_rerun_manifest.json",
    )
    args = parser.parse_args()

    root = args.root
    for subdir in ("logs", "scripts", "tables", "figures", "manifests", "reproductions"):
        (root / subdir).mkdir(parents=True, exist_ok=True)

    canonical_manifest = _load_manifest(args.canonical_manifest)
    specs = _dataset_specs(canonical_manifest)
    initial_state = _collect_initial_state(root, args.canonical_manifest, specs)
    code_path_rows = _code_path_inventory_rows()
    _write_csv(
        root / "tables" / "code_path_inventory.csv",
        code_path_rows,
        columns=[
            "stage",
            "file",
            "function",
            "relevant_parameters",
            "score_normalization_applied",
            "query_level_normalization_applied",
            "ranker_level_normalization_applied",
            "notes",
        ],
    )

    raw_score_rows: list[dict[str, Any]] = []
    pairwise_rows: list[dict[str, Any]] = []
    retained_rows: list[dict[str, Any]] = []
    graph_rows: list[dict[str, Any]] = []
    removed_rows: list[dict[str, Any]] = []
    dominance_rows: list[dict[str, Any]] = []
    reproduction_rows: list[dict[str, Any]] = []
    phase01_details: dict[str, Any] = {"datasets": {}}

    for dataset, spec in specs.items():
        print(f"[phase0/1] dataset={dataset}", flush=True)
        query_ids = load_query_ids_file(spec.query_ids_file)
        score_maps_by_ranker = {ranker: _load_score_file(spec.score_files[ranker]) for ranker in RANKERS}
        stored_vote_rows_by_variant = {variant: _load_votes_file(spec.vote_files[variant]) for variant in VARIANTS}
        phase01_details["datasets"][dataset] = {
            "top_k": spec.top_k,
            "top_n": spec.top_n,
            "n_queries_manifest": spec.n_queries,
            "query_ids_count": len(query_ids),
            "queries": {},
        }

        reconstructed_rows_by_variant: dict[str, list[dict[str, Any]]] = {variant: [] for variant in VARIANTS}
        pairwise_values_acc: dict[str, list[float]] = {ranker: [] for ranker in RANKERS}
        retained_summary_acc: dict[str, dict[str, float | int]] = {
            ranker: {
                "possible_pairs": 0,
                "retained_votes": 0,
                "retained_margin": 0.0,
            }
            for ranker in RANKERS
        }

        for qid in query_ids:
            per_query_ranker_scores = {
                ranker: score_maps_by_ranker[ranker].get(qid, {})
                for ranker in RANKERS
            }
            candidates, raw_vote_rows, pairwise_margins_by_ranker, retained_by_ranker, votes_by_pair = _reconstruct_votes_for_query(
                qid,
                per_query_ranker_scores,
                spec.top_k,
            )
            phase01_details["datasets"][dataset]["queries"][qid] = {
                "candidate_count": len(candidates),
                "candidates": candidates,
            }

            for ranker in RANKERS:
                score_values = list(per_query_ranker_scores[ranker].values())
                score_stats = _float_list_stats(score_values, prefix="")
                raw_score_rows.append(
                    {
                        "dataset": dataset,
                        "query_id": qid,
                        "ranker": ranker,
                        "top_n_manifest": spec.top_n,
                        "top_k_candidate_pool": spec.top_k,
                        "candidate_pool_size": len(candidates),
                        "scored_documents": len(score_values),
                        **score_stats,
                    }
                )
                pairwise_values = pairwise_margins_by_ranker[ranker]
                pairwise_values_acc[ranker].extend(pairwise_values)
                retained_summary_acc[ranker]["possible_pairs"] = int(retained_summary_acc[ranker]["possible_pairs"]) + int(retained_by_ranker[ranker]["possible_pairs"])
                retained_summary_acc[ranker]["retained_votes"] = int(retained_summary_acc[ranker]["retained_votes"]) + int(retained_by_ranker[ranker]["retained_votes"])
                retained_summary_acc[ranker]["retained_margin"] = float(retained_summary_acc[ranker]["retained_margin"]) + float(retained_by_ranker[ranker]["retained_margin"])

            for variant in VARIANTS:
                variant_rows = _apply_variant(qid, votes_by_pair, variant)
                reconstructed_rows_by_variant[variant].extend(variant_rows)

        for ranker in RANKERS:
            pairwise_stats = _margin_stats(pairwise_values_acc[ranker])
            pairwise_rows.append(
                {
                    "dataset": dataset,
                    "ranker": ranker,
                    "stage": "before_threshold",
                    **pairwise_stats,
                }
            )
            possible_pairs = int(retained_summary_acc[ranker]["possible_pairs"])
            retained_votes = int(retained_summary_acc[ranker]["retained_votes"])
            retained_margin = float(retained_summary_acc[ranker]["retained_margin"])
            total_raw_margin = float(pairwise_stats["total_absolute_margin"] or 0.0)
            retained_rows.append(
                {
                    "dataset": dataset,
                    "ranker": ranker,
                    "stage": "after_min_vote_margin_0p05",
                    "possible_pairs": possible_pairs,
                    "retained_votes": retained_votes,
                    "retained_vote_fraction": (retained_votes / possible_pairs) if possible_pairs else None,
                    "retained_margin": retained_margin,
                    "retained_margin_share": (retained_margin / total_raw_margin) if total_raw_margin > 0 else None,
                }
            )

        for variant in VARIANTS:
            stored_by_query = stored_vote_rows_by_variant[variant]
            reconstructed = reconstructed_rows_by_variant[variant]
            reconstructed_norm = _normalized_rows(reconstructed)
            stored_norm = _normalized_rows([row for rows in stored_by_query.values() for row in rows])
            reproduction_rows.append(
                {
                    "dataset": dataset,
                    "variant": variant,
                    "reconstructed_rows": len(reconstructed_norm),
                    "stored_rows": len(stored_norm),
                    "exact_match": reconstructed_norm == stored_norm,
                    "stored_sha256": _jsonl_sha256(spec.vote_files[variant]),
                }
            )

            graph, edge_ranker_weights, edge_ranker_set, edge_vote_counts = _graph_from_rows(reconstructed)
            total_graph_weight = float(sum(data.get("weight", 1.0) for _, _, data in graph.edges(data=True)))
            total_votes = len(reconstructed)
            total_edges = graph.number_of_edges()

            ranker_total_weight: dict[str, float] = defaultdict(float)
            ranker_vote_count: dict[str, int] = defaultdict(int)
            ranker_affected_edges: dict[str, set[tuple[str, str]]] = defaultdict(set)
            conditional_weight_sums: dict[str, float] = defaultdict(float)
            conditional_edge_denoms: dict[str, int] = defaultdict(int)

            for edge, contrib in edge_ranker_weights.items():
                edge_total = float(graph[edge[0]][edge[1]]["weight"])
                for ranker, weight in contrib.items():
                    ranker_total_weight[ranker] += float(weight)
                    ranker_affected_edges[ranker].add(edge)
                    conditional_weight_sums[ranker] += edge_total
                    conditional_edge_denoms[ranker] += 1
                for ranker in edge_ranker_set[edge]:
                    ranker_vote_count[ranker] += sum(1 for row in reconstructed if row["winner_doc_id"] == edge[0] and row["loser_doc_id"] == edge[1] and row["voter"] == ranker)

            dag, removed_records = _analyze_greedy_fas(graph, edge_ranker_weights)
            removed_weight_by_ranker = _sum_nested_weight(removed_records, "removed_ranker_weights")
            total_removed_weight = float(sum(rec["removed_weight"] for rec in removed_records))

            for ranker in RANKERS:
                graph_rows.append(
                    {
                        "dataset": dataset,
                        "variant": variant,
                        "stage": "graph_edge_weight",
                        "ranker": ranker,
                        "directional_votes_retained": ranker_vote_count.get(ranker, 0),
                        "graph_edges_influenced": len(ranker_affected_edges.get(ranker, set())),
                        "total_ranker_edge_weight": float(ranker_total_weight.get(ranker, 0.0)),
                        "ranker_weight_share_of_graph": (ranker_total_weight.get(ranker, 0.0) / total_graph_weight) if total_graph_weight > 0 else None,
                        "conditional_share_when_ranker_participates": (ranker_total_weight.get(ranker, 0.0) / conditional_weight_sums[ranker]) if conditional_weight_sums.get(ranker, 0.0) > 0 else None,
                        "contribution_per_vote": (ranker_total_weight.get(ranker, 0.0) / ranker_vote_count[ranker]) if ranker_vote_count.get(ranker, 0) else None,
                        "contribution_per_affected_edge": (ranker_total_weight.get(ranker, 0.0) / len(ranker_affected_edges[ranker])) if ranker_affected_edges.get(ranker) else None,
                        "total_graph_weight": total_graph_weight,
                        "graph_edge_count": total_edges,
                        "graph_vote_row_count": total_votes,
                    }
                )
                removed_ranker_edges = sum(1 for rec in removed_records if ranker in rec["removed_ranker_weights"])
                removed_rows.append(
                    {
                        "dataset": dataset,
                        "variant": variant,
                        "stage": "removed_fas_weight",
                        "ranker": ranker,
                        "removed_fas_weight": float(removed_weight_by_ranker.get(ranker, 0.0)),
                        "removed_weight_share": (removed_weight_by_ranker.get(ranker, 0.0) / total_removed_weight) if total_removed_weight > 0 else None,
                        "removed_edges_with_ranker_support": removed_ranker_edges,
                        "total_removed_edges": len(removed_records),
                        "total_removed_weight": total_removed_weight,
                        "dominant_removed_edge_count": sum(1 for rec in removed_records if rec["dominant_ranker"] == ranker),
                    }
                )

            bm25_graph_row = next(row for row in graph_rows if row["dataset"] == dataset and row["variant"] == variant and row["ranker"] == "bm25")
            dominance_rows.extend(
                [
                    {
                        "dataset": dataset,
                        "variant": variant,
                        "stage": "after_min_vote_margin_0p05_retained_margin_share",
                        "ranker": "bm25",
                        "value": next(row for row in retained_rows if row["dataset"] == dataset and row["ranker"] == "bm25")["retained_margin_share"],
                        "denominator_definition": "BM25 retained margin / total retained margin after per-vote 0.05 threshold within dataset",
                    },
                    {
                        "dataset": dataset,
                        "variant": variant,
                        "stage": "graph_weight_share",
                        "ranker": "bm25",
                        "value": bm25_graph_row["ranker_weight_share_of_graph"],
                        "denominator_definition": "BM25 contribution weight / total retained graph edge weight for dataset+variant",
                    },
                    {
                        "dataset": dataset,
                        "variant": variant,
                        "stage": "graph_weight_share_conditional_on_participation",
                        "ranker": "bm25",
                        "value": bm25_graph_row["conditional_share_when_ranker_participates"],
                        "denominator_definition": "BM25 contribution weight / total edge weight on edges where BM25 contributes for dataset+variant",
                    },
                ]
            )
            bm25_removed_row = next(row for row in removed_rows if row["dataset"] == dataset and row["variant"] == variant and row["ranker"] == "bm25")
            dominance_rows.append(
                {
                    "dataset": dataset,
                    "variant": variant,
                    "stage": "removed_fas_weight_share",
                    "ranker": "bm25",
                    "value": bm25_removed_row["removed_weight_share"],
                    "denominator_definition": "BM25-attributed removed edge weight / total removed FAS weight for dataset+variant",
                }
            )

            phase01_details["datasets"][dataset][variant] = {
                "reconstructed_rows": len(reconstructed_norm),
                "stored_rows": len(stored_norm),
                "exact_reproduction_match": reconstructed_norm == stored_norm,
                "total_graph_weight": total_graph_weight,
                "graph_edge_count": total_edges,
                "removed_edge_count": len(removed_records),
                "total_removed_weight": total_removed_weight,
            }

    _write_csv(root / "tables" / "raw_score_scale_by_query.csv", raw_score_rows)
    _write_csv(root / "tables" / "pairwise_margin_distribution.csv", pairwise_rows)
    _write_csv(root / "tables" / "retained_vote_contributions.csv", retained_rows)
    _write_csv(root / "tables" / "graph_edge_weight_contributions.csv", graph_rows)
    _write_csv(root / "tables" / "removed_fas_weight_contributions.csv", removed_rows)
    _write_csv(root / "tables" / "bm25_dominance_summary.csv", dominance_rows)
    _write_csv(root / "reproductions" / "vote_reproduction_checks.csv", reproduction_rows)
    (root / "manifests" / "phase01_details.json").write_text(
        json.dumps(phase01_details, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    graph_df = pd.read_csv(root / "tables" / "graph_edge_weight_contributions.csv")
    removed_df = pd.read_csv(root / "tables" / "removed_fas_weight_contributions.csv")
    dominance_df = pd.read_csv(root / "tables" / "bm25_dominance_summary.csv")

    _plot_box_from_csv(
        root / "tables" / "raw_score_scale_by_query.csv",
        "range",
        root / "figures" / "raw_score_range_by_ranker_dataset.png",
        "Raw Score Ranges by Dataset and Ranker",
        yscale="log",
    )
    _plot_box_from_csv(
        root / "tables" / "pairwise_margin_distribution.csv",
        "total_absolute_margin",
        root / "figures" / "pairwise_margin_distribution_by_ranker_dataset.png",
        "Total Pairwise Absolute Margins by Dataset and Ranker",
        yscale="log",
    )
    _plot_stacked_share(
        graph_df,
        "ranker_weight_share_of_graph",
        "graph_edge_weight",
        root / "figures" / "retained_graph_weight_share.png",
        "Retained Graph Weight Share by Dataset and Variant",
    )
    _plot_stacked_share(
        removed_df,
        "removed_weight_share",
        "removed_fas_weight",
        root / "figures" / "removed_fas_weight_share.png",
        "Removed FAS Weight Share by Dataset and Variant",
    )

    conditional_rows = dominance_df[dominance_df["stage"] == "graph_weight_share_conditional_on_participation"]
    if not conditional_rows.empty:
        min_val = float(conditional_rows["value"].min())
        max_val = float(conditional_rows["value"].max())
        range_text = f"{100.0 * min_val:.1f}%–{100.0 * max_val:.1f}%"
    else:
        min_val = max_val = math.nan
        range_text = "NA"

    bm25_report_lines = [
        "# BM25 Dominance Verification",
        "",
        "## Canonical Input Set",
        "",
        "- Score files and vote files were taken from `experiments/method_improvement_audit_20260711_205733/inputs/`.",
        "- Reconstructed `ms1`, `ms1_drop_mutual`, and `ms2` vote rows were compared against the stored JSONL artifacts.",
        "",
        "## Vote Reproduction Check",
        "",
    ]
    for row in reproduction_rows:
        bm25_report_lines.append(
            f"- `{row['dataset']}` / `{row['variant']}`: "
            f"reconstructed_rows={row['reconstructed_rows']}, stored_rows={row['stored_rows']}, "
            f"exact_match={row['exact_match']}."
        )
    bm25_report_lines.extend(
        [
            "",
            "## BM25 Share Definitions Used",
            "",
            "- `after_min_vote_margin_0p05_retained_margin_share`: BM25 retained native margin divided by the total retained native margin after the per-vote `0.05` threshold.",
            "- `graph_weight_share`: BM25-attributed retained edge weight divided by the total retained graph edge weight for a dataset and vote variant.",
            "- `graph_weight_share_conditional_on_participation`: BM25-attributed retained edge weight divided by the total weight of graph edges on which BM25 contributes at all.",
            "- `removed_fas_weight_share`: BM25-attributed removed edge weight divided by total removed FAS weight.",
            "",
            "## Preliminary Verification",
            "",
            f"- Conditional BM25 graph-weight share range across all dataset/variant rows: `{range_text}`.",
            "- Exact per-dataset values are listed in `tables/bm25_dominance_summary.csv`.",
            "- This range is the directly relevant denominator for the earlier claim that BM25 supplies roughly all retained weight whenever it participates in an edge.",
            "",
        ]
    )
    (root / "BM25_DOMINANCE_VERIFICATION.md").write_text("\n".join(bm25_report_lines), encoding="utf-8")

    command_log = [
        "# Commands Executed",
        "",
        "- `source .venv/bin/activate`",
        "- `git branch --show-current`",
        "- `git rev-parse HEAD`",
        "- `git status --short`",
        "- `python --version`",
        "- `pip freeze`",
        "- `df -h .`",
        "- `python -u reports/b3_margin_calibration_investigation/scripts/run_phase0_phase1.py --root reports/b3_margin_calibration_investigation --canonical-manifest experiments/method_improvement_audit_20260711_205733/phase_reports/canonical_rerun_manifest.json`",
        "",
        "The long-running audit command is expected to be launched through TMUX per the B3 policy; the TMUX wrapper command is recorded separately in `RUNNING_JOBS.md`.",
    ]
    (root / "COMMANDS_EXECUTED.md").write_text("\n".join(command_log), encoding="utf-8")

    audit_manifest = {
        "initial_state": initial_state,
        "code_path_inventory_csv": str(root / "tables" / "code_path_inventory.csv"),
        "phase01_details_json": str(root / "manifests" / "phase01_details.json"),
        "reproduction_checks_csv": str(root / "reproductions" / "vote_reproduction_checks.csv"),
        "tables": {
            "raw_score_scale_by_query": str(root / "tables" / "raw_score_scale_by_query.csv"),
            "pairwise_margin_distribution": str(root / "tables" / "pairwise_margin_distribution.csv"),
            "retained_vote_contributions": str(root / "tables" / "retained_vote_contributions.csv"),
            "graph_edge_weight_contributions": str(root / "tables" / "graph_edge_weight_contributions.csv"),
            "removed_fas_weight_contributions": str(root / "tables" / "removed_fas_weight_contributions.csv"),
            "bm25_dominance_summary": str(root / "tables" / "bm25_dominance_summary.csv"),
        },
        "figures": {
            "raw_score_range": str(root / "figures" / "raw_score_range_by_ranker_dataset.png"),
            "pairwise_margin_distribution": str(root / "figures" / "pairwise_margin_distribution_by_ranker_dataset.png"),
            "retained_graph_weight_share": str(root / "figures" / "retained_graph_weight_share.png"),
            "removed_fas_weight_share": str(root / "figures" / "removed_fas_weight_share.png"),
        },
    }
    (root / "audit_manifest.json").write_text(json.dumps(audit_manifest, indent=2, sort_keys=True), encoding="utf-8")
    print("[phase0/1] complete", flush=True)


if __name__ == "__main__":
    main()
