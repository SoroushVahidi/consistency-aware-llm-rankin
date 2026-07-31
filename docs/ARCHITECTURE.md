# Architecture Guide

This document exists so a new reader (human or AI assistant) can understand
this repository's purpose, structure, terminology, and current state without
reading every historical report. It is deliberately concise and focused on
active/canonical paths — it does not catalog every archived file (see
`reports/_archive/` and `docs/historical/` for historical material,
`docs/EXPERIMENTS.md` for the experiment-family index,
`docs/EXPERIMENT_ARTIFACT_POLICY.md` for output-tracking decisions, and
`PROJECT_STATUS.md` for the full documentation-authority map). See
`docs/RELEASE_READINESS.md` for the current CI/local validation contract and
branch-integration checklist.

---

## 1. Project Purpose

This repository studies **consistency-aware ranking from pairwise
preferences**: given a query and a candidate document pool, multiple
signals (classical retrieval rankers, or real LLM pairwise judgments) each
vote on pairwise document preferences. Those votes are assembled into a
directed, weighted **preference graph**. Disagreement among voters shows up
as **cycles** in that graph (structural inconsistency). A repair algorithm
(Minimum Weighted Feedback Arc Set, MWFAS) can remove a minimum-weight set
of edges to make the graph acyclic, from which a ranking is extracted. The
central research question is whether that **repair** step reliably improves
downstream retrieval effectiveness (nDCG), and how that answer depends on
choices made before repair ever runs (score normalization, vote
construction, candidate-pool size).

**Current scientific result (accurate as of the submitted manuscript,
`papers/JDIQ_2026/manuscript/main.tex`):** the result is **null/negative**
after appropriate statistical correction. Repair remains structurally
active (it does remove edges and can change top-*k* membership), but **no
repaired-vs-unrepaired nDCG cell survives Holm correction** in the primary
protocol, the larger-pool study, or direct exact-repair checks. The paper's
contribution is framed as **methodological**, not algorithmic: claims about
graph repair must report normalization, vote construction, pooling, and
evaluation-cutoff choices as first-class data-quality decisions, because
those choices determine both the graph being repaired and the effect any
evaluation can observe. Do not state or imply a positive repair effect
without citing the specific evidence package and correction method behind
that claim (see §6).

A smaller, separate **real-LLM exploratory pilot** (genuine
Azure/Gemini/Cohere/Fireworks pairwise judgments, 6 real queries) exists
alongside the classical score-vote evidence base. It is explicitly
directional, not a second large-*n* confirmatory study — see §6 and §7.

---

## 2. Architectural Layers

| Layer | Canonical directories/modules | Responsibility |
|---|---|---|
| **Core ranking & graph algorithms** | `src/consistency_ranker/{baseline_ranking,mwfas_solver,greedy_fas,graph_construction,pairwise_prefs,cycle_detection,evaluation,dag_linear_extensions,dag_ambiguity}.py` and the standalone fusion modules (`rrf_ranking.py`, `combsum_ranking.py`, `borda_fuse_ranking.py`, `soft_score_ranking.py`, `markov_graph_ranking.py`) | Dependency-free "leaf" layer: build preference graphs, detect cycles, repair (greedy/exact MWFAS), extract rankings, score nDCG. Imported everywhere; imports nothing else in this repository. |
| **Statistical inference** | `src/consistency_ranker/statistical_inference.py` | Bootstrap/permutation CIs, exact sign-flip tests, Holm/BH correction, cluster-aware inference for nested/replicated data. Another dependency-free leaf. |
| **Provenance & reproducibility** | `src/consistency_ranker/provenance.py` (canonical), `src/consistency_ranker/experiment_cli.py` (compatibility layer) | File hashing, git-commit/dirty-state capture, reproducibility-manifest schemas, canonical-output overwrite protection, offline/live-mode gating. See §4. |
| **Provider & acquisition infrastructure** | `src/consistency_ranker/multi_provider_eval/` (provider request/response/caching/spending), `src/consistency_ranker/adaptive_acquisition/`, `src/consistency_ranker/prior_robust/`, `src/consistency_ranker/multifactor_acquisition/`, `src/consistency_ranker/active_acquisition/` | Talks to real LLM providers; budget-limited/adaptive acquisition of judgments. |
| **Repair studies** (four distinct, related packages — see §5 terminology) | `src/consistency_ranker/reliability_repair/`, `repair_selector_mining/`, `repair_frontier/`, `repair_diagnostic/` | Each asks a different question about *when/whether* repair helps; see each package's own module docstring. |
| **Real-LLM exploratory pilot** | `src/consistency_ranker/extraction_study/`, `real_llm_reanalysis/` | Extraction-method comparison and query-clustered re-analysis of the pilot's own statistics (§6). |
| **Production policy selection** | `src/consistency_ranker/policy_selection/` (17 files: 2 production, 15 research — see §5, §7) | A *separate* research thread from repair: adaptive LLM-judge budget allocation. Production is locked to always-UHT after the "Outcome F" finding; everything else in the package is experimental and requires an explicit opt-in. |
| **Experiment orchestration** | `scripts/*.py` (108 files) | CLI entry points. Most are thin; a few (`run_real_experiment.py`) contain substantial directly-testable logic, not just argument parsing. |
| **Reports & evidence** | `reports/`, `outputs/`, `papers/JDIQ_2026/`, `docs/EXPERIMENTS.md`, `docs/EXPERIMENT_ARTIFACT_POLICY.md` | Generated experiment outputs, their tracking policy, and the manuscript. See §6 for which are canonical. |
| **Architecture safeguards** | `scripts/check_architecture_boundaries.py` | Detects circular import dependencies among subpackages (added after finding and fixing one real cycle — §4). |

This layering is real but was, until this document, **implicit** — nothing
prevented a new cross-layer import from silently violating it. The one
circular dependency ever found (`multi_provider_eval` ⟷
`multifactor_acquisition`) has been fixed and is now guarded by
`scripts/check_architecture_boundaries.py` in CI.

---

## 3. End-to-End Data Flow

```
pairwise judgments or ranker votes
  (consistency_ranker.pairwise_prefs.Preference: winner, loser, weight)
        │
        ▼
preference graph
  (consistency_ranker.graph_construction.build_graph → networkx.DiGraph)
        │
        ▼
cycle detection
  (consistency_ranker.cycle_detection)
        │
   ┌────┴─────────────────────────────┐
   │ unrepaired                        │ repaired
   ▼                                    ▼
ranking extraction                mwfas_solver.solve(graph, method="greedy"|"scip"|"exact")
  (baseline_ranking.py:              → repaired acyclic graph → ranking extraction
   topological_ranking,
   copeland_ranking, pagerank_ranking,
   borda_ranking, rank_centrality_ranking,
   hodge_rank_ranking, ...)
        │                                    │
        └────────────────┬───────────────────┘
                          ▼
                 evaluation.ndcg_at_k(ranking, qrels)
                          │
                          ▼
       statistical_inference.py:
         bootstrap_mean_interval / exact_sign_flip_pvalue / holm_adjust /
         cluster_bootstrap_mean_interval / cluster_exact_sign_flip_pvalue /
         is_significant_pvalue
                          │
                          ▼
    reports/<experiment_name>_<timestamp>/
      (FINAL_REPORT.md, tables/*.csv, provenance manifest via
       provenance.collect_provenance() or experiment_cli.write_run_manifest())
                          │
                          ▼
      papers/JDIQ_2026/manuscript/main.tex
        (evidence traced via papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md)
```

---

## 4. Canonical-Module Map

| Responsibility | Canonical implementation | Notes |
|---|---|---|
| Provenance & hashing | `consistency_ranker.provenance` (`file_sha256`, `git_commit_info`, `hash_paths`, `collect_provenance`, `protect_canonical_output`) | `consistency_ranker.experiment_cli` is a **compatibility layer**: its `resolve_git_commit`/`file_sha256` are thin wrappers delegating to `provenance`; its `ensure_output_dir`/`write_run_manifest`/`assert_offline_or_allowed` have no `provenance` equivalent and remain independent (genuinely different semantics — see both modules' docstrings). |
| Ranking baselines | `consistency_ranker.baseline_ranking` | `dag_linear_extensions.prior_priority_topological_ranking` is a **legacy alias** that delegates to `baseline_ranking.priority_topological_ranking` (verified byte-for-byte identical before consolidation) — kept only for that module's own test suite and `HARD_CONSTRAINT_METHODS` table. |
| Statistical inference | `consistency_ranker.statistical_inference` | Single module; no known duplicates. |
| MWFAS solving | `consistency_ranker.mwfas_solver` (`solve`, dispatches to `greedy`/`scip`/`exact`/`ilp`/`gurobi`) | `verify_canonical_solver_version()` pins the exact PySCIPOpt version every committed exact-repair result was generated with. |
| Provider requests | `consistency_ranker.multi_provider_eval` (`providers.py`, `MultiProviderJudge`) | Azure request-shaping constants live in `multi_provider_eval.azure_request` (canonical); `multifactor_acquisition.azure_request` is a compatibility shim re-exporting the same names (this is where the one known circular dependency used to live — now fixed). |
| Spending/cost tracking | `consistency_ranker.multi_provider_eval.spending.SpendingCeiling` | Single implementation. |
| Production policy selection | `consistency_ranker.policy_selection.production_runner.run_production_uht` + `production_config.PRODUCTION_OPERATING_POINT` | The *only* code path production may execute; see §7. Every other gate in `policy_selection/` is experimental. |
| Experiment manifests | `provenance.collect_provenance()` (richer schema: seeds, dependency/solver versions, cluster count) *or* `experiment_cli.write_run_manifest()` (simpler schema: script/config/argv/git_commit) | Two distinct, intentionally-not-merged schemas — different callers, different needs; neither is "more canonical" than the other. |
| Report/evidence validation | `scripts/validate_canonical_evidence_manifest.py`, `scripts/validate_report_links.py`, `scripts/run_secret_scan.py`, `scripts/check_architecture_boundaries.py` | Run via `make repo-ready` / `make check`. |

---

## 5. Terminology Guide

- **Preference**: one vote, `Preference(winner, loser, weight)`, that `winner` should rank above `loser`.
- **Comparison**: the source of a preference — a classical-ranker score margin, or a genuine LLM pairwise judgment.
- **Cycle**: a directed cycle in the preference graph (`u → v → ... → u`), meaning the aggregated votes disagree about relative order.
- **Inconsistency**: the presence of one or more cycles; quantified via `graph_construction.graph_summary` and `failure_mining.graph_features`.
- **Repair**: the MWFAS edge-removal step (`mwfas_solver.solve`) that restores acyclicity. Four distinct packages study different aspects of repair (not duplicates — see below):
  - `reliability_repair` — repairs a graph given per-edge *reliability* estimates.
  - `repair_selector_mining` — mines which (preserve, repair) action pairs are worth training a selector on (two fixed actions).
  - `repair_frontier` — discovers a *richer set of repair candidates* per query and asks whether a label-free rule can select among them (a "best of many" framing).
  - `repair_diagnostic` — asks whether repair's rare benefits are *predictable* from pre-repair graph features alone.
- **Repair frontier**: specifically `repair_frontier.build_repair_frontier`'s output — the set of candidate rankings assembled per query graph (incumbent, greedy repair, exact repair, SCC-local variants, label-free extractions), before any selection rule picks among them.
- **Diagnostic**: in this codebase, specifically `repair_diagnostic`'s bounded study of whether pre-repair features predict repair outcome — not a generic debugging term.
- **Extraction study**: `extraction_study/` — asks whether *extraction method choice* (which ranking-extraction algorithm is applied to a graph), not repair, explains observed ranking gains. Distinct from "extraction" meaning parsing a structured judgment out of an LLM's free-text response (`multi_provider_eval/parsing.py`) — same word, two unrelated meanings in this codebase; watch for this when reading unfamiliar code.
- **Operating point**: `policy_selection.production_config.PRODUCTION_OPERATING_POINT` — the frozen, locked configuration (`primary_policy="UHT"`, a non-routing safety floor) that production acquisition code executes. See §7.
- **Production policy**: the single policy (`UHT`) production is allowed to run; enforced by `PolicySelector.__post_init__` raising `ValueError` on any attempt to configure learned routing while `execution_mode is ExecutionMode.PRODUCTION_UHT`.
- **Research policy** (or "experimental gate"): any of the other policy-selection mechanisms in `policy_selection/` (hard, calibrated, selective, soft, staged, switching, hybrid, challenger) — all require `ExecutionMode.EXPERIMENTAL_GATE` to be requested explicitly; none is production-reachable by default.
- **Cluster-aware inference**: `statistical_inference.cluster_bootstrap_mean_interval` / `cluster_exact_sign_flip_pvalue` — resample **query clusters**, not individual rows, correcting a real bug where the real-LLM pilot's 120+ replicated rows (6 real queries × ~20 provider/pool variants) were treated as 120 independent observations.
- **Canonical evidence**: the specific, currently-cited result package for a given claim — see §6. "Canonical" always means "what the current submitted manuscript actually cites," not "the most recently generated" or "the largest" package; several historical packages remain tracked for provenance but are explicitly not canonical.

---

## 6. Experiment and Evidence Map

| Family | Canonical source | Status |
|---|---|---|
| Classical multi-ranker vote comparison (4 datasets, score-derived votes) | `reports/full_calibrated_core/` | **Canonical** — backs `main.tex` §4.1-4.3 |
| Normalization/pool-cutoff/baseline-fairness robustness | `reports/normalization_protocol_audit_20260714/`, `reports/candidate_pool_conditional_audit_20260714/`, `reports/final_revision_task1_pool_cutoff_20260715/`, `reports/final_revision_task4_exact_baseline_fairness_20260715/` | **Canonical**, supplementary robustness checks |
| Earlier four/two-dataset publication packages | `outputs/pub_vote_cmp_all4/`, `outputs/pub_vote_cmp_v2/` | **Historical** — last regenerated 2026-03-24, zero citations in `main.tex`; kept for ablation/provenance only |
| Real-LLM multi-provider pilot (6 real queries, 4 providers) | `reports/repair_frontier_20260729T144742Z/`, `reports/extraction_study_20260729T151610Z/`, `reports/repair_diagnostic_20260729T162748Z/` (row-level) | **Exploratory/directional** — row-level statistics are superseded for any inferential claim by the cluster-aware re-analysis below |
| Query-clustered re-analysis of the pilot above | `reports/real_llm_clustered_reanalysis_20260730T023745Z/` | **Canonical for inference** on the real-LLM pilot; point estimates in the row-level reports above remain valid, only their CIs/p-values are superseded |
| Integrated evidence audit (both bases together) | `reports/ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md` | **Canonical**, current; independently reviewed by `reports/ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md` |
| Outcome F: active-acquisition policy selection | `reports/policy_selection_20260726T030500Z/` | **Canonical, concluded** — no learned gate beat always-UHT; production locked accordingly (§7) |
| Raw real-LLM provider-response caches | `reports/multi_provider_repair_pilot_20260729T032348Z/raw_calls/`, `reports/multi_provider_repair_pilot_smoke_20260729T032209Z/raw_calls/`, `reports/reviewer_concerns_program_20260729T035320Z/raw_calls/` | **Excluded from Git** — compact parsed judgments/metadata are tracked where needed; raw transcripts are local/external-archive artifacts per `docs/EXPERIMENT_ARTIFACT_POLICY.md` |

Evidence-to-claim traceability for every number in `main.tex` is maintained
in `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md` (supersedes the older,
stale `MASTER_EVIDENCE_INVENTORY.csv`/`SECTION_EVIDENCE_MAP.csv` in the same
directory for lookups — those two predate `full_calibrated_core` and still
name the historical `pub_vote_cmp_all4` pipeline as canonical; kept for
provenance, not for current use).

---

## 7. Current Repository State

- **The Outcome F production guard exists and predates the repository-hygiene work described in this document.** It was committed before the reorganization/consolidation work this document describes, in the branch history that established `fix/outcome-f-production-operating-point`. It is a fully separate concern from repair (§1) — Outcome F is about *adaptive LLM-judge budget allocation policy*, not preference-graph repair.
- **Production misuse of learned routing is prevented by runtime validation, not just documentation.** `policy_selection.policy_gate.PolicySelector.__post_init__` raises `ValueError` if `execution_mode is ExecutionMode.PRODUCTION_UHT` and any learned-routing configuration (a non-default gate mode, or an attached calibration model) is present. Tests substitute a spy on `ProductionSafeguards`' methods and assert they were actually *called and changed execution* — the module's own docstring explicitly rejects "instantiating the object is not evidence of enforcement" as insufficient proof.
- **Recent repository work (this document's own motivating changes) primarily improved organization, statistical correctness, provenance, and experiment infrastructure** — not the scientific findings themselves. Specifically: a repository-hygiene reorganization (legacy reports/screenshots relocated into `docs/historical/`, `reports/_archive/`, etc.); a statistical bug fix (the real-LLM pilot's row-level bootstrap treated 120+ replicated rows as independent when only 6 queries are truly independent — now corrected via cluster-aware inference); a reproducibility hardening pass (solver-version pinning, a required CI job with zero tolerated test skips); and the consolidation/cycle-fix/documentation work described in this file.
- **Raw provider-response caches are deliberately not tracked under the explicit artifact policy.** Three real-LLM directories contain request/response transcripts that are not byte-reproducible on demand (re-querying providers may return different results as models update). Compact parsed judgments, model metadata, summaries, and row-level evidence are tracked where needed; raw transcripts and logs remain local/external-archive material. See `docs/EXPERIMENT_ARTIFACT_POLICY.md` and `docs/artifact_inventories/untracked_outputs_20260731.csv`.

---

## 8. Where to Start

| I want to understand... | Start here |
|---|---|
| **The core algorithm** (graphs, repair, ranking) | `src/consistency_ranker/graph_construction.py` → `mwfas_solver.py` → `baseline_ranking.py`; then `tests/test_graph_and_solver.py`, `tests/test_mwfas_solver.py`, `tests/test_baseline_ranking.py` |
| **Production policy selection** | `src/consistency_ranker/policy_selection/__init__.py`'s "Production vs research" docstring, then `production_config.py` → `production_runner.py`; tests in `tests/test_production_operating_point.py` |
| **The real-LLM experiments** | `docs/EXPERIMENTS.md`, then `reports/ir_evidence_audit_20260729T182949Z/FINAL_IR_EVIDENCE_AUDIT.md`, then the individual study STATUS.md files in `reports/repair_frontier_20260729T144742Z/` etc. |
| **Statistical analysis** | `src/consistency_ranker/statistical_inference.py`, especially the cluster-aware functions' docstrings; `tests/test_statistical_inference.py`, `tests/test_real_llm_clustered_reanalysis.py` |
| **Reproducibility** | `docs/REPRODUCTION_CANONICAL.md` for exact commands; `docs/EXPERIMENT_ARTIFACT_POLICY.md` for output-retention rules; `src/consistency_ranker/provenance.py` for the manifest/hashing primitives; `make verify-env` / `make check` / `make repo-ready` |
| **Release readiness / CI contract** | `docs/RELEASE_READINESS.md`; `.github/workflows/ci.yml`; `Makefile`; `scripts/run_cloud_validation.py` (canonical local/cloud replacement while GitHub Actions is blocked by a billing issue -- see `docs/EXPERIMENTS.md` "Cloud Validation") |
| **Tests** | `pytest -q` from the repo root; `tests/` mirrors `src/consistency_ranker/`'s module names 1:1 in most cases |
| **Manuscript evidence** | `papers/JDIQ_2026/manuscript/main.tex`, cross-referenced against `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md` |
| **Overall project status / handoff** | `PROJECT_STATUS.md` (the canonical entry point and documentation-authority map — read this first if any two documents disagree) |
