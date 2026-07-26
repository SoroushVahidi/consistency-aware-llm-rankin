"""Deterministic factor-cell completion recomputation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REQUIRED_POLICIES = ("UHT", "CHALLENGER", "HYBRID", "ROBUST_COMBINED")
REQUIRED_BUDGETS = (3, 5, 8)


@dataclass
class CellCompletionResult:
    cell_id: str
    previous_complete: bool
    recomputed_complete: bool
    reason: str
    effective_depth: int | None
    n_policy_complete: int
    n_policy_required: int
    n_valid_judgments: int
    has_stopped_policy: bool


def effective_depth_for_docs(doc_texts: dict[str, str], *, top_k: int = 12) -> int:
    usable = sum(1 for _d, t in doc_texts.items() if t and str(t).strip())
    return int(min(top_k, usable))


def is_cell_complete_from_rows(
    rows: list[dict[str, Any]],
    *,
    effective_depth: int | None = None,
) -> tuple[bool, str]:
    """A cell is complete only when required acquisition policies finished."""
    if not rows:
        return False, "no_rows"
    stopped = [
        r
        for r in rows
        if str(r.get("status", "")).startswith("stopped")
        or str(r.get("status", "")).startswith("skipped")
        or str(r.get("status", "")).startswith("error")
        or str(r.get("status", "")).startswith("partial")
    ]
    policy_ok = 0
    for policy in REQUIRED_POLICIES:
        for budget in REQUIRED_BUDGETS:
            hits = [
                r
                for r in rows
                if r.get("policy") == policy
                and int(float(r.get("budget") or -1)) == budget
                and str(r.get("status")) == "complete"
                and r.get("utility") not in (None, "")
            ]
            if hits:
                policy_ok += 1
    required = len(REQUIRED_POLICIES) * len(REQUIRED_BUDGETS)
    if policy_ok < required:
        return False, f"incomplete_policies:{policy_ok}/{required}"
    if stopped and any(
        r.get("policy") in REQUIRED_POLICIES for r in stopped
    ):
        return False, "required_policy_stopped"
    if effective_depth is not None and effective_depth < 2:
        return False, "effective_depth_below_min"
    return True, "all_required_policies_complete"


def recompute_completed_cells(
    *,
    output_dir: Path,
    previous_completed: set[str] | None = None,
    cell_effective_depth: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Recompute completion from CELL_SUMMARY; preserve audit trail."""
    previous_completed = previous_completed or set()
    if (output_dir / "completed_cells.json").exists() and not previous_completed:
        previous_completed = set(
            json.loads((output_dir / "completed_cells.json").read_text(encoding="utf-8"))
        )
    cell_effective_depth = cell_effective_depth or {}
    by_cell: dict[str, list[dict[str, Any]]] = {}
    csv_path = output_dir / "CELL_SUMMARY.csv"
    if csv_path.exists() and csv_path.stat().st_size > 0:
        import csv

        with csv_path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                cid = row.get("cell_id")
                if not cid:
                    continue
                by_cell.setdefault(cid, []).append(row)

    results: list[CellCompletionResult] = []
    recomputed: set[str] = set()
    for cid, rows in sorted(by_cell.items()):
        depth = cell_effective_depth.get(cid)
        ok, reason = is_cell_complete_from_rows(rows, effective_depth=depth)
        n_ok = sum(
            1
            for r in rows
            if r.get("policy") in REQUIRED_POLICIES
            and str(r.get("status")) == "complete"
            and int(float(r.get("budget") or -1)) in REQUIRED_BUDGETS
        )
        stopped = any(
            str(r.get("status", "")).startswith(("stopped", "skipped", "error", "partial"))
            and r.get("policy") in REQUIRED_POLICIES
            for r in rows
        )
        # valid judgments for this cell from PARSED if present
        n_valid = 0
        parsed = output_dir / "PARSED_JUDGMENTS.jsonl"
        if parsed.exists():
            with parsed.open(encoding="utf-8") as fh:
                for line in fh:
                    if cid.split("|")[1] in line and f"|{cid.split('|')[2]}|" in line:
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if obj.get("identity", "").endswith(
                            "|" + "|".join(cid.split("|")[2:])
                        ) or obj.get("identity", "").find("|".join(cid.split("|")[2:])) >= 0:
                            if obj.get("valid") or int(obj.get("z") or 0) != 0:
                                n_valid += 1
        res = CellCompletionResult(
            cell_id=cid,
            previous_complete=cid in previous_completed,
            recomputed_complete=ok,
            reason=reason,
            effective_depth=depth,
            n_policy_complete=n_ok,
            n_policy_required=len(REQUIRED_POLICIES) * len(REQUIRED_BUDGETS),
            n_valid_judgments=n_valid,
            has_stopped_policy=stopped,
        )
        results.append(res)
        if ok:
            recomputed.add(cid)

    corrections = [
        asdict(r)
        for r in results
        if r.previous_complete != r.recomputed_complete
    ]
    audit = {
        "previous_count": len(previous_completed),
        "recomputed_count": len(recomputed),
        "corrections": corrections,
        "code_version": "multifactor_acquisition_v1+completion_recompute_v1",
        "parser_version": "pairwise_parse_v2",
        "results": [asdict(r) for r in results if r.cell_id.startswith("scidocs|") and "azure" in r.cell_id][
            :20
        ],
    }
    (output_dir / "COMPLETED_CELLS_AUDIT.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )
    # Preserve previous file; write recomputed alongside.
    (output_dir / "completed_cells.previous.json").write_text(
        json.dumps(sorted(previous_completed), indent=2), encoding="utf-8"
    )
    (output_dir / "completed_cells.json").write_text(
        json.dumps(sorted(recomputed), indent=2), encoding="utf-8"
    )
    return {
        "previous_completed": sorted(previous_completed),
        "recomputed_completed": sorted(recomputed),
        "corrections": corrections,
        "audit_path": str(output_dir / "COMPLETED_CELLS_AUDIT.json"),
    }
