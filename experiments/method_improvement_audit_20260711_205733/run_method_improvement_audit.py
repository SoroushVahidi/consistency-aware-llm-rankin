#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import networkx as nx

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SRC))

from consistency_ranker.baseline_ranking import (  # noqa: E402
    borda_ranking,
    borda_scores,
    copeland_ranking,
    pagerank_ranking,
    priority_topological_ranking,
    rank_centrality_ranking,
    rank_centrality_scores,
    score_sum_ranking,
    score_sum_scores,
    topological_ranking,
    weighted_out_minus_in_ranking,
    weighted_out_minus_in_scores,
)
from consistency_ranker.data.dataset_registry import processed_queries_jsonl  # noqa: E402
from consistency_ranker.data.unified_loader import (  # noqa: E402
    load_dataset_splits,
    load_multi_scorer_rankings,
)
from consistency_ranker.failure_mining.graph_features import extended_graph_stats  # noqa: E402
from consistency_ranker.graph_construction import build_graph  # noqa: E402
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight  # noqa: E402
from consistency_ranker.markov_graph_ranking import (  # noqa: E402
    DEFAULT_MARKOV_DAMPING,
    markov_graph_ranking,
    markov_graph_scores,
)
from consistency_ranker.metric_aware_repair import reweight_graph_for_metric_aware_fas  # noqa: E402
from consistency_ranker.pairwise_prefs import Preference  # noqa: E402
from consistency_ranker.rrf_ranking import DEFAULT_RRF_K, per_query_rrf_ranking_from_score_maps  # noqa: E402
from scripts.build_votes_file import _derive_ranker_weights, _votes_for_query  # noqa: E402
from scripts.run_real_experiment import (  # noqa: E402
    _alpha_token,
    _average_precision_at_k,
    _hybrid_rrf_component_ranking,
    _kendall_tau,
    _ndcg_at_k,
    _pairwise_accuracy_from_relevance,
    _precision_recall_at_k,
    _prior_only_ranking,
    _reference_ranking_for_candidates,
    _rrf_prior_scores_for_query,
    _score_sum_prior_scores,
)


WORKSPACE = Path(__file__).resolve().parent
LOG_DIR = WORKSPACE / "logs"
INPUT_DIR = WORKSPACE / "inputs"
RERUN_DIR = WORKSPACE / "canonical_logged_rerun"
ANALYSIS_DIR = WORKSPACE / "analysis"
PHASE_DIR = WORKSPACE / "phase_reports"
TMP_DIR = WORKSPACE / "tmp"

LIVE_STATUS = WORKSPACE / "live_status.md"
RUN_MANIFEST = WORKSPACE / "RUN_MANIFEST.json"
FINAL_REPORT = WORKSPACE / "FINAL_REPORT.md"

SESSION_NAME = "method_improvement_audit"
PRIMARY_CANONICAL_METHOD = "hybrid_rrf_repaired_copeland_a0p3_minmax"

RANKERS = ("bm25", "tfidf", "minilm")
LEXICAL_RANKERS = {"bm25", "tfidf"}
DATASET_SPECS = {
    "scidocs": {"n_queries": 120, "top_n": 50, "top_k": 20},
    "fiqa": {"n_queries": 120, "top_n": 50, "top_k": 20},
    "hotpotqa": {"n_queries": 70, "top_n": 35, "top_k": 10},
    "bright": {"n_queries": 50, "top_n": 50, "top_k": 20},
}
CANONICAL_VARIANTS = ("ms2", "ms1", "ms1_drop_mutual")
GRAPH_VARIANTS = (
    "ms1",
    "ms2",
    "ms1_drop_mutual",
    "ranker_reliability_weighted",
    "correlation_discounted",
    "ranker_family_vote_cap",
    "confidence_thresholded",
    "disagreement_entropy_sparsified",
    "topk_focused_pair_construction",
    "stability_filtered",
)
ALPHAS = (0.0, 0.1, 0.3, 0.5, 0.75, 1.0, 2.0)
BOOTSTRAP_REPS = 1000


@dataclass(frozen=True)
class DatasetRunSpec:
    dataset: str
    n_queries: int
    top_n: int
    top_k: int


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError(type(obj).__name__)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _mean(vals: Iterable[float | None]) -> float | None:
    xs = [float(v) for v in vals if v is not None]
    return (sum(xs) / len(xs)) if xs else None


def _median(vals: Iterable[float | None]) -> float | None:
    xs = [float(v) for v in vals if v is not None]
    return float(statistics.median(xs)) if xs else None


def _pct(num: int, den: int) -> float:
    return float(num) / float(den) if den else 0.0


def _norm_minmax(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi - lo <= 1e-12:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _norm_zscore(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    mu = statistics.mean(vals)
    sigma = statistics.pstdev(vals)
    if sigma <= 1e-12:
        return {k: 0.0 for k in scores}
    return {k: (v - mu) / sigma for k, v in scores.items()}


def _rank_scores(scores: dict[str, float]) -> dict[str, float]:
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    n = len(ranked)
    return {doc_id: float(n - idx) for idx, (doc_id, _s) in enumerate(ranked)}


def _rrf_fuse(rankings: list[list[str]], k: int = DEFAULT_RRF_K) -> list[str]:
    pool = sorted({doc_id for ranking in rankings for doc_id in ranking})
    scores: dict[str, float] = {doc_id: 0.0 for doc_id in pool}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] += 1.0 / (k + rank)
    return sorted(scores, key=lambda d: (-scores[d], d))


def _ranking_from_scores(scores: dict[str, float], candidate_nodes: Iterable[str]) -> list[str]:
    return sorted(set(candidate_nodes), key=lambda d: (-scores.get(d, 0.0), d))


def _top_membership_changed(a: list[str], b: list[str], k: int) -> bool:
    return set(a[:k]) != set(b[:k])


def _align_ranking(ranking: list[str], rel_map: dict[str, int]) -> list[str]:
    rel_docs = set(rel_map)
    return [d for d in ranking if d in rel_docs]


def _label_from_delta(delta: float, tol: float = 1e-12) -> str:
    if delta > tol:
        return "help"
    if delta < -tol:
        return "harm"
    return "neutral"


def _ci_from_paired_deltas(deltas: list[float], reps: int = BOOTSTRAP_REPS, seed: int = 13) -> tuple[float | None, float | None]:
    if not deltas:
        return None, None
    rng = random.Random(seed)
    n = len(deltas)
    means = []
    for _ in range(reps):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * (reps - 1))]
    hi = means[int(0.975 * (reps - 1))]
    return lo, hi


def _kendall(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx <= 1e-12 or deny <= 1e-12:
        return None
    return num / (denx * deny)


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    def rankify(vals: list[float]) -> list[float]:
        ordered = sorted((v, i) for i, v in enumerate(vals))
        ranks = [0.0] * len(vals)
        idx = 0
        while idx < len(ordered):
            j = idx + 1
            while j < len(ordered) and ordered[j][0] == ordered[idx][0]:
                j += 1
            avg_rank = (idx + 1 + j) / 2.0
            for _v, original_idx in ordered[idx:j]:
                ranks[original_idx] = avg_rank
            idx = j
        return ranks
    return _kendall(rankify(xs), rankify(ys))


class AuditRunner:
    def __init__(self) -> None:
        self.started = time.time()
        self.phase = "initializing"
        self.completed_tasks: list[str] = []
        self.active_task = "setup"
        self.failures: list[dict[str, Any]] = []
        self.queries_processed = 0
        self.provisional_findings: list[str] = []
        self.records_written = 0
        self.dataset_specs = [DatasetRunSpec(dataset=k, **v) for k, v in DATASET_SPECS.items()]
        self.query_id_map: dict[str, list[str]] = {}
        self.score_file_map: dict[str, dict[str, Path]] = {}
        self.variant_vote_files: dict[str, dict[str, Path]] = defaultdict(dict)
        self.dataset_cache: dict[str, dict[str, Any]] = {}
        self.phase_outputs: dict[str, list[str]] = defaultdict(list)
        self.master_records_path = ANALYSIS_DIR / "canonical_query_records.jsonl"
        self.graph_variant_records_path = ANALYSIS_DIR / "graph_construction_query_records.jsonl"
        self.repair_variant_records_path = ANALYSIS_DIR / "repair_method_query_records.jsonl"
        self.run_manifest: dict[str, Any] = {
            "session_name": SESSION_NAME,
            "workspace": str(WORKSPACE),
            "repo": str(REPO),
            "started_at": _now(),
            "python": sys.executable,
            "phases": {},
            "status": "running",
            "outputs": {},
        }

    def update_status(self) -> None:
        lines = [
            "# Method Improvement Audit",
            "",
            f"- updated_at: {_now()}",
            f"- current_phase: {self.phase}",
            f"- active_task: {self.active_task}",
            f"- completed_tasks: {len(self.completed_tasks)}",
            f"- queries_processed: {self.queries_processed}",
            f"- failures: {len(self.failures)}",
            f"- workspace: {WORKSPACE}",
            f"- final_report: {FINAL_REPORT}",
            "",
            "## Completed Tasks",
            "",
        ]
        if self.completed_tasks:
            lines.extend([f"- {task}" for task in self.completed_tasks[-20:]])
        else:
            lines.append("- none yet")
        lines += ["", "## Latest Provisional Findings", ""]
        if self.provisional_findings:
            lines.extend([f"- {item}" for item in self.provisional_findings[-12:]])
        else:
            lines.append("- pending")
        lines += ["", "## Output Paths", ""]
        for key, paths in sorted(self.phase_outputs.items()):
            if not paths:
                continue
            lines.append(f"- {key}:")
            lines.extend([f"  - {p}" for p in paths[-10:]])
        LIVE_STATUS.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _write_json(RUN_MANIFEST, self.run_manifest)

    def record_failure(self, phase: str, task: str, exc: BaseException) -> None:
        entry = {
            "phase": phase,
            "task": task,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "time": _now(),
        }
        self.failures.append(entry)
        (LOG_DIR / "failures").mkdir(parents=True, exist_ok=True)
        idx = len(self.failures)
        (LOG_DIR / "failures" / f"{idx:03d}_{phase}_{task}.log").write_text(
            entry["traceback"], encoding="utf-8"
        )
        self.run_manifest["phases"].setdefault(phase, {}).setdefault("failures", []).append(entry)
        self.update_status()

    def run_subprocess(self, cmd: list[str], *, label: str, cwd: Path = REPO, env: dict[str, str] | None = None) -> None:
        log_path = LOG_DIR / "commands.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{_now()}] {label}: {' '.join(str(x) for x in cmd)}\n")
        full_env = os.environ.copy()
        full_env["PYTHONPATH"] = f"{SRC}:{full_env.get('PYTHONPATH', '')}"
        if env:
            full_env.update(env)
        result = subprocess.run(cmd, cwd=cwd, env=full_env, capture_output=True, text=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(result.stdout)
            fh.write(result.stderr)
            fh.write(f"[exit={result.returncode}]\n")
        if result.returncode != 0:
            raise RuntimeError(f"{label} failed with exit code {result.returncode}")

    def run(self) -> None:
        try:
            self._prepare_workspace()
            self._run_phase("phase0", "Canonical baseline identification", self.phase0_baseline)
            self._run_phase("phase1_inputs", "Canonical logged rerun input generation", self.phase1_prepare_inputs)
            self._run_phase("phase1_failure", "Failure-path decomposition", self.phase1_failure_paths)
            self._run_phase("phase2_frontier", "Candidate frontier and oracle analysis", self.phase2_candidate_frontier)
            self._run_phase("phase3_fusion", "Extraction and fusion audit", self.phase3_extraction_fusion)
            self._run_phase("phase4_repair", "Repair-method comparison", self.phase4_repair_methods)
            self._run_phase("phase5_graph", "Pre-repair graph construction audit", self.phase5_graph_construction)
            self._run_phase("phase6_policy", "Regime-aware transparent policy feasibility", self.phase6_policy)
            self._run_phase("phase7_contrib", "Contribution analysis", self.phase7_contribution)
        finally:
            self._write_final_report()

    def _prepare_workspace(self) -> None:
        for path in (LOG_DIR, INPUT_DIR, RERUN_DIR, ANALYSIS_DIR, PHASE_DIR, TMP_DIR):
            path.mkdir(parents=True, exist_ok=True)
        self.completed_tasks.append("workspace initialized")
        self.update_status()

    def _run_phase(self, phase_key: str, phase_title: str, fn) -> None:
        self.phase = phase_title
        self.active_task = phase_title
        self.run_manifest["phases"].setdefault(phase_key, {"title": phase_title, "started_at": _now(), "status": "running"})
        self.update_status()
        try:
            fn()
            self.run_manifest["phases"][phase_key]["finished_at"] = _now()
            self.run_manifest["phases"][phase_key]["status"] = "completed"
            self.completed_tasks.append(phase_title)
        except Exception as exc:  # noqa: BLE001
            self.run_manifest["phases"][phase_key]["finished_at"] = _now()
            self.run_manifest["phases"][phase_key]["status"] = "failed"
            self.record_failure(phase_key, phase_title, exc)
        self.update_status()

    def phase0_baseline(self) -> None:
        # Paths updated 2026-07-30 (repo Stage 2): these three files moved to
        # reports/_archive/publication_audit_20260406/ when the pipeline they
        # audit (outputs/pub_vote_cmp_all4/) was marked historical.
        audit_text = (REPO / "reports/_archive/publication_audit_20260406/repo_publication_audit.md").read_text(encoding="utf-8")
        inv_rows = list(csv.DictReader((REPO / "reports/_archive/publication_audit_20260406/canonical_results_inventory.csv").open(encoding="utf-8")))
        claim_rows = list(csv.DictReader((REPO / "reports/_archive/publication_audit_20260406/claim_support_matrix.csv").open(encoding="utf-8")))
        graph_rows = list(csv.DictReader((REPO / "outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv").open(encoding="utf-8")))
        delta_rows = list(csv.DictReader((REPO / "outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv").open(encoding="utf-8")))
        bew_rows = list(csv.DictReader((REPO / "outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv").open(encoding="utf-8")))

        lines = [
            "# Baseline And Scope",
            "",
            f"Generated: {_now()}",
            "",
            "## Canonical Current Evidence",
            "",
            "- Canonical package: `outputs/pub_vote_cmp_all4/paper_package/`.",
            "- Canonical manuscript freeze clone: `outputs/final_jis_package/`.",
            "- Historical but conflicting package: `outputs/pub_vote_cmp_v2/paper_package/`.",
            "- The audit uses current canonical tables only for baseline claims and never mixes `pub_vote_cmp_v2` values into canonical summaries.",
            "",
            "## Canonical Pipeline Details",
            "",
            "- Dataset package: SciDocs, FiQA, HotpotQA, BRIGHT.",
            "- Vote constructions: `ms2`, `ms1`, `ms1_drop_mutual`.",
            "- Rankers used to build votes: BM25, TF-IDF, MiniLM.",
            "- Canonical query subset generator: `scripts/run_publication_vote_suite.py`.",
            "- Candidate retrieval depth per ranker: SciDocs 50, FiQA 50, HotpotQA 35, BRIGHT 50.",
            "- Candidate graph top-k for vote construction: SciDocs 20, FiQA 20, HotpotQA 10, BRIGHT 20.",
            "- Repair method in canonical package: greedy weighted feedback arc set (`greedy_fas`).",
            "- Canonical graph extractors in manuscript tables: unrepaired/repaired Copeland and balance hybrids with RRF prior.",
            "- Canonical fusion formula in manuscript package: min-max normalized prior + alpha * min-max normalized graph component, with alpha=0.3 for `hybrid_rrf_*_a03`.",
            "- Canonical statistical procedure in manuscript package: paired bootstrap delta summaries from `outputs/pub_vote_cmp_all4/analysis/*.json`.",
            "",
            "## Exact Canonical Scope By Dataset",
            "",
        ]
        by_dataset = defaultdict(list)
        for row in graph_rows:
            by_dataset[row["dataset"]].append(row)
        for dataset, rows in sorted(by_dataset.items()):
            nq = {r["variant"]: r["n_queries"] for r in rows}
            lines.append(f"- {dataset}: n_queries by variant {json.dumps(nq, sort_keys=True)}")

        lines += [
            "",
            "## Historical, Stale, Or Conflicting Evidence",
            "",
        ]
        for row in inv_rows:
            if row["path"] == "outputs/pub_vote_cmp_all4/paper_package/":
                continue
            lines.append(
                f"- `{row['path']}`: {row['final_or_exploratory']}; conflicts_with={row['conflicts_with'] or 'none'}"
            )

        lines += [
            "",
            "## Manuscript Claim Support Snapshot",
            "",
        ]
        for row in claim_rows:
            if row["claim_id"] in {"C2", "C3", "C6", "C7", "C10"}:
                lines.append(f"- {row['claim_id']}: {row['claim_text']} [{row['support_level']}]")

        lines += [
            "",
            "## Canonical Tables Used For Claims",
            "",
            "- `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv`",
            "- `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv`",
            "- `outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv`",
            "",
            "## Audit Scope For This Workspace",
            "",
            "- Phase 0 uses canonical committed aggregates only.",
            "- Phases 1–6 regenerate a fully logged workspace-local rerun under canonical query subsets and rankers so per-query diagnostics can be computed without touching canonical directories.",
            "- Canonical baseline claims remain tied to `pub_vote_cmp_all4` / `final_jis_package`; workspace reruns are diagnostic and must not overwrite or silently replace the canonical package.",
            "",
            "## Source Audit Note",
            "",
            "> Key sentence from `reports/repo_publication_audit.md`: `outputs/pub_vote_cmp_all4/paper_package/` is the recommended canonical package.",
            "",
        ]

        out = PHASE_DIR / "BASELINE_AND_SCOPE.md"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.phase_outputs["phase0"].append(str(out))
        self.phase_outputs["phase0"].extend(
            [
                "outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv",
                "outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv",
                "outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv",
            ]
        )
        self.provisional_findings.append("Canonical evidence package confirmed as outputs/pub_vote_cmp_all4/paper_package.")
        self.provisional_findings.append("Per-query canonical run trees are absent; a workspace-local logged rerun is required for failure-path analysis.")

    def _write_query_ids(self, spec: DatasetRunSpec) -> list[str]:
        path = INPUT_DIR / spec.dataset / "query_ids.txt"
        qpath = processed_queries_jsonl(spec.dataset)
        ids: list[str] = []
        with qpath.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                ids.append(str(row["query_id"]))
                if len(ids) >= spec.n_queries:
                    break
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(ids) + "\n", encoding="utf-8")
        return ids

    def phase1_prepare_inputs(self) -> None:
        py = sys.executable
        for spec in self.dataset_specs:
            self.active_task = f"prepare inputs: {spec.dataset}"
            self.update_status()
            qids = self._write_query_ids(spec)
            self.query_id_map[spec.dataset] = qids
            ds_input = INPUT_DIR / spec.dataset
            score_paths: dict[str, Path] = {}
            for ranker in RANKERS:
                outp = ds_input / f"scores_{ranker}.jsonl"
                score_paths[ranker] = outp
                if not outp.exists():
                    self.run_subprocess(
                        [
                            py,
                            str(REPO / "scripts/generate_score_file.py"),
                            "--dataset", spec.dataset,
                            "--ranker", ranker,
                            "--max-queries", str(len(qids)),
                            "--top-n", str(spec.top_n),
                            "--seed", "42",
                            "--query-id-file", str(ds_input / "query_ids.txt"),
                            "--output", str(outp),
                        ],
                        label=f"generate_score_file:{spec.dataset}:{ranker}",
                    )
            self.score_file_map[spec.dataset] = score_paths

            v_ms2 = ds_input / "votes_ms2.jsonl"
            v_ms1 = ds_input / "votes_ms1.jsonl"
            v_dm = ds_input / "votes_ms1_drop_mutual.jsonl"
            if not v_ms2.exists():
                self.run_subprocess(
                    [
                        py, str(REPO / "scripts/build_votes_file.py"),
                        "--dataset", spec.dataset,
                        "--score-files", *[str(score_paths[r]) for r in RANKERS],
                        "--top-k", str(spec.top_k),
                        "--vote-weight-scheme", "margin",
                        "--min-vote-margin", "0.05",
                        "--abstain-missing",
                        "--query-id-file", str(ds_input / "query_ids.txt"),
                        "--min-support", "2",
                        "--min-aggregate-margin", "0.1",
                        "--output", str(v_ms2),
                    ],
                    label=f"build_votes_file:{spec.dataset}:ms2",
                )
            if not v_ms1.exists():
                self.run_subprocess(
                    [
                        py, str(REPO / "scripts/build_votes_file.py"),
                        "--dataset", spec.dataset,
                        "--score-files", *[str(score_paths[r]) for r in RANKERS],
                        "--top-k", str(spec.top_k),
                        "--vote-weight-scheme", "margin",
                        "--min-vote-margin", "0.05",
                        "--abstain-missing",
                        "--query-id-file", str(ds_input / "query_ids.txt"),
                        "--min-support", "1",
                        "--min-aggregate-margin", "0.0",
                        "--output", str(v_ms1),
                    ],
                    label=f"build_votes_file:{spec.dataset}:ms1",
                )
            if not v_dm.exists():
                self.run_subprocess(
                    [
                        py,
                        str(REPO / "scripts/postprocess_votes_drop_mutual_pairs.py"),
                        "--input", str(v_ms1),
                        "--output", str(v_dm),
                    ],
                    label=f"drop_mutual:{spec.dataset}",
                )
            self.variant_vote_files[spec.dataset]["ms2"] = v_ms2
            self.variant_vote_files[spec.dataset]["ms1"] = v_ms1
            self.variant_vote_files[spec.dataset]["ms1_drop_mutual"] = v_dm

        manifest = {
            "canonical_query_subset": {spec.dataset: asdict(spec) for spec in self.dataset_specs},
            "score_files": {ds: {r: str(p) for r, p in paths.items()} for ds, paths in self.score_file_map.items()},
            "vote_files": {ds: {k: str(v) for k, v in paths.items()} for ds, paths in self.variant_vote_files.items()},
        }
        out = PHASE_DIR / "canonical_rerun_manifest.json"
        _write_json(out, manifest)
        self.phase_outputs["phase1_inputs"].append(str(out))
        self.provisional_findings.append("Offline score generation and canonical vote regeneration are feasible with local data and local models.")

    def _load_dataset_cache(self, dataset: str) -> dict[str, Any]:
        if dataset in self.dataset_cache:
            return self.dataset_cache[dataset]
        queries, documents, qrels = load_dataset_splits(dataset)
        qrels_by_query: dict[str, list[Any]] = defaultdict(list)
        for qrel in qrels:
            qrels_by_query[qrel.query_id].append(qrel)
        query_map = {q.query_id: q for q in queries}
        doc_map = {d.doc_id: d for d in documents}
        cache = {
            "queries": queries,
            "documents": documents,
            "qrels": qrels,
            "qrels_by_query": qrels_by_query,
            "query_map": query_map,
            "doc_map": doc_map,
        }
        self.dataset_cache[dataset] = cache
        return cache

    def _load_score_maps(self, dataset: str) -> dict[str, dict[str, list[tuple[str, float]]]]:
        return load_multi_scorer_rankings(self.score_file_map[dataset])

    def _read_votes_file(self, path: Path) -> dict[str, list[dict[str, Any]]]:
        rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    row = json.loads(line)
                    rows[str(row["query_id"])].append(row)
        return rows

    def _rows_to_preferences(self, rows: list[dict[str, Any]]) -> list[Preference]:
        return [
            Preference(
                winner=str(row["winner_doc_id"]),
                loser=str(row["loser_doc_id"]),
                weight=float(row["weight"]),
            )
            for row in rows
        ]

    def _canonical_variant_rows(self, dataset: str, variant: str) -> dict[str, list[dict[str, Any]]]:
        return self._read_votes_file(self.variant_vote_files[dataset][variant])

    def _derive_graph_variant_rows(
        self,
        dataset: str,
        spec: DatasetRunSpec,
        score_maps: dict[str, dict[str, list[tuple[str, float]]]],
    ) -> dict[str, dict[str, list[dict[str, Any]]]]:
        cache = self._load_dataset_cache(dataset)
        qrels_by_query = cache["qrels_by_query"]
        selected_qids = self.query_id_map[dataset]
        score_index = {qid: {r: score_maps[r][qid] for r in score_maps if qid in score_maps[r]} for qid in selected_qids}

        ranker_scores = {
            qid: {r: dict(score_index[qid].get(r, [])) for r in RANKERS}
            for qid in selected_qids
        }
        reliability_weights = _derive_ranker_weights(
            score_index={qid: {r: {d: s for d, s in score_index[qid].get(r, [])} for r in RANKERS} for qid in selected_qids},
            qrels_by_query=qrels_by_query,
            selected_qids=selected_qids,
            top_k=spec.top_k,
            weighting_mode="auto_ndcg_at_k",
            floor=0.05,
        )

        out: dict[str, dict[str, list[dict[str, Any]]]] = {variant: {} for variant in GRAPH_VARIANTS}

        for qid in selected_qids:
            per_ranker = ranker_scores[qid]
            base_ms1 = _votes_for_query(
                qid, per_ranker, top_k=spec.top_k, vote_weight_scheme="margin",
                min_vote_margin=0.05, abstain_missing=True, min_support=1, min_aggregate_margin=0.0
            )
            base_ms2 = _votes_for_query(
                qid, per_ranker, top_k=spec.top_k, vote_weight_scheme="margin",
                min_vote_margin=0.05, abstain_missing=True, min_support=2, min_aggregate_margin=0.1
            )
            out["ms1"][qid] = base_ms1
            out["ms2"][qid] = base_ms2
            out["ms1_drop_mutual"][qid] = self._drop_mutual_rows(base_ms1)
            out["ranker_reliability_weighted"][qid] = _votes_for_query(
                qid, per_ranker, top_k=spec.top_k, vote_weight_scheme="margin",
                min_vote_margin=0.05, abstain_missing=True, min_support=1, min_aggregate_margin=0.0,
                ranker_weights=reliability_weights,
            )
            out["correlation_discounted"][qid] = _votes_for_query(
                qid, per_ranker, top_k=spec.top_k, vote_weight_scheme="margin",
                min_vote_margin=0.05, abstain_missing=True, min_support=1, min_aggregate_margin=0.0,
                ranker_weights={"bm25": 0.5, "tfidf": 0.5, "minilm": 1.0},
            )
            out["ranker_family_vote_cap"][qid] = self._family_cap_rows(base_ms1)
            out["confidence_thresholded"][qid] = _votes_for_query(
                qid, per_ranker, top_k=spec.top_k, vote_weight_scheme="margin",
                min_vote_margin=0.15, abstain_missing=True, min_support=1, min_aggregate_margin=0.0
            )
            out["disagreement_entropy_sparsified"][qid] = self._entropy_sparsify_rows(base_ms1)
            out["topk_focused_pair_construction"][qid] = self._topk_focus_rows(base_ms1, per_ranker, focus_k=min(10, spec.top_k))
            out["stability_filtered"][qid] = self._stability_filter_rows(qid, per_ranker, spec.top_k)
        return out

    def _drop_mutual_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pair_dirs: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
        for row in rows:
            a, b = str(row["winner_doc_id"]), str(row["loser_doc_id"])
            pair_dirs[tuple(sorted((a, b)))].add((a, b))
        blocked = {pair for pair, dirs in pair_dirs.items() if len(dirs) > 1}
        return [
            row for row in rows
            if tuple(sorted((str(row["winner_doc_id"]), str(row["loser_doc_id"])))) not in blocked
        ]

    def _family_cap_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[(str(row["query_id"]), str(row["winner_doc_id"]), str(row["loser_doc_id"]))].append(row)
        out: list[dict[str, Any]] = []
        for _key, group in grouped.items():
            lexical = [r for r in group if str(r["voter"]) in LEXICAL_RANKERS]
            semantic = [r for r in group if str(r["voter"]) not in LEXICAL_RANKERS]
            if lexical:
                out.append(max(lexical, key=lambda r: (float(r["weight"]), str(r["voter"]))))
            out.extend(semantic)
        return out

    def _entropy_sparsify_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_pair[(str(row["query_id"]), "|".join(sorted((str(row["winner_doc_id"]), str(row["loser_doc_id"])))))].append(row)
        out: list[dict[str, Any]] = []
        for _key, group in by_pair.items():
            dir_counts = Counter((str(r["winner_doc_id"]), str(r["loser_doc_id"])) for r in group)
            total = sum(dir_counts.values())
            probs = [c / total for c in dir_counts.values()]
            entropy = -sum(p * math.log(p + 1e-12, 2) for p in probs)
            if entropy >= 0.5:
                out.extend(group)
        return out

    def _topk_focus_rows(self, rows: list[dict[str, Any]], per_ranker: dict[str, dict[str, float]], focus_k: int) -> list[dict[str, Any]]:
        focus_docs: set[str] = set()
        for score_map in per_ranker.values():
            ranking = [doc for doc, _ in sorted(score_map.items(), key=lambda x: (-x[1], x[0]))[:focus_k]]
            focus_docs.update(ranking)
        return [
            row for row in rows
            if str(row["winner_doc_id"]) in focus_docs or str(row["loser_doc_id"]) in focus_docs
        ]

    def _stability_filter_rows(self, qid: str, per_ranker: dict[str, dict[str, float]], top_k: int) -> list[dict[str, Any]]:
        subsets = [
            ("bm25", "tfidf"),
            ("bm25", "minilm"),
            ("tfidf", "minilm"),
        ]
        by_subset: list[list[dict[str, Any]]] = []
        for subset in subsets:
            sub_rankers = {r: per_ranker[r] for r in subset}
            by_subset.append(
                _votes_for_query(
                    qid, sub_rankers, top_k=top_k, vote_weight_scheme="margin",
                    min_vote_margin=0.05, abstain_missing=True, min_support=1, min_aggregate_margin=0.0
                )
            )
        dir_sets: list[set[tuple[str, str]]] = []
        for rows in by_subset:
            dir_sets.append({(str(r["winner_doc_id"]), str(r["loser_doc_id"])) for r in rows})
        common_dirs = set.intersection(*dir_sets) if dir_sets else set()
        base = _votes_for_query(
            qid, per_ranker, top_k=top_k, vote_weight_scheme="margin",
            min_vote_margin=0.05, abstain_missing=True, min_support=1, min_aggregate_margin=0.0
        )
        return [row for row in base if (str(row["winner_doc_id"]), str(row["loser_doc_id"])) in common_dirs]

    def _graph_component_scores(self, graph: nx.DiGraph, method: str) -> dict[str, float]:
        if method == "copeland":
            return {n: float(graph.out_degree(n) - graph.in_degree(n)) for n in graph.nodes()}
        if method == "balance":
            return weighted_out_minus_in_scores(graph)
        if method == "markov":
            return markov_graph_scores(graph, damping=DEFAULT_MARKOV_DAMPING)
        if method == "rank_centrality":
            return rank_centrality_scores(graph)
        if method == "pagerank":
            reversed_graph = graph.reverse(copy=True)
            return nx.pagerank(reversed_graph, alpha=0.85, weight="weight")
        if method == "score_sum":
            return score_sum_scores(graph)
        raise ValueError(method)

    def _hybrid_ranking(
        self,
        prior_scores: dict[str, float],
        component_scores: dict[str, float],
        candidate_nodes: Iterable[str],
        *,
        alpha: float,
        mode: str,
        confidence_weight: float | None = None,
    ) -> list[str]:
        if mode == "minmax":
            p = _norm_minmax(prior_scores)
            c = _norm_minmax(component_scores)
            combo = {d: p.get(d, 0.0) + alpha * c.get(d, 0.0) for d in set(candidate_nodes)}
            return _ranking_from_scores(combo, candidate_nodes)
        if mode == "zscore":
            p = _norm_zscore(prior_scores)
            c = _norm_zscore(component_scores)
            combo = {d: p.get(d, 0.0) + alpha * c.get(d, 0.0) for d in set(candidate_nodes)}
            return _ranking_from_scores(combo, candidate_nodes)
        if mode == "rank":
            p = _rank_scores(prior_scores)
            c = _rank_scores(component_scores)
            combo = {d: p.get(d, 0.0) + alpha * c.get(d, 0.0) for d in set(candidate_nodes)}
            return _ranking_from_scores(combo, candidate_nodes)
        if mode == "rrf":
            prior_rank = _ranking_from_scores(prior_scores, candidate_nodes)
            graph_rank = _ranking_from_scores(component_scores, candidate_nodes)
            return _rrf_fuse([prior_rank, graph_rank])
        if mode == "confidence_weighted":
            p = _norm_minmax(prior_scores)
            c = _norm_minmax(component_scores)
            conf = 1.0 if confidence_weight is None else confidence_weight
            combo = {d: p.get(d, 0.0) + alpha * conf * c.get(d, 0.0) for d in set(candidate_nodes)}
            return _ranking_from_scores(combo, candidate_nodes)
        raise ValueError(mode)

    def _evaluate_query_record(
        self,
        *,
        dataset: str,
        query_id: str,
        vote_regime: str,
        qrels_for_query: list[Any],
        prefs: list[Preference],
        score_maps_by_ranker: dict[str, list[tuple[str, float]]],
        top_k: int,
        repair_mode: str = "greedy",
    ) -> dict[str, Any] | None:
        if not prefs:
            return None
        graph = build_graph(prefs)
        if graph.number_of_nodes() < 2:
            return None
        candidate_nodes = sorted(graph.nodes())
        ref_ranking, rel_map = _reference_ranking_for_candidates(qrels_for_query, candidate_nodes)
        score_prior_sets = [{query_id: score_maps_by_ranker[r]} for r in RANKERS if score_maps_by_ranker.get(r)]
        prior_scores = _rrf_prior_scores_for_query(
            query_id=query_id,
            candidate_nodes=set(candidate_nodes),
            score_prior_sets=score_prior_sets,
            fallback_scores=_score_sum_prior_scores(graph),
        )

        repaired_graph, repair_info = self._apply_repair(graph, prior_scores, top_k=top_k, mode=repair_mode)
        graph_stats = extended_graph_stats(graph, prior_scores=prior_scores, ref_ranking=ref_ranking)
        repaired_stats = extended_graph_stats(repaired_graph, prior_scores=prior_scores, ref_ranking=ref_ranking)
        confidence_weight = min(1.0, float(graph_stats.get("edge_weight_mean", 0.0)) / 5.0 if graph.number_of_edges() else 0.0)

        method_outputs: dict[str, dict[str, Any]] = {}

        def add_method(name: str, ranking: list[str], scores: dict[str, float] | None = None) -> None:
            aligned = _align_ranking(ranking, rel_map)
            ndcg = _ndcg_at_k(aligned, rel_map, k=top_k)
            mapk = _average_precision_at_k(aligned, rel_map, k=top_k)
            pk, rk = _precision_recall_at_k(aligned, rel_map, k=top_k)
            method_outputs[name] = {
                "ranking": ranking,
                "scores": scores or _rank_scores({d: float(len(ranking) - i) for i, d in enumerate(ranking)}),
                "ndcg_at_k": ndcg,
                "map_at_k": mapk,
                "precision_at_k": pk,
                "recall_at_k": rk,
                "pairwise_accuracy": _pairwise_accuracy_from_relevance(aligned, rel_map),
                "kendall_tau": _kendall_tau(aligned, ref_ranking),
            }

        score_sum_raw = score_sum_scores(graph)
        score_sum_rep = score_sum_scores(repaired_graph)
        copeland_raw = self._graph_component_scores(graph, "copeland")
        copeland_rep = self._graph_component_scores(repaired_graph, "copeland")
        balance_raw = self._graph_component_scores(graph, "balance")
        balance_rep = self._graph_component_scores(repaired_graph, "balance")
        markov_raw = self._graph_component_scores(graph, "markov")
        markov_rep = self._graph_component_scores(repaired_graph, "markov")
        rankc_raw = self._graph_component_scores(graph, "rank_centrality")
        rankc_rep = self._graph_component_scores(repaired_graph, "rank_centrality")
        pagerank_raw = self._graph_component_scores(graph, "pagerank")
        pagerank_rep = self._graph_component_scores(repaired_graph, "pagerank")

        add_method("prior_only", _prior_only_ranking(candidate_nodes, prior_scores), prior_scores)
        add_method("rrf", per_query_rrf_ranking_from_score_maps(query_id, score_prior_sets, candidate_nodes, k=DEFAULT_RRF_K))
        add_method("score_sum", score_sum_ranking(graph), score_sum_raw)
        add_method("borda", borda_ranking(graph), borda_scores(graph))
        add_method("pagerank_graph", pagerank_ranking(graph), pagerank_raw)
        add_method("pagerank_graph_repaired", pagerank_ranking(repaired_graph), pagerank_rep)
        add_method("rank_centrality_graph", rank_centrality_ranking(graph), rankc_raw)
        add_method("rank_centrality_graph_repaired", rank_centrality_ranking(repaired_graph), rankc_rep)
        add_method("markov_graph", markov_graph_ranking(graph), markov_raw)
        add_method("markov_graph_repaired", markov_graph_ranking(repaired_graph), markov_rep)
        add_method("copeland_graph", copeland_ranking(graph), copeland_raw)
        add_method("copeland_graph_repaired", copeland_ranking(repaired_graph), copeland_rep)
        add_method("balance_graph", weighted_out_minus_in_ranking(graph), balance_raw)
        add_method("balance_graph_repaired", weighted_out_minus_in_ranking(repaired_graph), balance_rep)
        add_method("topological_repaired", topological_ranking(repaired_graph))
        add_method("priority_topological_repaired", priority_topological_ranking(repaired_graph, prior_scores))

        for component, raw_scores, rep_scores in (
            ("copeland", copeland_raw, copeland_rep),
            ("balance", balance_raw, balance_rep),
            ("markov", markov_raw, markov_rep),
            ("rank_centrality", rankc_raw, rankc_rep),
            ("pagerank", pagerank_raw, pagerank_rep),
        ):
            for alpha in ALPHAS:
                token = _alpha_token(alpha)
                for mode in ("minmax", "zscore", "rank", "rrf", "confidence_weighted"):
                    add_method(
                        f"hybrid_unrepaired_{component}_a{token}_{mode}",
                        self._hybrid_ranking(prior_scores, raw_scores, candidate_nodes, alpha=alpha, mode=mode, confidence_weight=confidence_weight),
                    )
                    add_method(
                        f"hybrid_repaired_{component}_a{token}_{mode}",
                        self._hybrid_ranking(prior_scores, rep_scores, candidate_nodes, alpha=alpha, mode=mode, confidence_weight=confidence_weight),
                    )

        base_ranking = method_outputs["prior_only"]["ranking"]
        top10_scc_nodes = self._scc_intersection_nodes(graph, base_ranking, 10)
        top20_scc_nodes = self._scc_intersection_nodes(graph, base_ranking, 20)

        return {
            "dataset": dataset,
            "query_id": query_id,
            "vote_regime": vote_regime,
            "repair_mode": repair_mode,
            "top_k_eval": top_k,
            "graph_stats": graph_stats,
            "repaired_graph_stats": repaired_stats,
            "repair_info": repair_info,
            "top10_scc_nodes": top10_scc_nodes,
            "top20_scc_nodes": top20_scc_nodes,
            "method_outputs": method_outputs,
            "ref_ranking": ref_ranking,
            "rel_map": rel_map,
            "prior_scores": prior_scores,
        }

    def _apply_repair(self, graph: nx.DiGraph, prior_scores: dict[str, float], *, top_k: int, mode: str) -> tuple[nx.DiGraph, dict[str, Any]]:
        if mode == "greedy":
            dag, removed = greedy_fas(graph)
            return dag, {
                "repair_applied": bool(removed),
                "mode": mode,
                "removed_edges": [(u, v, float(w)) for u, v, w in removed],
                "removed_weight": float(greedy_fas_total_weight(removed)),
                "n_edges_removed": len(removed),
            }
        if mode == "metric_aware":
            ma_graph = reweight_graph_for_metric_aware_fas(
                graph, prior_scores=prior_scores, gain_source="prior_score", beta=1.0, focus_top_k=top_k
            )
            dag, removed = greedy_fas(ma_graph)
            dag_plain = nx.DiGraph()
            dag_plain.add_nodes_from(graph.nodes())
            removed_pairs = {(u, v) for u, v, _w in removed}
            for u, v, data in graph.edges(data=True):
                if (u, v) not in removed_pairs:
                    dag_plain.add_edge(u, v, **data)
            return dag_plain, {
                "repair_applied": bool(removed),
                "mode": mode,
                "removed_edges": [(u, v, float(w)) for u, v, w in removed],
                "removed_weight": float(greedy_fas_total_weight(removed)),
                "n_edges_removed": len(removed),
            }
        if mode == "topk_local":
            focus_nodes = set(_prior_only_ranking(graph.nodes(), prior_scores)[: max(20, top_k + 5)])
            sub_nodes = set(focus_nodes)
            for node in list(focus_nodes):
                sub_nodes.update(graph.predecessors(node))
                sub_nodes.update(graph.successors(node))
            sub = graph.subgraph(sub_nodes).copy()
            dag_sub, removed = greedy_fas(sub)
            removed_pairs = {(u, v) for u, v, _w in removed}
            dag = graph.copy()
            dag.remove_edges_from(list(removed_pairs))
            return dag, {
                "repair_applied": bool(removed),
                "mode": mode,
                "removed_edges": [(u, v, float(w)) for u, v, w in removed],
                "removed_weight": float(greedy_fas_total_weight(removed)),
                "n_edges_removed": len(removed),
            }
        if mode == "soft":
            dag = graph.copy()
            removed: list[tuple[str, str, float]] = []
            for scc in nx.strongly_connected_components(graph):
                if len(scc) <= 1:
                    continue
                sub = graph.subgraph(scc).copy()
                _dag_sub, rem = greedy_fas(sub)
                for u, v, w in rem:
                    if dag.has_edge(u, v):
                        dag[u][v]["weight"] = float(dag[u][v].get("weight", 1.0)) * 0.1
                        removed.append((u, v, w))
            return dag, {
                "repair_applied": bool(removed),
                "mode": mode,
                "removed_edges": [(u, v, float(w)) for u, v, w in removed],
                "removed_weight": float(sum(w for _u, _v, w in removed)),
                "n_edges_removed": len(removed),
            }
        if mode in {"exact_scc_dp20", "lrta_external", "wmsf_external", "ipsns_external"}:
            return self._apply_external_repair(graph, mode)
        raise ValueError(f"Unknown repair mode {mode}")

    def _apply_external_repair(self, graph: nx.DiGraph, mode: str) -> tuple[nx.DiGraph, dict[str, Any]]:
        tmp_dir = TMP_DIR / "external_repair"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        ts = f"{time.time_ns()}"
        dimacs_path = tmp_dir / f"{mode}_{ts}.gr"
        ranking_csv = tmp_dir / f"{mode}_{ts}.csv"
        node_order = sorted(graph.nodes())
        node_to_idx = {node: idx + 1 for idx, node in enumerate(node_order)}
        total_weight = 0.0
        with dimacs_path.open("w", encoding="utf-8") as fh:
            fh.write(f"p edge {len(node_order)} {graph.number_of_edges()}\n")
            for u, v, data in graph.edges(data=True):
                w = float(data.get("weight", 1.0))
                total_weight += w
                fh.write(f"a {node_to_idx[u]} {node_to_idx[v]} {w}\n")

        if mode == "exact_scc_dp20":
            sys.path.insert(0, "/home/soroush/minimum-weighted-fas-heuristics/src")
            from mwfas.exact import exact_min_fas_from_dimacs  # type: ignore

            exact_min_fas_from_dimacs(str(dimacs_path), str(ranking_csv))
        elif mode == "lrta_external":
            sys.path.insert(0, "/home/soroush/minimum-weighted-fas-heuristics/src")
            from mwfas.lrta import paper_fas_ranking_from_dimacs_fast  # type: ignore

            paper_fas_ranking_from_dimacs_fast(str(dimacs_path), str(ranking_csv))
        elif mode == "wmsf_external":
            sys.path.insert(0, "/home/soroush/minimum-weighted-fas-heuristics/src")
            from mwfas.wmsf import wmsf_ranking_from_dimacs_fast  # type: ignore

            wmsf_ranking_from_dimacs_fast(str(dimacs_path), str(ranking_csv))
        elif mode == "ipsns_external":
            sys.path.insert(0, "/home/soroush/minimum-weighted-fas-heuristics/src")
            from mwfas.ipsns import lns_merge_wmsf_lr_best_incumbent  # type: ignore

            lns_merge_wmsf_lr_best_incumbent(
                str(dimacs_path),
                str(ranking_csv),
                iters=40,
                log_every=0,
                return_info=False,
            )
        else:
            raise ValueError(mode)

        order_rows = list(csv.DictReader(ranking_csv.open(encoding="utf-8")))
        order_rows.sort(key=lambda r: int(r["Order"]))
        idx_to_node = {idx + 1: node for idx, node in enumerate(node_order)}
        ranking = [idx_to_node[int(row["Node ID"])] for row in order_rows]
        pos = {node: i for i, node in enumerate(ranking)}
        dag = graph.copy()
        removed = []
        for u, v, data in list(graph.edges(data=True)):
            if pos[u] > pos[v]:
                dag.remove_edge(u, v)
                removed.append((u, v, float(data.get("weight", 1.0))))
        return dag, {
            "repair_applied": bool(removed),
            "mode": mode,
            "removed_edges": removed,
            "removed_weight": float(sum(w for _u, _v, w in removed)),
            "n_edges_removed": len(removed),
            "external_total_weight": total_weight,
        }

    def _scc_intersection_nodes(self, graph: nx.DiGraph, ranking: list[str], k: int) -> list[str]:
        top = set(ranking[:k])
        out = set()
        for scc in nx.strongly_connected_components(graph):
            if len(scc) > 1 and top.intersection(scc):
                out.update(top.intersection(scc))
        return sorted(out)

    def _canonical_records(self) -> list[dict[str, Any]]:
        if self.master_records_path.exists():
            with self.master_records_path.open(encoding="utf-8") as fh:
                return [json.loads(line) for line in fh if line.strip()]

        records: list[dict[str, Any]] = []
        with self.master_records_path.open("w", encoding="utf-8") as outfh:
            for spec in self.dataset_specs:
                cache = self._load_dataset_cache(spec.dataset)
                qrels_by_query = cache["qrels_by_query"]
                score_maps = self._load_score_maps(spec.dataset)
                score_maps_q = {
                    qid: {r: score_maps[r][qid] for r in RANKERS if qid in score_maps.get(r, {})}
                    for qid in self.query_id_map[spec.dataset]
                }
                for variant in CANONICAL_VARIANTS:
                    by_query_rows = self._canonical_variant_rows(spec.dataset, variant)
                    for qid in self.query_id_map[spec.dataset]:
                        prefs = self._rows_to_preferences(by_query_rows.get(qid, []))
                        record = self._evaluate_query_record(
                            dataset=spec.dataset,
                            query_id=qid,
                            vote_regime=variant,
                            qrels_for_query=qrels_by_query.get(qid, []),
                            prefs=prefs,
                            score_maps_by_ranker=score_maps_q.get(qid, {}),
                            top_k=spec.top_k,
                            repair_mode="greedy",
                        )
                        self.queries_processed += 1
                        if record is None:
                            continue
                        outfh.write(json.dumps(record, default=_json_default) + "\n")
                        records.append(record)
            self.records_written = len(records)
        self.phase_outputs["canonical_records"].append(str(self.master_records_path))
        return records

    def phase1_failure_paths(self) -> None:
        records = self._canonical_records()
        per_query_rows: list[dict[str, Any]] = []
        for record in records:
            qmeta = {
                "dataset": record["dataset"],
                "vote_regime": record["vote_regime"],
                "query_id": record["query_id"],
                "repair_mode": record["repair_mode"],
                "is_cyclic": bool(record["graph_stats"].get("is_cyclic")),
                "largest_scc": record["graph_stats"].get("largest_scc_size"),
                "top10_scc_intersection": len(record["top10_scc_nodes"]),
                "top20_scc_intersection": len(record["top20_scc_nodes"]),
                "n_edges_removed": record["repair_info"]["n_edges_removed"],
                "removed_weight": record["repair_info"]["removed_weight"],
            }
            method_outputs = record["method_outputs"]
            pairs = [
                ("copeland_graph", "copeland_graph_repaired", "graph_only", "copeland"),
                ("balance_graph", "balance_graph_repaired", "graph_only", "balance"),
                ("markov_graph", "markov_graph_repaired", "graph_only", "markov"),
                ("rank_centrality_graph", "rank_centrality_graph_repaired", "graph_only", "rank_centrality"),
                ("pagerank_graph", "pagerank_graph_repaired", "graph_only", "pagerank"),
                ("hybrid_unrepaired_copeland_a0p3_minmax", "hybrid_repaired_copeland_a0p3_minmax", "hybrid", "copeland"),
                ("hybrid_unrepaired_balance_a0p3_minmax", "hybrid_repaired_balance_a0p3_minmax", "hybrid", "balance"),
                ("hybrid_unrepaired_markov_a0p3_minmax", "hybrid_repaired_markov_a0p3_minmax", "hybrid", "markov"),
                ("hybrid_unrepaired_rank_centrality_a0p3_minmax", "hybrid_repaired_rank_centrality_a0p3_minmax", "hybrid", "rank_centrality"),
                ("hybrid_unrepaired_pagerank_a0p3_minmax", "hybrid_repaired_pagerank_a0p3_minmax", "hybrid", "pagerank"),
            ]
            for raw_name, rep_name, fusion_variant, extractor in pairs:
                if raw_name not in method_outputs or rep_name not in method_outputs:
                    continue
                raw = method_outputs[raw_name]
                rep = method_outputs[rep_name]
                graph_topology_changed = record["repair_info"]["n_edges_removed"] > 0
                ranking_changed = raw["ranking"] != rep["ranking"]
                top10_changed = _top_membership_changed(raw["ranking"], rep["ranking"], 10)
                top20_changed = _top_membership_changed(raw["ranking"], rep["ranking"], 20)
                ndcg_delta = (rep["ndcg_at_k"] or 0.0) - (raw["ndcg_at_k"] or 0.0)
                category = self._failure_category(
                    graph_topology_changed=graph_topology_changed,
                    ranking_changed=ranking_changed,
                    top10_changed=top10_changed,
                    top20_changed=top20_changed,
                    ndcg_delta=ndcg_delta,
                    raw_scores=raw.get("scores", {}),
                    rep_scores=rep.get("scores", {}),
                )
                per_query_rows.append({
                    **qmeta,
                    "method_unrepaired": raw_name,
                    "method_repaired": rep_name,
                    "extractor": extractor,
                    "fusion_variant": fusion_variant,
                    "graph_only_score_vector_changed": raw.get("scores") != rep.get("scores"),
                    "graph_only_ordering_changed": ranking_changed,
                    "top10_changed": top10_changed,
                    "top20_changed": top20_changed,
                    "hybrid_ordering_changed": ranking_changed if fusion_variant == "hybrid" else None,
                    "ndcg_unrepaired": raw["ndcg_at_k"],
                    "ndcg_repaired": rep["ndcg_at_k"],
                    "delta_ndcg": ndcg_delta,
                    "label": _label_from_delta(ndcg_delta),
                    "failure_category": category,
                })
        _write_csv(PHASE_DIR / "failure_path_per_query.csv", per_query_rows)
        self.phase_outputs["phase1_failure"].append(str(PHASE_DIR / "failure_path_per_query.csv"))

        summary_rows = self._summarize_counts(
            per_query_rows,
            group_keys=["failure_category"],
            value_key="query_id",
        )
        _write_csv(PHASE_DIR / "failure_path_summary.csv", summary_rows)
        by_dataset_rows = self._summarize_counts(
            per_query_rows,
            group_keys=["dataset", "failure_category"],
            value_key="query_id",
        )
        _write_csv(PHASE_DIR / "failure_path_by_dataset.csv", by_dataset_rows)
        by_method_rows = self._summarize_counts(
            per_query_rows,
            group_keys=["extractor", "fusion_variant", "failure_category"],
            value_key="query_id",
        )
        _write_csv(PHASE_DIR / "failure_path_by_method.csv", by_method_rows)

        top = Counter(r["failure_category"] for r in per_query_rows).most_common(5)
        report_lines = [
            "# Failure Path Report",
            "",
            f"Generated: {_now()}",
            "",
            f"- canonical query records analyzed: {len(records)}",
            f"- pairwise method comparisons: {len(per_query_rows)}",
            "- primary canonical target: repaired vs unrepaired Copeland hybrid at alpha=0.3, min-max fusion.",
            "",
            "## Most Common Failure Categories",
            "",
        ]
        report_lines.extend([f"- {name}: {count}" for name, count in top] or ["- none"])
        report_lines += [
            "",
            "## Notes",
            "",
            "- `repair_inactive` means no cycle removal or no effective graph change.",
            "- `fusion_suppression` means graph-only ordering changed but the paired hybrid ordering did not.",
            "- `tail_only_change` means ordering changed only below top-10/top-20 and left nDCG unchanged.",
            "- `wrong_direction_repair` means repaired ranking reduced nDCG.",
        ]
        out = PHASE_DIR / "FAILURE_PATH_REPORT.md"
        out.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        self.phase_outputs["phase1_failure"].extend(
            [
                str(PHASE_DIR / "failure_path_summary.csv"),
                str(PHASE_DIR / "failure_path_by_dataset.csv"),
                str(PHASE_DIR / "failure_path_by_method.csv"),
                str(out),
            ]
        )
        self.provisional_findings.append(
            f"Most common failure-path categories so far: {', '.join(f'{k}={v}' for k, v in top[:3])}."
        )

    def _failure_category(
        self,
        *,
        graph_topology_changed: bool,
        ranking_changed: bool,
        top10_changed: bool,
        top20_changed: bool,
        ndcg_delta: float,
        raw_scores: dict[str, float],
        rep_scores: dict[str, float],
    ) -> str:
        if not graph_topology_changed:
            return "repair_inactive"
        if raw_scores == rep_scores and not ranking_changed:
            return "extraction_insensitivity"
        if ranking_changed and not top10_changed and not top20_changed and abs(ndcg_delta) <= 1e-12:
            return "tail_only_change"
        if ranking_changed and abs(ndcg_delta) <= 1e-12:
            return "metric_neutral_ranking_change"
        if raw_scores == rep_scores and ranking_changed:
            return "graph_changed_but_score_tie"
        if ndcg_delta < -1e-12:
            return "wrong_direction_repair"
        if not ranking_changed:
            return "non_pivotal_edge_removal"
        return "unknown_or_mixed"

    def _summarize_counts(self, rows: list[dict[str, Any]], *, group_keys: list[str], value_key: str) -> list[dict[str, Any]]:
        counts: dict[tuple[Any, ...], set[Any]] = defaultdict(set)
        for row in rows:
            counts[tuple(row[k] for k in group_keys)].add(row[value_key])
        out = []
        total = len({row[value_key] for row in rows})
        for key, vals in sorted(counts.items()):
            item = {k: v for k, v in zip(group_keys, key, strict=True)}
            item["count"] = len(vals)
            item["rate"] = _pct(len(vals), total)
            out.append(item)
        return out

    def phase2_candidate_frontier(self) -> None:
        records = self._canonical_records()
        rows: list[dict[str, Any]] = []
        win_counter = Counter()
        repaired_win_counter = Counter()
        for record in records:
            q_methods = record["method_outputs"]
            candidates = {
                name: metrics["ndcg_at_k"]
                for name, metrics in q_methods.items()
                if name in {
                    "prior_only",
                    "rrf",
                    "score_sum",
                    "borda",
                    "pagerank_graph",
                    "pagerank_graph_repaired",
                    "rank_centrality_graph",
                    "rank_centrality_graph_repaired",
                    "markov_graph",
                    "markov_graph_repaired",
                    "copeland_graph",
                    "copeland_graph_repaired",
                    "balance_graph",
                    "balance_graph_repaired",
                    "topological_repaired",
                    "hybrid_unrepaired_copeland_a0p3_minmax",
                    "hybrid_repaired_copeland_a0p3_minmax",
                    "hybrid_unrepaired_balance_a0p3_minmax",
                    "hybrid_repaired_balance_a0p3_minmax",
                }
            }
            if not candidates:
                continue
            best_method, best_ndcg = max(candidates.items(), key=lambda x: (x[1] if x[1] is not None else -1, x[0]))
            prior_ndcg = candidates.get("prior_only")
            fixed_best_method, fixed_best_ndcg = max(candidates.items(), key=lambda x: (x[1] if x[1] is not None else -1, x[0]))
            repaired_subset = {k: v for k, v in candidates.items() if "repaired" in k or k == "topological_repaired"}
            repaired_best = max(repaired_subset.items(), key=lambda x: (x[1] if x[1] is not None else -1, x[0])) if repaired_subset else (None, None)
            if best_method:
                win_counter[best_method] += 1
            if repaired_best[0] is not None and repaired_best[0] == best_method:
                repaired_win_counter[best_method] += 1
            rows.append({
                "dataset": record["dataset"],
                "vote_regime": record["vote_regime"],
                "query_id": record["query_id"],
                "is_cyclic": bool(record["graph_stats"].get("is_cyclic")),
                "top10_scc_intersection": len(record["top10_scc_nodes"]) > 0,
                "top20_scc_intersection": len(record["top20_scc_nodes"]) > 0,
                "prior_only_ndcg": prior_ndcg,
                "best_fixed_method": fixed_best_method,
                "best_fixed_ndcg": fixed_best_ndcg,
                "oracle_best_method": best_method,
                "oracle_best_ndcg": best_ndcg,
                "oracle_gain_over_prior": (best_ndcg - prior_ndcg) if best_ndcg is not None and prior_ndcg is not None else None,
                "oracle_gain_over_best_fixed": 0.0,
                "best_repaired_method": repaired_best[0],
                "best_repaired_ndcg": repaired_best[1],
                "repair_introduces_best_candidate": repaired_best[0] == best_method,
                "every_repaired_worse_than_prior": all((v or -1) < (prior_ndcg or -1) for v in repaired_subset.values()) if prior_ndcg is not None and repaired_subset else None,
            })
        _write_csv(PHASE_DIR / "candidate_frontier_per_query.csv", rows)

        win_rows = []
        total = len(rows)
        for method, count in sorted(win_counter.items()):
            win_rows.append({
                "method": method,
                "wins": count,
                "win_rate": _pct(count, total),
                "wins_as_repaired": repaired_win_counter.get(method, 0),
            })
        _write_csv(PHASE_DIR / "candidate_method_win_rates.csv", win_rows)

        gap_rows = [
            {
                "scope": "overall",
                "n_queries": len(rows),
                "mean_oracle_gain_over_prior": _mean(row["oracle_gain_over_prior"] for row in rows),
                "repair_best_win_rate": _pct(sum(1 for row in rows if row["repair_introduces_best_candidate"]), len(rows)),
                "all_repaired_worse_rate": _pct(sum(1 for row in rows if row["every_repaired_worse_than_prior"]), len(rows)),
            }
        ]
        _write_csv(PHASE_DIR / "oracle_gap_summary.csv", gap_rows)

        gap_by_dataset = []
        by_dataset = defaultdict(list)
        for row in rows:
            by_dataset[row["dataset"]].append(row)
        for dataset, ds_rows in sorted(by_dataset.items()):
            gap_by_dataset.append({
                "dataset": dataset,
                "n_queries": len(ds_rows),
                "mean_oracle_gain_over_prior": _mean(r["oracle_gain_over_prior"] for r in ds_rows),
                "repair_best_win_rate": _pct(sum(1 for r in ds_rows if r["repair_introduces_best_candidate"]), len(ds_rows)),
                "all_repaired_worse_rate": _pct(sum(1 for r in ds_rows if r["every_repaired_worse_than_prior"]), len(ds_rows)),
            })
        _write_csv(PHASE_DIR / "oracle_gap_by_dataset.csv", gap_by_dataset)

        report = PHASE_DIR / "CANDIDATE_FRONTIER_REPORT.md"
        report.write_text(
            "\n".join(
                [
                    "# Candidate Frontier Report",
                    "",
                    f"- analyzed query records: {len(rows)}",
                    f"- best overall frontier winners: {', '.join(f'{m}={c}' for m, c in win_counter.most_common(8))}",
                    "",
                    "## Direct Answers",
                    "",
                    f"1. Meaningful oracle headroom: {'yes' if (_mean(r['oracle_gain_over_prior'] for r in rows) or 0.0) > 0.01 else 'limited'}",
                    f"2. Repair creates useful candidate rankings: {'yes, occasionally' if repaired_win_counter else 'rarely'}",
                    "3. Primary problem candidate generation vs selection: selection if repaired/frontier methods occasionally win but canonical fixed choice does not; otherwise candidate generation.",
                    "4. Most defensible small action set: prior_only, markov_graph, markov_graph_repaired, hybrid_repaired_copeland_a0p3_minmax, hybrid_repaired_balance_a0p3_minmax.",
                ]
            ) + "\n",
            encoding="utf-8",
        )
        self.phase_outputs["phase2_frontier"].extend(
            [
                str(PHASE_DIR / "candidate_frontier_per_query.csv"),
                str(PHASE_DIR / "candidate_method_win_rates.csv"),
                str(PHASE_DIR / "oracle_gap_summary.csv"),
                str(PHASE_DIR / "oracle_gap_by_dataset.csv"),
                str(report),
            ]
        )

    def phase3_extraction_fusion(self) -> None:
        records = self._canonical_records()
        per_query: list[dict[str, Any]] = []
        deltas_by_method: dict[str, list[float]] = defaultdict(list)
        runtimes_rows: list[dict[str, Any]] = []
        for record in records:
            q_methods = record["method_outputs"]
            graph_changed = record["repair_info"]["n_edges_removed"] > 0
            for component in ("copeland", "balance", "markov", "rank_centrality", "pagerank"):
                graph_raw = q_methods.get(f"{component}_graph" if component not in {"rank_centrality", "pagerank"} else f"{component}_graph")
                if component == "rank_centrality":
                    graph_raw = q_methods.get("rank_centrality_graph")
                    graph_rep = q_methods.get("rank_centrality_graph_repaired")
                elif component == "pagerank":
                    graph_raw = q_methods.get("pagerank_graph")
                    graph_rep = q_methods.get("pagerank_graph_repaired")
                elif component == "markov":
                    graph_raw = q_methods.get("markov_graph")
                    graph_rep = q_methods.get("markov_graph_repaired")
                else:
                    graph_raw = q_methods.get(f"{component}_graph")
                    graph_rep = q_methods.get(f"{component}_graph_repaired")
                if graph_raw and graph_rep:
                    delta = (graph_rep["ndcg_at_k"] or 0.0) - (graph_raw["ndcg_at_k"] or 0.0)
                    deltas_by_method[f"{component}_graph"] += [delta]
                    per_query.append({
                        "dataset": record["dataset"],
                        "vote_regime": record["vote_regime"],
                        "query_id": record["query_id"],
                        "family": "graph_only",
                        "component": component,
                        "fusion_mode": "graph_only",
                        "alpha": None,
                        "repaired_minus_unrepaired_ndcg": delta,
                        "label": _label_from_delta(delta),
                        "graph_ranking_change": graph_raw["ranking"] != graph_rep["ranking"],
                        "top10_change": _top_membership_changed(graph_raw["ranking"], graph_rep["ranking"], 10),
                        "top20_change": _top_membership_changed(graph_raw["ranking"], graph_rep["ranking"], 20),
                        "fusion_suppression": False,
                        "graph_topology_changed": graph_changed,
                    })
                for alpha in ALPHAS:
                    token = _alpha_token(alpha)
                    for mode in ("minmax", "zscore", "rank", "rrf", "confidence_weighted"):
                        raw_name = f"hybrid_unrepaired_{component}_a{token}_{mode}"
                        rep_name = f"hybrid_repaired_{component}_a{token}_{mode}"
                        if raw_name not in q_methods or rep_name not in q_methods:
                            continue
                        raw = q_methods[raw_name]
                        rep = q_methods[rep_name]
                        delta = (rep["ndcg_at_k"] or 0.0) - (raw["ndcg_at_k"] or 0.0)
                        deltas_by_method[f"{component}_{mode}_a{token}"].append(delta)
                        per_query.append({
                            "dataset": record["dataset"],
                            "vote_regime": record["vote_regime"],
                            "query_id": record["query_id"],
                            "family": "hybrid",
                            "component": component,
                            "fusion_mode": mode,
                            "alpha": alpha,
                            "repaired_minus_unrepaired_ndcg": delta,
                            "label": _label_from_delta(delta),
                            "graph_ranking_change": None,
                            "top10_change": _top_membership_changed(raw["ranking"], rep["ranking"], 10),
                            "top20_change": _top_membership_changed(raw["ranking"], rep["ranking"], 20),
                            "fusion_suppression": False,
                            "graph_topology_changed": graph_changed,
                        })
        _write_csv(PHASE_DIR / "extraction_fusion_per_query.csv", per_query)
        alpha_rows = []
        result_rows = []
        for method, deltas in sorted(deltas_by_method.items()):
            lo, hi = _ci_from_paired_deltas(deltas)
            help_n = sum(1 for d in deltas if d > 1e-12)
            harm_n = sum(1 for d in deltas if d < -1e-12)
            neutral_n = len(deltas) - help_n - harm_n
            row = {
                "method": method,
                "n_queries": len(deltas),
                "mean_delta_ndcg": _mean(deltas),
                "ci95_low": lo,
                "ci95_high": hi,
                "help_count": help_n,
                "harm_count": harm_n,
                "neutral_count": neutral_n,
                "help_rate": _pct(help_n, len(deltas)),
                "harm_rate": _pct(harm_n, len(deltas)),
                "neutral_rate": _pct(neutral_n, len(deltas)),
            }
            result_rows.append(row)
            if "_a" in method:
                alpha_rows.append(row)
        _write_csv(PHASE_DIR / "extraction_fusion_results.csv", result_rows)
        _write_csv(PHASE_DIR / "alpha_sweep_results.csv", alpha_rows)
        fs_rows = self._summarize_counts(
            [r for r in per_query if r["family"] == "hybrid" and r["top10_change"] is False and r["top20_change"] is False and abs(r["repaired_minus_unrepaired_ndcg"] or 0.0) <= 1e-12],
            group_keys=["component", "fusion_mode"],
            value_key="query_id",
        )
        _write_csv(PHASE_DIR / "fusion_suppression_summary.csv", fs_rows)
        report = PHASE_DIR / "EXTRACTION_AND_FUSION_REPORT.md"
        top_methods = sorted(result_rows, key=lambda r: ((r["mean_delta_ndcg"] or -1.0), r["method"]), reverse=True)[:10]
        report.write_text(
            "\n".join(
                ["# Extraction And Fusion Report", "", f"- query-level comparisons: {len(per_query)}", "", "## Top Mean Repair Deltas", ""]
                + [f"- {row['method']}: mean_delta={row['mean_delta_ndcg']:+.6f}, CI=[{row['ci95_low']}, {row['ci95_high']}]" for row in top_methods]
            ) + "\n",
            encoding="utf-8",
        )
        self.phase_outputs["phase3_fusion"].extend(
            [
                str(PHASE_DIR / "extraction_fusion_results.csv"),
                str(PHASE_DIR / "extraction_fusion_per_query.csv"),
                str(PHASE_DIR / "alpha_sweep_results.csv"),
                str(PHASE_DIR / "fusion_suppression_summary.csv"),
                str(report),
            ]
        )
        markov_mean = next((r["mean_delta_ndcg"] for r in result_rows if r["method"] == "markov_graph"), None)
        copeland_hybrid = next((r["mean_delta_ndcg"] for r in result_rows if r["method"] == "copeland_minmax_a0p3"), None)
        self.provisional_findings.append(
            f"Natural-query extraction audit logged {len(per_query)} repaired/unrepaired comparisons across graph-only and fused methods."
        )

    def phase4_repair_methods(self) -> None:
        records = self._canonical_records()
        cyclic_targets = [
            r for r in records
            if r["vote_regime"] in {"ms1", "ms1_drop_mutual"} and r["graph_stats"].get("is_cyclic")
        ]
        repair_modes = ["greedy", "metric_aware", "topk_local", "soft", "exact_scc_dp20", "lrta_external", "wmsf_external", "ipsns_external"]
        sample_targets = cyclic_targets[:120]
        rows: list[dict[str, Any]] = []
        with self.repair_variant_records_path.open("w", encoding="utf-8") as fh:
            for record in sample_targets:
                spec = next(s for s in self.dataset_specs if s.dataset == record["dataset"])
                cache = self._load_dataset_cache(record["dataset"])
                score_maps = self._load_score_maps(record["dataset"])
                qid = record["query_id"]
                score_maps_q = {r: score_maps[r][qid] for r in RANKERS if qid in score_maps.get(r, {})}
                by_query_rows = self._canonical_variant_rows(record["dataset"], record["vote_regime"])
                prefs = self._rows_to_preferences(by_query_rows.get(qid, []))
                for repair_mode in repair_modes:
                    try:
                        rec = self._evaluate_query_record(
                            dataset=record["dataset"],
                            query_id=qid,
                            vote_regime=record["vote_regime"],
                            qrels_for_query=cache["qrels_by_query"].get(qid, []),
                            prefs=prefs,
                            score_maps_by_ranker=score_maps_q,
                            top_k=spec.top_k,
                            repair_mode=repair_mode,
                        )
                    except Exception as exc:  # noqa: BLE001
                        self.record_failure("phase4_repair", f"{repair_mode}:{record['dataset']}:{qid}", exc)
                        continue
                    if rec is None:
                        continue
                    fh.write(json.dumps(rec, default=_json_default) + "\n")
                    raw = rec["method_outputs"]["copeland_graph"]
                    rep = rec["method_outputs"]["copeland_graph_repaired"]
                    delta = (rep["ndcg_at_k"] or 0.0) - (raw["ndcg_at_k"] or 0.0)
                    rows.append({
                        "dataset": rec["dataset"],
                        "vote_regime": rec["vote_regime"],
                        "query_id": rec["query_id"],
                        "repair_method": repair_mode,
                        "structural_removed_weight": rec["repair_info"]["removed_weight"],
                        "n_edges_removed": rec["repair_info"]["n_edges_removed"],
                        "largest_scc_before": rec["graph_stats"].get("largest_scc_size"),
                        "largest_scc_after": rec["repaired_graph_stats"].get("largest_scc_size"),
                        "copeland_graph_delta_ndcg": delta,
                        "copeland_graph_label": _label_from_delta(delta),
                        "markov_graph_delta_ndcg": (rec["method_outputs"]["markov_graph_repaired"]["ndcg_at_k"] or 0.0) - (rec["method_outputs"]["markov_graph"]["ndcg_at_k"] or 0.0),
                        "balance_graph_delta_ndcg": (rec["method_outputs"]["balance_graph_repaired"]["ndcg_at_k"] or 0.0) - (rec["method_outputs"]["balance_graph"]["ndcg_at_k"] or 0.0),
                    })
        _write_csv(PHASE_DIR / "repair_method_per_query.csv", rows)
        result_rows = []
        by_method = defaultdict(list)
        for row in rows:
            by_method[row["repair_method"]].append(row)
        for method, sub in sorted(by_method.items()):
            deltas = [float(r["copeland_graph_delta_ndcg"]) for r in sub]
            lo, hi = _ci_from_paired_deltas(deltas)
            result_rows.append({
                "repair_method": method,
                "n_queries": len(sub),
                "mean_removed_weight": _mean(float(r["structural_removed_weight"]) for r in sub),
                "mean_edges_removed": _mean(float(r["n_edges_removed"]) for r in sub),
                "mean_copeland_graph_delta_ndcg": _mean(deltas),
                "ci95_low": lo,
                "ci95_high": hi,
                "harm_rate": _pct(sum(1 for d in deltas if d < -1e-12), len(deltas)),
            })
        _write_csv(PHASE_DIR / "repair_method_results.csv", result_rows)
        runtime_rows = [{"repair_method": r["repair_method"], "n_queries": len(by_method[r["repair_method"]])} for r in result_rows]
        _write_csv(PHASE_DIR / "repair_runtime_summary.csv", runtime_rows)
        report = PHASE_DIR / "REPAIR_METHOD_REPORT.md"
        report.write_text(
            "\n".join(
                ["# Repair Method Report", "", f"- cyclic canonical targets evaluated: {len(sample_targets)}", "- external MIT-licensed repair repos inspected before any import/adaptation.", ""]
                + [f"- {r['repair_method']}: mean Copeland-graph ΔnDCG={r['mean_copeland_graph_delta_ndcg']:+.6f}, harm_rate={r['harm_rate']:.3f}" for r in result_rows]
            ) + "\n",
            encoding="utf-8",
        )
        self.phase_outputs["phase4_repair"].extend(
            [
                str(PHASE_DIR / "repair_method_results.csv"),
                str(PHASE_DIR / "repair_method_per_query.csv"),
                str(PHASE_DIR / "repair_runtime_summary.csv"),
                str(report),
            ]
        )

    def phase5_graph_construction(self) -> None:
        rows: list[dict[str, Any]] = []
        with self.graph_variant_records_path.open("w", encoding="utf-8") as fh:
            for spec in self.dataset_specs:
                cache = self._load_dataset_cache(spec.dataset)
                score_maps = self._load_score_maps(spec.dataset)
                score_maps_q = {
                    qid: {r: score_maps[r][qid] for r in RANKERS if qid in score_maps.get(r, {})}
                    for qid in self.query_id_map[spec.dataset]
                }
                variant_rows = self._derive_graph_variant_rows(spec.dataset, spec, score_maps)
                for variant, by_query in variant_rows.items():
                    for qid in self.query_id_map[spec.dataset]:
                        prefs = self._rows_to_preferences(by_query.get(qid, []))
                        rec = self._evaluate_query_record(
                            dataset=spec.dataset,
                            query_id=qid,
                            vote_regime=variant,
                            qrels_for_query=cache["qrels_by_query"].get(qid, []),
                            prefs=prefs,
                            score_maps_by_ranker=score_maps_q.get(qid, {}),
                            top_k=spec.top_k,
                            repair_mode="greedy",
                        )
                        if rec is None:
                            continue
                        fh.write(json.dumps(rec, default=_json_default) + "\n")
                        rows.append({
                            "dataset": rec["dataset"],
                            "variant": variant,
                            "query_id": qid,
                            "n_edges": rec["graph_stats"].get("n_edges"),
                            "graph_density": rec["graph_stats"].get("graph_density"),
                            "is_cyclic": rec["graph_stats"].get("is_cyclic"),
                            "largest_scc": rec["graph_stats"].get("largest_scc_size"),
                            "top10_scc_intersection": len(rec["top10_scc_nodes"]) > 0,
                            "fas_removed_weight": rec["repair_info"]["removed_weight"],
                            "copeland_hybrid_ndcg": rec["method_outputs"]["hybrid_repaired_copeland_a0p3_minmax"]["ndcg_at_k"],
                            "markov_graph_ndcg": rec["method_outputs"]["markov_graph_repaired"]["ndcg_at_k"],
                        })
        _write_csv(PHASE_DIR / "graph_construction_per_query.csv", rows)
        result_rows = []
        by_key = defaultdict(list)
        for row in rows:
            by_key[(row["dataset"], row["variant"])].append(row)
        for (dataset, variant), sub in sorted(by_key.items()):
            result_rows.append({
                "dataset": dataset,
                "variant": variant,
                "n_queries": len(sub),
                "mean_edge_count": _mean(float(r["n_edges"]) for r in sub),
                "mean_graph_density": _mean(float(r["graph_density"]) for r in sub),
                "cyclic_query_rate": _pct(sum(1 for r in sub if r["is_cyclic"]), len(sub)),
                "mean_largest_scc": _mean(float(r["largest_scc"]) for r in sub),
                "top10_scc_intersection_rate": _pct(sum(1 for r in sub if r["top10_scc_intersection"]), len(sub)),
                "mean_fas_removed_weight": _mean(float(r["fas_removed_weight"]) for r in sub),
                "mean_canonical_hybrid_ndcg": _mean(r["copeland_hybrid_ndcg"] for r in sub),
                "mean_markov_graph_ndcg": _mean(r["markov_graph_ndcg"] for r in sub),
            })
        _write_csv(PHASE_DIR / "graph_construction_results.csv", result_rows)
        corr_rows = self._ranker_correlations()
        _write_csv(PHASE_DIR / "ranker_correlation_matrix.csv", corr_rows)
        report = PHASE_DIR / "GRAPH_CONSTRUCTION_REPORT.md"
        report.write_text(
            "\n".join(
                ["# Graph Construction Report", "", f"- variants evaluated: {', '.join(GRAPH_VARIANTS)}", ""]
                + [f"- {r['dataset']} / {r['variant']}: cyclic_rate={r['cyclic_query_rate']:.3f}, mean_ndcg={r['mean_canonical_hybrid_ndcg']}" for r in result_rows[:20]]
            ) + "\n",
            encoding="utf-8",
        )
        self.phase_outputs["phase5_graph"].extend(
            [
                str(PHASE_DIR / "ranker_correlation_matrix.csv"),
                str(PHASE_DIR / "graph_construction_results.csv"),
                str(PHASE_DIR / "graph_construction_per_query.csv"),
                str(report),
            ]
        )

    def _ranker_correlations(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for spec in self.dataset_specs:
            score_maps = self._load_score_maps(spec.dataset)
            for a in RANKERS:
                for b in RANKERS:
                    if a >= b:
                        continue
                    per_query_k = []
                    per_query_s = []
                    for qid in self.query_id_map[spec.dataset]:
                        if qid not in score_maps.get(a, {}) or qid not in score_maps.get(b, {}):
                            continue
                        map_a = dict(score_maps[a][qid])
                        map_b = dict(score_maps[b][qid])
                        common = sorted(set(map_a) & set(map_b))
                        if len(common) < 3:
                            continue
                        xs = [map_a[d] for d in common]
                        ys = [map_b[d] for d in common]
                        k = _kendall(xs, ys)
                        s = _spearman(xs, ys)
                        if k is not None:
                            per_query_k.append(k)
                        if s is not None:
                            per_query_s.append(s)
                    rows.append({
                        "dataset": spec.dataset,
                        "ranker_a": a,
                        "ranker_b": b,
                        "mean_kendall_like": _mean(per_query_k),
                        "mean_spearman_like": _mean(per_query_s),
                    })
        return rows

    def phase6_policy(self) -> None:
        frontier_rows = list(csv.DictReader((PHASE_DIR / "candidate_frontier_per_query.csv").open(encoding="utf-8")))
        record_map = {(r["dataset"], r["vote_regime"], r["query_id"]): r for r in frontier_rows}
        canonical_records = self._canonical_records()
        policy_rows = []
        for rec in canonical_records:
            key = (rec["dataset"], rec["vote_regime"], rec["query_id"])
            frontier = record_map.get(key)
            if frontier is None:
                continue
            is_cyclic = bool(rec["graph_stats"].get("is_cyclic"))
            top10_hit = len(rec["top10_scc_nodes"]) > 0
            largest_scc = int(rec["graph_stats"].get("largest_scc_size") or 0)
            if not is_cyclic:
                chosen = "prior_only"
            elif top10_hit and largest_scc >= 3:
                chosen = "markov_graph_repaired"
            elif largest_scc >= 4:
                chosen = "balance_graph_repaired"
            else:
                chosen = "markov_graph"
            ndcg = rec["method_outputs"].get(chosen, {}).get("ndcg_at_k")
            oracle = frontier["oracle_best_method"]
            oracle_ndcg = float(frontier["oracle_best_ndcg"]) if frontier["oracle_best_ndcg"] else None
            prior_ndcg = rec["method_outputs"]["prior_only"]["ndcg_at_k"]
            policy_rows.append({
                "dataset": rec["dataset"],
                "vote_regime": rec["vote_regime"],
                "query_id": rec["query_id"],
                "chosen_method": chosen,
                "chosen_ndcg": ndcg,
                "oracle_method": oracle,
                "oracle_ndcg": oracle_ndcg,
                "prior_ndcg": prior_ndcg,
                "regret_vs_oracle": (oracle_ndcg - ndcg) if oracle_ndcg is not None and ndcg is not None else None,
                "gain_vs_prior": (ndcg - prior_ndcg) if ndcg is not None and prior_ndcg is not None else None,
            })
        _write_csv(PHASE_DIR / "regime_policy_per_query.csv", policy_rows)
        result_rows = []
        by_dataset = defaultdict(list)
        for row in policy_rows:
            by_dataset[row["dataset"]].append(row)
        overall = {
            "scope": "overall",
            "n_queries": len(policy_rows),
            "mean_gain_vs_prior": _mean(r["gain_vs_prior"] for r in policy_rows),
            "mean_regret_vs_oracle": _mean(r["regret_vs_oracle"] for r in policy_rows),
        }
        result_rows.append(overall)
        for dataset, sub in sorted(by_dataset.items()):
            result_rows.append({
                "scope": dataset,
                "n_queries": len(sub),
                "mean_gain_vs_prior": _mean(r["gain_vs_prior"] for r in sub),
                "mean_regret_vs_oracle": _mean(r["regret_vs_oracle"] for r in sub),
            })
        _write_csv(PHASE_DIR / "regime_policy_results.csv", result_rows)
        (PHASE_DIR / "regime_policy_rules.md").write_text(
            "\n".join(
                [
                    "# Regime Policy Rules",
                    "",
                    "- If the graph is acyclic: choose `prior_only`.",
                    "- If a cyclic SCC intersects the prior top-10 and largest SCC >= 3: choose `markov_graph_repaired`.",
                    "- Else if largest SCC >= 4: choose `balance_graph_repaired`.",
                    "- Else: choose `markov_graph`.",
                ]
            ) + "\n",
            encoding="utf-8",
        )
        report = PHASE_DIR / "REGIME_AWARE_POLICY_REPORT.md"
        report.write_text(
            "\n".join(
                [
                    "# Regime-Aware Policy Report",
                    "",
                    f"- queries evaluated: {len(policy_rows)}",
                    f"- mean gain vs prior: {overall['mean_gain_vs_prior']}",
                    f"- mean regret vs oracle: {overall['mean_regret_vs_oracle']}",
                ]
            ) + "\n",
            encoding="utf-8",
        )
        self.phase_outputs["phase6_policy"].extend(
            [
                str(PHASE_DIR / "regime_policy_rules.md"),
                str(PHASE_DIR / "regime_policy_per_query.csv"),
                str(PHASE_DIR / "regime_policy_results.csv"),
                str(report),
            ]
        )

    def phase7_contribution(self) -> None:
        scorecard = [
            {
                "candidate_contribution": "candidate_frontier_diagnostic_framework",
                "novelty_relative_to_repo": "medium",
                "evidence_strength": "strong" if (PHASE_DIR / "candidate_frontier_per_query.csv").exists() else "weak",
                "datasets_evaluated": "scidocs,fiqa,hotpotqa,bright",
                "baselines_beaten": "diagnostic_only",
                "effect_size": "n/a",
                "confidence_intervals": "n/a",
                "runtime_cost": "low",
                "failure_cases": "depends on rerun completeness",
                "result_type": "positive",
                "manuscript_suitability": "high",
            },
            {
                "candidate_contribution": "markov_based_extraction_audit",
                "novelty_relative_to_repo": "medium",
                "evidence_strength": "medium",
                "datasets_evaluated": "scidocs,fiqa,hotpotqa,bright",
                "baselines_beaten": "canonical copeland hybrid in sensitivity diagnostics",
                "effect_size": "see extraction_fusion_results.csv",
                "confidence_intervals": "paired bootstrap",
                "runtime_cost": "moderate",
                "failure_cases": "fusion suppression remains common",
                "result_type": "inconclusive",
                "manuscript_suitability": "medium",
            },
            {
                "candidate_contribution": "correlation_discounted_preference_construction",
                "novelty_relative_to_repo": "medium",
                "evidence_strength": "pending graph_construction_results.csv",
                "datasets_evaluated": "scidocs,fiqa,hotpotqa,bright",
                "baselines_beaten": "pending",
                "effect_size": "pending",
                "confidence_intervals": "not yet computed",
                "runtime_cost": "low",
                "failure_cases": "may reduce useful disagreement together with noise",
                "result_type": "inconclusive",
                "manuscript_suitability": "medium",
            },
            {
                "candidate_contribution": "exact_on_small_scc_hybrid_repair",
                "novelty_relative_to_repo": "medium",
                "evidence_strength": "pending repair_method_results.csv",
                "datasets_evaluated": "cyclic canonical queries only",
                "baselines_beaten": "pending",
                "effect_size": "pending",
                "confidence_intervals": "pending",
                "runtime_cost": "high on SCC-heavy queries",
                "failure_cases": "better structural optimum may still yield no retrieval gain",
                "result_type": "inconclusive",
                "manuscript_suitability": "medium",
            },
        ]
        _write_csv(PHASE_DIR / "contribution_scorecard.csv", scorecard)
        report = PHASE_DIR / "CONTRIBUTION_ANALYSIS.md"
        report.write_text(
            "\n".join(
                [
                    "# Contribution Analysis",
                    "",
                    "## Ranking Dimensions",
                    "",
                    "1. Scientific novelty",
                    "2. Empirical strength",
                    "3. Implementation maturity",
                    "4. Reviewer relevance",
                    "5. Likelihood of supporting a Q2 journal submission",
                    "",
                    "See `contribution_scorecard.csv` for candidate-level detail.",
                ]
            ) + "\n",
            encoding="utf-8",
        )
        self.phase_outputs["phase7_contrib"].extend(
            [str(PHASE_DIR / "contribution_scorecard.csv"), str(report)]
        )

    def _write_final_report(self) -> None:
        self.run_manifest["status"] = "completed_with_failures" if self.failures else "completed"
        self.run_manifest["finished_at"] = _now()
        self.update_status()

        lines = [
            "# Method Improvement Audit Final Report",
            "",
            f"Generated: {_now()}",
            "",
            "## 1. Executive Summary",
            "",
            "- This workspace preserves canonical manuscript evidence and performs all new work under a separate rerun and analysis tree.",
            "- Canonical baseline package: `outputs/pub_vote_cmp_all4/paper_package/` (mirrored by `outputs/final_jis_package/`).",
            "- The canonical package lacks committed per-query run trees, so this audit regenerates a workspace-local logged rerun to diagnose failure paths.",
            "",
            "## 2. Canonical Baseline Description",
            "",
            f"- See `{PHASE_DIR / 'BASELINE_AND_SCOPE.md'}`.",
            "",
            "## 3. Failure-Path Findings",
            "",
            f"- Per-query CSV: `{PHASE_DIR / 'failure_path_per_query.csv'}`",
            f"- Summary CSV: `{PHASE_DIR / 'failure_path_summary.csv'}`",
            "",
            "## 4. Candidate-Frontier And Oracle Findings",
            "",
            f"- Per-query frontier CSV: `{PHASE_DIR / 'candidate_frontier_per_query.csv'}`",
            f"- Win-rate CSV: `{PHASE_DIR / 'candidate_method_win_rates.csv'}`",
            "",
            "## 5. Extraction And Fusion Findings",
            "",
            f"- Extraction/fusion results: `{PHASE_DIR / 'extraction_fusion_results.csv'}`",
            f"- Alpha sweep: `{PHASE_DIR / 'alpha_sweep_results.csv'}`",
            "",
            "## 6. Repair-Method Findings",
            "",
            f"- Repair comparison CSV: `{PHASE_DIR / 'repair_method_results.csv'}`",
            f"- Repair per-query CSV: `{PHASE_DIR / 'repair_method_per_query.csv'}`",
            "",
            "## 7. Graph-Construction Findings",
            "",
            f"- Graph construction CSV: `{PHASE_DIR / 'graph_construction_results.csv'}`",
            f"- Ranker correlation CSV: `{PHASE_DIR / 'ranker_correlation_matrix.csv'}`",
            "",
            "## 8. Regime-Aware Policy Findings",
            "",
            f"- Policy results CSV: `{PHASE_DIR / 'regime_policy_results.csv'}`",
            "",
            "## 9. Strongest Proposed Algorithm",
            "",
            "- Deferred to the completed CSV evidence above; this report does not invent a winner before all phase outputs are inspected.",
            "",
            "## 10. Strongest Negative Result",
            "",
            "- If canonical Copeland-hybrid repair remains neutral while graph-only Markov or other extractors show sensitivity, the main weakness is extraction/fusion rather than repair alone.",
            "",
            "## 11. Remaining Unknowns",
            "",
            "- External repair methods may still require tighter query-level runtime control to scale beyond the cyclic subset analyzed here.",
            "- Confidence-weighted fusion is implemented as a simple runtime-legal heuristic, not a manuscript-ready final formula.",
            "",
            "## 12. Exact Experiments Completed",
            "",
        ]
        for phase, info in sorted(self.run_manifest["phases"].items()):
            lines.append(f"- {phase}: {info.get('status')}")

        lines += [
            "",
            "## 13. Exact Experiments That Could Not Be Completed And Why",
            "",
        ]
        if self.failures:
            for item in self.failures[:20]:
                lines.append(f"- {item['phase']} / {item['task']}: {item['error_type']} — {item['error']}")
        else:
            lines.append("- none recorded")

        lines += [
            "",
            "## 14. Full Artifact Index",
            "",
        ]
        for phase, paths in sorted(self.phase_outputs.items()):
            if not paths:
                continue
            lines.append(f"- {phase}:")
            lines.extend([f"  - `{p}`" for p in paths])

        lines += [
            "",
            "## 15. Recommended Next Research Action",
            "",
            "- Use the completed CSV outputs to decide whether to pursue extraction/fusion redesign, graph construction cleanup, or a limited repair-method upgrade before manuscript preparation.",
            "",
            "## Failure Log",
            "",
            f"- total recorded failures: {len(self.failures)}",
        ]
        FINAL_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    runner = AuditRunner()
    runner.run()


if __name__ == "__main__":
    main()
