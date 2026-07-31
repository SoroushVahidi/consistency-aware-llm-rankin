"""Conservative USD pricing for multifactor acquisition ceilings.

Rates are public list-price estimates used for hard spend caps — not invoices.
Fireworks / Gemini rates are intentionally conservative upper bounds.
"""

from __future__ import annotations

from typing import Any

# USD per 1M tokens (input, output)
PROVIDER_RATES_USD_PER_M: dict[str, dict[str, float]] = {
    "azure": {"in": 0.40, "out": 1.60, "model": "gpt-4.1-mini"},
    "cohere": {"in": 2.50, "out": 10.0, "model": "command-r-plus-08-2024"},
    # conservative upper bound for gpt-oss-120b class
    "fireworks": {"in": 0.90, "out": 0.90, "model": "accounts/fireworks/models/gpt-oss-120b"},
    # gemini-2.5-flash conservative
    "gemini": {"in": 0.30, "out": 2.50, "model": "gemini-2.5-flash"},
}


def estimate_usd(provider: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = PROVIDER_RATES_USD_PER_M.get(provider)
    if rates is None:
        raise KeyError(f"No pricing configured for provider={provider!r}")
    return (
        float(prompt_tokens) / 1e6 * rates["in"]
        + float(completion_tokens) / 1e6 * rates["out"]
    )


def project_spend(
    *,
    providers: list[str],
    max_calls: int,
    prompt_tokens_low: int,
    prompt_tokens_exp: int,
    prompt_tokens_max: int,
    completion_tokens: int,
) -> dict[str, Any]:
    """Split max_calls evenly across providers for projection."""
    n_p = max(1, len(providers))
    per = max_calls // n_p
    rem = max_calls - per * n_p
    rows = []
    totals = {"low": 0.0, "expected": 0.0, "maximum": 0.0}
    for i, p in enumerate(providers):
        n = per + (1 if i < rem else 0)
        low = n * estimate_usd(p, prompt_tokens_low, completion_tokens)
        exp = n * estimate_usd(p, prompt_tokens_exp, completion_tokens)
        mx = n * estimate_usd(p, prompt_tokens_max, completion_tokens)
        rows.append(
            {
                "provider": p,
                "planned_calls": n,
                "usd_low": round(low, 4),
                "usd_expected": round(exp, 4),
                "usd_maximum": round(mx, 4),
                "rates": PROVIDER_RATES_USD_PER_M[p],
            }
        )
        totals["low"] += low
        totals["expected"] += exp
        totals["maximum"] += mx
    return {
        "by_provider": rows,
        "usd_low": round(totals["low"], 4),
        "usd_expected": round(totals["expected"], 4),
        "usd_maximum": round(totals["maximum"], 4),
        "assumptions": {
            "prompt_tokens_low": prompt_tokens_low,
            "prompt_tokens_exp": prompt_tokens_exp,
            "prompt_tokens_max": prompt_tokens_max,
            "completion_tokens": completion_tokens,
            "max_calls": max_calls,
        },
    }
