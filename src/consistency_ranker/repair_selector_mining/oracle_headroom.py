"""Oracle-headroom gate for the preserve-vs-repair research question.

Computes, from ALREADY-EXISTING per-query preserve/repair outcome tables
(no new experiments, no new LLM judgments), whether there is enough
per-query heterogeneity in the repair effect

    delta_q = M_q(repair) - M_q(preserve)

to justify attempting a learned preserve-vs-repair selector at all. This is
"Gate 0" -- it must be cleared before any label-generation/feature/model
work is worth doing; see ``docs/research/EXPERIMENT_ROADMAP.md``.

This module deliberately does NOT do any of the following (out of scope
for this offline, low-risk pass; see the roadmap doc):
  - train a predictive model;
  - compute pre-repair graph features (already implemented in
    ``candidate_selection.pre_outcome_features``, which needs the raw
    preference graphs, not just the CSV outcome tables this module reads);
  - run any new experiment or LLM call.

The go/no-go arithmetic mirrors the Outcome F policy-selection gate
(``src/consistency_ranker/policy_selection/`` -- see
``reports/policy_selection_20260726T030500Z/decision.json``'s
``oracle_corr - always_uht_corr > threshold`` rule), adapted from an
8-policy action space to the 2-action {preserve, repair} space, and adds
proper confidence intervals via ``statistical_inference`` (which the
Outcome F package itself does not use for its headroom number).
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from consistency_ranker.policy_selection.policy_utility import regret_vs_oracle
from consistency_ranker.statistical_inference import (
    BootstrapIntervalResult,
    bootstrap_mean_interval,
    delta_summary,
)

Action = Literal["preserve", "repair"]

# Column names expected in the input CSV. Matches
# reports/candidate_pool_conditional_audit_20260714/tables/pool_robustness_paired_deltas.csv
# (committed, 46,170 rows, 4 datasets) and is compatible with the same
# columns present in reports/final_revision_task4_exact_baseline_fairness_20260715/
# tables/exact_repaired_vs_unrepaired_pair_metrics.csv (local-only, exact-ILP
# variant) -- pass a different --unrepaired-col/--repaired-col pair via the
# CLI if a source table uses different names.
DEFAULT_QUERY_ID_COL = "query_id"
DEFAULT_UNREPAIRED_COL = "unrepaired_ndcg"
DEFAULT_REPAIRED_COL = "repaired_ndcg"
DEFAULT_DATASET_COL = "dataset"


@dataclass(frozen=True)
class PreserveRepairRecord:
    """One query's observed preserve and repair outcomes on the same metric.

    Both outcomes are OBSERVED (computed offline from the same graph), not
    one observed and one counterfactual -- see the "important methodological
    clarification" in the roadmap doc for why this is supervised
    effect-prediction, not causal-inference, at this stage.
    """

    dataset: str
    query_id: str
    preserve_metric: float
    repair_metric: float

    @property
    def delta(self) -> float:
        """Repair effect: positive means repair helped this query."""
        return self.repair_metric - self.preserve_metric

    @property
    def oracle_metric(self) -> float:
        return max(self.preserve_metric, self.repair_metric)

    @property
    def oracle_action(self) -> Action:
        # Ties resolve to "preserve" -- repair is never free in practice
        # (it changes a ranking and, later, will cost acquisition calls if
        # the re-query extension is added), so an exact tie should not be
        # attributed to repair.
        return "repair" if self.repair_metric > self.preserve_metric else "preserve"

    def key(self) -> tuple[str, str]:
        return (self.dataset, self.query_id)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_paired_delta_records(
    csv_path: str | Path,
    *,
    dataset: str | None = None,
    query_id_col: str = DEFAULT_QUERY_ID_COL,
    unrepaired_col: str = DEFAULT_UNREPAIRED_COL,
    repaired_col: str = DEFAULT_REPAIRED_COL,
    dataset_col: str = DEFAULT_DATASET_COL,
    extra_filters: dict[str, str] | None = None,
) -> list[PreserveRepairRecord]:
    """Load preserve/repair per-query records from an existing outcome CSV.

    ``extra_filters`` restricts rows to those matching ``row[col] == value``
    for every (col, value) pair -- use it to pin a single regime/pool/pair
    (e.g. ``{"regime": "ms1", "pool_id": "rrf_union_topk", "pair_name":
    "copeland_graph"}``) so the resulting records form one coherent
    preserve-vs-repair comparison rather than mixing several repair
    variants together. Rows with missing/non-numeric metric values are
    skipped, not coerced to 0 -- silently treating "missing" as "zero" would
    bias the headroom estimate.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")
    extra_filters = extra_filters or {}
    records: list[PreserveRepairRecord] = []
    skipped_missing = 0
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if dataset is not None and row.get(dataset_col) != dataset:
                continue
            if any(row.get(col) != value for col, value in extra_filters.items()):
                continue
            raw_u, raw_r = row.get(unrepaired_col), row.get(repaired_col)
            if raw_u in (None, "", "NA", "nan") or raw_r in (None, "", "NA", "nan"):
                skipped_missing += 1
                continue
            try:
                u, r = float(raw_u), float(raw_r)
            except ValueError:
                skipped_missing += 1
                continue
            records.append(
                PreserveRepairRecord(
                    dataset=str(row[dataset_col]),
                    query_id=str(row[query_id_col]),
                    preserve_metric=u,
                    repair_metric=r,
                )
            )
    if skipped_missing:
        import logging

        logging.getLogger(__name__).warning(
            "load_paired_delta_records: skipped %d rows with missing/non-numeric metrics",
            skipped_missing,
        )
    return records


@dataclass(frozen=True)
class OracleHeadroomResult:
    n_queries: int
    mean_preserve: float
    mean_repair: float
    mean_oracle: float
    always_preserve_is_safer_default: bool
    headroom_vs_best_baseline: float  # H = M_oracle - max(M_preserve, M_repair)
    headroom_ci: BootstrapIntervalResult
    frac_benefit_from_repair: float  # delta_q > 0
    frac_harmed_by_repair: float  # delta_q < 0
    frac_neutral_exact: float  # delta_q == 0 exactly
    delta_summary: dict[str, float | int | None]
    mean_regret_always_preserve: float
    mean_regret_always_repair: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["headroom_ci"] = asdict(self.headroom_ci)
        return d


def compute_oracle_headroom(
    records: list[PreserveRepairRecord],
    *,
    bootstrap_reps: int = 10_000,
    bootstrap_seed: int = 13,
) -> OracleHeadroomResult:
    """The core "gate 0" computation: is there oracle headroom at all?

    ``headroom_vs_best_baseline`` == ``mean_regret_always_preserve`` or
    ``mean_regret_always_repair`` (whichever baseline is stronger), computed
    via the shared ``regret_vs_oracle`` helper for auditability -- this is
    an identity, not a coincidence: since ``oracle_metric = max(preserve,
    repair)`` pointwise, ``regret_vs_oracle(chosen, oracle) = oracle -
    chosen`` exactly (never floored) for chosen in {preserve_metric,
    repair_metric}, so the mean regret of a fixed baseline against the
    oracle equals the oracle mean minus that baseline's mean.
    """
    if not records:
        raise ValueError("compute_oracle_headroom requires at least one record")

    preserve_vals = [r.preserve_metric for r in records]
    repair_vals = [r.repair_metric for r in records]
    oracle_vals = [r.oracle_metric for r in records]
    deltas = [r.delta for r in records]

    mean_preserve = sum(preserve_vals) / len(preserve_vals)
    mean_repair = sum(repair_vals) / len(repair_vals)
    mean_oracle = sum(oracle_vals) / len(oracle_vals)

    regret_always_preserve = [regret_vs_oracle(r.preserve_metric, r.oracle_metric) for r in records]
    regret_always_repair = [regret_vs_oracle(r.repair_metric, r.oracle_metric) for r in records]
    mean_regret_preserve = sum(regret_always_preserve) / len(regret_always_preserve)
    mean_regret_repair = sum(regret_always_repair) / len(regret_always_repair)

    best_baseline_mean = max(mean_preserve, mean_repair)
    headroom = mean_oracle - best_baseline_mean
    # Bootstrap the headroom gap directly over per-query regret-vs-the-
    # stronger-baseline, so the CI reflects query-level resampling
    # variability, not just a point estimate of two means' difference.
    stronger_baseline_regret = (
        regret_always_preserve if mean_preserve >= mean_repair else regret_always_repair
    )
    headroom_ci = bootstrap_mean_interval(
        stronger_baseline_regret, reps=bootstrap_reps, seed=bootstrap_seed
    )

    n = len(records)
    n_benefit = sum(1 for d in deltas if d > 0)
    n_harm = sum(1 for d in deltas if d < 0)
    n_neutral = n - n_benefit - n_harm

    return OracleHeadroomResult(
        n_queries=n,
        mean_preserve=mean_preserve,
        mean_repair=mean_repair,
        mean_oracle=mean_oracle,
        always_preserve_is_safer_default=mean_preserve >= mean_repair,
        headroom_vs_best_baseline=headroom,
        headroom_ci=headroom_ci,
        frac_benefit_from_repair=n_benefit / n,
        frac_harmed_by_repair=n_harm / n,
        frac_neutral_exact=n_neutral / n,
        delta_summary=delta_summary(deltas),
        mean_regret_always_preserve=mean_regret_preserve,
        mean_regret_always_repair=mean_regret_repair,
    )


GoNoGoDecision = Literal[
    "PROCEED_TO_LABELING",
    "NO_HEADROOM_DO_NOT_LEARN",
    "AMBIGUOUS_NEED_MORE_DATA",
]


@dataclass(frozen=True)
class GoNoGoResult:
    decision: GoNoGoDecision
    rationale: str
    headroom_threshold: float
    min_heterogeneity_fraction: float


def evaluate_go_no_go(
    result: OracleHeadroomResult,
    *,
    headroom_threshold: float = 0.01,
    min_heterogeneity_fraction: float = 0.05,
) -> GoNoGoResult:
    """Apply the pre-registered gate-0 decision rule (see roadmap doc).

    Mirrors the shape of Outcome F's ``oracle_corr - always_uht_corr >
    0.05`` rule, but this is gate ZERO (does headroom exist at all), not
    gate two (does a learned model realize it) -- Outcome F's own result
    (headroom existed, 0.1965, but no gate realized it) is exactly the
    failure mode this earlier gate exists to catch before repeating the
    same effort on a new action space.

    Three outcomes, deliberately not collapsed to a boolean:
      - PROCEED_TO_LABELING: the headroom CI's lower bound is above
        ``headroom_threshold`` AND both the beneficial and harmful
        fractions clear ``min_heterogeneity_fraction`` (heterogeneity, not
        just a mean shift, is required -- a small uniform shift is better
        addressed by changing the default policy, not by learning a
        per-query selector).
      - NO_HEADROOM_DO_NOT_LEARN: the headroom CI's upper bound is at or
        below ``headroom_threshold`` -- a learned selector cannot plausibly
        help by more than noise; see the negative-result fallback path.
      - AMBIGUOUS_NEED_MORE_DATA: the CI straddles the threshold, or
        heterogeneity is one-sided (e.g. plenty of harmed queries but
        almost no benefited ones, or vice versa) -- more data or a
        different metric/threshold is needed before deciding either way.
    """
    lo, hi = result.headroom_ci.lower, result.headroom_ci.upper
    heterogeneous = (
        result.frac_benefit_from_repair >= min_heterogeneity_fraction
        and result.frac_harmed_by_repair >= min_heterogeneity_fraction
    )

    if hi is not None and hi <= headroom_threshold:
        decision: GoNoGoDecision = "NO_HEADROOM_DO_NOT_LEARN"
        rationale = (
            f"Headroom 95% CI upper bound ({hi:.5f}) does not exceed the "
            f"threshold ({headroom_threshold:.5f}); a learned selector cannot "
            "plausibly beat the stronger fixed baseline by more than noise "
            "on this slice. Do not proceed to label/feature/model work on "
            "this slice; see the negative-result fallback path."
        )
    elif lo is not None and lo > headroom_threshold and heterogeneous:
        decision = "PROCEED_TO_LABELING"
        rationale = (
            f"Headroom 95% CI lower bound ({lo:.5f}) exceeds the threshold "
            f"({headroom_threshold:.5f}), and both directions are populated "
            f"(benefit={result.frac_benefit_from_repair:.1%}, "
            f"harm={result.frac_harmed_by_repair:.1%} >= "
            f"{min_heterogeneity_fraction:.1%} each) -- genuine per-query "
            "heterogeneity, not just a mean shift. Proceed to label "
            "generation and feature-schema work (still gated: this does not "
            "license model training yet -- see the roadmap's predictive-"
            "signal gate)."
        )
    else:
        decision = "AMBIGUOUS_NEED_MORE_DATA"
        rationale = (
            f"Headroom CI [{lo}, {hi}] straddles the threshold "
            f"({headroom_threshold:.5f}) or heterogeneity is one-sided "
            f"(benefit={result.frac_benefit_from_repair:.1%}, "
            f"harm={result.frac_harmed_by_repair:.1%}, need >= "
            f"{min_heterogeneity_fraction:.1%} each). Do not commit to "
            "either path; expand the query sample (e.g. additional regimes/"
            "pools/datasets already on disk) before deciding."
        )

    return GoNoGoResult(
        decision=decision,
        rationale=rationale,
        headroom_threshold=headroom_threshold,
        min_heterogeneity_fraction=min_heterogeneity_fraction,
    )


def write_oracle_headroom_report(
    result: OracleHeadroomResult,
    decision: GoNoGoResult,
    output_dir: str | Path,
    *,
    input_csv: str | Path,
    filters: dict[str, str] | None = None,
) -> None:
    """Deterministic report generation: same inputs -> byte-identical output.

    No wall-clock timestamps are embedded in the report body (only in the
    manifest's ``generated_at_utc``, which callers may omit for strict
    byte-identity testing).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    manifest = {
        "input_csv": str(input_csv),
        "input_csv_sha256": _sha256_file(Path(input_csv)),
        "filters": filters or {},
        "result": result.to_dict(),
        "decision": asdict(decision),
    }
    (out / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    lines = [
        "# Oracle-Headroom Gate Report (preserve vs. repair)",
        "",
        f"Input: `{input_csv}`" + (f" (filters: `{filters}`)" if filters else ""),
        f"Queries: {result.n_queries}",
        "",
        "## Aggregate outcomes",
        "",
        "| Policy | Mean metric |",
        "|---|---:|",
        f"| always_preserve | {result.mean_preserve:.6f} |",
        f"| always_repair | {result.mean_repair:.6f} |",
        f"| oracle | {result.mean_oracle:.6f} |",
        "",
        "Safer fixed default: "
        f"**{'preserve' if result.always_preserve_is_safer_default else 'repair'}**",
        "",
        "## Headroom",
        "",
        f"H = mean(oracle) - max(mean(preserve), mean(repair)) = "
        f"**{result.headroom_vs_best_baseline:.6f}**",
        f"95% CI ({result.headroom_ci.method}, {result.headroom_ci.reps} reps, "
        f"seed={result.headroom_ci.seed}): "
        f"[{result.headroom_ci.lower:.6f}, {result.headroom_ci.upper:.6f}]",
        "",
        "## Per-query heterogeneity",
        "",
        f"- Benefit from repair (delta > 0): {result.frac_benefit_from_repair:.1%}",
        f"- Harmed by repair (delta < 0): {result.frac_harmed_by_repair:.1%}",
        f"- Exactly neutral (delta == 0): {result.frac_neutral_exact:.1%}",
        f"- Mean regret of always-preserve vs. oracle: {result.mean_regret_always_preserve:.6f}",
        f"- Mean regret of always-repair vs. oracle: {result.mean_regret_always_repair:.6f}",
        "",
        "## Delta distribution",
        "",
        f"```\n{json.dumps(result.delta_summary, indent=2, sort_keys=True)}\n```",
        "",
        "## Gate-0 decision",
        "",
        f"**{decision.decision}**",
        "",
        decision.rationale,
        "",
    ]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


__all__ = [
    "PreserveRepairRecord",
    "load_paired_delta_records",
    "OracleHeadroomResult",
    "compute_oracle_headroom",
    "GoNoGoResult",
    "evaluate_go_no_go",
    "write_oracle_headroom_report",
]
