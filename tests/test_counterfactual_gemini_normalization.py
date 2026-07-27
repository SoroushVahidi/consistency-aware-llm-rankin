"""Regression tests for the Gemini fenced-JSON normalization fix.

Diagnosed from reports/counterfactual_collector_canary_v1_20260727T145126Z:
azure/cohere/fireworks (all routed through an OpenAI-compatible
chat-completions endpoint) returned parseable bare-JSON judgments for the
same pair, while gemini-2.5-flash (routed through the native google-genai SDK
path, which is not configured with response_mime_type/response_schema) ended
in parse_failure. The canary retains only a sha256 of the raw Gemini
response (never the raw bytes, by design), so the literal text could not be
recovered -- these fixtures reconstruct the shape google-genai is documented
to produce by default (the whole judgment wrapped in a single ```json fence)
rather than replaying a captured payload.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from consistency_ranker.counterfactual_benchmark.collector import run_collection
from consistency_ranker.counterfactual_pilot.schema import extract_json_payload, validate_judgment

REPO_ROOT = Path(__file__).resolve().parents[1]
CANARY_CONFIG_PATH = REPO_ROOT / "configs" / "counterfactual_collector_canary_v1.json"

BARE_JUDGMENT = json.dumps(
    {
        "preference": "ABSTAIN",
        "confidence": 0.9,
        "evidence_strength": "strong",
        "reason_code": "unsupported",
    }
)
FENCED_JUDGMENT = f"```json\n{BARE_JUDGMENT}\n```"
FENCED_JUDGMENT_NO_LANG_TAG = f"```\n{BARE_JUDGMENT}\n```"
FENCED_JUDGMENT_SINGLE_LINE = f"```json{BARE_JUDGMENT}```"


# ---------------------------------------------------------------------------
# extract_json_payload unit behavior
# ---------------------------------------------------------------------------


def test_extract_json_payload_unwraps_full_response_fence() -> None:
    text, used = extract_json_payload(FENCED_JUDGMENT)
    assert used is True
    assert json.loads(text) == json.loads(BARE_JUDGMENT)


def test_extract_json_payload_unwraps_fence_without_language_tag() -> None:
    text, used = extract_json_payload(FENCED_JUDGMENT_NO_LANG_TAG)
    assert used is True
    assert json.loads(text) == json.loads(BARE_JUDGMENT)


def test_extract_json_payload_unwraps_single_line_fence() -> None:
    text, used = extract_json_payload(FENCED_JUDGMENT_SINGLE_LINE)
    assert used is True
    assert json.loads(text) == json.loads(BARE_JUDGMENT)


def test_extract_json_payload_is_noop_for_bare_json() -> None:
    text, used = extract_json_payload(BARE_JUDGMENT)
    assert used is False
    assert text == BARE_JUDGMENT


def test_extract_json_payload_does_not_unwrap_prose_plus_fence() -> None:
    """Only a fence wrapping the *entire* response is unwrapped -- this is
    not a general JSON-substring extractor. Explanatory prose around the
    fence must still fail downstream, matching validate_judgment's existing
    strictness for any other malformed shape."""
    raw = f"Here is my judgment:\n{FENCED_JUDGMENT}\nHope that helps!"
    text, used = extract_json_payload(raw)
    assert used is False
    with pytest.raises(json.JSONDecodeError):
        json.loads(text)


def test_extract_json_payload_does_not_repair_unclosed_fence() -> None:
    raw = f"```json\n{BARE_JUDGMENT}"  # missing closing fence
    text, used = extract_json_payload(raw)
    assert used is False
    with pytest.raises(json.JSONDecodeError):
        json.loads(text)


def test_fenced_judgment_still_passes_strict_schema_validation() -> None:
    text, _used = extract_json_payload(FENCED_JUDGMENT)
    validated = validate_judgment(json.loads(text))
    assert validated["preference"] == "ABSTAIN"
    assert validated["reason_code"] == "unsupported"


def _fence(obj: dict) -> str:
    return f"```json\n{json.dumps(obj)}\n```"


_INVALID_INNER_PAYLOADS = [
    # invalid preference enum
    _fence(
        {
            "preference": "MAYBE",
            "confidence": 0.9,
            "evidence_strength": "strong",
            "reason_code": "unsupported",
        }
    ),
    # missing reason_code
    _fence({"preference": "A", "confidence": 0.9, "evidence_strength": "strong"}),
    # confidence wrong type
    _fence(
        {
            "preference": "A",
            "confidence": "high",
            "evidence_strength": "strong",
            "reason_code": "other",
        }
    ),
    # confidence out of range
    _fence(
        {
            "preference": "A",
            "confidence": 1.5,
            "evidence_strength": "strong",
            "reason_code": "other",
        }
    ),
    # invalid evidence_strength enum
    _fence(
        {
            "preference": "A",
            "confidence": 0.9,
            "evidence_strength": "very strong",
            "reason_code": "other",
        }
    ),
    # malformed JSON even after unwrapping
    "```json\n{not valid json at all\n```",
]


@pytest.mark.parametrize("raw", _INVALID_INNER_PAYLOADS)
def test_fence_unwrap_never_lets_genuinely_invalid_payloads_through(raw: str) -> None:
    text, _used = extract_json_payload(raw)
    with pytest.raises((json.JSONDecodeError, ValueError)):
        validate_judgment(json.loads(text))


# ---------------------------------------------------------------------------
# End-to-end through the collector, using the real frozen canary config
# ---------------------------------------------------------------------------


def _fake_call_fn_with_fenced_gemini(prompt: str, config: object) -> tuple[str, object]:
    class _Usage:
        prompt_tokens = 300
        completion_tokens = 40

    if getattr(config, "provider", None) == "gemini":
        return FENCED_JUDGMENT, _Usage()
    return BARE_JUDGMENT, _Usage()


def test_gemini_fenced_response_now_normalizes_successfully(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for var in ("AZURE_OPENAI_API_KEY", "COHERE_API_KEY", "FIREWORKS_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(var, "fake")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.example.invalid")

    out_dir = tmp_path / "gemini_fence_fix"
    summary = run_collection(
        config_path=CANARY_CONFIG_PATH,
        output_dir=out_dir,
        mode="live",
        repo_root=REPO_ROOT,
        is_canary=True,
        call_fn=_fake_call_fn_with_fenced_gemini,
    )
    assert summary["successful"] == 4
    assert summary["failed_after_inference"] == 0

    judgments = {
        json.loads(line)["provider"]: json.loads(line)
        for line in (out_dir / "normalized_judgments.jsonl").read_text().splitlines()
        if line.strip()
    }
    gemini_j = judgments["gemini"]
    assert gemini_j["success"] is True
    assert gemini_j["parse_failed"] is False
    assert gemini_j["wrapper_extraction_used"] is True
    assert gemini_j["preference"] == "ABSTAIN"

    # Providers that never sent a fenced response must show no wrapper
    # extraction -- the fix is a conditional no-op for them, never a change
    # in behavior or strictness.
    for provider in ("azure", "cohere", "fireworks"):
        j = judgments[provider]
        assert j["success"] is True
        assert j["wrapper_extraction_used"] is False


def test_other_providers_unaffected_when_they_send_genuinely_malformed_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The fence-unwrap fix must not weaken azure/cohere/fireworks validation:
    if one of them ever sent malformed JSON, it must still fail exactly as
    before (this collector never attributes a fix to more than the one
    provider path that needed it)."""
    for var in ("AZURE_OPENAI_API_KEY", "COHERE_API_KEY", "FIREWORKS_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(var, "fake")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.example.invalid")

    def call_fn(prompt: str, config: object) -> tuple[str, object]:
        class _Usage:
            prompt_tokens = 300
            completion_tokens = 40

        if getattr(config, "provider", None) == "gemini":
            return FENCED_JUDGMENT, _Usage()
        return "this is not json and not fenced either", _Usage()

    out_dir = tmp_path / "gemini_fence_others_malformed"
    summary = run_collection(
        config_path=CANARY_CONFIG_PATH,
        output_dir=out_dir,
        mode="live",
        repo_root=REPO_ROOT,
        is_canary=True,
        call_fn=call_fn,
    )
    judgments = {
        json.loads(line)["provider"]: json.loads(line)
        for line in (out_dir / "normalized_judgments.jsonl").read_text().splitlines()
        if line.strip()
    }
    assert judgments["gemini"]["success"] is True
    for provider in ("azure", "cohere", "fireworks"):
        j = judgments[provider]
        assert j["success"] is False
        assert j["parse_failed"] is True
        assert j["wrapper_extraction_used"] is False
    assert summary["successful"] == 1
    assert summary["failed_after_inference"] == 3
