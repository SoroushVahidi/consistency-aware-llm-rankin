"""Core provider-capability audit engine (fail-closed, ledger-capped)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

from consistency_ranker.experiment_cli import assert_offline_or_allowed, utc_stamp
from consistency_ranker.failure_mining.llm_runner import (
    _provider_call_config,
    detect_llm_providers,
)
from consistency_ranker.provider_capability.fixture import (
    CANDIDATE_A,
    CANDIDATE_B,
    FIXTURE_ID,
    PROMPT_VERSION,
    fixture_hash,
    fixture_payload,
    format_smoke_prompt,
    prompt_hash,
)
from consistency_ranker.provider_capability.ledger import LiveCallCapExceeded, LiveCallLedger
from consistency_ranker.provider_capability.parse_smoke import (
    map_preference_to_document,
    parse_smoke_response,
)
from consistency_ranker.provider_capability.sanitize import (
    env_names_for_provider,
    redact_text,
    sanitize_mapping,
    sanitize_model_identity,
)
from consistency_ranker.provider_capability.schema import (
    AUDIT_PROVIDERS,
    empty_capability_record,
)

# Optional injectable caller for tests: (prompt, config) -> (raw_text, usage)
CallFn = Callable[[str, Any], tuple[str, Any]]


def request_hash(
    *,
    provider: str,
    model: str | None,
    purpose: str,
    orientation: str,
    seed: int,
) -> str:
    blob = "|".join(
        [
            provider,
            str(model or ""),
            purpose,
            orientation,
            str(seed),
            prompt_hash(),
            fixture_hash(),
        ]
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _estimate_input_tokens(prompt: str) -> int:
    # Conservative char/4 estimate; ledger enforces hard token caps separately.
    return max(1, len(prompt) // 4)


def _usage_tokens(usage: object | None) -> tuple[int, int]:
    if usage is None:
        return 0, 0
    return (
        int(getattr(usage, "prompt_tokens", 0) or 0),
        int(getattr(usage, "completion_tokens", 0) or 0),
    )


def _dry_run_raw(*, orientation: str, seed: int) -> str:
    # Prefer A for ab, and after remap still doc_a for ba display swap.
    # orientation ba with preference B => doc_a.
    if orientation == "ab":
        pref = "A"
    else:
        pref = "B"
    return json.dumps(
        {
            "preference": pref,
            "confidence": 0.9,
            "evidence_strength": "strong",
            "reason_code": "direct_relevance",
            "dry_run": True,
            "seed": seed,
        }
    )


def inventory_providers(providers: list[str]) -> list[dict[str, Any]]:
    """Credential presence + configured model identity (no network)."""
    statuses = {s.provider: s for s in detect_llm_providers(providers)}
    rows = []
    for p in providers:
        st = statuses.get(p)
        cfg = _provider_call_config(p)
        reason = redact_text(st.reason if st else "unknown provider")
        rows.append(
            {
                "provider": p,
                "configured": bool(st and st.available),
                "auth_mode": getattr(st, "mode", None) if st else None,
                "reason": reason,
                "model_or_deployment": sanitize_model_identity(p, cfg.get("model")),
                "family": cfg.get("family"),
                "vertex_mode": bool(cfg.get("gemini_use_vertex")),
                "base_url_configured": bool(cfg.get("base_url")),
                "env_var_names": env_names_for_provider(p),
                # Never include api_key / project values.
            }
        )
    return rows


def _build_pairwise_config(provider: str, *, seed: int, max_tokens: int, dry_run: bool) -> Any:
    from rerankers.llm_pairwise import PairwiseConfig

    call_cfg = _provider_call_config(provider)
    kwargs: dict[str, Any] = dict(
        provider=call_cfg["family"],
        model=str(call_cfg["model"]),
        api_key=call_cfg.get("api_key"),
        base_url=call_cfg.get("base_url"),
        temperature=0.0,
        max_tokens=max_tokens,
        dry_run=dry_run,
        seed=seed,
        gemini_use_vertex=bool(call_cfg.get("gemini_use_vertex", False)),
        vertex_project=call_cfg.get("vertex_project"),
        vertex_location=call_cfg.get("vertex_location"),
        extra_body=call_cfg.get("extra_body"),
    )
    if call_cfg.get("max_tokens_override") is not None:
        kwargs["max_tokens"] = min(int(call_cfg["max_tokens_override"]), max_tokens)
    return PairwiseConfig(**kwargs)


def _one_judgment(
    *,
    provider: str,
    purpose: str,
    orientation: str,
    seed: int,
    mode: str,
    ledger: LiveCallLedger,
    max_tokens: int,
    call_fn: CallFn | None,
    judgments_path: Path,
) -> dict[str, Any]:
    cfg = _provider_call_config(provider)
    model = sanitize_model_identity(provider, cfg.get("model"))
    rh = request_hash(
        provider=provider,
        model=model,
        purpose=purpose,
        orientation=orientation,
        seed=seed,
    )
    if ledger.already_completed(rh) and mode == "live":
        return {
            "provider": provider,
            "purpose": purpose,
            "orientation": orientation,
            "request_hash": rh,
            "resumed": True,
            "success": True,
            "skipped_duplicate": True,
        }

    if orientation == "ab":
        doc_a, doc_b = CANDIDATE_A, CANDIDATE_B
    else:
        doc_a, doc_b = CANDIDATE_B, CANDIDATE_A
    prompt = format_smoke_prompt(document_a=doc_a, document_b=doc_b)
    est_in = _estimate_input_tokens(prompt)

    raw = ""
    usage = None
    err = None
    success = False
    parse: dict[str, Any] = {}
    latency = None
    is_retry = False
    pt = ct = 0

    if mode == "live":
        ledger.begin_request(
            provider=provider,
            purpose=purpose,
            request_hash=rh,
            estimated_input_tokens=est_in,
            max_output_tokens=max_tokens,
            is_retry=False,
        )
        t0 = time.perf_counter()
        fn = call_fn
        if fn is None:
            from rerankers.llm_pairwise import _call_llm

            fn = _call_llm

        def _attempt() -> tuple[str, Any]:
            config = _build_pairwise_config(
                provider, seed=seed, max_tokens=max_tokens, dry_run=False
            )
            return fn(prompt, config)

        try:
            raw, usage = _attempt()
            success = True
        except Exception as exc:  # noqa: BLE001
            err = redact_text(str(exc)[:400])
            raw, usage = "", None
            success = False
            ledger.finish_request(
                provider=provider,
                purpose=purpose,
                request_hash=rh,
                success=False,
                latency_seconds=time.perf_counter() - t0,
                parse_status="error",
                raw_response="",
                is_retry=False,
                error=err,
            )
            if ledger.max_retries_per_request >= 1:
                is_retry = True
                retry_hash = rh + ":retry"
                try:
                    ledger.begin_request(
                        provider=provider,
                        purpose=purpose + "_retry",
                        request_hash=retry_hash,
                        estimated_input_tokens=est_in,
                        max_output_tokens=max_tokens,
                        is_retry=True,
                    )
                    raw, usage = _attempt()
                    success = True
                    err = None
                    latency = time.perf_counter() - t0
                    pt, ct = _usage_tokens(usage)
                    parse = parse_smoke_response(raw)
                    ledger.finish_request(
                        provider=provider,
                        purpose=purpose + "_retry",
                        request_hash=retry_hash,
                        success=bool(parse.get("preference")),
                        prompt_tokens=pt,
                        completion_tokens=ct,
                        latency_seconds=latency,
                        parse_status=str(parse.get("parse_status")),
                        raw_response=raw,
                        is_retry=True,
                        error=None,
                    )
                    # Mark primary hash completed so resume skips the pair.
                    if parse.get("preference") is not None:
                        ledger.completed_request_hashes.add(rh)
                except LiveCallCapExceeded as cap_exc:
                    err = redact_text(str(cap_exc))
                    success = False
                except Exception as exc2:  # noqa: BLE001
                    err = redact_text(str(exc2)[:400])
                    success = False
                    latency = time.perf_counter() - t0
                    ledger.finish_request(
                        provider=provider,
                        purpose=purpose + "_retry",
                        request_hash=retry_hash,
                        success=False,
                        latency_seconds=latency,
                        parse_status="error",
                        raw_response="",
                        is_retry=True,
                        error=err,
                    )
            if not success:
                return {
                    "fixture_id": FIXTURE_ID,
                    "prompt_version": PROMPT_VERSION,
                    "provider": provider,
                    "model_or_deployment": model,
                    "purpose": purpose,
                    "orientation": orientation,
                    "seed": seed,
                    "request_hash": rh,
                    "success": False,
                    "preference_displayed": None,
                    "preference_document_id": None,
                    "parse_status": "error",
                    "structured_ok": False,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "latency_seconds": time.perf_counter() - t0,
                    "mode": mode,
                    "is_retry": is_retry,
                    "error": err,
                    "raw_response_hash": hashlib.sha256(b"").hexdigest(),
                }
            # successful retry already finished above; fall through to record
        else:
            latency = time.perf_counter() - t0
            pt, ct = _usage_tokens(usage)
            parse = parse_smoke_response(raw)
            ledger.finish_request(
                provider=provider,
                purpose=purpose,
                request_hash=rh,
                success=bool(parse.get("preference")),
                prompt_tokens=pt,
                completion_tokens=ct,
                latency_seconds=latency,
                parse_status=str(parse.get("parse_status")),
                raw_response=raw,
                is_retry=False,
                error=None,
            )
        if not parse:
            latency = time.perf_counter() - t0
            pt, ct = _usage_tokens(usage)
            parse = parse_smoke_response(raw)
    elif mode == "dry_run":
        raw = _dry_run_raw(orientation=orientation, seed=seed)
        parse = parse_smoke_response(raw)
        success = True
        latency = 0.0
        pt = ct = 0
    else:
        # cache-only: no call
        return {
            "provider": provider,
            "purpose": purpose,
            "orientation": orientation,
            "request_hash": rh,
            "success": False,
            "skipped": "cache_only",
            "parse_status": "skipped",
        }

    mapped = map_preference_to_document(parse.get("preference"), orientation=orientation)
    rec = {
        "fixture_id": FIXTURE_ID,
        "prompt_version": PROMPT_VERSION,
        "provider": provider,
        "model_or_deployment": model,
        "purpose": purpose,
        "orientation": orientation,
        "seed": seed,
        "request_hash": rh,
        "success": bool(success),
        "preference_displayed": parse.get("preference"),
        "preference_document_id": mapped,
        "confidence": parse.get("confidence"),
        "evidence_strength": parse.get("evidence_strength"),
        "reason_code": parse.get("reason_code"),
        "parse_status": parse.get("parse_status"),
        "structured_ok": parse.get("structured_ok"),
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "latency_seconds": latency,
        "mode": mode,
        "is_retry": is_retry,
        "error": err,
        "raw_response_hash": hashlib.sha256((raw or "").encode()).hexdigest(),
        # Never store raw response in the committed/normalized stream.
    }
    with judgments_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(sanitize_mapping(rec), default=str) + "\n")
    return rec


def run_provider_audit(
    *,
    providers: list[str],
    mode: str,
    out_dir: Path,
    seed: int = 42,
    max_total_live_calls: int = 16,
    max_live_calls_per_provider: int = 4,
    max_estimated_cost_usd: float | None = 2.0,
    max_input_tokens: int = 100_000,
    max_output_tokens_budget: int = 12_000,
    max_tokens_per_call: int = 128,
    allow_optional_call4: bool = False,
    call_fn: CallFn | None = None,
) -> dict[str, Any]:
    """Run inventory + bounded smoke protocol.

    Modes: ``cache_only``, ``dry_run``, ``live``.
    """
    if mode not in {"cache_only", "dry_run", "live"}:
        raise ValueError(mode)
    providers = [p for p in providers if p in AUDIT_PROVIDERS]
    if not providers:
        raise ValueError("No valid providers selected")

    judgments_path = out_dir / "judgments.jsonl"
    ledger = LiveCallLedger(
        max_total_live_calls=max_total_live_calls,
        max_live_calls_per_provider=max_live_calls_per_provider,
        max_estimated_cost_usd=max_estimated_cost_usd,
        max_total_input_tokens=max_input_tokens,
        max_total_output_tokens=max_output_tokens_budget,
        path=out_dir / "live_call_ledger.jsonl",
    )
    ledger.load()

    inventory = inventory_providers(providers)
    (out_dir / "fixture.json").write_text(
        json.dumps(fixture_payload(), indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "inventory.json").write_text(
        json.dumps(sanitize_mapping(inventory), indent=2) + "\n", encoding="utf-8"
    )

    capabilities: dict[str, dict[str, Any]] = {}
    all_judgments: list[dict[str, Any]] = []

    for inv in inventory:
        p = inv["provider"]
        cap = empty_capability_record(p)
        cap["configured"] = bool(inv["configured"])
        cap["model_or_deployment"] = inv["model_or_deployment"]
        cap["underlying_model_family"] = inv.get("family")
        if not inv["configured"]:
            cap["errors"].append("credentials_not_configured")
            cap["limitations"].append("No live or dry-run smoke executed.")
            capabilities[p] = cap
            continue

        if mode == "cache_only":
            cap["limitations"].append("cache_only: no smoke calls executed")
            capabilities[p] = cap
            continue

        # Call 1: structured AB
        try:
            j1 = _one_judgment(
                provider=p,
                purpose="structured_ab",
                orientation="ab",
                seed=seed,
                mode=mode,
                ledger=ledger,
                max_tokens=max_tokens_per_call,
                call_fn=call_fn,
                judgments_path=judgments_path,
            )
        except LiveCallCapExceeded as exc:
            cap["errors"].append(redact_text(str(exc)))
            capabilities[p] = cap
            continue
        all_judgments.append(j1)
        cap["live_requests_used"] = ledger.calls_by_provider.get(p, 0) if mode == "live" else 0
        if j1.get("success"):
            cap["authentication_verified"] = True
            cap["model_identity_verified"] = True
            cap["structured_output"]["supported"] = bool(j1.get("structured_ok"))
            cap["structured_output"]["verified"] = bool(j1.get("structured_ok"))
            cap["smoke_preference_ab"] = j1.get("preference_document_id")
            cap["token_usage_reported"] = (
                True
                if mode == "dry_run"
                else bool(j1.get("prompt_tokens") or j1.get("completion_tokens"))
            )
            if mode == "dry_run":
                # dry-run does not prove provider token reporting
                cap["token_usage_reported"] = None
            cap["latency_measured"] = j1.get("latency_seconds") is not None
            cap["seed"]["accepted"] = True  # accepted by client config; not verified
            cap["prompt_tokens"] += int(j1.get("prompt_tokens") or 0)
            cap["completion_tokens"] += int(j1.get("completion_tokens") or 0)
        else:
            cap["errors"].append(j1.get("error") or "structured_ab_failed")
            capabilities[p] = cap
            continue

        # Call 2: position swap BA
        try:
            j2 = _one_judgment(
                provider=p,
                purpose="position_swap_ba",
                orientation="ba",
                seed=seed,
                mode=mode,
                ledger=ledger,
                max_tokens=max_tokens_per_call,
                call_fn=call_fn,
                judgments_path=judgments_path,
            )
        except LiveCallCapExceeded as exc:
            cap["errors"].append(redact_text(str(exc)))
            capabilities[p] = cap
            continue
        all_judgments.append(j2)
        cap["live_requests_used"] = ledger.calls_by_provider.get(p, 0) if mode == "live" else 0
        if j2.get("success"):
            cap["position_swap"]["tested"] = True
            cap["smoke_preference_ba_mapped"] = j2.get("preference_document_id")
            cap["position_swap"]["document_identity_consistent"] = bool(
                j1.get("preference_document_id") == j2.get("preference_document_id")
            )
            # Position sensitive if document-level preference changes under swap.
            cap["position_swap"]["position_sensitive"] = (
                j1.get("preference_document_id") != j2.get("preference_document_id")
            )
            cap["prompt_tokens"] += int(j2.get("prompt_tokens") or 0)
            cap["completion_tokens"] += int(j2.get("completion_tokens") or 0)
        else:
            cap["errors"].append(j2.get("error") or "position_swap_failed")

        # Call 3: repeat AB
        try:
            j3 = _one_judgment(
                provider=p,
                purpose="repeat_ab",
                orientation="ab",
                seed=seed,
                mode=mode,
                ledger=ledger,
                max_tokens=max_tokens_per_call,
                call_fn=call_fn,
                judgments_path=judgments_path,
            )
        except LiveCallCapExceeded as exc:
            cap["errors"].append(redact_text(str(exc)))
            capabilities[p] = cap
            continue
        all_judgments.append(j3)
        cap["live_requests_used"] = ledger.calls_by_provider.get(p, 0) if mode == "live" else 0
        if j3.get("success"):
            cap["repeatability"]["tested"] = True
            cap["smoke_preference_ab_repeat"] = j3.get("preference_document_id")
            cap["repeatability"]["same_preference"] = (
                j1.get("preference_document_id") == j3.get("preference_document_id")
            )
            cap["prompt_tokens"] += int(j3.get("prompt_tokens") or 0)
            cap["completion_tokens"] += int(j3.get("completion_tokens") or 0)
        else:
            cap["errors"].append(j3.get("error") or "repeat_ab_failed")

        # Call 4 optional: skipped by default (no native Cohere Rerank adapter wired).
        if allow_optional_call4:
            cap["limitations"].append(
                "optional_call4_requested_but_no_native_rerank_adapter_wired; skipped"
            )
            cap["rerank_endpoint"]["available"] = None
            cap["rerank_endpoint"]["verified"] = False
        else:
            cap["rerank_endpoint"]["available"] = None
            cap["rerank_endpoint"]["verified"] = False
            cap["limitations"].append(
                "Native provider rerank endpoint not exercised (no adapter / Call 4 skipped)."
            )

        cap["logprobs"]["supported"] = None
        cap["logprobs"]["verified"] = False
        cap["limitations"].append("logprobs not tested in this audit")
        cap["estimated_cost_usd"] = None
        capabilities[p] = cap

    ledger_summary = ledger.summary()
    comparison = _build_comparison(capabilities, all_judgments, ledger_summary, mode)
    result = {
        "created_utc": utc_stamp(),
        "mode": mode,
        "fixture_id": FIXTURE_ID,
        "fixture_hash": fixture_hash(),
        "prompt_hash": prompt_hash(),
        "providers": providers,
        "capabilities": sanitize_mapping(capabilities),
        "comparison": sanitize_mapping(comparison),
        "ledger": sanitize_mapping(ledger_summary),
        "paid_api_calls": ledger_summary["total_live_calls"] if mode == "live" else 0,
        "live_calls_by_provider": ledger_summary["live_calls_by_provider"],
        "batch_jobs_submitted": 0,
        "note": (
            "These calls verify connectivity and instrumentation only. "
            "They do not establish provider ranking quality."
        ),
    }
    (out_dir / "capabilities.json").write_text(
        json.dumps(result["capabilities"], indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "comparison.json").write_text(
        json.dumps(result["comparison"], indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "ledger_summary.json").write_text(
        json.dumps(result["ledger"], indent=2) + "\n", encoding="utf-8"
    )
    return result


def _build_comparison(
    capabilities: dict[str, dict[str, Any]],
    judgments: list[dict[str, Any]],
    ledger: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    rows = []
    for p, cap in capabilities.items():
        rows.append(
            {
                "provider": p,
                "configured": cap.get("configured"),
                "authentication_verified": cap.get("authentication_verified"),
                "model_or_deployment": cap.get("model_or_deployment"),
                "structured_output_verified": (cap.get("structured_output") or {}).get(
                    "verified"
                ),
                "preference_ab": cap.get("smoke_preference_ab"),
                "preference_ba_mapped": cap.get("smoke_preference_ba_mapped"),
                "document_identity_consistent": (cap.get("position_swap") or {}).get(
                    "document_identity_consistent"
                ),
                "repeat_same_preference": (cap.get("repeatability") or {}).get(
                    "same_preference"
                ),
                "token_usage_reported": cap.get("token_usage_reported"),
                "latency_measured": cap.get("latency_measured"),
                "live_requests_used": cap.get("live_requests_used"),
                "errors": cap.get("errors"),
            }
        )
    return {
        "mode": mode,
        "rows": rows,
        "n_judgments_recorded": len(judgments),
        "ledger_totals": {
            "total_live_calls": ledger.get("total_live_calls"),
            "prompt_tokens": ledger.get("prompt_tokens"),
            "completion_tokens": ledger.get("completion_tokens"),
            "estimated_cost_usd": ledger.get("estimated_cost_usd"),
        },
        "scientific_disclaimer": (
            "These calls verify connectivity and instrumentation only. "
            "They do not establish provider ranking quality."
        ),
    }


def render_final_report(result: dict[str, Any]) -> str:
    lines = [
        "# Provider capability audit — FINAL REPORT",
        "",
        f"Generated: `{result.get('created_utc')}`",
        f"Mode: `{result.get('mode')}`",
        "",
        "> These calls verify connectivity and instrumentation only. "
        "They do **not** establish provider ranking quality.",
        "",
        "## Caps and safety",
        "",
        f"- paid_api_calls: `{result.get('paid_api_calls')}`",
        f"- live_calls_by_provider: `{result.get('live_calls_by_provider')}`",
        f"- batch_jobs_submitted: `{result.get('batch_jobs_submitted')}`",
        f"- estimated_cost_usd: `{((result.get('ledger') or {}).get('estimated_cost_usd'))}` "
        f"(unknown when provider prices are unavailable)",
        "",
        "## Per-provider summary",
        "",
        "| Prov | Cfg | Auth | Model | Struct | AB | BA | Consist | Repeat | N |",
        "|---|---|---|---|---|---|---|---|---|---:|",
    ]
    for row in (result.get("comparison") or {}).get("rows") or []:
        lines.append(
            (
                f"| {row.get('provider')} | {row.get('configured')} | "
                f"{row.get('authentication_verified')} | "
                f"`{row.get('model_or_deployment')}` | "
                f"{row.get('structured_output_verified')} | "
                f"{row.get('preference_ab')} | {row.get('preference_ba_mapped')} | "
                f"{row.get('document_identity_consistent')} | "
                f"{row.get('repeat_same_preference')} | "
                f"{row.get('live_requests_used')} |"
            )
        )
    lines += [
        "",
        "## Limitations",
        "",
        "- One synthetic pair; no IR quality claims.",
        "- Seed acceptance ≠ determinism verification.",
        "- logprobs and native rerank left unknown when not tested.",
        "- Project IDs, endpoints, and credentials are redacted.",
        "",
    ]
    return "\n".join(lines)


def resolve_mode(
    *,
    allow_provider_calls: bool,
    dry_run: bool,
    cache_only: bool,
) -> str:
    return assert_offline_or_allowed(
        allow_provider_calls=allow_provider_calls,
        dry_run=dry_run,
        cache_only=cache_only,
    )
