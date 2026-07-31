# Contributions

**Purpose:** an authoritative map of what this repository actually
contributes -- scientific and engineering -- so a future coding or research
agent does not have to re-derive it from 30+ overlapping `docs/*.md` files or
infer unsupported claims from report directory names. Every row below was
independently verified against the current manuscript source, tests, and
tracked evidence (not assumed from a filename or an older status document).

**If this document and any individual `docs/*.md` file disagree**, trust this
document for *classification* (canonical / negative / exploratory / internal)
and trust `papers/JDIQ_2026/manuscript/main.tex` for exact *numbers*. See
`docs/PROJECT_STATUS.md` for what is currently active/unfinished, and
`docs/claim_evidence_registry.yaml` for a machine-readable per-claim index.

**A future agent must not infer, from any report title, filename, or
directory name in this repository, that:**
1. Graph repair generally improves nDCG (the central, settled result is the opposite -- §1.1, §3).
2. Exploratory Borda/extraction-study effects are statistically confirmed (they are row-level point estimates that do not survive cluster-aware correction -- §1.2, §3).
3. Gurobi's agreement with SCIP is a paper contribution (it is an internal correctness check, never a manuscript claim -- §1.6, §3).
4. Learned policy routing is production-approved (Outcome F concluded the opposite; production is locked to a fixed default -- §1.7, §3).
5. Replicated rows from the real-LLM pilot are independent samples (there are 6 independent queries, not ~120 -- §1.2, §3).

## Contribution at a glance

| # | Contribution | Category | Status | Manuscript? |
|---|---|---|---|---|
| 1.1 | Data-quality taxonomy + construction-sensitivity demonstration | Scientific | Canonical | Yes |
| 1.1 | Exact MWFAS repair (SCIP) | Scientific | Canonical | Yes |
| 1.1 | Structural repair does not reliably improve retrieval (central result) | Scientific | Canonical, negative/conditional | Yes |
| 1.2 | Cluster-aware statistical inference | Scientific/methodological | Canonical (for its scope) | No |
| 1.3 | Extraction study / repair frontier / repair diagnostic | Scientific | Exploratory, row-level | No |
| 1.4 | Repository-scale oracle-headroom (preserve-vs-repair) | Scientific | Negative -- NO-GO | No (separate companion paper) |
| 1.5 | Real-LLM multi-provider pilot | Scientific | Exploratory | Directional only |
| 1.6 | Gurobi vs. SCIP solver cross-validation + scaling study | Internal validation | Internal validation only | **No -- never** |
| 1.7 | Production policy selection ("Outcome F") | Scientific | Negative, concluded | No |
| 1.8 | Consistency-aware pivot (3 pilots) | Scientific | Complete, mixed results | No |
| 2 | Solver abstraction, provenance infra, architecture guardrails, artifact policy, fresh-checkout fix, claim registry | Engineering | Complete | N/A |

---

## 1. Scientific contributions

### 1.1 Consistency-aware preference-graph repair program (`papers/JDIQ_2026/`)

This is the repository's one **submitted, canonical** scientific program.
Everything else in this section is either internal validation of it, or a
separate, non-manuscript research thread run on the same codebase.

| Field | Value |
|---|---|
| Contribution | A seven-dimension data-quality audit taxonomy for pairwise-preference graphs (provenance, calibration, vote semantics, conflict structure, repair quality, downstream utility, reproducibility), plus an empirical demonstration that construction choices (raw vs. normalized scores, vote regime, candidate-pool size) materially change graph structure and must be reported as first-class decisions. |
| Status | **Canonical** (submitted manuscript) |
| Implementation | `src/consistency_ranker/{graph_construction,cycle_detection,pairwise_prefs}.py` |
| Principal evidence | `reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables/` |
| Generating script | `full_calibration_utils.py:run_full_core()` (`reports/full_calibrated_core/scripts/`) |
| Principal tests | `tests/test_graph_and_solver.py`, `tests/test_normalization_protocols.py`, `tests/test_data_pairwise.py` |
| Manuscript section | Abstract; Table 1 (`tab:dq-taxonomy`); Figure 2 (`fig:bm25-share`); Table 3 row 1 |
| Limitations | 4 datasets (BRIGHT, FiQA, HotpotQA, SciDocs), score-derived votes for the primary evidence base (real-LLM judgments are a separate, smaller exploratory addendum, §1.5) |
| Double-blind suitable | Yes -- already in `main.tex` |

| Field | Value |
|---|---|
| Contribution | Exact Minimum Weighted Feedback Arc Set (MWFAS) repair pipeline (linear-ordering MIP: `before[u,v]` binary vars, antisymmetry + transitivity constraints, minimize removed weight), solved with the free, open-source SCIP solver, as the canonical exact backend. |
| Status | **Canonical** |
| Implementation | `src/consistency_ranker/mwfas_solver.py` (`solve(..., method="scip"/"exact"/"ilp")`), `src/consistency_ranker/exact_fas.py` (independent brute-force cross-check, `n<=10`) |
| Principal evidence | `reports/exact_open_source_ilp_repair_investigation/` -- 1,025/1,025 canonical queries solved to proven optimality; SCIP objective independently matched brute-force on 49 synthetic/real cases |
| Generating script | `reports/exact_open_source_ilp_repair_investigation/scripts/run_exact_open_ilp_study.py` |
| Principal tests | `tests/test_exact_mwfas_scip.py`, `tests/test_mwfas_solver.py`, `tests/test_solver_version_gate.py` |
| Manuscript section | §4.2-4.3 ("1,025/1,025 proven optimal", "0/36 canonical + 0/56 larger-pool Holm-significant") |
| Limitations | Exact solving is intractable well before the n=50/100 scales used in unrelated synthetic scale-sweep experiments -- see `reports/exact_solver_scaling_study_20260731T162314Z/` (§1.6). |
| Double-blind suitable | Yes -- SCIP only; no Gurobi result is used (see §1.6 and `papers/JDIQ_2026/manuscript/integrity_audit/EXTERNAL_SOLVER_IDENTITY.md`) |

| Field | Value |
|---|---|
| Contribution | **The central, settled result**: structural graph repair is real and non-trivial (removes cycles, changes top-*k* membership, exact repair removes materially less weight than greedy on cyclic queries) but **does not reliably improve retrieval quality (nDCG)** -- zero repaired-vs-unrepaired cells survive Holm correction across the primary protocol, the larger-pool study, or the exact-repair check. |
| Status | **Canonical, negative/conditional** (this is the manuscript's thesis, not an incidental finding) |
| Implementation | Evaluation pipeline in `reports/full_calibrated_core/scripts/full_calibration_utils.py`; statistics in `src/consistency_ranker/statistical_inference.py` (Holm correction, bootstrap CI, exact sign-flip) |
| Principal evidence | `reports/full_calibrated_core/`, `reports/normalization_protocol_audit_20260714/`, `reports/candidate_pool_conditional_audit_20260714/`, `reports/final_revision_task1_pool_cutoff_20260715/`, `reports/final_revision_task4_exact_baseline_fairness_20260715/` |
| Manuscript section | Table 3 rows 3-6, Table 4, Figure 3; Limitations §, `main.tex:459` ("a narrower and stronger conclusion than 'repair helps' or 'repair never helps'") |
| Limitations | Finite statistical power (median \|Δ\| 0.0036 vs. Holm-adjusted 80%-power MDE 0.0207 -- the null could mask a small true effect); ranker/benchmark scope; bounded real-LLM evidence |
| Double-blind suitable | Yes -- this is the paper |

### 1.2 Cluster-aware statistical inference for repeated judgments

| Field | Value |
|---|---|
| Contribution | Bootstrap/permutation inference that resamples independent **query clusters** rather than individual rows, correcting a real bug in an earlier analysis that treated a real-LLM pilot's 120+ replicated rows (6 queries x ~20 provider/pool variants) as 120 i.i.d. observations. |
| Status | **Methodological**, canonical for its own scope (not used by the main manuscript's primary evidence, which does not have this replication structure) |
| Implementation | `src/consistency_ranker/statistical_inference.py` (`compute_cluster_means`, `cluster_bootstrap_mean_interval`, `cluster_exact_sign_flip_pvalue`, `cluster_exact_permutation_correlation`) |
| Principal evidence | `reports/real_llm_clustered_reanalysis_20260730T023745Z/` |
| Generating script | `scripts/run_real_llm_clustered_reanalysis.py` |
| Principal tests | `tests/test_statistical_inference.py`, `tests/test_real_llm_clustered_reanalysis.py` |
| Manuscript section | Not cited by `main.tex` -- corrects inference for the separate real-LLM exploratory pilot (§1.5), not the primary score-derived evidence base |
| Limitations | Re-analysis of an n=6-query pilot; several claims that were "significant" at the (incorrect) row level are **no longer supported** after correction -- see §3 (Non-contributions) |
| Double-blind suitable | Not applicable (not in the manuscript); safe as an internal engineering/statistics correction |

### 1.3 Extraction reliability, repair-frontier, and repair-diagnostic studies

Three related but distinct exploratory studies over the same small real-LLM
pilot (6 queries, 4 providers); each asks a different question about *when*
repair choices matter.

| Field | Value |
|---|---|
| Contribution | Extraction study: whether ranking-*extraction*-method choice (not repair) explains observed ranking gains. |
| Status | **Exploratory/directional** at the row level; inferential claims (not point estimates) are superseded by the clustered reanalysis (§1.2) |
| Implementation | `src/consistency_ranker/extraction_study/` |
| Principal evidence | `reports/extraction_study_20260729T151610Z/`, re-analyzed in `reports/real_llm_clustered_reanalysis_20260730T023745Z/extraction_clustered_results.csv` |
| Principal tests | `tests/test_extraction_study.py` |
| Manuscript section | Not in `main.tex` |
| Double-blind suitable | Not applicable (not in the manuscript) |

| Field | Value |
|---|---|
| Contribution | Repair frontier: enumerates a richer set of repair/extraction candidates per query (incumbent, greedy, exact, SCC-local variants) and asks whether a label-free rule can select among them; estimates oracle headroom. |
| Status | **Exploratory/directional**; row-level inferential claims superseded by §1.2 |
| Implementation | `src/consistency_ranker/repair_frontier/` |
| Principal evidence | `reports/repair_frontier_20260729T144742Z/`, re-analyzed in `reports/real_llm_clustered_reanalysis_20260730T023745Z/repair_frontier_clustered_results.csv` |
| Principal tests | `tests/test_repair_frontier.py` |
| Manuscript section | Not in `main.tex` |
| Double-blind suitable | Not applicable |

| Field | Value |
|---|---|
| Contribution | Repair diagnostic: whether pre-repair graph features predict repair outcome (does repair help or harm *this* query). |
| Status | **Exploratory** at the row level (one flagged Holm-significant association) -- **does not survive** cluster-aware re-analysis (§3); separately, the follow-on repository-scale version of this question reached a firm **NO-GO** (§1.4) |
| Implementation | `src/consistency_ranker/repair_diagnostic/` |
| Principal evidence | `reports/repair_diagnostic_20260729T162748Z/`, re-analyzed in `.../repair_diagnostic_clustered_results.csv` |
| Principal tests | `tests/test_repair_diagnostic.py` |
| Manuscript section | Not in `main.tex` |
| Double-blind suitable | Not applicable |

### 1.4 Repository-scale oracle-headroom analysis (preserve-vs-repair, NO-GO)

| Field | Value |
|---|---|
| Contribution | Tests whether a query's pre-repair graph properties can predict, in principle, whether repair will help that specific query -- at repository scale (419 distinct queries, 122,203 unified rows from 76 already-existing per-query source files across 4 datasets), not just the 6-query pilot. |
| Status | **Negative/null -- NO-GO, concluded.** Oracle headroom is real (query-level 95% CI [0.0020, 0.0030]) but ~8x below the manuscript's own Holm-adjusted 80%-power minimum-detectable-effect (0.0207); every pre-repair covariate shows negligible univariate association. Converges with four independent prior attempts at the same question (`outputs/learned_selector/`, `experiments/failure_class_audit_20260711_212157/`, `src/consistency_ranker/repair_selector_mining/` (never executed), and the pilot-scale diagnostic in §1.3). |
| Implementation | `scripts/run_oracle_headroom_analysis.py`, `scripts/run_repository_scale_headroom_analysis.py` |
| Principal evidence | `reports/oracle_headroom_gate0_20260728T230000Z/`, `reports/repository_scale_headroom_analysis/` (see `research_decision.md` for the stop decision) |
| Principal tests | `tests/test_oracle_headroom.py`, `tests/test_repository_scale_headroom_analysis.py` |
| Manuscript section | **Explicitly not cited by `main.tex`** -- belongs to the separate `papers/negative_result_2026/` companion-paper track, not a revision of the JDIQ submission |
| Double-blind suitable | N/A for JDIQ; is the intended evidentiary basis for the separate negative-result paper |

### 1.5 Real-LLM multi-provider pilot (exploratory addendum)

| Field | Value |
|---|---|
| Contribution | Genuine (non-synthetic) Azure/Gemini/Cohere/Fireworks pairwise judgments on 6 real queries, used as a small, explicitly directional robustness check alongside the classical score-vote evidence base -- **not** a second large-*n* confirmatory study. |
| Status | **Exploratory** |
| Implementation | `src/consistency_ranker/multi_provider_eval/` |
| Principal evidence | `reports/multi_provider_repair_pilot_20260729T032348Z/` (compact summaries; raw transcripts intentionally excluded from Git per `docs/EXPERIMENT_ARTIFACT_POLICY.md`) |
| Manuscript section | Referenced qualitatively, if at all; not the source of any numbered manuscript claim |
| Double-blind suitable | Directional only -- do not present as confirmatory |

### 1.6 Gurobi vs. SCIP solver cross-validation and scaling study (internal validation)

| Field | Value |
|---|---|
| Contribution | Independent verification of the canonical SCIP-based exact-repair result using a second, industrial-grade commercial MIP solver (Gurobi 13.0.2, WLS academic license, available for the first time on 2026-07-31); plus a first empirical characterization of where exact MWFAS solving becomes intractable (both solvers fail by n=50 on synthetic cyclic graphs; SCIP already fails by n=40, Gurobi still succeeds there). |
| Status | **Internal validation / robustness characterization only.** Not a scientific contribution in its own right -- confirms an existing result and characterizes solver performance, does not change any conclusion. |
| Implementation | Uses the existing, unmodified `mwfas_solver.py` `_solve_gurobi`/`_solve_scip` backends |
| Principal evidence | `reports/gurobi_vs_scip_solver_cross_validation_20260731T162314Z/` (1,025/1,025 queries: 0 objective mismatches, 0 removed-edge-set mismatches, 0 not-both-proven-optimal), `reports/exact_solver_scaling_study_20260731T162314Z/` (SCIP times out at n=40 within 30s; Gurobi solves it in 4.5-9.6s; both fail by n=50) |
| Manuscript section | **None, deliberately.** Per `papers/JDIQ_2026/manuscript/integrity_audit/EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md` (a related, though not identical, anonymity-driven decision about a *different* external solver package) and every other repo doc (`README.md`, `docs/REPRODUCTION_CANONICAL.md`, `docs/READ_ME_FIRST_FOR_AI.md`), Gurobi is never cited as producing a manuscript result. This validation does not change that. |
| Double-blind suitable | **No -- must never be added to `main.tex` or any anonymized submission material.** |

### 1.7 Production policy selection / "Outcome F" (separate research thread)

Not part of the JDIQ manuscript (zero references to "policy_selection",
"Outcome F", or "production_uht" in `main.tex`) -- a genuinely separate
research thread on the same codebase, about adaptive LLM-judge budget
allocation, not preference-graph repair.

**Naming note (do not conflate):** this section's "Outcome F" is an
outcome-letter in the policy-selection thread's own A-F decision taxonomy.
It is unrelated to `main.tex`'s `tab:dq-taxonomy` audit dimension "F"
("graph repair is assumed to improve retrieval") -- that is the
manuscript's own, differently-scoped A-G lettering for a different
question. Same letter, two unrelated taxonomies, no shared meaning.

| Field | Value |
|---|---|
| Contribution | Established that an oracle query-specific acquisition-policy selector beats a fixed always-UHT default in principle (margin 0.1965 corrected utility), but that **no currently-implemented learned/hard/calibrated/selective/soft/staged gate realizes that gap** -- one gate (`selective_three_way`) was actively worse than the fixed default. |
| Status | **Negative result, concluded.** Production locked to the fixed default (`always-UHT` + a non-routing safety floor) as a direct consequence. |
| Implementation | `src/consistency_ranker/policy_selection/` (`production_config.py`, `production_runner.py`, `policy_gate.py`) |
| Principal evidence | `reports/policy_selection_20260726T030500Z/` |
| Generating script | `scripts/run_policy_selection_experiment.py` |
| Principal tests | `tests/test_policy_selection.py`, `tests/test_production_operating_point.py` |
| Manuscript section | Not in `main.tex` |
| Double-blind suitable | Not applicable |

### 1.8 Consistency-aware active-acquisition / regularized-aggregation / stopping-rule pivot

A separate, current research thread (three same-day pilots, all built on one
real, frozen SciDocs oracle: 50 queries, 15 candidates, C(15,2)=105 exhaustive
real gpt-4o-mini pairwise judgments per query) -- independent of the JDIQ
repair program, sharing only the general theme of sparse/inconsistent LLM
preference evidence.

| Field | Value |
|---|---|
| Contribution | Offline active pair-selection strategy (uncertainty x counterfactual top-k impact x ambiguity). |
| Status | **Negative result, complete.** Loses to random unrevealed-pair selection at both 10% and 20% budget checkpoints (Holm-corrected). |
| Principal evidence | `reports/offline_active_acquisition_pilot_20260728T142414Z/` |
| Manuscript section | Not applicable to JDIQ; candidate for a separate future writeup, none currently drafted |

| Field | Value |
|---|---|
| Contribution | Prior-regularized Bradley-Terry aggregation (reduces to the BM25 prior at zero evidence, relaxes as evidence accumulates). |
| Status | **Safety-dominant, not universally superior.** Significantly beats BM25 at 10%/20% budget and significantly reduces severe-harm rate vs. naive sparse Copeland aggregation at 5%/10% budget; does **not** establish significantly higher raw mean nDCG/AUC than the strongest non-oracle baseline (`pure_bt_no_prior`) -- a disclosed limit, not an oversight. |
| Principal evidence | `reports/regularized_aggregation_pilot_20260728T164943Z/` |

| Field | Value |
|---|---|
| Contribution | Risk-controlled, qrel-free stopping rule (worst-case top-k-change statistic) layered on the aggregator above. |
| Status | **Complete, "useful but incomplete."** Median stop budget 34.3% (< 40% target); 0/35 test queries showed severe harm; does not meet its own quality-recovery bar (>=95% of exhaustive improvement recovered), traced to the aggregator's slow-converging tail, not a stopping-rule defect. |
| Principal evidence | `reports/stopping_rule_pilot_20260728T190000Z/` |
| Limitations (all three pilots) | Validated on exactly one real oracle (50 SciDocs queries, one judge model, one candidate-pool size) -- no cross-dataset/cross-judge generalization evidence exists yet. |

---

## 2. Engineering contributions

*(Repository cleanup, reorganization, and documentation are explicitly **not**
listed here as contributions in their own right -- they support reproducing
and understanding the scientific work above, they are not the work.)*

| Contribution | Implementation | Tests | Notes |
|---|---|---|---|
| Unified MWFAS solver abstraction (greedy / SCIP / Gurobi behind one interface, with a solver-version gate for canonical reproduction) | `src/consistency_ranker/mwfas_solver.py` | `tests/test_mwfas_solver.py`, `tests/test_exact_mwfas_scip.py`, `tests/test_solver_version_gate.py` | `verify_canonical_solver_version()` pins PySCIPOpt==6.2.1, the exact version every committed exact-repair result was generated with |
| Provenance and reproducibility-manifest infrastructure | `src/consistency_ranker/provenance.py` | `tests/test_provenance.py` | File hashing, git-commit/dirty-state capture, canonical-output overwrite protection |
| Architecture-boundary enforcement (import-cycle detector) | `scripts/check_architecture_boundaries.py` | `tests/test_check_architecture_boundaries.py` | Built after finding and fixing one real circular dependency (`multi_provider_eval` <-> `multifactor_acquisition`); wired into CI |
| Experiment/output artifact policy (two complementary documents) | `docs/ARTIFACT_POLICY.md` (broad, dated decision log), `docs/EXPERIMENT_ARTIFACT_POLICY.md` (timestamped-experiment/raw-provider-cache specifics) | -- | Genuinely distinct scopes, not a duplicate; each names the other |
| Portability checks (no hardcoded machine-specific paths in active code/docs) | `scripts/check_active_portability.py` | `tests/test_active_portability.py` | Historical generated reports are explicitly exempted (immutable provenance) |
| Production policy guardrails (runtime-enforced, not just documented) | `src/consistency_ranker/policy_selection/{policy_gate,production_config,production_runner,safe_fallback}.py` | `tests/test_policy_selection.py` | `PolicySelector.__post_init__` raises `ValueError` on any attempt to configure learned routing while in production execution mode; tests assert the safeguard was actually *called*, not just instantiated |
| Reproducible experiment infrastructure | `docs/REPRODUCTION_CANONICAL.md` (exact seeds, table-to-command map) | `make verify-env`, `make test-full`, `scripts/check_repo_ready.py` | Supersedes the stale `docs/REPRODUCTION_Q1.md` |
| **Fresh-checkout test reproducibility (2026-07-31)** | `tests/conftest.py` (`real_data` marker autouse skip-guard), `pyproject.toml` (marker registration + default deselection), `Makefile` (`test-real-data` target), `.gitignore` (untracked `reports/final_revision_task3_ranker_dependence_20260715/scripts/` fix) | `tests/test_fresh_checkout_reproducibility.py` | Fixed ~64 tests that previously hard-failed (not skipped) on a genuinely fresh clone because they silently depended on developer-local prepared datasets or a gitignored source directory; see `docs/EXPERIMENTS.md` "Test Tiers" |
| Claim-to-evidence registry and validator | `docs/claim_evidence_registry.yaml`, `scripts/validate_claim_evidence_registry.py` | -- | Machine-readable index of major claims with canonical/noncanonical status, evidence paths, and manuscript applicability |

---

## 3. Non-contributions and rejected claims

Statements below are conclusions this repository's own evidence **does not
support**. Listed so a future agent does not resurrect a superseded claim
from an old report title or an early drafting document.

| Claim NOT supported | Why | Evidence |
|---|---|---|
| "Graph repair improves retrieval quality" (as a general/unconditional claim) | The validated result is conditional/negative: repair is structurally active but does not reliably move nDCG after correction. | `main.tex` Table 3-4; `docs/ARCHITECTURE.md` §1 |
| "A selective/conditional repair policy empirically improves over both always-FAS and never-FAS" | This was an **earlier, since-abandoned** project direction (pre-JDIQ-pivot). `docs/LITERATURE_ALIGNMENT.md` and `docs/THEORETICAL_FOUNDATION.md` still contain this claim but describe a project framing the current manuscript does not use. | Contradicted by `main.tex`'s actual (opposite) thesis; both docs now carry a superseded banner (added 2026-07-31) |
| "Borda is significantly worse than the incumbent ranking" (extraction study) | Row-level bootstrap (n=120, i.i.d. assumption) showed a significant CI; at the true n=6 cluster level, exact sign-flip p=0.9375 after Holm correction. Direction isn't even consistent across queries (2/6 vs. 4/6). | `reports/real_llm_clustered_reanalysis_20260730T023745Z/conclusion_change_matrix.csv` |
| "`is_cyclic`/`topk_involvement` predicts repair benefit" (repair diagnostic) | Row-level Holm-significant association does not survive cluster-aware re-analysis (Holm p=1.0 at true n=6). Independently, the repository-scale follow-up found negligible association for every covariate (§1.4). | Same file; `reports/repository_scale_headroom_analysis/research_decision.md` |
| "A learned policy selector/gate beats the fixed default" (Outcome F) | No learned/hard/calibrated/selective/soft/staged gate beat always-UHT; one was actively worse. | `reports/policy_selection_20260726T030500Z/decision.json` |
| "Multifactor acquisition improves retrieval quality at matched budget" | Only cost-only utility signals are established; the original evaluation had four concrete measurement bugs (now corrected, still no quality win found). | `docs/MULTIFACTOR_PRODUCTION_UHT_EVAL_INVALIDATION.md` |
| "The active pair-selection proposal (uncertainty x impact x ambiguity) is a viable acquisition strategy" | Evidenced-worse than random on the one oracle tested. | `reports/offline_active_acquisition_pilot_20260728T142414Z/` |
| "Repository-scale oracle headroom supports a predictive preserve-vs-repair model" | Explicit NO-GO -- headroom is ~8x below the detectable-effect floor. | `reports/repository_scale_headroom_analysis/research_decision.md` |
| Historical `outputs/pub_vote_cmp_all4/`, `outputs/pub_vote_cmp_v2/`, `outputs/q1_journal_package/` as "canonical evidence" | Zero citations in `main.tex`; superseded by `reports/full_calibrated_core/` (2026-07-15 pipeline swap). `docs/experiment_inventory.md` and `reports/experiment_inventory.json` still label the old package "Canonical" -- both corrected 2026-07-31. | `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md` |
| "Solver superiority (Gurobi vs. SCIP) is a manuscript contribution" | It is an internal robustness/correctness check only, run after this repository's own SCIP-based result was already canonical and complete; explicitly excluded from any anonymized submission material. | §1.6 above |
| Statistical significance from row-level pseudo-replication in general | Any repeated-judgment analysis that resamples rows instead of independent query clusters over-states significance -- this is the exact bug §1.2 corrects. Treat any *uncorrected* row-level p-value in a historical report as provisional, not confirmatory. | `src/consistency_ranker/statistical_inference.py` cluster-aware functions' docstrings |

---

## See also

- `docs/PROJECT_STATUS.md` -- what is active, unfinished, and what to work on next (this document is a map of *what exists and its status*, not a live TODO list).
- `docs/ARCHITECTURE.md` -- module layering, terminology, canonical-module map.
- `docs/EXPERIMENTS.md` -- experiment-family index, entry points, test tiers.
- `docs/claim_evidence_registry.yaml` -- machine-readable per-claim registry with stable IDs.
- `papers/JDIQ_2026/EVIDENCE_PROVENANCE_20260730.md` -- exact number-to-table-cell provenance for every `main.tex` claim.
