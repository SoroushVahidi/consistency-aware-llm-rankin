# Repository-Scale Preserve-vs-Repair Headroom Analysis

**Generated:** 2026-07-28. **Purpose:** determine, from all already-existing
per-query repair-outcome evidence in this repository, whether the
preserve-vs-repair predictive-model research direction
(`docs/research/RESEARCH_TRAJECTORY.md`) should continue. **No new
experiments, no new LLM judgments, no network calls, no model training.**
Every number below is independently reproducible by re-running
`python scripts/run_repository_scale_headroom_analysis.py`.

**Bottom line: the recommendation is NO-GO.** See `research_decision.md`
for the full reasoning; this README gives the numbers.

## What was analyzed

76 already-existing, already-committed per-query outcome source files
(full list with row counts in `summary.json`'s `source_coverage`, and in
`per_query_effects.csv`'s `source_file` column), unified into one table:

| Source family | Rows | Repair algorithm |
|---|---:|---|
| `pool_robustness_greedy` | 46,170 | greedy |
| `full_calibrated_core_greedy` | 30,780 | greedy |
| `pool_cutoff_greedy` | 29,220 | greedy |
| `exact_ilp_task4` | 7,866 | exact ILP |
| `new_baseline_greedy` | 4,104 | greedy |
| `real_llm_integrity_policy_sensitivity` | 1,974 | greedy |
| `pool_cutoff_exact_ilp` | 1,710 | exact ILP |
| `cycle_type_diagnostic` | 379 | greedy |
| **Total** | **122,203** | |

**4 datasets** (SciDocs, FiQA, HotpotQA, BRIGHT), **419 distinct
(dataset, query_id) pairs**, each repeated across a mean of ~292
experimental regimes (vote construction × candidate pool × pool size ×
metric cutoff × pair/extraction method × protocol).

Sources found but deliberately excluded, with reasons, are documented in
`research_decision.md`'s companion audit trail and in code comments in
`scripts/run_repository_scale_headroom_analysis.py`; the main exclusions
were aggregate/summary tables (no per-query rows to contribute) and
packaging-stage mirror copies of the same underlying data (to avoid
double-counting).

## Headline numbers

**Use `query_level_headroom_RECOMMENDED` in `summary.json`, not the
row-level pooled number** — the row-level statistic treats 122,203 rows as
independent when only 419 distinct queries exist (each repeated across
many regimes), which makes its confidence interval artificially narrow.
The query-level number aggregates each query across all its regimes first.

| Quantity | Row-level (pseudo-replicated, for reference only) | **Query-level (recommended)** |
|---|---:|---:|
| n | 122,203 rows | **419 distinct queries** |
| Oracle headroom | 0.00270 | **0.00251** |
| 95% CI | [0.00257, 0.00283] | **[0.00204, 0.00302]** |
| Fraction benefiting from repair | 4.9% | **28.2%** |
| Fraction harmed by repair | 4.2% | **27.2%** |
| Fraction exactly neutral | 90.8% | **44.6%** |

The two estimates of the headroom point value agree closely (0.0025–0.0027)
— the pseudo-replication mainly affects CI width and the benefit/harm/
neutral fractions (which differ because most of a given query's ~292
regime-repeats are literally identical/near-identical to each other,
inflating the row-level neutral fraction).

**Context that makes 0.0025 legible:** the JDIQ manuscript's own
statistical-power analysis
(`reports/final_revision_task2_statistical_power_20260715/`) established a
Holm-adjusted, 80%-power minimum-detectable-effect of **0.0207** for this
metric family. The query-level oracle headroom is **~8x smaller** than
that — even a perfect, error-free preserve-vs-repair oracle would produce
an average gain the study's own methodology could not reliably
distinguish from noise.

## Headroom by regime (the dominant explanatory variable)

| Dataset | Regime | Headroom | 95% CI (row-level) |
|---|---|---:|---:|
| BRIGHT | `ms1` (high cyclicity) | 0.00841 | [0.00760, 0.00923] |
| SciDocs | `ms1` | 0.00587 | [0.00540, 0.00635] |
| FiQA | `ms1` | 0.00575 | [0.00521, 0.00632] |
| HotpotQA | `ms1` | 0.00407 | [0.00329, 0.00494] |
| BRIGHT | `ms1_drop_mutual` | 0.00053 | [0.00038, 0.00071] |
| SciDocs | `ms1_drop_mutual` | 0.00052 | [0.00038, 0.00068] |
| FiQA | `ms1_drop_mutual` | 0.00040 | [0.00028, 0.00053] |
| HotpotQA | `ms1_drop_mutual` | 0.00000 | [0.00000, 0.00000] |
| all 4 datasets | `ms2` (near-acyclic) | ≈0.000001–0.000009 | ≈[0, 0.00002] |

This is a clean, monotonic, consistent pattern across every dataset:
headroom tracks vote-construction cyclicity almost perfectly, and `ms2`
(the near-acyclic regime) has essentially zero headroom everywhere. Full
table: `headroom_by_regime.csv`.

Exact ILP repair shows higher pooled headroom (0.0066) than greedy repair
(0.0024) — noted as weak evidence (row-level only, not yet re-verified at
query-level for this specific split) in `evidence_table.csv`.

## Predictability upper bounds

From `predictability_upper_bounds.json`: every available pre-repair
numeric covariate (repair cost, largest-SCC size, graph density) has
Pearson |r| between 0.018 and 0.039 against the repair effect (r² < 0.2%
of variance explained) — statistically significant only because of the
large sample size, not practically informative. `is_cyclic` shows Cohen's
d = 0.034 (roughly 6x below the conventional "small effect" threshold of
0.2).

## Files in this directory

- `README.md` — this file.
- `summary.json` — headline numbers, both pooled and query-level, delta distribution, source coverage.
- `evidence_table.csv` — claim-by-claim evidence/confidence/status table.
- `research_decision.md` — Phase 6 failure analysis of 4 prior attempts + Phase 7 go/no-go decision.
- `per_query_effects.csv` — the full unified table, 122,203 rows, one row per (query, experimental regime), with provenance columns.
- `per_query_aggregated_effects.csv` — 419 rows, one per distinct (dataset, query_id), used for the recommended query-level headroom statistic.
- `headroom_by_regime.csv` — headroom sliced by dataset, repair algorithm, dataset×regime, pair family, and source family.
- `predictability_upper_bounds.json` — correlation/mutual-information/ANOVA results for available covariates.

## Reproduce

```
python scripts/run_repository_scale_headroom_analysis.py
```

Deterministic given the same input files (fixed bootstrap seeds); reads
only files already committed or already present locally under `reports/`
and `experiments/` (a few JDIQ-era working directories referenced here are
local-only per `docs/ARTIFACT_POLICY.md` and would need to be regenerated
from their own task's `REPRODUCE.sh`/instructions on a fresh clone — none
were modified by this analysis).
