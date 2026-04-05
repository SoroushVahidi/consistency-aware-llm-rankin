"""
run_small_llm_pairwise_experiment.py
====================================

Lightweight SciDocs-focused LLM pairwise preference run to test external validity.

- Checks LLM API availability (no secrets printed).
- Runs a small pairwise experiment on a sampled query subset (default: SciDocs).
- Compares prior vs unrepaired vs repaired rankings on nDCG/Recall/MRR.
- Writes a manifest, per-query CSV, summary CSV, and Markdown report.

Usage (once OPENAI_API_KEY or GEMINI_API_KEY is configured and openai/google-genai
packages are installed):

    python scripts/run_small_llm_pairwise_experiment.py \
        --dataset scidocs --provider openai --model gpt-4o-mini \
        --max-queries 10 --top-k 8 --output-dir outputs/llm_pairwise_small/scidocs_openai
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from consistency_ranker.baseline_ranking import score_sum_ranking
from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.data.dataset_registry import get_config
from consistency_ranker.data.query_ids import eligible_query_ids, has_usable_eval_labels
from consistency_ranker.data.unified_loader import load_dataset_splits
from consistency_ranker.evaluation import ndcg_at_k, recall_at_k
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas
from consistency_ranker.pairwise_prefs import Preference
from consistency_ranker.utils.llm_api_status import detect_providers
from rerankers.common import BudgetTracker, write_pairwise_file
from rerankers.llm_pairwise import LLMCallStats, PairwiseConfig, collect_all_pairs


def _sample_queries(qrels, max_queries: int, seed: int) -> list[str]:
    eligible = eligible_query_ids(qrels)
    rng = random.Random(seed)
    rng.shuffle(eligible)
    return eligible[:max_queries]


def _probe_model(provider: str, model: str) -> tuple[bool, str]:
    """Run the smallest safe sanity call for a specific provider/model."""
    if provider == "openai":
        try:
            import openai  # type: ignore

            client = openai.OpenAI()
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Reply with a single letter: A"}],
                temperature=0.0,
                max_tokens=1,
            )
            text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
            return True, f"success ({text[:20]})"
        except Exception as exc:
            return False, str(exc)
    if provider == "gemini":
        try:
            import os

            from google import genai  # type: ignore
            from google.genai import types  # type: ignore

            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model=model,
                contents="Reply with a single letter: A",
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=1,
                ),
            )
            text = (resp.text or "").strip()
            return True, f"success ({text[:20]})"
        except Exception as exc:
            return False, str(exc)
    return False, f"unsupported provider: {provider}"


def _build_candidate_pool(
    dataset: str,
    max_queries: int,
    top_k: int,
    seed: int,
) -> list[tuple[str, str, list[tuple[str, str]], dict[str, int]]]:
    cfg = get_config(dataset)
    queries, documents, qrels = load_dataset_splits(cfg)

    if not queries or not documents or not qrels:
        raise RuntimeError(
            f"Dataset '{dataset}' is empty or not prepared. "
            "Run scripts/download_datasets.py and scripts/prepare_datasets.py first."
        )

    qrels_by_q: dict[str, list] = defaultdict(list)
    for entry in qrels:
        qrels_by_q[entry.query_id].append(entry)
    docs_by_id = {getattr(d, "doc_id", str(i)): d for i, d in enumerate(documents)}
    query_by_id = {q.query_id: q for q in queries}

    sampled = _sample_queries(qrels, max_queries=max_queries, seed=seed)
    pool: list[tuple[str, str, list[tuple[str, str]], dict[str, int]]] = []
    for qid in sampled:
        q = query_by_id.get(qid)
        qr = qrels_by_q.get(qid, [])
        if q is None or not has_usable_eval_labels(qr):
            continue
        entries = sorted(qr, key=lambda e: (-e.relevance, e.doc_id))[:top_k]
        candidates: list[tuple[str, str]] = []
        rel_map: dict[str, int] = {}
        for e in entries:
            doc = docs_by_id.get(e.doc_id)
            if doc is None:
                continue
            text = getattr(doc, "text", "") or getattr(doc, "title", "") or str(doc)
            candidates.append((e.doc_id, text))
            rel_map[e.doc_id] = max(rel_map.get(e.doc_id, 0), int(e.relevance))
        if len(candidates) >= 2:
            qtext = getattr(q, "text", "") or getattr(q, "title", "") or str(q)
            pool.append((qid, qtext, candidates, rel_map))
    return pool


def _copeland_from_graph(graph) -> list[str]:
    scores = {n: graph.out_degree(n) - graph.in_degree(n) for n in graph.nodes()}
    return sorted(scores, key=lambda n: (-scores[n], n))


def _backward_edge_weight(graph, ranking: Iterable[str]) -> float:
    pos = {n: i for i, n in enumerate(ranking)}
    return sum(
        d.get("weight", 1.0)
        for u, v, d in graph.edges(data=True)
        if pos.get(u) is not None and pos.get(v) is not None and pos[v] < pos[u]
    )


def _evaluate_rankings(
    graph,
    dag,
    rel_map: dict[str, int],
    rankings: dict[str, list[str]],
    k: int,
) -> list[dict]:
    relevant = {d for d, r in rel_map.items() if r > 0}
    rows = []
    for name, ranking in rankings.items():
        ndcg = ndcg_at_k(ranking, rel_map, k=k)
        rec = recall_at_k(ranking, relevant, k=k)
        bew = _backward_edge_weight(graph if "unrepaired" in name else dag, ranking)
        rows.append(
            {
                "method": name,
                "ndcg_at_k": ndcg,
                "recall_at_k": rec,
                "bew": bew,
            }
        )
    return rows


def _write_capability_report(
    output_dir: Path,
    statuses: dict,
    probes: dict[str, dict[str, str | bool]],
    selected: str | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "selected_provider": selected,
        "providers": {k: asdict(v) for k, v in statuses.items()},
        "model_probes": probes,
    }
    (output_dir / "capability_report.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# LLM API Capability Check",
        "",
        f"- Selected provider: **{selected or 'none'}**",
    ]
    for name, res in statuses.items():
        probe = probes.get(name, {})
        lines.append(
            f"- {name}: env_present={res.env_present} import_ok={res.import_ok} "
            f"probe_ok={res.probe_ok}; model_tested={probe.get('model', 'n/a')} "
            f"model_probe_ok={probe.get('ok', False)} — {probe.get('message', res.message)}"
        )
    (output_dir / "capability_report.md").write_text("\n".join(lines), encoding="utf-8")


def _summarize(rows: list[dict]) -> list[dict]:
    by_method: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_method[r["method"]].append(r)

    summary = []
    for name, vals in by_method.items():
        n = len(vals)
        def _avg(key: str) -> float | None:
            data = [v[key] for v in vals if v.get(key) is not None]
            return sum(data) / len(data) if data else None

        summary.append(
            {
                "method": name,
                "n_queries": n,
                "ndcg_mean": _avg("ndcg_at_k"),
                "recall_mean": _avg("recall_at_k"),
                "bew_mean": _avg("bew"),
            }
        )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Small LLM pairwise preference experiment.")
    parser.add_argument("--dataset", default="scidocs")
    parser.add_argument("--provider", choices=["openai", "gemini", "auto"], default="auto")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--max-queries", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--probe", action="store_true", help="Attempt live model listing probe.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Where to write outputs (default: outputs/llm_pairwise_small/<dataset>_<provider>)",
    )
    parser.add_argument(
        "--call-delay",
        type=float,
        default=0.0,
        help="Seconds to sleep between API calls.",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=None,
        help="Optional hard cap on API calls.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use deterministic mock judgments (no API calls).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_dir = args.output_dir
    if output_dir is None:
        output_dir = Path("outputs") / "llm_pairwise_small" / f"{args.dataset}_{args.provider}"
    output_dir.mkdir(parents=True, exist_ok=True)

    statuses = detect_providers(probe=args.probe)
    provider_models = {
        "openai": args.model if args.provider == "openai" else "gpt-4o-mini",
        "gemini": args.model if args.provider == "gemini" else "gemini-2.5-flash",
    }
    probes: dict[str, dict[str, str | bool]] = {}
    for provider_name in ("openai", "gemini"):
        st = statuses[provider_name]
        model_name = provider_models[provider_name]
        if st.env_present and st.import_ok:
            ok, message = _probe_model(provider_name, model_name)
        else:
            ok, message = False, st.message
        probes[provider_name] = {
            "model": model_name,
            "ok": ok,
            "message": message,
        }

    selected_provider = args.provider
    if args.provider == "auto":
        selected_provider = None
        for name in ("openai", "gemini"):
            if probes.get(name, {}).get("ok", False):
                selected_provider = name
                break
        _write_capability_report(output_dir, statuses, probes, selected_provider)
        if selected_provider is None:
            print("[capability] No working provider found (OpenAI/Gemini).")
            print(f"[capability] See {output_dir/'capability_report.md'}")
            return 1
    else:
        _write_capability_report(output_dir, statuses, probes, selected_provider)
        selected_probe = probes[selected_provider]
        if not bool(selected_probe.get("ok", False)):
            print(
                f"[capability] Provider '{selected_provider}' failed model sanity call: "
                f"{selected_probe.get('message', 'unknown error')}"
            )
            print(f"[capability] See {output_dir/'capability_report.md'}")
            return 1

    selected_model = args.model if args.provider != "auto" else str(
        probes[selected_provider]["model"]
    )

    print(
        f"[setup] dataset={args.dataset} provider={selected_provider} model={selected_model}"
    )
    print(f"[setup] output_dir={output_dir}")

    pool = _build_candidate_pool(
        args.dataset,
        max_queries=args.max_queries,
        top_k=args.top_k,
        seed=args.seed,
    )
    if not pool:
        raise RuntimeError("No eligible queries found after filtering; cannot proceed.")

    cache_dir = output_dir / "judgment_cache"
    stats = LLMCallStats()
    budget = BudgetTracker(max_calls=args.max_calls)

    config = PairwiseConfig(
        model=selected_model,
        provider=selected_provider,
        dry_run=args.dry_run,
        cache_dir=cache_dir,
        call_delay=args.call_delay,
        max_calls=args.max_calls,
        debias_position=False,
        seed=args.seed,
    )

    all_prefs: dict[str, list[tuple[str, str, float]]] = {}
    metadata: dict[str, dict] = {}

    print(
        f"[judge] collecting pairwise preferences for {len(pool)} queries "
        f"(dry_run={args.dry_run})"
    )
    for idx, (qid, qtext, candidates, _) in enumerate(pool, 1):
        try:
            pairs, meta = collect_all_pairs(qid, qtext, candidates, config, stats=stats)
        except Exception as exc:
            print(f"[judge] error on query {qid}: {exc}")
            break
        all_prefs[qid] = pairs
        meta["n_pairs"] = len(pairs)
        metadata[qid] = meta
        print(
            f"  [{idx}/{len(pool)}] {qid[:12]}… pairs={len(pairs)} "
            f"api_calls={stats.api_calls} cache_hits={stats.cache_hits}"
        )
        if budget.budget_exhausted:
            print("  budget exhausted; stopping early")
            break

    if not all_prefs:
        print("[judge] no judgments collected; exiting.")
        return 1

    write_pairwise_file(all_prefs, output_dir / "pairwise.jsonl")

    print("[eval] scoring prior vs unrepaired vs repaired …")
    rows: list[dict] = []
    for qid, qtext, candidates, rel_map in pool:
        prefs = all_prefs.get(qid)
        if not prefs:
            continue

        graph = build_graph(
            [Preference(winner=w, loser=loser, weight=wt) for w, loser, wt in prefs]
        )
        dag, _ = greedy_fas(graph)
        cyclic = has_cycle(graph)

        rankings = {
            "prior_score_sum": score_sum_ranking(graph),
            "unrepaired_copeland": _copeland_from_graph(graph),
            "repaired_copeland": _copeland_from_graph(dag),
        }
        eval_rows = _evaluate_rankings(graph, dag, rel_map, rankings, k=args.top_k)
        for r in eval_rows:
            r.update({"dataset": args.dataset, "query_id": qid, "is_cyclic": cyclic})
        rows.extend(eval_rows)

    per_query_csv = output_dir / "per_query_metrics.csv"
    if rows:
        with per_query_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "dataset",
                    "query_id",
                    "method",
                    "is_cyclic",
                    "ndcg_at_k",
                    "recall_at_k",
                    "bew",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

    summary = _summarize(rows)
    summary_csv = output_dir / "summary.csv"
    if summary:
        with summary_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["method", "n_queries", "ndcg_mean", "recall_mean", "bew_mean"],
            )
            writer.writeheader()
            writer.writerows(summary)

    manifest = {
        "dataset": args.dataset,
        "provider": selected_provider,
        "model": selected_model,
        "max_queries": args.max_queries,
        "top_k": args.top_k,
        "seed": args.seed,
        "dry_run": args.dry_run,
        "probe": args.probe,
        "api_status": {k: asdict(v) for k, v in statuses.items()},
        "model_probes": probes,
        "n_queries_collected": len(all_prefs),
        "api_calls": stats.api_calls,
        "cache_hits": stats.cache_hits,
        "judgment_cache": str(cache_dir),
        "manifest_path": str(output_dir / "manifest.json"),
        "per_query_csv": str(per_query_csv),
        "summary_csv": str(summary_csv),
    }
    prompt_text = config.prompt_template_path.read_text(encoding="utf-8")
    manifest["prompt_template"] = prompt_text
    manifest["prompt_template_sha256"] = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    manifest["timestamp_utc"] = datetime.now(UTC).isoformat()
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        git_commit = "unknown"
    manifest["git_commit"] = git_commit
    manifest["query_ids_collected"] = sorted(all_prefs.keys())
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        f"# Small LLM Pairwise Experiment — {args.dataset}",
        "",
        f"- Provider: **{selected_provider}**",
        f"- Model: **{selected_model}**",
        f"- Queries attempted: {len(pool)}",
        f"- Queries collected: {len(all_prefs)}",
        f"- top_k: {args.top_k}",
        f"- dry_run: {args.dry_run}",
        f"- API calls: {stats.api_calls}",
        f"- Cache hits: {stats.cache_hits}",
        "",
        "## Provider capability",
    ]
    for name, res in statuses.items():
        probe = probes.get(name, {})
        lines.append(
            f"- {name}: env_present={res.env_present} import_ok={res.import_ok} "
            f"probe_ok={res.probe_ok}; model_tested={probe.get('model', 'n/a')} "
            f"model_probe_ok={probe.get('ok', False)} — {probe.get('message', res.message)}"
        )
    lines.append("")

    if summary:
        lines.append("## Summary (nDCG/Recall)")
        lines.append("")
        lines.append("| Method | nDCG | Recall | BEW |")
        lines.append("|--------|------|--------|-----|")
        for s in summary:
            ndcg = f"{s['ndcg_mean']:.4f}" if s["ndcg_mean"] is not None else "—"
            rec = f"{s['recall_mean']:.4f}" if s["recall_mean"] is not None else "—"
            bew = f"{s['bew_mean']:.2f}" if s["bew_mean"] is not None else "—"
            lines.append(f"| {s['method']} | {ndcg} | {rec} | {bew} |")
        lines.append("")
        if {"unrepaired_copeland", "repaired_copeland"}.issubset({s["method"] for s in summary}):
            u = next(s for s in summary if s["method"] == "unrepaired_copeland")
            r = next(s for s in summary if s["method"] == "repaired_copeland")
            delta = (r["ndcg_mean"] or 0.0) - (u["ndcg_mean"] or 0.0)
            lines.append(f"ΔnDCG (repaired - unrepaired): {delta:+.4f}")
    else:
        lines.append("No summary metrics available.")

    (output_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[done] wrote outputs under {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
