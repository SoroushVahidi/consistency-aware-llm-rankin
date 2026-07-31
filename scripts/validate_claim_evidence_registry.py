#!/usr/bin/env python3
"""
validate_claim_evidence_registry.py
====================================
Validates docs/claim_evidence_registry.yaml:

- every claim id is unique;
- every path in implementation_paths/generating_scripts/evidence_paths
  exists on disk (relative to the repo root);
- every superseded_by entry references an existing claim id;
- a claim marked canonical: true is not internal_validation-status (Gurobi
  validation and similar internal checks must never be mislabeled canonical);
- a claim marked manuscript_applicable: true is not status: superseded
  (a superseded claim should never be presented as manuscript-suitable);
- a claim marked status: superseded has a non-empty superseded_by list is
  NOT required (a claim can be superseded by "the corrected understanding"
  narratively, not always by another single claim id) -- but if
  superseded_by is non-empty, every id in it must exist.

This is a structural check (do the referenced paths/ids exist and are the
claims internally consistent), not a numeric re-verification of the claims
themselves.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REGISTRY_PATH = _REPO_ROOT / "docs" / "claim_evidence_registry.yaml"

_REQUIRED_FIELDS = {
    "id",
    "claim",
    "status",
    "canonical",
    "manuscript_applicable",
    "implementation_paths",
    "generating_scripts",
    "evidence_paths",
    "statistical_unit",
    "correction_method",
    "sample_size",
    "limitations",
    "superseded_by",
}
_VALID_STATUSES = {
    "canonical",
    "negative_result",
    "exploratory",
    "internal_validation",
    "superseded",
}


def _path_exists(rel_path: str) -> bool:
    return (_REPO_ROOT / rel_path).exists()


def main() -> int:
    if not _REGISTRY_PATH.exists():
        print(f"FAIL: registry not found at {_REGISTRY_PATH}")
        return 1

    data = yaml.safe_load(_REGISTRY_PATH.read_text())
    claims = data.get("claims", [])
    if not claims:
        print("FAIL: registry has no claims")
        return 1

    errors: list[str] = []
    seen_ids: set[str] = set()

    for claim in claims:
        cid = claim.get("id", "<missing id>")
        missing_fields = _REQUIRED_FIELDS - set(claim.keys())
        if missing_fields:
            errors.append(f"{cid}: missing required field(s): {sorted(missing_fields)}")

        if cid in seen_ids:
            errors.append(f"{cid}: duplicate claim id")
        seen_ids.add(cid)

        status = claim.get("status")
        if status not in _VALID_STATUSES:
            errors.append(
                f"{cid}: invalid status {status!r} (must be one of {sorted(_VALID_STATUSES)})"
            )

        if claim.get("canonical") is True and status == "internal_validation":
            errors.append(
                f"{cid}: marked canonical=true but status=internal_validation -- "
                "internal validation (e.g. solver cross-checks) must never be canonical"
            )

        if claim.get("canonical") is True and status == "superseded":
            errors.append(
                f"{cid}: marked canonical=true but status=superseded -- "
                "a superseded row-level/historical result must never be used as canonical evidence"
            )

        if claim.get("manuscript_applicable") is True and status == "superseded":
            errors.append(f"{cid}: marked manuscript_applicable=true but status=superseded")

        if claim.get("manuscript_applicable") is True and status == "internal_validation":
            errors.append(
                f"{cid}: marked manuscript_applicable=true but status=internal_validation -- "
                "internal-only validation (e.g. Gurobi checks) must never be manuscript-applicable"
            )

        for field in ("implementation_paths", "generating_scripts", "evidence_paths"):
            for rel_path in claim.get(field, []) or []:
                if not _path_exists(rel_path):
                    errors.append(f"{cid}: {field} path does not exist: {rel_path}")

    all_ids = {c.get("id") for c in claims}
    for claim in claims:
        cid = claim.get("id", "<missing id>")
        for target in claim.get("superseded_by", []) or []:
            if target not in all_ids:
                errors.append(f"{cid}: superseded_by references unknown claim id {target!r}")

    if errors:
        print(f"FAIL: {len(errors)} problem(s) found in {_REGISTRY_PATH}:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK: {len(claims)} claims validated, 0 problems ({_REGISTRY_PATH})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
