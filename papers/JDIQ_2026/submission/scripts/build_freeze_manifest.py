#!/usr/bin/env python3
"""
build_freeze_manifest.py
=========================
Records the exact frozen scientific inputs behind the JDIQ 2026 submission:
git state, canonical per-query outputs, canonical aggregate tables,
protocol/pool/regime/method registries, solver configuration, statistical
correction families, and qrels/score-file hashes (read back from existing
manifests, not recomputed, so this script cannot silently disagree with the
per-cell manifests that already pinned these values at generation time).

Writes papers/JDIQ_2026/submission/SUBMISSION_FREEZE_MANIFEST.json.
Read-only with respect to every canonical output; does not run any
experiment.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
SUBMISSION_DIR = REPO_ROOT / "papers" / "JDIQ_2026" / "submission"

FULL_CAL_SCRIPTS = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
for p in (REPO_ROOT, REPO_ROOT / "src", FULL_CAL_SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

CANONICAL_TABLE_DIRS = [
    REPO_ROOT / "reports" / "full_calibrated_core" / "tables",
    REPO_ROOT / "reports" / "normalization_protocol_audit_20260714" / "tables",
    REPO_ROOT / "reports" / "candidate_pool_conditional_audit_20260714" / "tables",
    REPO_ROOT / "reports" / "exact_open_source_ilp_repair_investigation" / "tables",
]

CANONICAL_OUTPUT_ROOTS = [
    REPO_ROOT
    / "reports"
    / "full_calibrated_core"
    / "outputs"
    / "calibrated_all4"
    / "protocol_runs",
    REPO_ROOT / "reports" / "full_calibrated_core" / "outputs" / "calibrated_all4" / "pool_runs",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _git_status_dirty_count() -> int:
    out = _git("status", "--short")
    return len([line for line in out.splitlines() if line.strip()])


def _table_checksums() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for d in CANONICAL_TABLE_DIRS:
        if not d.exists():
            continue
        rel_dir = str(d.relative_to(REPO_ROOT))
        out[rel_dir] = {}
        for f in sorted(d.glob("*.csv")):
            out[rel_dir][f.name] = _sha256(f)
    return out


def _manifest_provenance() -> dict[str, Any]:
    """Read qrels_hash/source_score_hashes back from every already-generated
    per-cell manifest.json, grouped by dataset, rather than recomputing --
    if these ever disagreed with the manifests, that would itself be the
    finding, not something to paper over by recomputing a fresh hash here."""
    by_dataset: dict[str, dict[str, Any]] = {}
    n_manifests = 0
    heads_seen: set[str] = set()
    for root in CANONICAL_OUTPUT_ROOTS:
        if not root.exists():
            continue
        for manifest_path in sorted(root.glob("*/*/*/manifest.json")):
            n_manifests += 1
            data = json.loads(manifest_path.read_text())
            dataset = data["dataset"]
            heads_seen.add(data.get("head", "unknown"))
            entry = by_dataset.setdefault(
                dataset,
                {
                    "qrels_hash": data.get("qrels_hash"),
                    "source_score_hashes": data.get("source_score_hashes"),
                },
            )
            if entry["qrels_hash"] != data.get("qrels_hash"):
                entry["qrels_hash"] = (
                    f"INCONSISTENT: saw both {entry['qrels_hash']} and {data.get('qrels_hash')}"
                )
            if entry["source_score_hashes"] != data.get("source_score_hashes"):
                entry["source_score_hashes"] = "INCONSISTENT across manifests"
    return {
        "n_manifests_read": n_manifests,
        "distinct_git_heads_recorded_in_manifests": sorted(heads_seen),
        "by_dataset": by_dataset,
    }


def _registries() -> dict[str, Any]:
    from candidate_pool_policies import POOL_SPECS
    from run_full_calibrated_core import (
        CANONICAL_NAME_ALIASES,
        DATASETS,
        METHOD_LABELS,
        PAIR_SPECS,
        PROTOCOL_SPECS,
        REGIMES,
    )

    return {
        "datasets": list(DATASETS),
        "regimes": list(REGIMES),
        "protocols": {pid: dict(spec) for pid, spec in PROTOCOL_SPECS.items()},
        "canonical_name_aliases": dict(CANONICAL_NAME_ALIASES),
        "candidate_pools": {pid: spec.to_dict() for pid, spec in POOL_SPECS.items()},
        "methods": dict(METHOD_LABELS),
        "pair_specs": [
            {"pair_name": p[0], "unrepaired_key": p[1], "repaired_key": p[2], "pair_family": p[3]}
            for p in PAIR_SPECS
        ],
    }


def _statistical_families() -> dict[str, Any]:
    return {
        "bootstrap": {"resamples": 10000, "seed": 13},
        "paired_permutation": {"permutations": 10000, "seed": 17},
        "multiplicity_families": {
            "primary_protocol_only": {
                "n_tests": 60,
                "definition": "1 protocol x 4 datasets x 3 regimes x 5 pairs",
            },
            "F1_headline": {
                "n_tests": 180,
                "definition": "3 headline protocols (primary_minmax_retention_matched, "
                "independent_minmax_quantile_q0p5, independent_rank_percentile_q0p5) x 4 x 3 x 5",
            },
            "F2_all_legitimate": {
                "n_tests": 240,
                "definition": "F1_headline + robustness_zscore_retention, x 4 x 3 x 5",
            },
            "F3_everything": {
                "n_tests": 720,
                "definition": "all 12 registered protocols x 4 x 3 x 5",
            },
            "pool_alternatives": {
                "n_tests": 240,
                "definition": "4 alternative candidate pools x 4 x 3 x 5",
            },
            "pool_all_five": {
                "n_tests": 300,
                "definition": "5 candidate pools (incl. canonical) x 4 x 3 x 5",
            },
            "new_baselines": {
                "n_tests": 48,
                "definition": "4 new baseline pairs x 4 datasets x 3 regimes",
            },
            "scidocs_ms1_scoped": {
                "n_tests": 5,
                "definition": "5 method pairs, SciDocs ms1 only, primary protocol",
            },
        },
        "correction_methods": ["Holm", "Benjamini-Hochberg"],
        "alpha": 0.05,
    }


def _solver_configuration() -> dict[str, Any]:
    return {
        "primary_repair": "greedy cycle peeling (deterministic, no external solver)",
        "exact_repair_robustness_check": {
            "solver": "SCIP via PySCIPOpt",
            "commercial_dependency": False,
            "legacy_optional_backend": (
                'method="gurobi" exists in src/consistency_ranker/mwfas_solver.py '
                "but is never used to produce any committed result table"
            ),
        },
    }


def main() -> int:
    t0 = time.time()
    manifest: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git": {
            "head": _git("rev-parse", "HEAD"),
            "head_commit_datetime": _git("log", "-1", "--format=%ci"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty_path_count": _git_status_dirty_count(),
            "note": "dirty_path_count > 0 is expected: this manifest freezes the "
            "*content* of canonical outputs by checksum, independent of "
            "whether the working tree is committed. See Task 6 final report "
            "for the proposed commit covering this exact state.",
        },
        "manuscript_source": {
            "main_tex": str(
                (REPO_ROOT / "papers/JDIQ_2026/manuscript/main.tex").relative_to(REPO_ROOT)
            ),
            "main_tex_sha256": _sha256(REPO_ROOT / "papers/JDIQ_2026/manuscript/main.tex"),
            "references_bib_sha256": _sha256(
                REPO_ROOT / "papers/JDIQ_2026/manuscript/references.bib"
            ),
        },
        "canonical_table_checksums": _table_checksums(),
        "canonical_per_query_output_provenance": _manifest_provenance(),
        "registries": _registries(),
        "statistical_families": _statistical_families(),
        "solver_configuration": _solver_configuration(),
    }
    manifest["_build_seconds"] = round(time.time() - t0, 2)

    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SUBMISSION_DIR / "SUBMISSION_FREEZE_MANIFEST.json"
    out_path.write_text(json.dumps(manifest, indent=2, sort_keys=False))
    print(f"Wrote {out_path}")
    n_tables = sum(len(v) for v in manifest["canonical_table_checksums"].values())
    print(f"Table checksums recorded: {n_tables}")
    provenance = manifest["canonical_per_query_output_provenance"]
    print(f"Per-query manifests read: {provenance['n_manifests_read']}")
    print(
        "Distinct git heads seen in per-cell manifests: "
        f"{provenance['distinct_git_heads_recorded_in_manifests']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
