"""Small environment/API readiness check for OpenAI + Hugging Face."""

from __future__ import annotations

import importlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path


def _present(name: str) -> bool:
    return bool(os.environ.get(name))


def _import_status(module_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module_name)
        return True, "ok"
    except Exception as exc:
        return False, f"import_error: {exc.__class__.__name__}: {exc}"


def _check_openai_probe(key_present: bool, import_ok: bool) -> tuple[bool, str, str]:
    if not key_present:
        return False, "missing_key", "blocked: OPENAI_API_KEY absent"
    if not import_ok:
        return False, "missing_import", "blocked: openai import missing"

    try:
        import openai  # type: ignore

        client = openai.OpenAI()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Reply with the single letter A."}],
            max_tokens=1,
            temperature=0,
        )
        text = ""
        if getattr(resp, "choices", None):
            text = (resp.choices[0].message.content or "").strip()
        return True, "ok", f"ok: received response '{text[:20]}'"
    except Exception as exc:
        name = exc.__class__.__name__
        msg = str(exc).lower()
        if "authentication" in msg or "invalid api key" in msg or name in {"AuthenticationError"}:
            category = "auth_failure"
        elif "model" in msg and ("not found" in msg or "access" in msg):
            category = "model_access_failure"
        elif (
            "connection" in msg
            or "timeout" in msg
            or name in {"APIConnectionError", "APITimeoutError"}
        ):
            category = "network_failure"
        elif "rate limit" in msg or name == "RateLimitError":
            category = "rate_limit_failure"
        else:
            category = "api_failure"
        return False, category, f"{category}: {name}: {exc}"


def _check_hf_probe(token_present: bool, import_ok: bool) -> tuple[bool, str, str]:
    if not token_present:
        return False, "missing_token", "blocked: HF_TOKEN absent"
    if not import_ok:
        return False, "missing_import", "blocked: huggingface_hub import missing"

    try:
        from huggingface_hub import HfApi

        token = os.environ.get("HF_TOKEN")
        api = HfApi(token=token)
        info = api.whoami(token=token)
        name = info.get("name") if isinstance(info, dict) else str(info)
        return True, "ok", f"ok: authenticated as {name}"
    except Exception as exc:
        name = exc.__class__.__name__
        msg = str(exc).lower()
        if "401" in msg or "unauthorized" in msg or "invalid" in msg:
            category = "auth_failure"
        elif "connection" in msg or "timeout" in msg:
            category = "network_failure"
        else:
            category = "api_failure"
        return False, category, f"{category}: {name}: {exc}"


def main() -> int:
    output_dir = Path("outputs/api_readiness_check")
    output_dir.mkdir(parents=True, exist_ok=True)

    openai_key_present = _present("OPENAI_API_KEY")
    hf_token_present = _present("HF_TOKEN")

    openai_import_ok, openai_import_msg = _import_status("openai")
    hfhub_import_ok, hfhub_import_msg = _import_status("huggingface_hub")
    datasets_import_ok, datasets_import_msg = _import_status("datasets")

    openai_probe_ok, openai_probe_category, openai_probe_msg = _check_openai_probe(
        openai_key_present, openai_import_ok
    )
    hf_probe_ok, hf_probe_category, hf_probe_msg = _check_hf_probe(
        hf_token_present, hfhub_import_ok
    )

    openai_probe_attempted = openai_key_present and openai_import_ok
    hf_probe_attempted = hf_token_present and hfhub_import_ok

    blocking: list[str] = []
    if not openai_key_present:
        blocking.append("OPENAI_API_KEY is absent")
    if not hf_token_present:
        blocking.append("HF_TOKEN is absent")
    if not openai_import_ok:
        blocking.append("Python package 'openai' is not importable")
    if not hfhub_import_ok:
        blocking.append("Python package 'huggingface_hub' is not importable")
    if not datasets_import_ok:
        blocking.append("Python package 'datasets' is not importable")
    if not openai_probe_ok:
        blocking.append(f"OpenAI probe failed: {openai_probe_msg}")
    if not hf_probe_ok:
        blocking.append(f"Hugging Face probe failed: {hf_probe_msg}")

    ready_for_small_llm_pairwise_experiment = bool(
        openai_probe_ok
        and hf_probe_ok
        and openai_key_present
        and hf_token_present
        and openai_import_ok
        and hfhub_import_ok
        and datasets_import_ok
    )

    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "OPENAI_API_KEY_present": openai_key_present,
        "HF_TOKEN_present": hf_token_present,
        "openai_import_ok": openai_import_ok,
        "openai_import_message": openai_import_msg,
        "huggingface_hub_import_ok": hfhub_import_ok,
        "huggingface_hub_import_message": hfhub_import_msg,
        "datasets_import_ok": datasets_import_ok,
        "datasets_import_message": datasets_import_msg,
        "openai_probe_attempted": openai_probe_attempted,
        "openai_probe_success": openai_probe_ok if openai_probe_attempted else False,
        "openai_probe_category": openai_probe_category,
        "openai_probe_message": openai_probe_msg,
        "hf_probe_attempted": hf_probe_attempted,
        "hf_probe_success": hf_probe_ok if hf_probe_attempted else False,
        "hf_probe_category": hf_probe_category,
        "hf_probe_message": hf_probe_msg,
        "ready_for_small_llm_pairwise_experiment": ready_for_small_llm_pairwise_experiment,
        "blocking_issues": blocking,
    }

    (output_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# API Readiness Check",
        "",
        f"- OPENAI_API_KEY_present: **{'yes' if openai_key_present else 'no'}**",
        f"- HF_TOKEN_present: **{'yes' if hf_token_present else 'no'}**",
        f"- openai_import_ok: **{'yes' if openai_import_ok else 'no'}** ({openai_import_msg})",
        (
            f"- huggingface_hub_import_ok: **{'yes' if hfhub_import_ok else 'no'}** "
            f"({hfhub_import_msg})"
        ),
        (
            f"- datasets_import_ok: **{'yes' if datasets_import_ok else 'no'}** "
            f"({datasets_import_msg})"
        ),
        (
            f"- openai_probe_attempted: **{'yes' if openai_probe_attempted else 'no'}**; "
            f"success: **{'yes' if openai_probe_ok and openai_probe_attempted else 'no'}** "
            f"({openai_probe_category}: {openai_probe_msg})"
        ),
        (
            f"- hf_probe_attempted: **{'yes' if hf_probe_attempted else 'no'}**; "
            f"success: **{'yes' if hf_probe_ok and hf_probe_attempted else 'no'}** "
            f"({hf_probe_category}: {hf_probe_msg})"
        ),
        (
            "- ready_for_small_llm_pairwise_experiment: "
            f"**{'yes' if ready_for_small_llm_pairwise_experiment else 'no'}**"
        ),
        "",
        "## Blocking issues",
    ]
    if blocking:
        lines.extend([f"- {b}" for b in blocking])
    else:
        lines.append("- None")

    (output_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
