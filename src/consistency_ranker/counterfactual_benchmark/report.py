"""Output-directory writers: plan, ledger-adjacent artifacts, and FINAL_REPORT.md."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

NON_CLAIMS = (
    "provider superiority",
    "policy superiority",
    "noninferiority",
    "oracle opportunity",
    "production readiness",
    "statistical significance",
)


def status_label(*, mode: str, is_canary: bool) -> str:
    if mode == "dry_run":
        return "DRY RUN — NO PROVIDER DATA"
    if is_canary:
        return "CANARY — INSTRUMENTATION ONLY"
    return "MICRO-PILOT — OPERATIONAL VALIDATION ONLY"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def write_final_report(
    output_dir: Path,
    *,
    label: str,
    mode: str,
    is_canary: bool,
    summary: dict[str, Any],
) -> None:
    lines = [
        f"# {label}",
        "",
        f"Mode: `{mode}`  |  Canary: `{is_canary}`",
        "",
        "## This report does NOT establish:",
        "",
    ]
    lines += [f"- {c}" for c in NON_CLAIMS]
    lines += [
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(summary, indent=2, default=str),
        "```",
        "",
    ]
    if is_canary:
        lines += [
            "## Canary scope",
            "",
            "This run is an instrumentation-only canary. It lacks the complete "
            "frozen presentation and repeat protocol of the micro-pilot and "
            "**must not** be merged into micro-pilot benchmark data.",
            "",
        ]
    (output_dir / "FINAL_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
