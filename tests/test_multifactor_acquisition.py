"""Tests for multifactor acquisition sampling and pricing (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from consistency_ranker.multifactor_acquisition.pricing import estimate_usd, project_spend
from consistency_ranker.multifactor_acquisition.sampling import (
    QUOTAS,
    SEED,
    sample_queries,
)


def test_pricing_known_providers():
    assert estimate_usd("azure", 1_000_000, 0) == 0.40
    assert estimate_usd("cohere", 0, 1_000_000) == 10.0
    proj = project_spend(
        providers=["azure", "cohere"],
        max_calls=100,
        prompt_tokens_low=100,
        prompt_tokens_exp=200,
        prompt_tokens_max=400,
        completion_tokens=10,
    )
    assert proj["usd_maximum"] >= proj["usd_expected"] >= proj["usd_low"]
    assert proj["usd_maximum"] < 20.0


@pytest.mark.real_data
def test_sample_queries_quotas_deterministic():
    repo = Path(__file__).resolve().parents[1]
    a, _ = sample_queries(repo, seed=SEED, quotas=QUOTAS)
    b, _ = sample_queries(repo, seed=SEED, quotas=QUOTAS)
    assert len(a) == 30
    assert [s.query_id for s in a] == [s.query_id for s in b]
    from collections import Counter

    c = Counter(s.dataset for s in a)
    assert c == QUOTAS
    # original-query uniqueness
    assert len({s.query_id for s in a}) == 30
