"""Unified multi-provider pairwise caller with provenance records."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Literal

from consistency_ranker.failure_mining.llm_runner import (
    _provider_call_config,
    classify_llm_error,
    detect_llm_providers,
    health_check_provider,
)
from consistency_ranker.multi_provider_eval.cache import (
    ProvenanceJudgmentStore,
    canonical_pair_id,
    make_cache_key,
)
from consistency_ranker.multi_provider_eval.parsing import (
    PARSER_VERSION,
    normalize_winner,
    parse_pairwise_response_detailed,
)
from consistency_ranker.multi_provider_eval.prompts import format_prompt, get_prompt
from consistency_ranker.multi_provider_eval.schema import JudgmentRecord
from consistency_ranker.multi_provider_eval.spending import SpendingCeiling
from consistency_ranker.multifactor_acquisition.azure_request import (
    AZURE_MAX_TOKENS_V1,
    AZURE_REQUEST_PROFILE,
    AZURE_SYSTEM_MESSAGE_V1,
)
from rerankers.llm_pairwise import PairwiseConfig, _call_llm

TARGET_PROVIDERS = ("azure", "cohere", "fireworks", "gemini")


def azure_request_kwargs() -> dict[str, Any]:
    """Provider-isolated Azure compact A/B request shaping."""
    return {
        "max_tokens": AZURE_MAX_TOKENS_V1,
        "system_message": AZURE_SYSTEM_MESSAGE_V1,
        "request_profile": AZURE_REQUEST_PROFILE,
    }


def discover_provider_models() -> dict[str, dict[str, Any]]:
    """Return configured model identifiers from env/config (no network)."""
    out: dict[str, dict[str, Any]] = {}
    for provider in TARGET_PROVIDERS:
        cfg = _provider_call_config(provider)
        tiers: dict[str, str] = {"default": str(cfg["model"])}
        if provider == "azure":
            strong = os.environ.get("AZURE_OPENAI_STRONG_DEPLOYMENT")
            if strong and strong != cfg["model"]:
                tiers["strong"] = strong
        out[provider] = {
            "family": cfg.get("family"),
            "mode": cfg.get("mode"),
            "tiers": tiers,
            "base_url_set": bool(cfg.get("base_url")),
            "vertex": bool(cfg.get("gemini_use_vertex")),
        }
    return out


def provider_credential_audit() -> list[dict[str, Any]]:
    statuses = detect_llm_providers(list(TARGET_PROVIDERS))
    return [
        {
            "provider": s.provider,
            "available": s.available,
            "reason": s.reason,
            "mode": s.mode,
        }
        for s in statuses
    ]


def smoke_test_providers(
    providers: list[str] | None = None,
) -> list[dict[str, Any]]:
    """One cheap live call per provider. Records failure categories."""
    providers = providers or list(TARGET_PROVIDERS)
    results = []
    for p in providers:
        t0 = time.perf_counter()
        result = health_check_provider(p)
        result["latency_seconds"] = time.perf_counter() - t0
        results.append(result)
    return results


def _build_pairwise_config(
    provider: str,
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    dry_run: bool = False,
    system_message: str | None = None,
) -> tuple[PairwiseConfig, dict[str, Any]]:
    call_cfg = _provider_call_config(provider)
    use_model = model or str(call_cfg["model"])
    mt = max_tokens
    if mt is None:
        mt = int(call_cfg.get("max_tokens_override") or 32)
    sys_msg = system_message
    kwargs: dict[str, Any] = dict(
        provider=call_cfg["family"],
        model=use_model,
        api_key=call_cfg.get("api_key"),
        base_url=call_cfg.get("base_url"),
        temperature=temperature,
        max_tokens=mt,
        dry_run=dry_run,
        gemini_use_vertex=bool(call_cfg.get("gemini_use_vertex", False)),
        vertex_project=call_cfg.get("vertex_project"),
        vertex_location=call_cfg.get("vertex_location"),
        extra_body=call_cfg.get("extra_body"),
        concurrency=1,
        system_message=sys_msg,
    )
    return PairwiseConfig(**kwargs), call_cfg


def _usage_tokens(usage: object | None) -> tuple[int, int, int]:
    if usage is None:
        return 0, 0, 0
    pt = int(getattr(usage, "prompt_tokens", 0) or 0)
    ct = int(getattr(usage, "completion_tokens", 0) or 0)
    tt = int(getattr(usage, "total_tokens", 0) or (pt + ct))
    return pt, ct, tt


class MultiProviderJudge:
    """Execute oriented pairwise comparisons with ceilings and resume cache."""

    def __init__(
        self,
        store: ProvenanceJudgmentStore,
        ceiling: SpendingCeiling,
        *,
        dry_run: bool = False,
        code_version: str = "multi_provider_eval_v1",
    ) -> None:
        self.store = store
        self.ceiling = ceiling
        self.dry_run = dry_run
        self.code_version = code_version

    def compare(
        self,
        *,
        provider: str,
        model: str | None,
        query_id: str,
        query_text: str,
        doc_a_id: str,
        doc_a_text: str,
        doc_b_id: str,
        doc_b_text: str,
        orientation: Literal["ab", "ba"],
        prompt_version: str,
        temperature: float = 0.0,
        top_p: float | None = None,
        max_tokens: int | None = None,
        seed: int | None = 0,
        repeat_index: int = 0,
        system_message: str | None = None,
        request_profile: str | None = None,
    ) -> JudgmentRecord:
        spec = get_prompt(prompt_version)
        # Azure multifactor defaults: compact A/B profile (isolated from Cohere
        # and from non-multifactor Azure callers).
        eff_max_tokens = max_tokens
        eff_system = system_message
        eff_profile = request_profile
        apply_azure_profile = provider == "azure" and (
            eff_profile is not None
            or str(self.code_version).startswith("multifactor_acquisition")
        )
        if apply_azure_profile:
            if eff_max_tokens is None:
                eff_max_tokens = AZURE_MAX_TOKENS_V1
            if eff_system is None:
                eff_system = AZURE_SYSTEM_MESSAGE_V1
            if eff_profile is None:
                eff_profile = AZURE_REQUEST_PROFILE
        config, call_cfg = _build_pairwise_config(
            provider,
            model=model,
            temperature=temperature,
            max_tokens=eff_max_tokens,
            dry_run=self.dry_run,
            system_message=eff_system if apply_azure_profile else system_message,
        )
        model_id = config.model
        if orientation == "ab":
            shown_a, shown_b = doc_a_text, doc_b_text
        else:
            shown_a, shown_b = doc_b_text, doc_a_text
        prompt = format_prompt(
            spec, query=query_text, document_a=shown_a, document_b=shown_b
        )
        code_v = self.code_version
        if eff_profile:
            code_v = f"{self.code_version}+{eff_profile}+{PARSER_VERSION}"
        cache_key = make_cache_key(
            provider=provider,
            model=model_id,
            prompt_version=prompt_version,
            query_id=query_id,
            doc_a_id=doc_a_id,
            doc_b_id=doc_b_id,
            orientation=orientation,
            temperature=temperature,
            top_p=top_p,
            max_tokens=config.max_tokens,
            seed=seed,
            code_version=code_v,
            repeat_index=repeat_index,
        )
        cached = self.store.get(cache_key)
        if cached is not None:
            fields = set(JudgmentRecord.__dataclass_fields__)
            payload = {k: v for k, v in cached.items() if k in fields}
            payload["from_cache"] = True
            return JudgmentRecord(**payload)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        pair_id = canonical_pair_id(query_id, doc_a_id, doc_b_id)

        if not self.ceiling.allow(provider):
            return JudgmentRecord(
                provider=provider,
                model=model_id,
                deployment_or_endpoint=call_cfg.get("base_url"),
                query_id=query_id,
                doc_a_id=doc_a_id,
                doc_b_id=doc_b_id,
                canonical_pair_id=pair_id,
                displayed_orientation=orientation,
                prompt_version=prompt_version,
                raw_response="",
                parsed_choice="INVALID",
                normalized_winner_id=None,
                tie_or_abstention=True,
                valid=False,
                temperature=temperature,
                top_p=top_p,
                max_tokens=config.max_tokens,
                seed=seed,
                timestamp_utc=ts,
                cache_key=cache_key,
                code_version=code_v,
                from_cache=False,
                error_category="budget_exhausted",
                error_message=self.ceiling.stopped_reason
                or f"provider_ceiling:{provider}",
            )

        raw = ""
        usage = None
        err_cat = None
        err_msg = None
        retries = 0
        t0 = time.perf_counter()
        try:
            if self.dry_run:
                # Deterministic mock respecting allow_tie occasionally.
                h = abs(hash(cache_key)) % 100
                if spec.allows_tie and h < 10:
                    raw = '{"choice":"TIE","confidence":"low"}'
                elif h < 50:
                    raw = (
                    "A" if not spec.structured_json
                    else '{"choice":"A","confidence":"medium"}'
                )
                else:
                    raw = (
                    "B" if not spec.structured_json
                    else '{"choice":"B","confidence":"medium"}'
                )
            else:
                raw, usage = _call_llm(prompt, config)
        except Exception as exc:
            err_cat = classify_llm_error(exc)
            err_msg = str(exc)[:500]
            raw = ""
        latency = time.perf_counter() - t0
        pt, ct, tt = _usage_tokens(usage)

        if err_cat:
            choice = "INVALID"
            conf = None
            note = err_cat
            fmt_cat = "incompatible_shape"
        else:
            choice, conf, note, fmt_cat = parse_pairwise_response_detailed(
                raw,
                allow_tie=spec.allows_tie,
                structured_json=spec.structured_json,
                completion_tokens=ct,
                max_tokens=config.max_tokens,
            )
        winner, abstain = normalize_winner(
            choice,
            doc_a_id=doc_a_id,
            doc_b_id=doc_b_id,
            orientation=orientation,
        )
        valid = choice in {"A", "B", "TIE", "INSUFFICIENT_INFORMATION"} and err_cat is None

        # Count live network attempts against ceilings (success or failure).
        if not self.dry_run:
            self.ceiling.record(provider, prompt_tokens=pt, completion_tokens=ct)

        rec = JudgmentRecord(
            provider=provider,
            model=model_id,
            deployment_or_endpoint=str(call_cfg.get("base_url") or call_cfg.get("mode") or ""),
            query_id=query_id,
            doc_a_id=doc_a_id,
            doc_b_id=doc_b_id,
            canonical_pair_id=pair_id,
            displayed_orientation=orientation,
            prompt_version=prompt_version,
            raw_response=raw,
            parsed_choice=choice,  # type: ignore[arg-type]
            normalized_winner_id=winner,
            tie_or_abstention=abstain,
            valid=valid,
            confidence_category=conf,
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=tt,
            latency_seconds=latency,
            retry_count=retries,
            seed=seed,
            temperature=temperature,
            top_p=top_p,
            max_tokens=config.max_tokens,
            timestamp_utc=ts,
            cache_key=cache_key,
            code_version=code_v,
            from_cache=False,
            error_category=err_cat,
            error_message=err_msg,
            extra={
                "parse_note": note,
                "repeat_index": repeat_index,
                "parser_version": PARSER_VERSION,
                "output_format_category": fmt_cat,
                "request_profile": eff_profile,
            },
        )
        self.store.put(rec)
        return rec
