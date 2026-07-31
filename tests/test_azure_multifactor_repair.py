"""Focused regression tests for Azure multifactor repair (no billed calls)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from consistency_ranker.multi_provider_eval.parsing import (
    PARSER_VERSION,
    classify_raw_response,
    parse_pairwise_response,
    parse_pairwise_response_detailed,
)
from consistency_ranker.multifactor_acquisition.analyze import write_final_report
from consistency_ranker.multifactor_acquisition.azure_request import (
    AZURE_MAX_TOKENS_V1,
    AZURE_REQUEST_PROFILE,
    AZURE_SYSTEM_MESSAGE_V1,
)
from consistency_ranker.multifactor_acquisition.completion import (
    effective_depth_for_docs,
    is_cell_complete_from_rows,
)
from consistency_ranker.multifactor_acquisition.live_judge import CircuitState
from consistency_ranker.multifactor_acquisition.reparse import reparse_raw_responses
from consistency_ranker.multifactor_acquisition.sampling import effective_depth

FIXTURES = Path(__file__).parent / "fixtures" / "azure_multifactor_raw_responses.json"


@pytest.fixture(scope="module")
def azure_fixtures():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


class TestAzureResponseCategories:
    def test_exact_labels(self, azure_fixtures):
        labels = [f for f in azure_fixtures if f["raw_response"] in {"A", "B"}]
        assert labels
        for f in labels:
            cat = classify_raw_response(f["raw_response"])
            assert cat == "exact_label"
            c, _, note, fmt = parse_pairwise_response_detailed(f["raw_response"])
            assert c in {"A", "B"}
            assert fmt == "exact_label"

    def test_truncated_neither_prose_unusable(self, azure_fixtures):
        bad = [
            f
            for f in azure_fixtures
            if f["completion_tokens"] == 32 and not f["valid_original"]
        ]
        assert len(bad) == 8
        for f in bad:
            cat = classify_raw_response(
                f["raw_response"],
                completion_tokens=f["completion_tokens"],
                max_tokens=f["max_tokens"],
            )
            assert cat == "truncated_output"
            c, _, note, fmt = parse_pairwise_response_detailed(
                f["raw_response"],
                completion_tokens=f["completion_tokens"],
                max_tokens=f["max_tokens"],
            )
            assert c == "INVALID"
            assert note in {"truncated_output", "ambiguous_or_malformed"}

    def test_no_fuzzy_prose_guessing(self):
        prose = (
            "Neither A nor B is relevant to the query about classical musicians. "
            "However, since the instruction requires a choice, document A is "
            "slightly less irrelevant overall when considering peak experiences."
        )
        # Without an exact final-line label, must remain INVALID.
        c, _, note, _ = parse_pairwise_response_detailed(prose)
        assert c == "INVALID"

    def test_exact_last_line_label_accepted(self):
        text = "Both passages are weak.\nA"
        c, _, note, fmt = parse_pairwise_response_detailed(text)
        assert c == "A" and note == "exact_last_line_label"

    def test_fenced_json(self):
        text = '```json\n{"choice":"B"}\n```'
        c, _, note, fmt = parse_pairwise_response_detailed(text, structured_json=True)
        assert c == "B" and fmt == "fenced_json"

    def test_strict_json(self):
        c, _, note, fmt = parse_pairwise_response_detailed(
            '{"choice":"A"}', structured_json=True
        )
        assert c == "A" and fmt == "strict_json"


class TestOfflineReparse:
    def test_reparse_does_not_recover_truncated(self, tmp_path, azure_fixtures):
        raw = tmp_path / "RAW_RESPONSES.jsonl"
        with raw.open("w", encoding="utf-8") as fh:
            for f in azure_fixtures:
                fh.write(
                    json.dumps(
                        {
                            "provider": "azure",
                            "raw_response": f["raw_response"],
                            "completion_tokens": f["completion_tokens"],
                            "max_tokens": f["max_tokens"],
                            "valid": f["valid_original"],
                            "prompt_version": f["prompt_version"],
                            "cell_identity": f["id"],
                            "cache_key": f["id"],
                        }
                    )
                    + "\n"
                )
        before = raw.read_text(encoding="utf-8")
        summary = reparse_raw_responses(raw, provider="azure", out_path=tmp_path / "out.jsonl")
        after = raw.read_text(encoding="utf-8")
        assert before == after
        assert summary["examined"] == 20
        assert summary["newly_valid_vs_original"] == 0
        assert summary["unusable"] == 8
        assert summary["valid_after_reparse"] == 12
        assert summary["parser_version"] == PARSER_VERSION


class TestAzureRequestConfig:
    def test_compact_profile_constants(self):
        assert AZURE_MAX_TOKENS_V1 >= 8
        assert AZURE_MAX_TOKENS_V1 <= 64
        assert "A or B" in AZURE_SYSTEM_MESSAGE_V1
        assert AZURE_REQUEST_PROFILE.startswith("azure_compact")

    def test_pairwise_config_accepts_system_message(self):
        from rerankers.llm_pairwise import PairwiseConfig

        cfg = PairwiseConfig(
            provider="openai",
            model="gpt-4.1-mini",
            max_tokens=AZURE_MAX_TOKENS_V1,
            system_message=AZURE_SYSTEM_MESSAGE_V1,
        )
        assert cfg.system_message == AZURE_SYSTEM_MESSAGE_V1
        assert cfg.max_tokens == AZURE_MAX_TOKENS_V1


class TestCircuitBreakerDenominator:
    def test_fires_on_high_parse_failure_rate(self):
        from consistency_ranker.multifactor_acquisition.live_judge import LiveCellJudge

        c = CircuitState()
        for _ in range(20):
            c.recent_http_ok_malformed.append(1)
            c.recent_attempts.append(True)
        # Use a minimal harness via _check_circuits
        cell_judge = object.__new__(LiveCellJudge)
        cell_judge.circuit = c
        cell_judge.provider_spend = {"azure": 0.0}
        cell_judge.provider_spend_cap = 10.0
        LiveCellJudge._check_circuits(cell_judge)
        assert c.broken and c.reason == "malformed_output_rate"

    def test_missing_docs_do_not_enter_malformed_denominator(self):
        c = CircuitState()
        # Simulate only skips — malformed deque stays empty.
        c.accounting.missing_doc_text_skips = 100
        assert list(c.recent_http_ok_malformed) == []
        cell_judge = object.__new__(
            __import__(
                "consistency_ranker.multifactor_acquisition.live_judge",
                fromlist=["LiveCellJudge"],
            ).LiveCellJudge
        )
        cell_judge.circuit = c
        cell_judge.provider_spend = {"azure": 0.0}
        cell_judge.provider_spend_cap = 10.0
        from consistency_ranker.multifactor_acquisition.live_judge import LiveCellJudge

        LiveCellJudge._check_circuits(cell_judge)
        assert not c.broken

    def test_healthy_window_does_not_fire(self):
        from consistency_ranker.multifactor_acquisition.live_judge import LiveCellJudge

        c = CircuitState()
        for i in range(20):
            c.recent_attempts.append(True)
            c.recent_http_ok_malformed.append(1 if i < 2 else 0)  # 10% malformed
        cell_judge = object.__new__(LiveCellJudge)
        cell_judge.circuit = c
        cell_judge.provider_spend = {"azure": 0.0}
        cell_judge.provider_spend_cap = 10.0
        LiveCellJudge._check_circuits(cell_judge)
        assert not c.broken


class TestCompletedCellLogic:
    def _policy_rows(self, status="complete"):
        rows = []
        for policy in ("UHT", "CHALLENGER", "HYBRID", "ROBUST_COMBINED"):
            for budget in (3, 5, 8):
                rows.append(
                    {
                        "policy": policy,
                        "budget": budget,
                        "status": status,
                        "utility": 0.1 if status == "complete" else None,
                    }
                )
        return rows

    def test_fully_complete(self):
        ok, reason = is_cell_complete_from_rows(self._policy_rows(), effective_depth=12)
        assert ok

    def test_partial_orientation_stopped(self):
        rows = self._policy_rows()
        rows[-1]["status"] = "stopped"
        rows[-1]["utility"] = None
        ok, reason = is_cell_complete_from_rows(rows, effective_depth=12)
        assert not ok

    def test_one_missing_judgment_policy(self):
        rows = self._policy_rows()[:-1]
        ok, _ = is_cell_complete_from_rows(rows, effective_depth=12)
        assert not ok

    def test_effective_depth_below_min(self):
        ok, reason = is_cell_complete_from_rows(self._policy_rows(), effective_depth=1)
        assert not ok and "effective_depth" in reason


class TestEffectiveDepth:
    @pytest.mark.parametrize("n,expected", [(2, 2), (5, 5), (11, 11), (12, 12), (20, 12)])
    def test_depths(self, n, expected):
        assert effective_depth(n) == expected

    def test_doc_text_filter(self):
        docs = {"a": "x", "b": "", "c": "y", "d": "z"}
        assert effective_depth_for_docs(docs, top_k=12) == 3


class TestReportNoTruncation:
    def test_large_policy_results_not_cut(self, tmp_path):
        summaries = [
            {
                "policy": f"P{i}",
                "budget": 8,
                "provider": "cohere",
                "prompt_version": "legacy_v1",
                "n_query_units": 30,
                "mean_delta_vs_uht": 0.01 * i,
                "ci95_low": 0.0,
                "ci95_high": 0.02,
            }
            for i in range(80)
        ]
        path = tmp_path / "FINAL_REPORT.md"
        write_final_report(
            path,
            {
                "verdict": "TEST",
                "coverage": {"planned_cells": 240},
                "cost": {"spend_usd": 1.0},
                "policy_results": {"policy_summaries": summaries},
            },
        )
        text = path.read_text(encoding="utf-8")
        assert "P79" in text
        assert '"n_match' not in text  # no mid-token truncation artifact
        assert "ANALYSIS.json" in text


class TestResumeAllowlistAndDedup:
    def test_parse_backward_compat(self):
        # Old API still works
        c, _, note = parse_pairwise_response("B")
        assert c == "B"

    def test_provider_allowlist_cli_flag_present(self):
        src = Path("scripts/run_real_query_multifactor_acquisition.py").read_text()
        assert "--providers" in src
        assert "additional-max-calls" in src
        assert "additional-max-usd" in src
        assert "1300" in src
