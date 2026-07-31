#!/usr/bin/env python3
"""Matched real-query multifactor budgeted acquisition (live providers).

Hard constraints: no OpenAI new calls; USD ceiling $20; wall-clock via external
timeout; resume-safe append-only caches; max 20 unique judgments per factor cell.
"""

from __future__ import annotations

import argparse
import atexit
import copy
import csv
import hashlib
import json
import os
import signal
import socket
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

# collections import no longer required after verdict rewrite

from consistency_ranker.adaptive_acquisition import synthetic_roster  # noqa: E402
from consistency_ranker.multi_provider_eval.prompts import PROMPT_FAMILY  # noqa: E402
from consistency_ranker.multi_provider_eval.providers import (  # noqa: E402
    discover_provider_models,
    provider_credential_audit,
    smoke_test_providers,
)
from consistency_ranker.multifactor_acquisition.analyze import (  # noqa: E402
    analyze_cell_summaries,
    build_policy_comparison_table,
    eval_ranking,
    load_qrels,
    ranking_from_evidence,
    ranking_from_prior,
    render_verdict,
    write_final_report,
)
from consistency_ranker.multifactor_acquisition.azure_request import (  # noqa: E402
    AZURE_REQUEST_PROFILE,
)
from consistency_ranker.multifactor_acquisition.completion import (  # noqa: E402
    recompute_completed_cells,
)
from consistency_ranker.multifactor_acquisition.live_judge import (  # noqa: E402
    CellLock,
    CircuitState,
    LiveCellJudge,
    build_mp_judge,
)
from consistency_ranker.multifactor_acquisition.pricing import (  # noqa: E402
    PROVIDER_RATES_USD_PER_M,
    project_spend,
)
from consistency_ranker.multifactor_acquisition.reparse import (  # noqa: E402
    reparse_raw_responses,
)
from consistency_ranker.multifactor_acquisition.sampling import (  # noqa: E402
    QUOTAS,
    SEED,
    TOP_K,
    load_samples_from_csv,
    sample_queries,
    sampled_to_rows,
)
from consistency_ranker.policy_selection.diagnostic_probes import (  # noqa: E402
    ProbeConfig,
    run_diagnostic_probes,
)
from consistency_ranker.policy_selection.policy_runner import (  # noqa: E402
    _build_cfg,
    policy_to_engine_kwargs,
)
from consistency_ranker.policy_selection.production_runner import (  # noqa: E402
    run_production_uht,
)
from consistency_ranker.prior_robust import (  # noqa: E402
    make_initial_robust_state,
    run_robust_acquisition,
)

PROMPTS = ("legacy_v1", "concise_v1")
ORIENTATIONS: tuple[Literal["ab", "ba"], ...] = ("ab", "ba")
POLICIES = ("UHT", "CHALLENGER", "HYBRID", "ROBUST_COMBINED")
BUDGETS = (3, 5, 8)
MAX_CALLS = 4800
MAX_USD = 20.0
MAX_USD_PER_PROVIDER = 10.0
MAX_CELL_CALLS = 20
SMOKE_USD_CAP = 0.20
CODE_VERSION = "multifactor_acquisition_v1"
RESUME_MAX_ADDITIONAL_CALLS = 1300
RESUME_MAX_ADDITIONAL_USD = 1.0


def _count_api_failures(failures_path: Path) -> int:
    if not failures_path.exists():
        return 0
    n = 0
    with failures_path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("is_skip") or row.get("category") == "data_availability_skip":
                continue
            if row.get("reason") == "missing_doc_text":
                continue
            n += 1
    return n


def _count_skips(skips_path: Path, failures_path: Path) -> int:
    n = 0
    for path in (skips_path, failures_path):
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("reason") == "missing_doc_text" or row.get("is_skip"):
                    n += 1
    return n


_STOP = {"flag": False}


def _state_ranking(state) -> list[str]:
    r = getattr(state, "ranking", None)
    if callable(r):
        return list(r())
    if isinstance(r, list) and r:
        return list(r)
    pr = getattr(state, "prior_ranking", None)
    if callable(pr):
        return list(pr())
    return []


class TaggedJudge:
    def __init__(self, inner: LiveCellJudge, tag: str) -> None:
        self.inner = inner
        self.tag = tag

    def available(self, action) -> bool:
        return self.inner.available(action)

    def judge(self, action):
        return self.inner.judge(action, consumer=self.tag)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(path)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        fh.flush()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    # union keys
    keys: list[str] = []
    seen = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def acquire_lock(lock_path: Path, meta: dict[str, Any]) -> None:
    if lock_path.exists():
        try:
            old = json.loads(lock_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            old = {}
        pid = int(old.get("pid") or 0)
        if pid and _pid_alive(pid):
            raise SystemExit(f"Refuse: lock held by live pid={pid} at {lock_path}")
    meta = {**meta, "pid": os.getpid(), "hostname": socket.gethostname(), "acquired_at": _utc()}
    _write_json(lock_path, meta)


def release_lock(lock_path: Path) -> None:
    if lock_path.exists():
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            if int(data.get("pid") or 0) == os.getpid():
                data["released_at"] = _utc()
                data["status"] = "released"
                _write_json(lock_path, data)
        except Exception:  # noqa: BLE001
            pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def select_providers(smoke_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pick two healthy non-OpenAI providers: prefer azure+cohere, else cheapest diverse."""
    healthy = []
    for r in smoke_results:
        ok = bool(r.get("ok") or r.get("available") or r.get("success"))
        if r.get("status") == "ok":
            ok = True
        if r.get("error"):
            ok = False
        if not ok:
            continue
        p = str(r.get("provider"))
        if p == "openai" or p not in PROVIDER_RATES_USD_PER_M:
            continue
        healthy.append(r)
    if len(healthy) < 2:
        return []
    models = discover_provider_models()
    by_name = {r["provider"]: r for r in healthy}
    # Prefer azure + cohere (verified USD rates + prior oriented caches).
    if "azure" in by_name and "cohere" in by_name:
        pair = ["azure", "cohere"]
    else:
        scored = []
        for r in healthy:
            p = r["provider"]
            rates = PROVIDER_RATES_USD_PER_M[p]
            scored.append((rates["in"] + rates["out"], p))
        scored.sort()
        pair = [scored[0][1]]
        fam0 = str(models.get(pair[0], {}).get("family") or pair[0])
        second = None
        for _, p in scored[1:]:
            if str(models.get(p, {}).get("family") or p) != fam0:
                second = p
                break
        pair.append(second or scored[1][1])
    out = []
    for p in pair:
        out.append(
            {
                "provider": p,
                "model": models[p]["tiers"]["default"],
                "family": models[p].get("family"),
                "smoke": by_name[p],
            }
        )
    return out


def prompt_hashes() -> dict[str, str]:
    out = {}
    for pid in PROMPTS:
        spec = PROMPT_FAMILY[pid]
        out[pid] = hashlib.sha256(spec.template.encode("utf-8")).hexdigest()
    return out


def run_policy_on_state(
    *,
    policy: str,
    state,
    profiles,
    judge,
    budget: int,
    top_k: int,
    seed: int,
    true_ranking: list[str] | None,
    alt_priors: list[dict[str, float]] | None,
):
    mapping = policy_to_engine_kwargs(policy)  # type: ignore[arg-type]
    cfg = _build_cfg(mapping["cfg"], budget=budget, seed=seed, top_k=top_k)
    # remaining budget already set on state
    return run_robust_acquisition(
        state,
        profiles,
        judge,
        cfg=cfg,
        alt_priors=alt_priors,
        true_ranking=true_ranking,
        policy_name=mapping["policy_name"],
    )


def process_cell(
    *,
    output_dir: Path,
    sample,
    provider: str,
    model: str,
    prompt_version: str,
    orientation: Literal["ab", "ba"],
    mp_judge,
    circuits: dict[str, CircuitState],
    provider_spend: dict[str, float],
    global_spend: list[float],
    qrels_map: dict[str, dict[str, dict[str, int]]],
    completed: set[str],
) -> list[dict[str, Any]]:
    cell_id = (
        f"{sample.dataset}|{sample.query_id}|{provider}|{prompt_version}|{orientation}"
    )
    if cell_id in completed:
        return []

    if circuits[provider].broken:
        return [
            {
                "cell_id": cell_id,
                "status": "skipped_circuit_broken",
                "provider": provider,
                "query_id": sample.query_id,
            }
        ]

    cell = CellLock(
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        orientation=orientation,
        query_id=sample.query_id,
        query_text=sample.query_text,
        doc_texts=getattr(sample, "doc_texts"),
        max_unique_calls=MAX_CELL_CALLS,
        effective_depth=int(getattr(sample, "effective_depth", len(sample.doc_ids))),
    )
    judge = LiveCellJudge(
        cell=cell,
        mp_judge=mp_judge,
        cost_ledger_path=output_dir / "COST_LEDGER.csv",
        raw_path=output_dir / "RAW_RESPONSES.jsonl",
        parsed_path=output_dir / "PARSED_JUDGMENTS.jsonl",
        failures_path=output_dir / "FAILURES.jsonl",
        circuit=circuits[provider],
        provider_spend=provider_spend,
        provider_spend_cap=MAX_USD_PER_PROVIDER,
        global_spend_cap=MAX_USD,
        global_spend=global_spend,
        consumers_log_path=output_dir / "CONSUMER_LOG.jsonl",
        skips_path=output_dir / "SKIPS.jsonl",
    )
    # Reuse prior valid judgments by deterministic identity (no Cohere re-calls).
    judge.preload_parsed(output_dir / "PARSED_JUDGMENTS.jsonl")
    profiles = synthetic_roster(n_models=1, n_prompts=1)
    # Force profile ids unused — LiveCellJudge remaps.
    candidates = list(sample.doc_ids)
    prior = dict(sample.prior_scores)
    # Prior ranking is a baseline/diagnostic only — never relevance ground truth.
    prior_ranking = ranking_from_prior(prior)
    qrels = qrels_map.get(sample.dataset, {}).get(sample.query_id, {})
    depth = int(getattr(sample, "effective_depth", len(candidates)))
    top_k_eff = min(TOP_K, depth, len(candidates))

    rows: list[dict[str, Any]] = []

    # Baseline always-unrepaired / always-repair placeholders filled after pool grows.
    base_state = make_initial_robust_state(
        query_id=sample.query_id,
        candidate_ids=candidates,
        prior_scores=prior,
        budget=max(BUDGETS),
        top_k=top_k_eff,
        seed=SEED,
    )
    probe_judge = TaggedJudge(judge, "mixed_diagnostic_probe")
    probe_state = copy.deepcopy(base_state)
    probe_cfg = ProbeConfig(design="mixed_diagnostic", max_budget=3, profile_index=0)
    probe_res = run_diagnostic_probes(
        probe_state, profiles, probe_judge, cfg=probe_cfg, alt_priors=None, seed=SEED
    )
    probe_calls = int(probe_res.n_executed)
    _append_jsonl(
        output_dir / "POLICY_ACTIONS.jsonl",
        {
            "cell_id": cell_id,
            "phase": "probe",
            "probe": probe_res.to_dict(),
            "unique_calls": judge.n_unique_calls,
        },
    )

    # always unrepaired
    oc, u = eval_ranking(
        prior_ranking,
        qrels,
        k=top_k_eff,
        n_calls=0,
        policy="always_unrepaired",
        prior_ranking=prior_ranking,
        candidate_pool=candidates,
    )
    rows.append(
        _row(
            cell_id,
            sample,
            provider,
            model,
            prompt_version,
            orientation,
            "always_unrepaired",
            0,
            oc,
            u,
            judge,
            status="complete",
        )
    )

    for policy in POLICIES:
        for budget in BUDGETS:
            if _STOP["flag"] or global_spend[0] >= MAX_USD or circuits[provider].broken:
                rows.append(
                    _row(
                        cell_id,
                        sample,
                        provider,
                        model,
                        prompt_version,
                        orientation,
                        policy,
                        budget,
                        None,
                        None,
                        judge,
                        status="stopped",
                    )
                )
                continue
            st = copy.deepcopy(probe_state)
            # Budget semantics: total unique+policy steps capped by budget.
            # Probe already consumed probe_calls from the shared judge; policy may
            # use remaining = max(0, budget - probe_calls) additional selections.
            remaining = max(0, int(budget) - probe_calls)
            st.remaining_budget = remaining
            st.budget = budget
            tagged = TaggedJudge(judge, f"{policy}@b{budget}")
            try:
                before = judge.n_unique_calls
                result = run_policy_on_state(
                    policy=policy,
                    state=st,
                    profiles=profiles,
                    judge=tagged,
                    budget=remaining,
                    top_k=top_k_eff,
                    seed=SEED,
                    # Engine may use a ranking for internal diagnostics only; never qrels.
                    true_ranking=None,
                    alt_priors=None,
                )
                ranking = _state_ranking(result.state)
                n_calls = min(budget, probe_calls + max(0, judge.n_unique_calls - before))
                # catastrophic: no relevant in top-k while relevants exist outside
                rel = {d for d, r in qrels.items() if r > 0}
                cat = bool(rel) and not (set(ranking[:top_k_eff]) & rel) and bool(
                    rel & set(candidates)
                )
                buried = None
                if rel:
                    hit_rel = set(ranking[:top_k_eff]) & rel
                    mid = max(1, top_k_eff // 2)
                    buried = bool(hit_rel) and any(
                        candidates.index(d) >= mid
                        for d in hit_rel
                        if d in candidates
                    )
                oc, u = eval_ranking(
                    ranking,
                    qrels,
                    k=top_k_eff,
                    n_calls=n_calls,
                    policy=policy,
                    catastrophic=cat,
                    buried_recovered=buried,
                    prior_ranking=prior_ranking,
                    candidate_pool=candidates,
                )
                status = "complete"
                if judge.stopped_reason:
                    status = f"partial:{judge.stopped_reason}"
                rows.append(
                    _row(
                        cell_id,
                        sample,
                        provider,
                        model,
                        prompt_version,
                        orientation,
                        policy,
                        budget,
                        oc,
                        u,
                        judge,
                        status=status,
                    )
                )
                _append_jsonl(
                    output_dir / "POLICY_TRACES.jsonl",
                    {
                        "cell_id": cell_id,
                        "policy": policy,
                        "budget": budget,
                        "n_calls": n_calls,
                        "utility": u,
                        "ranking": ranking,
                        "stopping_reason": getattr(result, "stopping_reason", None),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                _append_jsonl(
                    output_dir / "FAILURES.jsonl",
                    {
                        "cell_id": cell_id,
                        "policy": policy,
                        "budget": budget,
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:800],
                        "trace": traceback.format_exc()[-2000:],
                        "ts": _utc(),
                    },
                )
                rows.append(
                    _row(
                        cell_id,
                        sample,
                        provider,
                        model,
                        prompt_version,
                        orientation,
                        policy,
                        budget,
                        None,
                        None,
                        judge,
                        status=f"error:{type(exc).__name__}",
                    )
                )

    # always-repair from shared parsed evidence for this cell
    evidence = []
    for line in (output_dir / "PARSED_JUDGMENTS.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        if sample.query_id not in line or provider not in line:
            continue
        if prompt_version not in line:
            continue
        if f'"displayed_orientation": "{orientation}"' not in line:
            continue
        evidence.append(json.loads(line))
    # fallback: from judge cache
    if not evidence:
        evidence = [ev.to_dict() for ev in judge._cache.values()]
    rep_rank = ranking_from_evidence(evidence, candidates, repair=True)
    unrepaired_rank = ranking_from_evidence(evidence, candidates, repair=False)
    for name, ranking, calls in (
        ("always_repair", rep_rank, judge.n_unique_calls),
        ("graph_unrepaired", unrepaired_rank, judge.n_unique_calls),
    ):
        oc, u = eval_ranking(
            ranking,
            qrels,
            k=top_k_eff,
            n_calls=calls,
            policy=name,
            prior_ranking=prior_ranking,
            candidate_pool=candidates,
        )
        rows.append(
            _row(
                cell_id,
                sample,
                provider,
                model,
                prompt_version,
                orientation,
                name,
                judge.n_unique_calls,
                oc,
                u,
                judge,
                status="complete",
            )
        )

    # Safeguard comparison: plain UHT vs production UHT at each budget (shared judge)
    for budget in BUDGETS:
        if _STOP["flag"] or circuits[provider].broken:
            break
        try:
            # plain named UHT
            st = make_initial_robust_state(
                query_id=sample.query_id,
                candidate_ids=candidates,
                prior_scores=prior,
                budget=budget,
                top_k=top_k_eff,
                seed=SEED,
            )
            before = judge.n_unique_calls
            # If cell already at ceiling, these become cache-only reconstructions.
            plain = run_policy_on_state(
                policy="UHT",
                state=st,
                profiles=profiles,
                judge=TaggedJudge(judge, f"safeguard_plain_uht@b{budget}"),
                budget=budget,
                top_k=top_k_eff,
                seed=SEED,
                true_ranking=None,
                alt_priors=None,
            )
            plain_calls = max(0, judge.n_unique_calls - before)
            plain_rank = _state_ranking(plain.state)
            oc_p, u_p = eval_ranking(
                plain_rank,
                qrels,
                k=top_k_eff,
                n_calls=plain_calls,
                policy="plain_uht",
                prior_ranking=prior_ranking,
                candidate_pool=candidates,
            )
            rows.append(
                _row(
                    cell_id,
                    sample,
                    provider,
                    model,
                    prompt_version,
                    orientation,
                    "plain_uht",
                    budget,
                    oc_p,
                    u_p,
                    judge,
                    status="complete",
                )
            )
            # Production path: candidate pool only — never prior-as-truth.
            world_prod = {
                "candidate_ids": candidates,
                "prior_scores": prior,
                "judge": TaggedJudge(judge, f"safeguard_production_uht@b{budget}"),
            }
            before = judge.n_unique_calls
            prod = run_production_uht(
                world=world_prod,
                budget=budget,
                top_k=top_k_eff,
                seed=SEED,
                query_id=sample.query_id,
            )
            prod_calls = int(getattr(prod, "n_calls", max(0, judge.n_unique_calls - before)))
            prod_rank = list(getattr(prod, "ranking", None) or prior_ranking)
            oc_r, u_r = eval_ranking(
                prod_rank,
                qrels,
                k=top_k_eff,
                n_calls=prod_calls,
                policy="production_uht",
                prior_ranking=prior_ranking,
                candidate_pool=candidates,
            )
            sg = getattr(prod, "safeguards", None)
            sg_extra = sg.to_dict() if hasattr(sg, "to_dict") else {"repr": str(sg)}
            rows.append(
                _row(
                    cell_id,
                    sample,
                    provider,
                    model,
                    prompt_version,
                    orientation,
                    "production_uht",
                    budget,
                    oc_r,
                    u_r,
                    judge,
                    status="complete",
                    extra={
                        "safeguards": sg_extra,
                        "execution_mode": getattr(
                            getattr(prod, "execution_mode", None), "value", None
                        ),
                        "executed_policy": getattr(prod, "executed_policy", None),
                        "experimental_escalation_disabled": True,
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001
            _append_jsonl(
                output_dir / "FAILURES.jsonl",
                {
                    "cell_id": cell_id,
                    "phase": "safeguard",
                    "budget": budget,
                    "error": str(exc)[:800],
                    "ts": _utc(),
                },
            )

    # per-query oracle among acquisition policies at budget 8
    b8 = [
        r
        for r in rows
        if r.get("budget") == 8
        and r.get("policy") in POLICIES
        and r.get("utility") is not None
    ]
    if b8:
        best = max(b8, key=lambda r: float(r["utility"]))
        meta_keys = (
            "cell_id",
            "dataset",
            "query_id",
            "provider",
            "model",
            "prompt_version",
            "orientation",
        )
        rows.append(
            {
                **{k: best[k] for k in meta_keys},
                "policy": "oracle",
                "budget": 8,
                "utility": best["utility"],
                "best_policy": best["policy"],
                "status": "complete",
                "n_calls": best.get("n_calls"),
                "ndcg_at_k": best.get("ndcg_at_k"),
            }
        )

    _append_jsonl(
        output_dir / "CELL_SUMMARY.jsonl",
        {
            "cell_id": cell_id,
            "rows": len(rows),
            "unique_calls": judge.n_unique_calls,
            "cache_hits": judge.n_cache_hits,
            "effective_depth": top_k_eff,
            "ts": _utc(),
        },
    )
    from consistency_ranker.multifactor_acquisition.completion import is_cell_complete_from_rows

    ok, reason = is_cell_complete_from_rows(rows, effective_depth=top_k_eff)
    if ok:
        completed.add(cell_id)
    else:
        _append_jsonl(
            output_dir / "CELL_COMPLETION_DECISIONS.jsonl",
            {
                "cell_id": cell_id,
                "marked_complete": False,
                "reason": reason,
                "effective_depth": top_k_eff,
                "ts": _utc(),
            },
        )
    # persist completed set
    (output_dir / "completed_cells.json").write_text(
        json.dumps(sorted(completed), indent=2), encoding="utf-8"
    )
    return rows


def _row(
    cell_id,
    sample,
    provider,
    model,
    prompt_version,
    orientation,
    policy,
    budget,
    oc,
    u,
    judge,
    *,
    status: str,
    extra: dict | None = None,
) -> dict[str, Any]:
    extra_oc = None if oc is None else (oc.extra or {})
    return {
        "cell_id": cell_id,
        "dataset": sample.dataset,
        "query_id": sample.query_id,
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "orientation": orientation,
        "policy": policy,
        "budget": budget,
        "utility": u,
        "ndcg_at_k": None if oc is None else extra_oc.get("ndcg_at_k"),
        "mrr_at_k": None if oc is None else extra_oc.get("mrr_at_k"),
        "recall_at_k": None if oc is None else extra_oc.get("recall_at_k"),
        "prior_topk_jaccard": None if oc is None else extra_oc.get("prior_topk_jaccard"),
        "prior_kendall_tau": None if oc is None else extra_oc.get("prior_kendall_tau"),
        "prior_topk_jaccard_informative": (
            None if oc is None else extra_oc.get("prior_topk_jaccard_informative")
        ),
        "agreement_metric_informative": (
            None if oc is None else extra_oc.get("agreement_metric_informative")
        ),
        "topk_jaccard": None if oc is None else oc.topk_jaccard,
        "n_calls": None if oc is None else oc.n_calls,
        "catastrophic": None if oc is None else oc.catastrophic,
        "buried_recovered": None if oc is None else oc.buried_recovered,
        "has_qrels": None if oc is None else extra_oc.get("has_qrels"),
        "missing_qrels_reason": None if oc is None else extra_oc.get("missing_qrels_reason"),
        "status": status,
        "unique_calls_cell": judge.n_unique_calls,
        "cache_hits_cell": judge.n_cache_hits,
        "effective_depth": getattr(sample, "effective_depth", None),
        "extra": extra or {},
        "ts": _utc(),
    }


def update_status(path: Path, **fields: Any) -> None:
    cur = {}
    if path.exists():
        try:
            cur = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cur = {}
    cur.update(fields)
    cur["heartbeat_utc"] = _utc()
    cur["pid"] = os.getpid()
    _write_json(path, cur)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--skip-smoke", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-cells", type=int, default=None, help="Debug cap on factor cells")
    ap.add_argument(
        "--providers",
        type=str,
        default=None,
        help="Comma-separated provider allowlist (e.g. azure). Default: auto-select two.",
    )
    ap.add_argument(
        "--additional-max-calls",
        type=int,
        default=None,
        help="Resume-only cap on additional external calls.",
    )
    ap.add_argument(
        "--additional-max-usd",
        type=float,
        default=None,
        help="Resume-only cap on additional USD spend.",
    )
    ap.add_argument(
        "--offline-reparse-only",
        action="store_true",
        help="Reparse RAW_RESPONSES and recompute completed cells; no API calls.",
    )
    args = ap.parse_args()

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.offline_reparse_only:
        summary = reparse_raw_responses(
            output_dir / "RAW_RESPONSES.jsonl",
            provider="azure",
            out_path=output_dir / "REPARSED_JUDGMENTS_pairwise_parse_v2.jsonl",
        )
        audit = recompute_completed_cells(output_dir=output_dir)
        _write_json(
            output_dir / "OFFLINE_REPAIR_SUMMARY.json",
            {"reparse": summary, "completion": {
                "previous_count": len(audit["previous_completed"]),
                "recomputed_count": len(audit["recomputed_completed"]),
                "corrections": audit["corrections"],
            }},
        )
        print(json.dumps({"reparse": summary, "corrections": audit["corrections"]}, indent=2))
        return 0

    lock_path = output_dir / "EXPERIMENT.lock"
    status_path = output_dir / "STATUS.json"

    def _on_signal(signum, _frame):
        _STOP["flag"] = True
        update_status(status_path, phase="signal", signal=int(signum), stopping=True)

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    acquire_lock(
        lock_path,
        {
            "experiment_id": output_dir.name,
            "tmux_session": os.environ.get("TMUX_SESSION", ""),
            "output_dir": str(output_dir),
            "start_time": _utc(),
            "commit": os.popen("git rev-parse HEAD").read().strip(),
        },
    )
    atexit.register(lambda: release_lock(lock_path))

    update_status(status_path, phase="preflight", healthy=True, spend_usd=0.0)

    # Credentials audit (names only)
    creds = provider_credential_audit()
    _write_json(output_dir / "PROVIDER_CREDENTIAL_AUDIT.json", creds)

    smoke_results: list[dict[str, Any]]
    if args.skip_smoke and (output_dir / "STAGE0_SMOKE_RESULTS.json").exists():
        smoke_results = json.loads((output_dir / "STAGE0_SMOKE_RESULTS.json").read_text())
    else:
        update_status(status_path, phase="smoke")
        smoke_results = smoke_test_providers(["azure", "cohere", "fireworks", "gemini"])
        _write_json(output_dir / "STAGE0_SMOKE_RESULTS.json", smoke_results)

    allow = None
    if args.providers:
        allow = [p.strip() for p in args.providers.split(",") if p.strip()]

    if allow:
        models_disc = discover_provider_models()
        selected = []
        for p in allow:
            # Prefer prior MANIFEST model if present.
            model = None
            if (output_dir / "MANIFEST.json").exists():
                man = json.loads((output_dir / "MANIFEST.json").read_text())
                for s in man.get("providers") or []:
                    if s.get("provider") == p:
                        model = s.get("model")
            if model is None:
                model = (models_disc.get(p) or {}).get("tiers", {}).get("default")
            selected.append({"provider": p, "model": model, "family": "openai"})
        if not selected:
            raise SystemExit("Empty --providers allowlist")
    else:
        selected = select_providers(smoke_results)
        if len(selected) < 2:
            write_final_report(
                output_dir / "FINAL_REPORT.md",
                {
                    "verdict": "BLOCKED — INCOMPLETE MATCHED ACQUISITION",
                    "coverage": {
                        "reason": "fewer than 2 healthy non-OpenAI providers",
                        "smoke": smoke_results,
                    },
                },
            )
            (output_dir / "INCOMPLETE.md").write_text(
                "Preflight failure: fewer than two healthy non-OpenAI providers.\n",
                encoding="utf-8",
            )
            update_status(status_path, phase="failed_preflight", healthy=False)
            return 2

    providers = [s["provider"] for s in selected]
    models = {s["provider"]: s["model"] for s in selected}
    projection = project_spend(
        providers=providers,
        max_calls=MAX_CALLS,
        prompt_tokens_low=400,
        prompt_tokens_exp=900,
        prompt_tokens_max=1800,
        completion_tokens=40,
    )
    if projection["usd_maximum"] > MAX_USD:
        # shrink max calls so max estimate fits
        scale = MAX_USD / projection["usd_maximum"]
        eff_max = int(MAX_CALLS * scale * 0.95)
    else:
        eff_max = MAX_CALLS
    projection = project_spend(
        providers=providers,
        max_calls=eff_max,
        prompt_tokens_low=400,
        prompt_tokens_exp=900,
        prompt_tokens_max=1800,
        completion_tokens=40,
    )
    _write_json(output_dir / "COST_PROJECTION.json", projection)
    if projection["usd_maximum"] > MAX_USD + 1e-6:
        (output_dir / "INCOMPLETE.md").write_text(
            f"Preflight failure: projected max USD {projection['usd_maximum']} > {MAX_USD}\n",
            encoding="utf-8",
        )
        update_status(status_path, phase="failed_cost_projection", healthy=False)
        return 2

    # Freeze the original 30-query sample on resume; never redraw after results.
    query_csv = output_dir / "QUERY_SAMPLE.csv"
    if args.resume and query_csv.exists():
        samples = load_samples_from_csv(REPO, query_csv)
        audit = json.loads((output_dir / "QUERY_SAMPLE_AUDIT.json").read_text()) if (
            output_dir / "QUERY_SAMPLE_AUDIT.json"
        ).exists() else []
    else:
        samples, audit = sample_queries(REPO, seed=SEED, quotas=QUOTAS)
        _write_csv(output_dir / "QUERY_SAMPLE.csv", sampled_to_rows(samples))
        _write_json(output_dir / "QUERY_SAMPLE_AUDIT.json", audit)
    ph = prompt_hashes()

    factor_cells = []
    for sq in samples:
        for p in providers:
            for prompt in PROMPTS:
                for orient in ORIENTATIONS:
                    factor_cells.append(
                        {
                            "dataset": sq.dataset,
                            "query_id": sq.query_id,
                            "provider": p,
                            "model": models[p],
                            "prompt_version": prompt,
                            "prompt_hash": ph[prompt],
                            "orientation": orient,
                            "effective_depth": int(getattr(sq, "effective_depth", len(sq.doc_ids))),
                            "requested_top_k": TOP_K,
                            "cell_id": f"{sq.dataset}|{sq.query_id}|{p}|{prompt}|{orient}",
                        }
                    )
    if not args.resume or not (output_dir / "FACTOR_CELLS.csv").exists():
        _write_csv(output_dir / "FACTOR_CELLS.csv", factor_cells)
    if args.max_cells is not None:
        factor_cells = factor_cells[: args.max_cells]

    manifest = {
        "experiment": CODE_VERSION,
        "created_utc": _utc(),
        "commit": os.popen("git rev-parse HEAD").read().strip(),
        "seed": SEED,
        "quotas": QUOTAS,
        "n_queries": len(samples),
        "providers": selected,
        "prompts": list(PROMPTS),
        "prompt_hashes": ph,
        "orientations": list(ORIENTATIONS),
        "budgets": list(BUDGETS),
        "policies": list(POLICIES),
        "top_k": TOP_K,
        "max_unique_calls_per_cell": MAX_CELL_CALLS,
        "max_calls_global": eff_max,
        "max_usd_global": MAX_USD,
        "max_usd_per_provider": MAX_USD_PER_PROVIDER,
        "n_factor_cells": len(factor_cells),
        "cost_projection": projection,
        "probe": {"design": "mixed_diagnostic", "budget": 3},
        "azure_request_profile": AZURE_REQUEST_PROFILE,
    }
    if not args.resume or not (output_dir / "MANIFEST.json").exists():
        _write_json(output_dir / "MANIFEST.json", manifest)
    else:
        _write_json(output_dir / "MANIFEST.resume_overlay.json", manifest)

    # write helper scripts
    (output_dir / "STOP.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f'kill -INT $(jq -r .pid "{output_dir}/EXPERIMENT.lock") || true\n',
        encoding="utf-8",
    )
    os.chmod(output_dir / "STOP.sh", 0o755)
    (output_dir / "RESUME.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f'cd "{REPO}"\nsource .venv/bin/activate\n'
        f'export PYTHONPATH=src\n'
        f'python scripts/run_real_query_multifactor_acquisition.py --output-dir "{output_dir}" '
        f"--resume --skip-smoke --providers azure "
        f"--additional-max-calls {RESUME_MAX_ADDITIONAL_CALLS} "
        f"--additional-max-usd {RESUME_MAX_ADDITIONAL_USD}\n",
        encoding="utf-8",
    )
    os.chmod(output_dir / "RESUME.sh", 0o755)
    (output_dir / "REPRODUCE.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        "# Offline-only analysis replay (no network).\n"
        f'cd "{REPO}"\nsource .venv/bin/activate\nexport PYTHONPATH=src\n'
        'OUT="${1:?new output dir}"\n'
        "python scripts/run_real_query_multifactor_acquisition.py "
        '--output-dir "$OUT" --resume --skip-smoke --dry-run\n'
        "echo \"NOTE: dry-run reproduce validates wiring; full offline "
        'metric rebuild uses persisted PARSED_JUDGMENTS.jsonl."\n',
        encoding="utf-8",
    )
    os.chmod(output_dir / "REPRODUCE.sh", 0o755)

    add_call_cap = args.additional_max_calls
    add_usd_cap = args.additional_max_usd
    if args.resume:
        if add_call_cap is None:
            add_call_cap = RESUME_MAX_ADDITIONAL_CALLS
        if add_usd_cap is None:
            add_usd_cap = RESUME_MAX_ADDITIONAL_USD
    # Historical spend from ledger (resume must not reset accounting).
    prior_spend = 0.0
    prior_by_prov: dict[str, float] = {p: 0.0 for p in providers}
    prior_calls = 0
    ledger_path = output_dir / "COST_LEDGER.csv"
    if args.resume and ledger_path.exists():
        with ledger_path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                prior_calls += 1
                try:
                    usd = float(row.get("estimated_usd") or 0.0)
                except ValueError:
                    usd = 0.0
                prior_spend += usd
                p = str(row.get("provider") or "")
                if p in prior_by_prov:
                    prior_by_prov[p] += usd

    call_ceiling = eff_max
    usd_ceiling = MAX_USD
    if args.resume and add_call_cap is not None:
        call_ceiling = prior_calls + int(add_call_cap)
    if args.resume and add_usd_cap is not None:
        usd_ceiling = prior_spend + float(add_usd_cap)
        usd_ceiling = min(usd_ceiling, MAX_USD)

    mp_judge, ceiling = build_mp_judge(
        output_dir / "judgment_store.jsonl",
        max_calls_global=call_ceiling,
        max_calls_per_provider={p: call_ceiling for p in providers},
        max_usd_global=usd_ceiling,
        dry_run=bool(args.dry_run),
    )
    if args.resume and prior_calls:
        ceiling.new_calls_global = int(prior_calls)
        # Attribute prior calls to providers from ledger.
        if ledger_path.exists():
            with ledger_path.open(encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    p = str(row.get("provider") or "")
                    ceiling.new_calls_by_provider[p] = (
                        ceiling.new_calls_by_provider.get(p, 0) + 1
                    )
        ceiling.estimated_usd_global = float(prior_spend)

    circuits = {p: CircuitState() for p in providers}
    provider_spend = {p: float(prior_by_prov.get(p, 0.0)) for p in providers}
    global_spend = [float(prior_spend)]
    completed: set[str] = set()
    if args.resume and (output_dir / "completed_cells.json").exists():
        # Recompute completion; do not trust historical flags alone.
        depth_map = {c["cell_id"]: int(c.get("effective_depth") or TOP_K) for c in factor_cells}
        audit = recompute_completed_cells(
            output_dir=output_dir,
            cell_effective_depth=depth_map,
        )
        completed = set(audit["recomputed_completed"])
        # Keep Cohere completes even if azure-only factor_cells list is shorter.
        if allow == ["azure"]:
            prev = set(audit["previous_completed"])
            completed |= {c for c in prev if "|cohere|" in c}
            # Re-write including cohere preserves.
            (output_dir / "completed_cells.json").write_text(
                json.dumps(sorted(completed), indent=2), encoding="utf-8"
            )
        _write_json(
            output_dir / "RESUME_HISTORY.json",
            {
                "ts": _utc(),
                "providers": providers,
                "request_profile": AZURE_REQUEST_PROFILE,
                "additional_max_calls": add_call_cap,
                "additional_max_usd": add_usd_cap,
                "prior_spend": prior_spend,
                "prior_calls": prior_calls,
                "completed_cells": len(completed),
                "completion_corrections": audit.get("corrections"),
            },
        )

    qrels_map = {
        ds: load_qrels(REPO, ds) for ds in ("scidocs", "hotpotqa", "fiqa")
    }

    update_status(
        status_path,
        phase="acquisition",
        providers=providers,
        models=models,
        n_cells=len(factor_cells),
        completed_cells=len(completed),
        spend_usd=0.0,
        projection_expected_usd=projection["usd_expected"],
        successful_calls=0,
        failures=0,
    )

    all_rows: list[dict[str, Any]] = []
    # reload prior rows if resume
    cell_csv = output_dir / "CELL_SUMMARY.csv"
    if args.resume and cell_csv.exists():
        with cell_csv.open(encoding="utf-8") as fh:
            all_rows.extend(list(csv.DictReader(fh)))

    samples_by_id = {(s.dataset, s.query_id): s for s in samples}
    progress_rows = []
    t0 = time.time()
    n_done = 0
    for i, cell in enumerate(factor_cells):
        if _STOP["flag"]:
            break
        if global_spend[0] >= MAX_USD:
            update_status(status_path, phase="stopped_usd_ceiling", spend_usd=global_spend[0])
            break
        if ceiling.stopped_reason:
            update_status(status_path, phase="stopped_ceiling", reason=ceiling.stopped_reason)
            break
        sample = samples_by_id[(cell["dataset"], cell["query_id"])]
        rows = process_cell(
            output_dir=output_dir,
            sample=sample,
            provider=cell["provider"],
            model=cell["model"],
            prompt_version=cell["prompt_version"],
            orientation=cell["orientation"],
            mp_judge=mp_judge,
            circuits=circuits,
            provider_spend=provider_spend,
            global_spend=global_spend,
            qrels_map=qrels_map,
            completed=completed,
        )
        all_rows.extend([r for r in rows if "policy" in r])
        n_done += 1
        progress_rows.append(
            {
                "i": i,
                "cell_id": cell["cell_id"],
                "spend_usd": global_spend[0],
                "unique_calls_global": ceiling.new_calls_global,
                "ts": _utc(),
            }
        )
        if n_done % 1 == 0:
            _write_csv(output_dir / "PROGRESS.csv", progress_rows)
            _write_csv(output_dir / "CELL_SUMMARY.csv", [r for r in all_rows if "policy" in r])
            update_status(
                status_path,
                phase="acquisition",
                completed_cells=len(completed),
                cell_index=i,
                spend_usd=global_spend[0],
                provider_spend=provider_spend,
                successful_calls=ceiling.new_calls_global,
                api_failures=_count_api_failures(output_dir / "FAILURES.jsonl"),
                data_skips=_count_skips(output_dir / "SKIPS.jsonl", output_dir / "FAILURES.jsonl"),
                failures=_count_api_failures(output_dir / "FAILURES.jsonl"),
                circuits={
                    p: {"broken": circuits[p].broken, "reason": circuits[p].reason}
                    for p in providers
                },
                elapsed_s=time.time() - t0,
                providers=providers,
            )

    # Offline analysis
    update_status(status_path, phase="analysis")
    # Archive prior truncated report once before overwrite.
    final_path = output_dir / "FINAL_REPORT.md"
    if final_path.exists() and not (output_dir / "FINAL_REPORT.partial_pre_repair.md").exists():
        final_path.replace(output_dir / "FINAL_REPORT.partial_pre_repair.md")
    policy_rows = [
        r
        for r in all_rows
        if r.get("policy") in POLICIES and r.get("utility") not in (None, "")
    ]
    # coerce
    for r in policy_rows:
        try:
            r["utility"] = float(r["utility"])
            r["budget"] = int(float(r["budget"]))
        except Exception:  # noqa: BLE001
            pass
    analysis = analyze_cell_summaries(policy_rows) if policy_rows else {"policy_summaries": []}
    comparison_rows = [
        r
        for r in all_rows
        if r.get("policy")
        in (
            "UHT",
            "CHALLENGER",
            "HYBRID",
            "ROBUST_COMBINED",
            "plain_uht",
            "production_uht",
            "always_unrepaired",
        )
        and r.get("budget") not in (None, "")
    ]
    for r in comparison_rows:
        try:
            if r.get("utility") not in (None, ""):
                r["utility"] = float(r["utility"])
            r["budget"] = int(float(r["budget"]))
        except Exception:  # noqa: BLE001
            pass
    comparison_table = build_policy_comparison_table(
        comparison_rows,
        baseline_policy="production_uht",
        policies=(
            "production_uht",
            "plain_uht",
            "UHT",
            "CHALLENGER",
            "HYBRID",
            "ROBUST_COMBINED",
            "always_unrepaired",
        ),
        budgets=tuple(BUDGETS),
    )
    verdict_detail = render_verdict(comparison_table)
    _write_json(
        output_dir / "ANALYSIS.json",
        {
            **analysis,
            "comparison_table": comparison_table,
            "verdict_detail": verdict_detail,
        },
    )

    n_complete_cells = len(completed)
    planned = len(factor_cells)
    if (output_dir / "MANIFEST.json").exists():
        try:
            planned = int(
                json.loads((output_dir / "MANIFEST.json").read_text()).get(
                    "n_factor_cells", planned
                )
            )
        except Exception:  # noqa: BLE001
            planned = max(planned, 240)
    if n_complete_cells >= planned and not _STOP["flag"]:
        verdict = str(verdict_detail.get("verdict") or "INCONCLUSIVE")
    else:
        verdict = "BLOCKED — INCOMPLETE MATCHED ACQUISITION"
        verdict_detail = {
            **verdict_detail,
            "verdict": verdict,
            "reason": "Incomplete matched acquisition coverage.",
        }

    write_final_report(
        output_dir / "FINAL_REPORT.md",
        {
            "verdict": verdict,
            "verdict_detail": verdict_detail,
            "comparison_table": comparison_table,
            "evaluation_contract": analysis.get("evaluation_contract"),
            "coverage": {
                "planned_cells": planned,
                "completed_cells": n_complete_cells,
                "providers": selected,
                "prompts": list(PROMPTS),
                "orientations": list(ORIENTATIONS),
                "budgets": list(BUDGETS),
                "queries": len(samples),
                "quotas": QUOTAS,
                "depth_heterogeneity_note": (
                    "effective_depth = min(12, usable candidate texts); "
                    "FiQA may be reduced-depth; see FACTOR_CELLS.csv / QUERY_SAMPLE.csv."
                ),
                "cohere_complete": sum(1 for c in completed if "|cohere|" in c),
                "azure_complete": sum(1 for c in completed if "|azure|" in c),
            },
            "cost": {
                "spend_usd": global_spend[0],
                "provider_spend": provider_spend,
                "calls": ceiling.summary(),
                "projection": projection,
                "elapsed_s": time.time() - t0,
            },
            "policy_results": analysis,
            "criteria": {
                "note": (
                    "Prespecified comparison covers CHALLENGER, HYBRID, and "
                    "ROBUST_COMBINED against production_uht on matched nDCG; "
                    "neural router forbidden."
                )
            },
            "transfer": {"providers": providers, "prompts": list(PROMPTS)},
            "safeguards": {
                "note": (
                    "plain_uht vs production_uht rows in CELL_SUMMARY.csv; "
                    "safeguard metadata distinguishes required/attempted/executed/skipped."
                )
            },
        },
    )
    incomplete_bits = []
    if n_complete_cells < planned:
        incomplete_bits.append(
            f"Completed {n_complete_cells}/{planned} factor cells."
        )
    if _STOP["flag"]:
        incomplete_bits.append("Stopped on signal (wall-clock or STOP.sh).")
    if any(circuits[p].broken for p in providers):
        incomplete_bits.append(
            "Circuit breakers: "
            + json.dumps({p: circuits[p].reason for p in providers if circuits[p].broken})
        )
    if not incomplete_bits:
        incomplete_bits.append(
            "All planned factor cells completed; no missing cells were silently filled."
        )
    (output_dir / "INCOMPLETE.md").write_text(
        "# INCOMPLETE\n\n" + "\n".join(f"- {b}" for b in incomplete_bits) + "\n",
        encoding="utf-8",
    )
    update_status(
        status_path,
        phase="done",
        verdict=verdict,
        spend_usd=global_spend[0],
        completed_cells=n_complete_cells,
        elapsed_s=time.time() - t0,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
