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


def _check_openai_probe(key_present: bool, import_ok: bool) -> tuple[bool, str]:
    if not key_present:
        return False, "blocked: OPENAI_API_KEY absent"
    if not import_ok:
        return False, "blocked: openai import missing"

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
        return True, f"ok: received response '{text[:20]}'"
    except Exception as exc:
        name = exc.__class__.__name__
        msg = str(exc).lower()
        if "authentication" in msg or "invalid api key" in msg or name in {"AuthenticationError"}:
            category = "auth_error"
        elif "model" in msg and ("not found" in msg or "access" in msg):
            category = "model_access_error"
        elif (
            "connection" in msg
            or "timeout" in msg
            or name in {"APIConnectionError", "APITimeoutError"}
        ):
            category = "network_error"
        elif "rate limit" in msg or name == "RateLimitError":
            category = "rate_limit_error"
        else:
            category = "api_error"
        return False, f"{category}: {name}: {exc}"


def _check_hf_probe(token_present: bool, import_ok: bool) -> tuple[bool, str]:
    if not token_present:
        return False, "blocked: HF_TOKEN absent"
    if not import_ok:
        return False, "blocked: huggingface_hub import missing"

    try:
        from huggingface_hub import HfApi

        token = os.environ.get("HF_TOKEN")
        api = HfApi(token=token)
        info = api.whoami(token=token)
        name = info.get("name") if isinstance(info, dict) else str(info)
        return True, f"ok: authenticated as {name}"
    except Exception as exc:
        name = exc.__class__.__name__
        msg = str(exc).lower()
        if "401" in msg or "unauthorized" in msg or "invalid" in msg:
            category = "auth_error"
        elif "connection" in msg or "timeout" in msg:
            category = "network_error"
        else:
            category = "api_error"
        return False, f"{category}: {name}: {exc}"


def main() -> int:
    output_dir = Path("outputs/api_readiness_check")
    output_dir.mkdir(parents=True, exist_ok=True)

    openai_key_present = _present("OPENAI_API_KEY")
    hf_token_present = _present("HF_TOKEN")

    openai_import_ok, openai_import_msg = _import_status("openai")
    hfhub_import_ok, hfhub_import_msg = _import_status("huggingface_hub")
    datasets_import_ok, datasets_import_msg = _import_status("datasets")

    openai_probe_ok, openai_probe_msg = _check_openai_probe(openai_key_present, openai_import_ok)
    hf_probe_ok, hf_probe_msg = _check_hf_probe(hf_token_present, hfhub_import_ok)

    blocking: list[str] = []
    if not openai_key_present:
        blocking.append("OPENAI_API_KEY is absent")
    if not hf_token_present:
        blocking.append("HF_TOKEN is absent")
    if not openai_import_ok:
        blocking.append("Python package 'openai' is not importable")
    if not hfhub_import_ok:
        blocking.append("Python package 'huggingface_hub' is not importable")
    if not openai_probe_ok:
        blocking.append(f"OpenAI probe failed: {openai_probe_msg}")
    if not hf_probe_ok:
        blocking.append(f"Hugging Face probe failed: {hf_probe_msg}")

    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "credentials": {
            "OPENAI_API_KEY_present": openai_key_present,
            "HF_TOKEN_present": hf_token_present,
        },
        "imports": {
            "openai": {"ok": openai_import_ok, "message": openai_import_msg},
            "huggingface_hub": {"ok": hfhub_import_ok, "message": hfhub_import_msg},
            "datasets": {"ok": datasets_import_ok, "message": datasets_import_msg},
        },
        "probes": {
            "openai": {
                "attempted": openai_key_present and openai_import_ok,
                "ok": openai_probe_ok,
                "message": openai_probe_msg,
            },
            "huggingface": {
                "attempted": hf_token_present and hfhub_import_ok,
                "ok": hf_probe_ok,
                "message": hf_probe_msg,
            },
        },
        "ready_for_small_llm_pairwise_experiment": bool(openai_probe_ok),
        "blocking_issues": blocking,
    }

    (output_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# API Readiness Check",
        "",
        f"- OPENAI_API_KEY present: **{'yes' if openai_key_present else 'no'}**",
        f"- HF_TOKEN present: **{'yes' if hf_token_present else 'no'}**",
        f"- openai import works: **{'yes' if openai_import_ok else 'no'}** ({openai_import_msg})",
        (
            f"- huggingface_hub import works: **{'yes' if hfhub_import_ok else 'no'}** "
            f"({hfhub_import_msg})"
        ),
        (
            f"- datasets import works: **{'yes' if datasets_import_ok else 'no'}** "
            f"({datasets_import_msg})"
        ),
        f"- OpenAI probe works: **{'yes' if openai_probe_ok else 'no'}** ({openai_probe_msg})",
        f"- Hugging Face probe works: **{'yes' if hf_probe_ok else 'no'}** ({hf_probe_msg})",
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
