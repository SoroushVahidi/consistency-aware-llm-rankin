#!/usr/bin/env python3
"""
Multi-provider LLM pairwise robustness experiment (staged).

Stages:
  0  Provider smoke tests (1 call each; live only with --allow-provider-calls)
  1  Balanced pilot on a fixed manifest
  2  Controlled main expansion (optional, budget-gated)
  3  Robustness subset: prompts × orientations × repeats

Never overwrites existing judgment caches. New records go under a versioned
report directory.

Fail-closed modes (exactly one required):
  --cache-only              inventory / analyze existing caches; no network
  --dry-run                 simulate provider calls (no network)
  --allow-provider-calls    live provider traffic (may incur cost)

Examples:
  PYTHONPATH=src python scripts/run_multi_provider_llm_robustness.py \\
      --stage 0 --cache-only
  PYTHONPATH=src python scripts/run_multi_provider_llm_robustness.py \\
      --stage 1 --dry-run
  PYTHONPATH=src python scripts/run_multi_provider_llm_robustness.py \\
      --stage 1 --allow-provider-calls
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from consistency_ranker.evaluation import ndcg_at_k
from consistency_ranker.experiment_cli import (
    assert_offline_or_allowed,
    ensure_output_dir,
    utc_stamp,
    write_run_manifest,
)
from consistency_ranker.multi_provider_eval.audit_inventory import inventory_judgment_caches
from consistency_ranker.multi_provider_eval.cache import ProvenanceJudgmentStore
from consistency_ranker.multi_provider_eval.ensemble import (
    agreement_only_edges,
    confidence_weighted_vote,
    majority_across_models,
)
from consistency_ranker.multi_provider_eval.graph_eval import (
    evaluate_preference_graph,
    records_to_preferences,
)
from consistency_ranker.multi_provider_eval.manifest import (
    estimate_call_budget,
    write_manifest,
)
from consistency_ranker.multi_provider_eval.orientation import aggregate_orientation_pair
from consistency_ranker.multi_provider_eval.providers import (
    TARGET_PROVIDERS,
    MultiProviderJudge,
    discover_provider_models,
    provider_credential_audit,
    smoke_test_providers,
)
from consistency_ranker.multi_provider_eval.spending import SpendingCeiling

REPO_ROOT = Path(__file__).resolve().parents[1]


def _utc() -> str:
    return utc_stamp()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row:
            if k not in seen:
                seen.add(k)
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _build_manifest_from_existing_cache(
    *,
    cache_path: Path,
    queries_path: Path,
    documents_path: Path,
    n_queries: int,
    n_docs: int,
    seed: int,
    max_doc_chars: int,
) -> dict[str, Any]:
    """Sample pilot pairs from an existing OpenAI cache without using qrels."""
    import hashlib
    import random

    judgments = _load_jsonl(cache_path)
    by_q: dict[str, set[str]] = defaultdict(set)
    for rec in judgments:
        qid = str(rec.get("query_id", ""))
        for d in rec.get("doc_ids") or []:
            by_q[qid].add(str(d))
        for k in ("winner", "loser", "winner_doc_id", "loser_doc_id"):
            if rec.get(k):
                by_q[qid].add(str(rec[k]))
    eligible = sorted(qid for qid, docs in by_q.items() if len(docs) >= n_docs)
    h = hashlib.sha256(f"{seed}::pilot_manifest".encode()).hexdigest()
    rng = random.Random(int(h[:16], 16))
    chosen_q = sorted(rng.sample(eligible, min(n_queries, len(eligible))))

    qtext = {
        str(r["query_id"]): str(r.get("text") or r.get("query") or "")
        for r in _load_jsonl(queries_path)
    }
    dtext = {
        str(r["doc_id"]): str(r.get("text") or r.get("contents") or r.get("title") or "")
        for r in _load_jsonl(documents_path)
    }

    items = []
    for qid in chosen_q:
        docs_ids = sorted(by_q[qid])
        rng_q = random.Random(int(hashlib.sha256(f"{seed}::{qid}".encode()).hexdigest()[:16], 16))
        pick = sorted(rng_q.sample(docs_ids, n_docs))
        docs = []
        for did in pick:
            full = dtext.get(did, "")
            docs.append(
                {
                    "doc_id": did,
                    "text": full[:max_doc_chars],
                    "truncated": len(full) > max_doc_chars,
                }
            )
        pairs = []
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                pairs.append({"doc_a_id": docs[i]["doc_id"], "doc_b_id": docs[j]["doc_id"]})
        items.append(
            {
                "dataset": "scidocs",
                "query_id": qid,
                "query_text": qtext.get(qid, ""),
                "documents": docs,
                "pairs": pairs,
            }
        )
    n_pairs = sum(len(it["pairs"]) for it in items)
    return {
        "manifest_version": "pilot_v1_from_existing_cache",
        "seed": seed,
        "dataset": "scidocs",
        "source_cache": str(cache_path.relative_to(REPO_ROOT)),
        "n_queries": len(items),
        "n_docs_per_query": n_docs,
        "n_unordered_pairs": n_pairs,
        "max_doc_chars": max_doc_chars,
        "selection_note": (
            "Query/doc IDs sampled from existing OpenAI SciDocs judgment cache; "
            "qrels not used for selection (only for optional post-hoc metrics)."
        ),
        "items": items,
    }


def _load_qrels_map(path: Path) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(dict)
    if not path.exists():
        return out
    for rec in _load_jsonl(path):
        out[str(rec["query_id"])][str(rec["doc_id"])] = int(rec["relevance"])
    return out


def run_stage0(
    out_dir: Path,
    *,
    mode: str,
) -> dict[str, Any]:
    creds = provider_credential_audit()
    models = discover_provider_models()
    inventory = inventory_judgment_caches(REPO_ROOT)
    _write_json(out_dir / "PROVIDER_CREDENTIAL_AUDIT.json", creds)
    _write_json(out_dir / "PROVIDER_MODELS.json", models)
    _write_csv(out_dir / "EXISTING_CACHE_INVENTORY.csv", inventory)

    if mode == "live":
        smoke = smoke_test_providers(list(TARGET_PROVIDERS), dry_run=False)
    elif mode == "dry_run":
        smoke = smoke_test_providers(list(TARGET_PROVIDERS), dry_run=True)
    else:
        smoke = [
            {
                "provider": p,
                "ok": False,
                "category": "cache_only_skipped",
                "message": "Smoke skipped (--cache-only); no network call.",
                "model": None,
                "latency_seconds": 0.0,
            }
            for p in TARGET_PROVIDERS
        ]
    _write_json(out_dir / "STAGE0_SMOKE_RESULTS.json", smoke)

    audit_md = [
        "# Provider and model availability audit",
        "",
        f"Generated: `{_utc()}`",
        f"Mode: `{mode}`",
        "",
        "## Credentials (presence only)",
        "",
    ]
    for c in creds:
        audit_md.append(
            f"- **{c['provider']}**: available={c['available']} "
            f"mode={c.get('mode')} — {c['reason']}"
        )
    audit_md += ["", "## Configured model tiers", ""]
    for p, info in models.items():
        audit_md.append(f"- **{p}**: family={info['family']} tiers={info['tiers']}")
    audit_md += ["", "## Stage 0 smoke tests", ""]
    for s in smoke:
        audit_md.append(
            f"- **{s['provider']}** / `{s.get('model')}`: "
            f"ok={s.get('ok')} category={s.get('category')} "
            f"latency={s.get('latency_seconds', 0):.2f}s"
        )
    audit_md += [
        "",
        "## Existing cache inventory (summary)",
        "",
        f"Found **{len(inventory)}** pairwise judgment cache files under the repo.",
        "See `EXISTING_CACHE_INVENTORY.csv` for paths, sizes, and provenance risks.",
        "",
        "### Critical provenance finding",
        "",
        "Legacy `JudgmentCache` keys omit model, prompt version, temperature, and "
        "orientation. `LLMRunner` mitigates via `provider_model` subdirectories; "
        "OpenAI pilot scripts sharing one cache dir do not. New experiments use "
        "`ProvenanceJudgmentStore` with full cache keys under this report namespace.",
        "",
    ]
    (out_dir / "AUDIT_PROVIDERS_AND_CACHES.md").write_text("\n".join(audit_md))
    return {"creds": creds, "models": models, "smoke": smoke, "inventory": inventory, "mode": mode}


def _provider_model_plan(
    models: dict[str, dict[str, Any]],
    *,
    include_strong: bool,
) -> list[tuple[str, str]]:
    plan = []
    for p in TARGET_PROVIDERS:
        tiers = models[p]["tiers"]
        plan.append((p, tiers["default"]))
        if include_strong and "strong" in tiers:
            plan.append((p, tiers["strong"]))
    return plan


def run_calls_for_manifest(
    *,
    judge: MultiProviderJudge,
    manifest: dict[str, Any],
    provider_models: list[tuple[str, str]],
    prompt_versions: list[str],
    orientations: list[str],
    repeats: int,
    temperature: float,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in manifest["items"]:
        doc_map = {d["doc_id"]: d["text"] for d in item["documents"]}
        for pair in item["pairs"]:
            a, b = pair["doc_a_id"], pair["doc_b_id"]
            for provider, model in provider_models:
                for prompt_version in prompt_versions:
                    for orientation in orientations:
                        for rep in range(repeats):
                            if not judge.ceiling.allow(provider):
                                continue
                            rec = judge.compare(
                                provider=provider,
                                model=model,
                                query_id=item["query_id"],
                                query_text=item["query_text"],
                                doc_a_id=a,
                                doc_a_text=doc_map[a],
                                doc_b_id=b,
                                doc_b_text=doc_map[b],
                                orientation=orientation,  # type: ignore[arg-type]
                                prompt_version=prompt_version,
                                temperature=temperature,
                                seed=manifest["seed"],
                                repeat_index=rep,
                            )
                            records.append(rec.to_dict())
    return records


def analyze_records(
    records: list[dict[str, Any]],
    *,
    qrels: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    # Orientation consistency by provider/model/prompt
    by_group: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        gkey = (
            r["provider"],
            r["model"],
            r["prompt_version"],
            r["canonical_pair_id"],
            float(r.get("temperature") or 0.0),
        )
        by_group[gkey].append(r)

    orient_rows = []
    for gkey, group in by_group.items():
        # Prefer one ab and one ba (first valid each).
        ab = next((x for x in group if x["displayed_orientation"] == "ab"), None)
        ba = next((x for x in group if x["displayed_orientation"] == "ba"), None)
        if not ab or not ba:
            continue
        cons = aggregate_orientation_pair([ab, ba])
        orient_rows.append(
            {
                "provider": gkey[0],
                "model": gkey[1],
                "prompt_version": gkey[2],
                "canonical_pair_id": gkey[3],
                "temperature": gkey[4],
                "position_consistent": cons.get("position_consistent"),
                "contradictory": cons.get("contradictory"),
                "first_position_bias_signal": cons.get("first_position_bias_signal"),
                "both_abstain": cons.get("both_abstain"),
                "reason": cons.get("reason"),
            }
        )

    # Validity rates
    validity = []
    for (provider, model, prompt), grp in _group_by(
        records, lambda r: (r["provider"], r["model"], r["prompt_version"])
    ).items():
        n = len(grp)
        validity.append(
            {
                "provider": provider,
                "model": model,
                "prompt_version": prompt,
                "n_calls": n,
                "frac_valid": sum(1 for r in grp if r.get("valid")) / n if n else 0.0,
                "frac_invalid": sum(1 for r in grp if r.get("parsed_choice") == "INVALID")
                / n
                if n
                else 0.0,
                "frac_tie_or_abstain": sum(1 for r in grp if r.get("tie_or_abstention"))
                / n
                if n
                else 0.0,
                "frac_from_cache": sum(1 for r in grp if r.get("from_cache")) / n if n else 0.0,
                "mean_latency": _mean([r.get("latency_seconds") for r in grp]),
                "sum_prompt_tokens": sum(int(r.get("prompt_tokens") or 0) for r in grp),
                "sum_completion_tokens": sum(
                    int(r.get("completion_tokens") or 0) for r in grp
                ),
                "new_calls": sum(1 for r in grp if not r.get("from_cache")),
            }
        )

    # Per-query graph metrics for legacy_v1 + orientation-consistent ablation
    graph_rows = []
    qids = sorted({r["query_id"] for r in records})
    for provider, model in sorted({(r["provider"], r["model"]) for r in records}):
        for prompt in sorted({r["prompt_version"] for r in records}):
            subset = [
                r
                for r in records
                if r["provider"] == provider
                and r["model"] == model
                and r["prompt_version"] == prompt
            ]
            for qid in qids:
                for mode, flag in (
                    ("single_orient_ab_only", False),
                    ("orientation_consistent", True),
                ):
                    if mode == "single_orient_ab_only":
                        prefs = records_to_preferences(
                            [r for r in subset if r["displayed_orientation"] == "ab"],
                            query_id=qid,
                        )
                    else:
                        prefs = records_to_preferences(
                            subset, query_id=qid, orientation_consistent_only=True
                        )
                    stats = evaluate_preference_graph(prefs)
                    row = {
                        "provider": provider,
                        "model": model,
                        "prompt_version": prompt,
                        "query_id": qid,
                        "aggregation_mode": mode,
                        "n_prefs": stats["n_prefs"],
                        "n_two_cycles": stats["n_two_cycles"],
                        "n_nontrivial_sccs": stats["n_nontrivial_sccs"],
                        "fas_removed_edges": stats["fas_removed_edges"],
                        "fas_removed_weight": stats["fas_removed_weight"],
                        "retained_edge_fraction": stats["retained_edge_fraction"],
                        "originally_acyclic": stats["originally_acyclic"],
                        "ambiguity_bucket": (stats["ambiguity"] or {}).get(
                            "ambiguity_bucket"
                        ),
                    }
                    if qrels and stats["ranking"]:
                        row["ndcg"] = ndcg_at_k(
                            stats["ranking"], qrels.get(qid, {}), k=10
                        )
                    graph_rows.append(row)

    # Ensembles on legacy_v1 ab+consistent winners (no qrels)
    legacy = [
        r
        for r in records
        if r["prompt_version"] == "legacy_v1"
        and r.get("valid")
        and r.get("normalized_winner_id")
    ]
    # Collapse to orientation-consistent edges first where possible
    consistent_edges = []
    for pid, grp in _group_by(legacy, lambda r: r["canonical_pair_id"]).items():
        cons = aggregate_orientation_pair(grp)
        if cons.get("ok") and cons.get("position_consistent") and cons.get("agreed_winner"):
            ab = cons["ab"]
            consistent_edges.append(
                {
                    **ab,
                    "normalized_winner_id": cons["agreed_winner"],
                }
            )
    ensembles = {
        "majority": majority_across_models(consistent_edges),
        "agreement_only": agreement_only_edges(consistent_edges, min_models=2),
        "confidence_weighted": confidence_weighted_vote(consistent_edges),
    }
    ensemble_summary = {
        name: {"n_edges": len(edges)} for name, edges in ensembles.items()
    }

    # Position consistency rates
    orient_summary = []
    for (provider, model, prompt), grp in _group_by(
        orient_rows, lambda r: (r["provider"], r["model"], r["prompt_version"])
    ).items():
        n = len(grp)
        orient_summary.append(
            {
                "provider": provider,
                "model": model,
                "prompt_version": prompt,
                "n_pairs": n,
                "frac_position_consistent": sum(
                    1 for r in grp if r.get("position_consistent")
                )
                / n
                if n
                else None,
                "frac_contradictory": sum(1 for r in grp if r.get("contradictory")) / n
                if n
                else None,
                "frac_first_position_bias": sum(
                    1 for r in grp if r.get("first_position_bias_signal")
                )
                / n
                if n
                else None,
            }
        )

    return {
        "orientation_pairs": orient_rows,
        "orientation_summary": orient_summary,
        "validity_summary": validity,
        "graph_metrics": graph_rows,
        "ensemble_summary": ensemble_summary,
    }


def _group_by(rows, key_fn):
    out = defaultdict(list)
    for r in rows:
        out[key_fn(r)].append(r)
    return out


def _mean(vals):
    xs = [float(v) for v in vals if v is not None]
    return sum(xs) / len(xs) if xs else None


def write_final_report(
    out_dir: Path,
    *,
    stage0: dict[str, Any],
    spending: dict[str, Any],
    analysis: dict[str, Any] | None,
    call_plan: dict[str, Any],
    incomplete: list[str],
) -> None:
    smoke_ok = [s for s in stage0["smoke"] if s.get("ok")]
    smoke_bad = [s for s in stage0["smoke"] if not s.get("ok")]
    lines = [
        "# Multi-provider LLM robustness — FINAL REPORT",
        "",
        f"Generated: `{_utc()}`",
        "",
        "## 1. Provider audit summary",
        "",
        f"- Smoke OK: {', '.join(s['provider'] for s in smoke_ok) or '(none)'}",
        f"- Smoke FAIL: {', '.join(s['provider'] for s in smoke_bad) or '(none)'}",
        f"- Existing pairwise caches inventoried: {len(stage0['inventory'])}",
        "",
        "## 2. Call plan and spending",
        "",
        "```json",
        json.dumps({"plan": call_plan, "spending": spending}, indent=2),
        "```",
        "",
        "## 3. Orientation consistency",
        "",
    ]
    if analysis:
        lines += [
            "| Provider | Model | Prompt | N | Consist | Contradict | 1st-bias |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
        for r in analysis["orientation_summary"]:
            lines.append(
                f"| {r['provider']} | `{r['model']}` | {r['prompt_version']} | "
                f"{r['n_pairs']} | {_fmt(r['frac_position_consistent'])} | "
                f"{_fmt(r['frac_contradictory'])} | {_fmt(r['frac_first_position_bias'])} |"
            )
        lines += ["", "## 4. Validity / cost proxies", ""]
        lines += [
            "| Provider | Model | Prompt | N | Valid | New | Tok_in | Latency |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
        for r in analysis["validity_summary"]:
            lines.append(
                f"| {r['provider']} | `{r['model']}` | {r['prompt_version']} | "
                f"{r['n_calls']} | {r['frac_valid']:.3f} | {r['new_calls']} | "
                f"{r['sum_prompt_tokens']} | {_fmt(r['mean_latency'])} |"
            )
        lines += [
            "",
            "## 5. Cycle / repair (legacy_v1 ab-only vs orientation-consistent)",
            "",
            "See `graph_metrics.csv`. Headline extractor remains "
            "**prior-priority topological ranking** on the repaired DAG.",
            "",
            "## 6. Ensembles (judgment-free)",
            "",
            json.dumps(analysis["ensemble_summary"], indent=2),
            "",
            "## 7. Manuscript implications",
            "",
            "- Do **not** claim cross-provider robustness beyond the executed "
            "matched cells in this report.",
            "- Soft score rankings remain a separate family from hard topo extraction.",
            "- Legacy caches lack model/prompt provenance; do not mix them silently.",
            "",
        ]
    lines += ["## 8. Incomplete / unsupported", ""]
    lines.extend(f"- {x}" for x in incomplete)
    lines += [
        "",
        "## 9. Reproduce",
        "",
        "```bash",
        "source .venv/bin/activate",
        "PYTHONPATH=src python scripts/run_multi_provider_llm_robustness.py \\",
        f"  --output-dir {out_dir} --stage all",
        "```",
        "",
    ]
    (out_dir / "FINAL_REPORT.md").write_text("\n".join(lines))
    (out_dir / "INCOMPLETE.md").write_text(
        "# Incomplete\n\n" + "\n".join(f"- {x}" for x in incomplete) + "\n"
    )


def _fmt(v):
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Report directory (default: reports/multi_provider_llm_robustness_<UTC>).",
    )
    parser.add_argument(
        "--stage",
        choices=["0", "1", "2", "3", "all"],
        default="0",
        help="Default is stage 0 (audit). Live stages require --allow-provider-calls.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate provider calls without network.",
    )
    parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Inventory/analyze existing caches only; no provider calls.",
    )
    parser.add_argument(
        "--allow-provider-calls",
        action="store_true",
        help="Explicit opt-in for live provider traffic (may incur cost).",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-queries", type=int, default=2)
    parser.add_argument("--n-docs", type=int, default=4)
    parser.add_argument("--max-doc-chars", type=int, default=1200)
    parser.add_argument("--max-calls-global", type=int, default=180)
    parser.add_argument("--include-strong-azure", action="store_true")
    parser.add_argument(
        "--pilot-prompts",
        nargs="+",
        default=["legacy_v1", "json_tie_v1"],
    )
    parser.add_argument(
        "--robustness-prompts",
        nargs="+",
        default=["legacy_v1", "concise_v1", "json_ab_v1", "json_tie_v1"],
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--stochastic-temperature", type=float, default=0.7)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into a non-empty --output-dir.",
    )
    args = parser.parse_args()
    mode = assert_offline_or_allowed(
        allow_provider_calls=args.allow_provider_calls,
        dry_run=args.dry_run,
        cache_only=args.cache_only,
    )

    stamp = _utc()
    out_dir = ensure_output_dir(
        (
            args.output_dir
            or (REPO_ROOT / "reports" / f"multi_provider_llm_robustness_{stamp}")
        ).resolve(),
        overwrite=args.overwrite,
    )

    config = {
        "stage": args.stage,
        "mode": mode,
        "seed": args.seed,
        "n_queries": args.n_queries,
        "n_docs": args.n_docs,
        "max_doc_chars": args.max_doc_chars,
        "max_calls_global": args.max_calls_global,
        "include_strong_azure": bool(args.include_strong_azure),
        "pilot_prompts": list(args.pilot_prompts),
        "robustness_prompts": list(args.robustness_prompts),
        "repeats": args.repeats,
        "stochastic_temperature": args.stochastic_temperature,
        "paid_api_calls_allowed": mode == "live",
        "timestamp": stamp,
    }
    _write_json(out_dir / "config.json", config)
    write_run_manifest(
        out_dir,
        script="scripts/run_multi_provider_llm_robustness.py",
        config=config,
        repo_root=REPO_ROOT,
    )

    incomplete: list[str] = []
    stage0 = run_stage0(out_dir, mode=mode)
    ok_providers = [
        s["provider"]
        for s in stage0["smoke"]
        if s.get("ok") and s.get("category") != "dry_run_skipped"
    ]
    if mode == "dry_run":
        ok_providers = list(TARGET_PROVIDERS)
    for s in stage0["smoke"]:
        if not s.get("ok") and s.get("category") not in {
            "cache_only_skipped",
            "dry_run_skipped",
        }:
            incomplete.append(
                f"Provider {s['provider']} smoke failed ({s.get('category')}): "
                f"{str(s.get('message', ''))[:160]}"
            )

    if args.stage == "0" or mode == "cache_only":
        analysis = None
        if (out_dir / "judgment_records.jsonl").exists():
            records = _load_jsonl(out_dir / "judgment_records.jsonl")
            qrels = _load_qrels_map(
                REPO_ROOT / "data/processed/beir/scidocs/qrels.jsonl"
            )
            analysis = analyze_records(records, qrels=qrels or None)
            _write_json(out_dir / "ANALYSIS.json", analysis)
        write_final_report(
            out_dir,
            stage0=stage0,
            spending={},
            analysis=analysis,
            call_plan={},
            incomplete=incomplete
            + (
                ["Stages 1–3 not requested (--stage 0)."]
                if args.stage == "0"
                else ["cache-only mode: live stages skipped."]
            ),
        )
        print(f"Stage 0 / cache-only complete → {out_dir} (mode={mode})")
        return

    if mode == "live" and not ok_providers:
        incomplete.append("No providers passed smoke tests; refusing live stages.")
        write_final_report(
            out_dir,
            stage0=stage0,
            spending={},
            analysis=None,
            call_plan={},
            incomplete=incomplete,
        )
        print(f"Aborted after Stage 0 → {out_dir}")
        return

    cache_path = (
        REPO_ROOT
        / "outputs/openai_scidocs_real_pairwise_q50_k15/judgment_cache/llm_pairwise_judgments.jsonl"
    )
    if not cache_path.exists():
        raise SystemExit(
            f"Missing seed cache for manifest construction: {cache_path}. "
            "Provide the cache, or use --stage 0 --cache-only for offline audit."
        )
    manifest = _build_manifest_from_existing_cache(
        cache_path=cache_path,
        queries_path=REPO_ROOT / "data/processed/beir/scidocs/queries.jsonl",
        documents_path=REPO_ROOT / "data/processed/beir/scidocs/documents.jsonl",
        n_queries=args.n_queries,
        n_docs=args.n_docs,
        seed=args.seed,
        max_doc_chars=args.max_doc_chars,
    )
    write_manifest(out_dir / "sampling_manifest.json", manifest)

    models = stage0["models"]
    # Stage 1: default tier only, ok providers, pilot prompts, both orientations, 1 repeat, temp=0
    providers = [p for p in TARGET_PROVIDERS if p in ok_providers or mode == "dry_run"]
    if mode == "dry_run" and not providers:
        providers = list(TARGET_PROVIDERS)
    stage1_models = [(p, models[p]["tiers"]["default"]) for p in providers]
    if args.include_strong_azure and "azure" in providers and "strong" in models["azure"]["tiers"]:
        # Strong tier only on robustness / stage2 to control spend
        pass

    plan1 = estimate_call_budget(
        manifest,
        n_providers=len(stage1_models),
        n_prompts=len(args.pilot_prompts),
        orientations=2,
        repeats=1,
    )
    _write_json(out_dir / "CALL_PLAN_STAGE1.json", plan1)

    ceiling = SpendingCeiling(
        max_new_calls_global=args.max_calls_global,
        max_new_calls_per_provider={
            "azure": 70,
            "cohere": 50,
            "fireworks": 40,
            "gemini": 50,
        },
    )
    store = ProvenanceJudgmentStore(out_dir / "judgment_records.jsonl")
    # Resume-safe: count prior live records in this namespace toward ceilings
    # so a re-run does not double-bill up to the same absolute limit again.
    prior_live = [
        r
        for r in store.all_records()
        if not r.get("from_cache") and r.get("error_category") != "budget_exhausted"
    ]
    for r in prior_live:
        ceiling.record(
            str(r["provider"]),
            prompt_tokens=int(r.get("prompt_tokens") or 0),
            completion_tokens=int(r.get("completion_tokens") or 0),
        )
    judge = MultiProviderJudge(store, ceiling, dry_run=(mode == "dry_run"))

    all_records: list[dict[str, Any]] = []
    if args.stage in {"1", "all"}:
        recs = run_calls_for_manifest(
            judge=judge,
            manifest=manifest,
            provider_models=stage1_models,
            prompt_versions=list(args.pilot_prompts),
            orientations=["ab", "ba"],
            repeats=1,
            temperature=0.0,
        )
        all_records.extend(recs)
        _write_json(out_dir / "STAGE1_SPENDING.json", ceiling.summary())

    # Stage 3 robustness subset: first query only, all prompts, repeats at temp 0 and stochastic
    if args.stage in {"3", "all"}:
        rob_manifest = {
            **manifest,
            "items": manifest["items"][:1],
            "n_queries": min(1, manifest["n_queries"]),
            "n_unordered_pairs": sum(len(it["pairs"]) for it in manifest["items"][:1]),
            "manifest_version": "robustness_subset_v1",
        }
        write_manifest(out_dir / "robustness_manifest.json", rob_manifest)
        # deterministic repeats
        recs = run_calls_for_manifest(
            judge=judge,
            manifest=rob_manifest,
            provider_models=stage1_models,
            prompt_versions=list(args.robustness_prompts),
            orientations=["ab", "ba"],
            repeats=args.repeats,
            temperature=0.0,
        )
        all_records.extend(recs)
        # stochastic setting (smaller: legacy prompt only)
        recs = run_calls_for_manifest(
            judge=judge,
            manifest=rob_manifest,
            provider_models=stage1_models,
            prompt_versions=["legacy_v1"],
            orientations=["ab", "ba"],
            repeats=args.repeats,
            temperature=args.stochastic_temperature,
        )
        all_records.extend(recs)

    # Stage 2: optional strong Azure on pilot pairs, legacy prompt only
    if args.stage in {"2", "all"} and args.include_strong_azure:
        strong = models.get("azure", {}).get("tiers", {}).get("strong")
        if strong and ("azure" in providers or mode == "dry_run"):
            recs = run_calls_for_manifest(
                judge=judge,
                manifest=manifest,
                provider_models=[("azure", strong)],
                prompt_versions=["legacy_v1"],
                orientations=["ab", "ba"],
                repeats=1,
                temperature=0.0,
            )
            all_records.extend(recs)
        else:
            incomplete.append("Strong Azure tier not run (missing or provider failed).")
    elif args.stage in {"2", "all"}:
        incomplete.append(
            "Stage 2 strong-tier expansion skipped (pass --include-strong-azure)."
        )

    # Deduplicate by cache_key for analysis (store already unique)
    by_key = {r["cache_key"]: r for r in all_records if r.get("cache_key")}
    # Also reload from store for resume honesty
    for r in store.all_records():
        by_key[r["cache_key"]] = r
    records = list(by_key.values())
    _write_json(out_dir / "SPENDING_SUMMARY.json", ceiling.summary())

    qrels = _load_qrels_map(REPO_ROOT / "data/processed/beir/scidocs/qrels.jsonl")
    analysis = analyze_records(records, qrels=qrels)
    _write_csv(out_dir / "orientation_pairs.csv", analysis["orientation_pairs"])
    _write_csv(out_dir / "orientation_summary.csv", analysis["orientation_summary"])
    _write_csv(out_dir / "validity_summary.csv", analysis["validity_summary"])
    _write_csv(out_dir / "graph_metrics.csv", analysis["graph_metrics"])

    new_by_provider = ceiling.summary()["new_calls_by_provider"]
    cached = sum(1 for r in records if r.get("from_cache"))
    incomplete += [
        "No new public LLM API pricing scraped in this run; report tokens/calls as cost proxies.",
        "Full corpus repetition across all datasets not executed (budget discipline).",
        "Ensemble weights were not fit on validation labels (defaults / agreement only).",
        "Manuscript text not edited; evidence is confined to this report directory.",
    ]
    if ceiling.stopped_reason:
        incomplete.append(f"Spending ceiling triggered: {ceiling.stopped_reason}")

    write_final_report(
        out_dir,
        stage0=stage0,
        spending=ceiling.summary(),
        analysis=analysis,
        call_plan={
            "stage1": plan1,
            "providers": providers,
            "pilot_prompts": args.pilot_prompts,
            "dry_run": mode == "dry_run",
            "mode": mode,
            "n_records_in_store": len(store),
            "n_cached_reads_observed": cached,
            "new_calls_by_provider": new_by_provider,
        },
        incomplete=incomplete,
    )

    mode_flag = {
        "dry_run": "--dry-run",
        "cache_only": "--cache-only",
        "live": "--allow-provider-calls",
    }[mode]
    repro = f"""#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
source .venv/bin/activate
PYTHONPATH=src python scripts/run_multi_provider_llm_robustness.py \\
  --output-dir "$(dirname "$0")" \\
  --stage {args.stage} \\
  --seed {args.seed} \\
  --n-queries {args.n_queries} \\
  --n-docs {args.n_docs} \\
  --max-calls-global {args.max_calls_global} \\
  {mode_flag} \\
  --overwrite
"""
    (out_dir / "REPRODUCE.sh").write_text(repro)
    (out_dir / "REPRODUCE.sh").chmod(0o755)

    print(f"Wrote report to {out_dir}")
    print(f"Records in store: {len(store)}; new calls: {ceiling.summary()['new_calls_global']}")
    print(f"New calls by provider: {new_by_provider}")


if __name__ == "__main__":
    main()
