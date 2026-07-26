# Reviewer Concern Gap Audit

**Audit date:** 2026-07-26 (local, evening of 2026-07-25)
**Auditor:** read-only repository inventory (no billed API calls, no source/test/report modification)
**Scope:** entire working tree at `fix/outcome-f-production-operating-point` @ `3e02b73`, audited against the two Iran Journal of Computer Science reviewer reports (decision 2026-07-05)
**Files created by this audit:** this file only.

---

## 1. Executive Summary

Of the **14** distinct Iran JCS reviewer concerns: **4 are RESOLVED** (C6 graph-only, C7 exact FAS baseline, C8 greedy-vs-exact attribution, C9 Copeland/balance justification via added families), **5 are SUBSTANTIALLY ADDRESSED** (C3 modern LLM rerankers present with completed runs; C5 fusion artifact ablated by α-sweeps; C10 PageRank/RankCentrality/BT/Markov/SpringRank present with HodgeRank explicitly excluded; C12 statistical machinery + null-result reframing; C14 JDIQ compression), **4 are PARTIALLY ADDRESSED** (C2/C11 predictive criterion — Outcome F shows current gates fail while an oracle still wins; C4 real-LLM volume exists but the matched multi-factor pilot does not; C13 multi-dataset coverage incomplete), and **1 needs manuscript reframing rather than new methods** (C1 “logically obvious”). **0 concerns are INVALIDATED BY NEW EVIDENCE** in the sense of overturning the reviewers; exact-vs-greedy evidence *does* invalidate the worry that weak retrieval gains are an artifact of a poor heuristic (C8 → RESOLVED).

**Major proposed baselines already exist and must not be re-implemented:** exact SCIP MWFAS (1,025/1,025 optimal), unrepaired/greedy/exact three-way fairness, PageRank, Rank Centrality, Bradley–Terry, Markov, SpringRank/SerialRank, graph-only method keys, α-sweeps, RRF/CombSUM/Borda fusion, RankGPT-style listwise, pairwise/pointwise LLM, local MiniLM cross-encoder, UHT/challenger/hybrid/robust acquisition, and four smoke-tested providers (Azure, Cohere, Fireworks, Vertex Gemini). HodgeRank, Plackett–Luce, RankLLM/RankZephyr/RankVicuna, personalized PageRank, CP-SAT, and learned fusion remain absent by decision or omission — none of these is the cheapest next step.

**Single best next task:** a **zero-cost offline real-query gate/repair utility replay** on existing SciDocs OpenAI pairwise (q50), failure-mining azure+cohere oriented caches, and the 200-record multi-provider provenance store — producing a per-query decision table (repair vs unrepaired; always-UHT vs challenger/robust) with query-clustered inference — *before* any new billed 30–40×2×2×orientation pilot. That pilot remains P1 only for cells the caches cannot fill. Paid calls are **not** required for the selected next task.

---

## 2. Repository and Branch State

All values below were re-derived directly from git during this audit (not copied from prior reports).

| Item | Value |
|---|---|
| Repository root | `/home/soroush/consistency-aware-llm-rankin` |
| Current branch | `fix/outcome-f-production-operating-point` |
| Current commit | `3e02b73666506f3eb894f5df2c531284ea31a60e` ("Update JDIQ title page with verified support and acknowledgments", 2026-07-15) |
| Upstream | **None configured** for this branch (`git rev-parse @{upstream}` fails); remote `origin` = `github.com/SoroushVahidi/consistency-aware-llm-rankin.git`; `main` tracks `origin/main` and is at the same commit |
| Merge base with `main` | `3e02b73` — **identical to HEAD**; the branch contains **zero commits** of its own |
| Staged changes | none |
| Unstaged modified (tracked) | `pyproject.toml` (+6: ruff E501 per-file-ignores for policy_selection), `src/consistency_ranker/__init__.py` (+3: exports `dag_linear_extensions`, `dag_ambiguity`, `soft_score_ranking`), `src/consistency_ranker/baseline_ranking.py` (+10: docstring note) — 19 insertions total |
| Untracked files | **1,163** (716 under `reports/`, 353 under `papers/`, 75 under `src/`, 9 `scripts/`, 8 `tests/`, plus `AUDIT_LOCAL_BRANCH.md`, `REMEDIATION_REPORT.md`) |
| Reviewable commit for the remediation? | **No.** Every line of the Outcome D/F, remediation, and 2026-07-25 experiment work is uncommitted (untracked or unstaged). There is no commit range to review; audit finding F-004 remains open. |

### Claims independently re-verified this session

| Reported claim | Verification | Result |
|---|---|---|
| 781 tests pass | `pytest -q -p no:cacheprovider` (full suite) | **781 passed in 10.85 s** — confirmed |
| `PolicySelector()` defaults to production UHT | live Python: `PolicySelector().mode / .execution_mode` | `always_uht` / `production_uht` — confirmed; `PolicySelector(mode="selective_three_way")` raises `ValueError` in production; `resolve_execution_mode(None)` → `production_uht` |
| Ruff clean on changed files | `ruff check --no-cache` on `policy_selection/`, `scripts/run_production_uht.py`, `tests/test_production_operating_point.py` | All checks passed — confirmed |
| mypy 36 → 0 on policy-selection | `mypy src/consistency_ranker/policy_selection --ignore-missing-imports` (mypy 2.1.0) | "Success: no issues found in 17 source files" — confirmed |
| Frozen Outcome F benchmark reproduces bit-for-bit | Full re-run of `scripts/run_policy_selection_experiment.py` into `/tmp/ps_audit_verify` (synthetic judges only), diffed against `reports/policy_selection_20260726T030500Z/` | **All 192 `gate_rows.json` rows identical (0 mismatches).** `summary.json`/`decision.json` numerically identical except `runtime_s` and `NaN` self-comparison. **Provenance nuance:** the frozen `summary.json`/`decision.json` contain three keys the current code does not emit — `operating_point.interim_safety_floor`, `operating_point.interim_safeguards`, `decision_rationale` — so the frozen decision files were post-processed or written by an earlier script revision. Numeric reproduction is exact; byte-level reproduction of those two JSON files is not possible with current code. |
| Historical artifacts unchanged | `git status` — the frozen report dirs are untracked and this audit wrote nothing into them | Confirmed (only this file was created) |

---

## 3. Research Timeline

Chronological map of all locally identifiable work relevant to the reviewer concerns. Sources: dated commit log, report-directory timestamps (`stat`), and report headers.

| When | Work | Evidence |
|---|---|---|
| ≤ 2026-03 | Original manuscript "Consistency-Aware Reranking via Preference-Graph Repair: Structural Gains and Conditional Retrieval Effects" + core library (greedy FAS, Copeland/balance/Markov extraction, hybrid fusion, synthetic + BEIR-style experiments; `outputs/` precomputed results) | repo root zip `Consistency_Aware_Reranking_..._IJCS.zip`; `outputs/`; commits ≤ 2026-04 |
| 2026-03-24 | IP&M desk reject (venue fit) | `reports/final_revision_task6_.../tables/rejection_history_matrix.md` row 10 |
| 2026-04-04 | JIIS desk reject (scope) | same, row 11 |
| 2026-04-05/06 | Real OpenAI pairwise runs completed (HotpotQA/SciDocs), API-readiness checks; "3-dataset real-LLM evidence" alignment | commits `775c929`, `791c09f` |
| 2026-07-05 | **Iran JCS rejection** — decision email, 2 reviewers (thread `19f33ef60276e744`, editor Habib Izadkhah) | `reports/final_revision_task9_.../tables/iran_jcs_final_closure_matrix.md` |
| 2026-07-12→15 | JDIQ pivot: 10 revision tasks (`reports/final_revision_task1..task10_20260715/`), retitle to a data-quality framing, exact-baseline fairness (task 4), DQ framework (task 5), rejection audit (task 6), page-limit freeze, JDIQ submission frozen at `3e02b73` | commit log 2026-07-12..15; `reports/final_revision_*`; `papers/JDIQ_2026/` |
| 2026-07-25 11:09–11:11 | 3 aborted/superseded linear-extension report stubs (`...T150000Z`, `T151500Z`, `T152000Z`) | dir mtimes |
| 2026-07-25 14:57–14:58 | **Linear-extension extraction experiment** (`reports/linear_extension_extraction_20260725T190000Z` + final `T191500Z`): new `dag_linear_extensions.py`, `dag_ambiguity.py`, `soft_score_ranking.py` incl. SpringRank/SerialRank transfer from the author's other repos (`minimum-weighted-fas-heuristics`, `ranking-by-feedback-arc-set`) | report §1; `scripts/linear_extension_method_audit.md` |
| 2026-07-25 15:27 | **Multi-provider LLM robustness pilot** (`reports/multi_provider_llm_robustness_20260725T200000Z`): smoke OK for azure/cohere/fireworks/gemini; **200 real billed calls** (azure 60, cohere 50, fireworks 40, gemini 50); 2 SciDocs queries × 4 docs × both orientations × 4 providers; marked INCOMPLETE (global 200-call ceiling) | `FINAL_REPORT.md`, `INCOMPLETE.md`, `STAGE1_SPENDING.json` |
| 2026-07-25 16:39 | **Reliability-aware repair** (`reports/reliability_aware_repair_20260725T210000Z`): reliability-weighted construction/repair variants, Holm-corrected paired tests, Outcome C | `FINAL_REPORT.md`, `INCOMPLETE.md` |
| 2026-07-25 17:40 | **Adaptive acquisition** (`reports/adaptive_acquisition_20260725T220000Z`): 18-policy acquisition sweep incl. `uncertainty_x_topk_impact` (UHT), Outcome B | `FINAL_REPORT.md` |
| 2026-07-25 18:47 | **Prior-robust / Outcome D** (`reports/prior_robust_20260725T233000Z`): 8 seeds × 6 priors × 3 judges × 10 policies; "gate robust path on diagnostics"; Q̂ estimator | `FINAL_REPORT.md`, `decision.json` |
| 2026-07-25 22:59 | Policy-selection quick run (`...T025426Z`, **Outcome A**, superseded) | dir + `decision.json` |
| 2026-07-25 23:00–23:01 | **Policy-selection full benchmark / Outcome F** (`reports/policy_selection_20260726T030500Z`): 16 gate modes × 12 held-out cells; no learned gate beat always-UHT; interim OP = always-UHT + safety floor | `FINAL_REPORT.md` |
| 2026-07-25 23:17 | Independent audit `AUDIT_LOCAL_BRANCH.md` (verdict NOT PRODUCTION-READY, findings F-001..F-017) | file mtime |
| 2026-07-25 23:43–23:47 | **Production remediation** on `fix/outcome-f-production-operating-point`: `execution_mode.py`, `production_config.py`, `production_runner.py`, `scripts/run_production_uht.py`, 31 contract tests; `REMEDIATION_REPORT.md`; `IMPLEMENTATION_STATUS_20260726.md` added to frozen report dir | file mtimes; §2 verification above |

---

## 4. Reviewer Concerns

Source of record: `reports/final_revision_task9_final_peer_review_20260715/tables/iran_jcs_final_closure_matrix.md` (fresh full Gmail re-read of decision thread `19f33ef60276e744`, confirmed complete against Task 6's `rejection_history_matrix.md`). The 14 concerns below are kept materially distinct; reviewer attribution follows the quoted text.

| ID | Reviewer | Exact concern (quoted where available) |
|---|---|---|
| C1 | R1 | "The main finding … is a logical necessity rather than a novel discovery … a trivial outcome of the defined construction rules … insufficient for a significant publication." |
| C2 | R1+R2 | Lacks a new, generalizable insight/criterion predicting when repair helps (novelty variant raised by both). |
| C3 | R1 | "core experiments are based on a non-LLM multi-ranker pipeline … outdated pipeline … modern retrieval field is largely focused on LLM-based reranking … Generalizing the results to modern settings is not well-supported." (TF-IDF/BM25/MiniLM primary pipeline) |
| C4 | R2 | "real LLM experiments are too limited to support the broader framing." |
| C5 | R1 | "hybrid ranking formula … very specific way of integrating the repaired graph … conditional effect might be an artifact of this formulation" (linear prior+graph fusion may suppress/distort repair effects) |
| C6 | R1 | "does not sufficiently investigate whether conclusions hold using only graph scores or different fusion strategies." |
| C7 | R1 | "relies on a greedy cycle-peeling heuristic … does not compare this against any stronger or exact baseline." |
| C8 | R1 | "unclear whether limited gains are due to inherent limitations or poor performance of this heuristic" (weak gains may reflect the chosen heuristic, not graph repair itself). |
| C9 | R2 | "focuses on Copeland and balance scores … does not justify why these were chosen over … other plausible alternatives." |
| C10 | R2 | "…such as PageRank or HodgeRank" — spectral/flow-based extraction methods absent or insufficiently evaluated. |
| C11 | R2 | "stops short of offering actionable advice … does not provide a clear criterion for deciding when repair should be applied in a new setting." |
| C12 | R1 | "actual retrieval improvements are minimal and mostly statistically uncertain … weak and inconsistent evidence does not justify the paper's contribution as a significant advancement in retrieval research." |
| C13 | R1+R2 | Results may be dataset-specific / "concerns about whether findings are specific to these rules or more general." |
| C14 | R2 (+R1 overlap) | "The manuscript is somewhat repetitive and could be shortened." — and (R1) overstates its contribution. |

Task 9's independent re-read confirmed **no additional criticisms** exist in the decision email beyond these (closure-matrix row 10).

---

## 5. Reviewer-Concern Matrix

| ID | Reviewer | Exact concern | Existing code | Existing tests | Existing experiments | Existing artifacts | Current evidence | Status | Remaining gap | Cheapest nonduplicative next action | Real calls? | Provider / local | Est. calls | Est. cost | Acceptance criterion | Manuscript implication |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | R1 | Finding is a logical necessity / trivial construction outcome | JDIQ DQ reframing (`sec:dq-object`, taxonomy); contribution list in Task 5/8/9 reports | n/a (framing) | n/a | `reports/final_revision_task{5,9}_*/`; `iran_jcs_final_closure_matrix.md` row 1 | Reframing exists and is end-to-end consistent for JDIQ; does not neutralize an IR-methods novelty demand | **NEEDS MANUSCRIPT REFRAMING** | No new method will resolve “triviality”; either keep DQ framing or accept residual novelty risk | Do **not** invent a new baseline; write an IJCS-facing response that cites C7/C8/C12 evidence as *measurement* contribution | No | — | 0 | $0 | Independent reader can state the claimed contribution without using the phrase “repair sometimes helps” | Lead with taxonomy/decision-rule; demote repair-helps claims |
| C2 | R1+R2 | No generalizable criterion predicting when repair helps | `prior_quality.py:137-201` (Q̂); `policy_calibration.py` P(UHT optimal); `repair_selector_mining/`; `gate_features.py`; Outcome F gates | `tests/test_policy_selection.py`; `tests/test_prior_robust.py` | Outcome D + F (synthetic); repair-selector overnight | `reports/prior_robust_20260725T233000Z/`; `reports/policy_selection_20260726T030500Z/` (oracle corr≈0.17 vs always-UHT≈−0.03; no learned gate wins) | Oracle advantage is real; current predictors are **not** decision-safe on synthetic held-out n=12 | **PARTIALLY ADDRESSED** | No validated *real-query* criterion; Outcome F ≠ “selection impossible” | Offline replay of repaired vs unrepaired + UHT vs robust on existing real caches (§15) | No (first); maybe later | Reuse azure/cohere/openai caches | 0 new | $0 | Held-out real-query table where a pre-specified rule beats always-repair and always-no-repair on corrected utility, or a documented failure to do so | Report checklist + explicit “no validated selector yet” |
| C3 | R1 | Pipeline is TF-IDF/BM25/MiniLM, not modern LLM reranking | `llm_pairwise.py`, `llm_listwise.py` (RankGPT-style), `llm_pointwise.py`, `cross_encoder.py` | `tests/test_modern_baselines.py` | SciDocs listwise q20, pairwise q50, pointwise q20; MiniLM 500q | `outputs/openai_scidocs_real_{pairwise_q50,pointwise_q20,listwise_q20}_k15/`; `outputs/final_modern_baselines/scidocs/` | Modern LLM *judgment/rerank* machinery and completed runs exist; RankZephyr/RankLLM **absent** (do not port) | **SUBSTANTIALLY ADDRESSED** | Manuscript still under-cites existing LLM runs relative to IR-methods expectations; no RankZephyr | Cite existing RankGPT-style/pairwise/pointwise/cross-encoder artifacts; **do not** implement RankLLM | No | — | 0 | $0 | Related-work + results tables explicitly list the completed LLM protocols | Replace “outdated pipeline” language with protocol inventory |
| C4 | R2 | Real LLM experiments too limited | Multi-provider stack; OpenAI/Gemini/Azure/Cohere clients | multi_provider tests; readiness scripts | OpenAI SciDocs 50 / HotpotQA 20 / FiQA 10; failure-mining oriented; multi-provider **2q** pilot | §8 inventory; `INCOMPLETE.md` on multi-provider report | Volume exists on one provider; matched multi-factor design does **not** | **PARTIALLY ADDRESSED** | Joint 30–40×2×2×orientation factorial missing | Offline analysis of existing caches first; then fill missing cells only | Deferred | Azure + Cohere preferred (largest oriented cache) | 0 now; later O(200–800) | later ~tokens only (USD table unset) | Scope statement matches actual N/providers/prompts/orientations | Bound LLM claims as protocol audit unless pilot completes |
| C5 | R1 | Linear prior+graph fusion may distort repair effects | Hybrid formula `run_method_improvement_audit.py:809-813`; α-sweep; unrepaired hybrids | Task4 / normalization tests | α∈{0.1,0.3,0.5,1.0} calibrated-core; fas_balance sweeps | `alpha_query_metrics.csv`; Task4 tables | α-sensitivity + unrepaired hybrids already tested | **SUBSTANTIALLY ADDRESSED** | None requiring new fusion math | Cite existing α-sweep; avoid re-deriving CombMNZ (DO_NOT_ADD) | No | — | 0 | $0 | Paper states α=0.3 is not unique and reports graph-only rows | Keep fusion as sensitivity, not contribution |
| C6 | R1 | Graph-only / alternative fusion insufficiently tested | Graph-only method keys; `fas_balance` α=0 = graph-only (`baseline_ranking.py:229-243`); RRF/CombSUM/Borda | `test_alpha_zero_matches_balance_ranking`; Task4 | Pure Copeland/balance/Markov/PageRank/… graph rankings in Task4 + calibrated-core | `reports/final_revision_task4_…/`; full_calibrated_core CSVs | Graph-only **is** recoverable and reported; note α=1 in manuscript hybrid is **still fusion** | **RESOLVED** | Doc clarity on two α semantics | None scientific; optional doc note on α semantics | No | — | 0 | $0 | Tables include named graph-only rows | Already in JDIQ baseline tables |
| C7 | R1 | No stronger/exact baseline vs greedy peeling | `mwfas_solver.py` SCIP; `exact_fas.py` brute | `tests/test_exact_mwfas_scip.py` | 1,025/1,025 proven optimal; Task4 three-way | `reports/exact_open_source_ilp_repair_investigation/`; Task4 FINAL_REPORT | Exact baseline complete | **RESOLVED** | Do not re-run ILP | Cite 1,025 optimality + 0 Holm-significant retrieval cells | No | — | 0 | $0 | Exact cited with query count and optimality proof rate | Strongest answer to R1 |
| C8 | R1 | Weak gains may reflect heuristic, not repair | Same as C7 + structural gap tables | SCIP≤greedy weight tests | Structural gap large (mean weight 2.31→1.70); retrieval Δ≈0 after Holm | `structural_summary_greedy_vs_ilp.csv`; Task4 0/36 & 0/56 Holm-sig | Evidence attributes limited retrieval gains to **repair itself**, not greedy suboptimality | **RESOLVED** | — | Do not invent another approximate FAS | No | — | 0 | $0 | Explicit sentence: exact repair closes structural gap without retrieval significance | Directly answers R1 attribution worry |
| C9 | R2 | Copeland/balance insufficiently justified | PageRank, RankCentrality, BT, Markov, Borda, SpringRank, SerialRank | Task4 tests; soft-ranking tests | Task4 three-way; linear-extension soft catalog | Task4 tables; `linear_extension_extraction_20260725T191500Z/` | Families expanded and justified | **SUBSTANTIALLY ADDRESSED** | Soft SerialRank weak (τ≈0.24) — already reported | No new extractor required | No | — | 0 | $0 | Baseline section lists ≥ PageRank + RankCentrality + BT with rationale | Keep exclusion list for Elo/TrueSkill |
| C10 | R2 | PageRank / HodgeRank absent | PageRank FIV; HodgeRank **DO only** (explicit exclusion) | Task4 PageRank tests | PageRank in Task4 | `baseline_completeness_decision.md` | PageRank done; HodgeRank deliberately out of scope | **SUBSTANTIALLY ADDRESSED** | Hodge cyclic energy still absent as a *feature* too | Do **not** implement HodgeRank unless a venue demands it; optional cyclic-energy feature only if predictive work needs it | No | — | 0 | $0 | Manuscript states exclusion reason | Already drafted for JDIQ |
| C11 | R2 | No actionable advice / when to apply repair | `tab:practical-implications` checklist; Outcome F interim always-UHT+floor; production runner | 31 production contract tests | Outcome F; production remediation | `policy_selection_…/FINAL_REPORT.md`; `REMEDIATION_REPORT.md`; production code | Checklist + “always-UHT interim” exist; predictive selector failed | **PARTIALLY ADDRESSED** | Real-query actionable rule still missing; floor cost unvalidated (§11) | Same as C2 offline replay; plus synthetic safeguard-cost save (§11 P0 ops) | No | — | 0 | $0 | Decision table or explicit negative result on real caches | Prefer narrow checklist over false predictor |
| C12 | R1 | Retrieval gains minimal / statistically uncertain | `statistical_inference.py` (sign-flip, bootstrap, Holm/BH/BY); evaluation metrics | Task2 power reports; bootstrap scripts | Holm-corrected nulls throughout Task4 / exact-ILP | Task2/4 reports; `bootstrap_method_deltas.py` | Uncertainty is **measured**, not ignored; query is the test unit | **SUBSTANTIALLY ADDRESSED** | MAP helper missing from `evaluation.py` (consumed as column only) | Do not re-bootstrap completed cells; optional MAP function centralization | No | — | 0 | $0 | All headline deltas carry multiplicity-aware inference | Embrace null as DQ finding |
| C13 | R1+R2 | Results may be dataset-/rule-specific | SciDocs/FiQA/HotpotQA/BRIGHT + synthetic regimes; multi-extractor Task4 | Task1/3/4 tests | Multi-dataset proxy + limited real LLM | §6.5; Task3 ranker-dependence | Multi-dataset proxy strong; real LLM breadth thin; TREC DL absent locally | **PARTIALLY ADDRESSED** | No TREC DL data locally; multi-provider N=2 | Offline multi-dataset cache replay; download TREC DL only if IR venue demands | No (first) | — | 0 | $0 | Same qualitative conclusion on ≥3 datasets or documented exception | Stress multi-dataset + multi-extractor |
| C14 | R2 (+R1) | Repetitive / overstates contribution | Task 8 compression 49→39 pp; Task 9 fresh-read dedup | n/a | n/a | `reports/final_revision_task{8,9}_*/` | Substantially shortened for JDIQ; IJCS zip still older text | **SUBSTANTIALLY ADDRESSED** | If returning to IJCS, re-apply compression to that lineage | Doc/manuscript alignment only | No | — | 0 | $0 | No triple-restated null headline; contribution list matches evidence | Align claims with §5 statuses |

**Status counts:** RESOLVED 4 · SUBSTANTIALLY ADDRESSED 5 · PARTIALLY ADDRESSED 4 · NEEDS MANUSCRIPT REFRAMING 1 · NOT ADDRESSED 0 · INVALIDATED BY NEW EVIDENCE 0 (C8’s *worry* is invalidated by evidence, which is why it is labeled RESOLVED).

---

## 6. Baseline Inventory

Status vocabulary: FULLY IMPLEMENTED AND VALIDATED (FIV) / IMPLEMENTED BUT NOT VALIDATED (INV) / PARTIALLY IMPLEMENTED (PI) / IMPLEMENTED UNDER ANOTHER NAME (IUAN) / EXPERIMENT COMPLETED (EC) / EXPERIMENT PARTIALLY COMPLETED (EPC) / DOCUMENTED ONLY (DO) / PLANNED-TODO ONLY (PT) / ABSENT (AB) / UNCLEAR (UN).

### 6.1 Repair and ordering baselines

| Item | Status | Key evidence |
|---|---|---|
| No repair (unrepaired) | FIV | `reports/full_calibrated_core/scripts/full_calibration_utils.py:123-141`; `scripts/run_real_experiment.py:2076-2080`; artifact `reports/final_revision_task4_exact_baseline_fairness_20260715/tables/three_way_unrepaired_greedy_exact.csv` (unrepaired Copeland 0.325 vs greedy 0.336) |
| Greedy cycle peeling (current) | FIV | `src/consistency_ranker/greedy_fas.py:25-78`; `tests/test_greedy_fas.py`; canonical driver `full_calibration_utils.py:997-1004` |
| Alternative greedy repair | PI | Metric-aware reweight + same peeling: `src/consistency_ranker/metric_aware_repair.py:1-19`; cost-attr greedy: `src/consistency_ranker/reliability_repair/reliability_weighted_repair.py:17-40` (+ `reports/reliability_aware_repair_20260725T210000Z/`). No alternate peeling strategy (max-weight, Eades) in-package |
| Local-ratio / MWFAS-inspired repair | PI (external only) | LRTA reached only via `sys.path.insert(0, "/home/soroush/minimum-weighted-fas-heuristics/src")` in `experiments/method_improvement_audit_20260711_205733/run_method_improvement_audit.py:1042-1057`; not vendored into `src/` |
| Exact min-weight FAS (ILP) | FIV | SCIP MIP `src/consistency_ranker/mwfas_solver.py:178-312` (aliases `scip`/`exact`/`ilp` at `:420-426`); `tests/test_exact_mwfas_scip.py`; **1,025/1,025 queries proven optimal** (`reports/exact_open_source_ilp_repair_investigation/FINDINGS.md`; mean FAS weight greedy 2.31 vs exact 1.70) |
| Exact Kemeny optimization | PI / IUAN | Local adjacent-swap Kemenization `src/consistency_ranker/baseline_ranking.py:358-419`; the MWFAS linear-ordering MIP is Kemeny-equivalent for weighted tournaments but never named Kemeny; closest-extension Kendall ILP (HiGHS) `dag_linear_extensions.py:517-538` is prior-distance on a DAG, not Kemeny aggregation |
| CP-SAT / ILP formulation | IUAN (SCIP primary, Gurobi legacy, HiGHS for closest extension); CP-SAT AB | `mwfas_solver.py:26-38, 233-255, 315-417`; `dag_linear_extensions.py:562-588` |
| Brute-force exact ordering (small n) | FIV | `src/consistency_ranker/exact_fas.py:28-99` (n≤10); `docs/tables/exact_vs_greedy_summary.csv`; SCIP↔brute 49/49 match (`tables/scip_vs_bruteforce_validation.json`) |
| Approximation baseline w/ guarantees | PT | `TODO.md:25` only |
| Heuristic optimality-gap computation | FIV | `scripts/run_exact_vs_greedy.py`; `reports/exact_open_source_ilp_repair_investigation/tables/structural_summary_greedy_vs_ilp.csv`; test `test_scip_removed_weight_never_worse_than_greedy` |
| Repair-objective eval independent of retrieval | FIV | `cycle_detection.py:21-100`; structural CSVs in exact-ILP report; `multi_provider_eval/graph_eval.py:57-102` |

**Other-repo reuse:** yes, documented. The sibling repos `minimum-weighted-fas-heuristics` (exact SCC DP, LRTA, WMSF, IPSNS via hardcoded `sys.path`; identity audit at `papers/JDIQ_2026/manuscript/integrity_audit/EXTERNAL_SOLVER_IDENTITY.md`) and `ranking-by-feedback-arc-set` (SpringRank + SerialRank **transferred into** `src/consistency_ranker/soft_score_ranking.py:73-188`) are already reused; EXP11 Kahn tie-breaker ideas were mapped into `dag_linear_extensions.py` (`reports/linear_extension_extraction_20260725T191500Z/AUDIT.md:25-45`). Proposing to "port the MWFAS repo" would duplicate work already done.

### 6.2 Graph extraction and aggregation

| Method | Status | Key evidence / properties |
|---|---|---|
| Balance score | FIV | `baseline_ranking.py:193-207`; weighted; doc-id tie-break; isolates→0; used in primary hybrids + Task 4 |
| Copeland | FIV | `baseline_ranking.py:296-299` (unweighted out−in); also `src/rerankers/tournament_agg.py:42-76`; primary hybrids |
| PageRank | FIV | `baseline_ranking.py:302-355` (reverse graph, α=0.85, weighted, max_iter=100, tol=1e-6); Task 4 three-way tables; **no explicit doc-id tie-break** (noted in Task 4 §9) |
| Personalized PageRank | AB | no `personalize=` usage in `src/` |
| HodgeRank / Hodge decomposition / cyclic energy | DO (explicit exclusion) | `reports/final_revision_task9_.../tables/baseline_completeness_decision.md`; manuscript justifies exclusion; zero implementation |
| Rank Centrality | FIV | `baseline_ranking.py:439-508` (weighted, no teleport, max_iter=200, tol=1e-8; disconnected components stay separate); Task 4 tables |
| Bradley–Terry | FIV | `src/rerankers/tournament_agg.py:109-186` (MM, max_iter=100, tol=1e-6); Task 4 tables |
| Plackett–Luce | AB | bib-only |
| Borda (graph) | FIV | `baseline_ranking.py:422-436` (unweighted out-degree) |
| Kemeny ranking | PI | see 6.1 |
| Spectral ranking | IUAN | SerialRank (Fiedler) `soft_score_ranking.py:138-188`; SpringRank `:73-135`; validated in `reports/linear_extension_extraction_20260725T191500Z/` (soft_springrank mean τ≈0.56; soft_serialrank ≈0.24 — weak) |
| Stationary-distribution / Markov | FIV | `markov_graph_ranking.py:1-150` (teleport 0.15, max_iter=10k, tol=1e-10; unique π on disconnected graphs); Task 4 `markov_graph`/`markov_hybrid` |
| GNN-based ranking | AB | SerialRank comment cites GNNRank convention only |
| Score-sum | FIV | `baseline_ranking.py:65-113` |
| Topological / linear-extension family | FIV | `dag_linear_extensions.py` (lexicographic Kahn, static/dynamic balance, normalized-balance, ratio, source-sink peeling, closest extension greedy/exact/ILP, random sampling); ambiguity features `dag_ambiguity.py`; `tests/test_dag_linear_extensions.py`; experiment `reports/linear_extension_extraction_20260725T191500Z/` |
| Win-rate / tournament sort | INV | `tournament_agg.py`; unit tests only; not in calibrated-core PAIR_SPECS |

### 6.3 Fusion methods

| Item | Status | Key evidence |
|---|---|---|
| Prior only | FIV | `run_real_experiment.py:691-696`; `hybrid_rrf_prior_only` α=0 mode |
| Graph only | FIV (as named methods) | `copeland_graph`, `balance_graph`, `markov_graph`, etc. (`reports/full_calibrated_core/scripts/run_full_calibrated_core.py:191-211`) |
| Fixed linear fusion | FIV | manuscript hybrids α=0.3 min-max (`full_calibration_utils.py:1152-1190`); formula `norm(prior) + α·norm(graph)` at `run_method_improvement_audit.py:809-813` |
| Tuned linear fusion | EC (grid, not learned) | `scripts/run_fas_balance_alpha_*.py`; calibrated-core α sweep {0.1, 0.3, 0.5, 1.0} → `alpha_query_metrics.csv` |
| Alpha sweep | EC | synthetic {0.0, 0.25, 0.5, 1.0, 2.0} (`run_fas_balance_alpha_sweep.py:68`); real CLI default {0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0} (`run_real_experiment.py:2207`) |
| Normalized linear fusion | FIV | min-max both sides; also `zscore` / `rank` modes (`run_method_improvement_audit.py:814-823`) |
| RRF | FIV | `rrf_ranking.py` (k=60); tests; full_calibrated_core |
| CombSUM | FIV | `combsum_ranking.py`; tests |
| CombMNZ | EPC / DO | exploratory only, decision DO_NOT_ADD (`reports/jdiq-overnight-cont-20260713-230229/tables/phase03_combmnz.json`; scidocs CombSUM 0.1866 vs CombMNZ 0.1884); no `src/` module |
| Borda fusion | FIV | `borda_fuse_ranking.py` |
| Learned fusion | AB (explicitly declined) | Task 9/10 scope decisions |
| Rank / min-max / z-score normalization | FIV | hybrid modes + `tests/test_normalization_protocols.py`; primary protocol `minmax_query_ranker` |
| Score calibration | FIV | full_calibrated_core + `reports/normalization_protocol_audit_20260714/` |
| Fusion sensitivity analysis | EC | alpha sweeps + unrepaired/repaired ablations + Task 4 pool fairness |

**Graph-only via α — two conflicting semantics coexist:**
- Manuscript hybrid (`run_method_improvement_audit.py:812`): `combo = norm(prior) + α·norm(graph)` → α=0 is **prior-only**; no α value yields graph-only; graph-only is provided by separate method keys.
- Library `fas_balance_score_prior_alpha_beta_ranking` (`baseline_ranking.py:229-243`): score = β·norm(balance) + α·norm(prior) → **α=0 is graph-only** (tested by `test_alpha_zero_matches_balance_ranking`).
Reviewer concern C6 (graph-only) is therefore already answerable from existing artifacts; no new fusion mechanism is needed to demonstrate it.

### 6.4 Modern LLM reranking

| Item | Status | Key evidence |
|---|---|---|
| RankGPT-style listwise (sliding window) | EC | `src/rerankers/llm_listwise.py:4-56, 169-330`; run `outputs/openai_scidocs_real_listwise_q20_k15/` (gpt-4o-mini, window 15, step 7, 20 queries, $0.0051). Note: `docs/related_work_positioning_note.md:32-36` stale — says unimplemented |
| RankLLM / RankVicuna | AB | no match |
| RankZephyr | DO | related-work discussion only (`papers/JDIQ_2026/manuscript/IJCS_REUSE_AUDIT.md:41-47`) |
| Pairwise LLM (PRP-style, all-pairs → Copeland) | EC | `src/rerankers/llm_pairwise.py:4-26, 588-708`; SciDocs q50 (5,250 judgments), HotpotQA q20, FiQA q10; multi-provider pilot 2026-07-25 |
| Pointwise LLM | EC | `src/rerankers/llm_pointwise.py`; `outputs/openai_scidocs_real_pointwise_q20_k15/` (300 calls) |
| Setwise LLM | DO | related-work only |
| Sliding-window | EC | see listwise |
| All-pairs comparison | EC | `llm_pairwise.py:588-624` |
| Tournament comparison | EC (aggregation, not acquisition) | `tournament_agg.py:244-305`; `tests/test_modern_baselines.py:106-162` |
| UHT (uncertainty × top-k impact) | FIV (synthetic only) | `adaptive_acquisition/acquisition_policies.py:112-131, 298-330`; `ranking_impact.py:132-142`; `policy_selection/policy_runner.py:52-58`; validated in `reports/adaptive_acquisition_20260725T220000Z/` |
| Challenger / hybrid / robust policies | FIV (synthetic only) | `prior_robust/challenger_pool.py:13-143`; `robust_acquisition.py:20-149`; `policy_runner.py:74-132`; `reports/prior_robust_20260725T233000Z/`, `reports/policy_selection_20260726T030500Z/` |
| Local cross-encoder | EC | `src/rerankers/cross_encoder.py`; `outputs/final_modern_baselines/scidocs/` (`cross-encoder/ms-marco-MiniLM-L-6-v2`, 500 queries, nDCG 0.8977) |

### 6.5 Datasets and judgments (summary)

| Dataset | Local data | Real-LLM judgments | Status |
|---|---|---|---|
| SciDocs | raw 70M + processed (1000 q / 29,928 qrels) | OpenAI gpt-4o-mini pairwise q20⊂q30⊂q50 (5,250 judgments, k=15, **no orientation reversal**, `debias_position: false`); pointwise q20; listwise q20; Gemini pilot 2q/380 judgments; multi-provider pilot 2q × 4 providers × AB/BA | DATA + EXPERIMENT COMPLETED (single-provider); multi-provider PARTIAL |
| HotpotQA | raw 678M + processed | OpenAI pairwise q10, q20 (900); failure-mining oriented azure+cohere | DATA + EXPERIMENT COMPLETED (q20) |
| FiQA | raw 92M + processed | OpenAI q20 run **only 10 queries processed** (46 judgments); failure-mining ≤25 oriented | DATA + EXPERIMENT PARTIAL |
| BRIGHT | raw 1.8G + processed (1,384 q) | proxy vote graphs; failure-mining LLM ≤25 q | DATA + proxy EC; LLM partial |
| TREC DL 2019/2020, MS MARCO, NFCorpus | registry stubs only (8 KB READMEs) | none | REFERENCED ONLY |
| SciFact, TREC-COVID, NovelEval | — | — | ABSENT |
| Synthetic burial-heavy regimes | generated in-code | synthetic judges (`outsider_buried`, `nontransitive`, `shared_position_bias`) | EC (`prior_robust`, `policy_selection` reports) |
| Failure-mining LLM corpus | `reports/failure_mining_llm_v3/` | azure+cohere, `debias_position=True`, 6,010 ab + 6,010 ba live calls over 69 query_ids, 22,008 prompt-level records (2026-07-09/10) | EC (single-prompt family) |

### 6.6 Judgment-bias controls (summary)

Implemented and exercised: orientation reversal (`src/rerankers/llm_pairwise.py:527-572`; `multi_provider_eval/orientation.py:9-64`), first-position-bias measurement (`orientation.py:51-54`), prompt variants (`multi_provider_eval/prompts.py:50-79`: `legacy_v1`, `concise_v1`, `json_ab_v1`, `json_tie_v1`), provider variants, majority voting (`orientation.py:67+`, `ensemble.py:13-51`), confidence weighting (`ensemble.py:91-124`), tie/abstention parsing (`multi_provider_eval/parsing.py:12-93`), cycle measures (`cycle_detection.py`), round-robin pool policy (`candidate_pool_policies.py:75-80`), active comparison selection (`adaptive_acquisition/acquisition_policies.py:312-355`), outsider probes (`production_runner.py:163-190`), mixed diagnostic probes (`diagnostic_probes.py`). Repeated-judgment grids: implemented (`run_multi_provider_llm_robustness.py --repeats`, default 3) but the stochastic repeat grid was cut off by the 200-call ceiling. **Notable gap:** the high-volume OpenAI runs (q20/q30/q50) were collected with `debias_position: false` — no orientation reversal — so the largest single-provider corpus cannot answer order-bias questions by itself.

### 6.7 The proposed 30–40 query × 2 providers × 2 prompts × orientation pilot — already run?

**No.** All four factors have never been satisfied jointly. Closest artifacts:
- `reports/multi_provider_llm_robustness_20260725T200000Z/`: 4 providers × both orientations × up to 4 prompts, **but only 2 SciDocs queries** (200 calls; stopped at the global ceiling; only `legacy_v1` covers all providers × both queries × both orientations).
- `outputs/openai_scidocs_real_pairwise_q30_k15/`: **30 queries** complete, but 1 provider, 1 prompt, no orientation.
- `reports/failure_mining_llm_v3/`: 2 providers (azure+cohere) with orientation on ~25 queries/dataset over 3 datasets, but a single prompt family and a failure-mining (not calibration) design.
The design is explicitly listed as **future work** in `scripts/run_policy_selection_experiment.py:971-974` and in the Outcome F report. Classification: machinery PRESENT, joint experiment ABSENT.

---

## 7. Provider Infrastructure Inventory

Shared machinery: exponential-backoff retries (`src/rerankers/llm_pairwise.py:239-314, 377-422`); full-provenance cache keys (provider/model/prompt/orientation/decoding/seed/code-version/repeat) in `src/consistency_ranker/multi_provider_eval/cache.py:14-47` with append-only resumable store (`cache.py:55-95`); records persist raw response, tokens, latency, retries, seed, temperature, endpoint, timestamps (`multi_provider_eval/schema.py:30-67`); call/token spending ceilings (`multi_provider_eval/spending.py:10-94`; USD pricing **not configured** — `SPENDING_SUMMARY.json` reports $0.00 despite 200 calls). **Known hazard:** the legacy `JudgmentCache` keys only on query/docs/method (`src/rerankers/common.py:51-67`) — no model/prompt/orientation provenance — affecting all 18 legacy caches (`EXISTING_CACHE_INVENTORY.csv`).

| Provider | Client | Credentials | Smoke (2026-07-25) | Successful runs | Usable model IDs |
|---|---|---|---|---|---|
| OpenAI | `openai.OpenAI` chat + Responses fallback (`llm_pairwise.py:68-82, 239-285`) | `OPENAI_API_KEY` | (not in pilot) | SciDocs q50 pairwise 5,250 judgments (2,100 new calls, 0 errors); pointwise 300; listwise 20; HotpotQA q20; FiQA 10q | `gpt-4o-mini` |
| Gemini / Vertex AI | `google.genai.Client`, direct-key + Vertex/ADC (`llm_pairwise.py:326-375`) | `GEMINI_API_KEY`/`GOOGLE_API_KEY`; Vertex via `GOOGLE_GENAI_USE_VERTEXAI` + ADC (`failure_mining/llm_runner.py:162-234`) | OK, 1.65 s | 50 pilot calls (Vertex `gemini-2.5-flash`); earlier direct pilot 2q/380 judgments then free-tier 429 quota exhaustion | `gemini-2.5-flash` (Vertex); legacy `gemini-3.1-flash-lite-preview` |
| Fireworks | OpenAI-compatible; `FIREWORKS_BASE_URL` (`llm_runner.py:315-339`) | `FIREWORKS_API_KEY` | OK, 0.46 s | 40 pilot calls; validity 24/24, position consistency 11/12 | `accounts/fireworks/models/gpt-oss-120b` (old default llama-v3p1-8b 404s) |
| Cohere | compatibility API `https://api.cohere.ai/compatibility/v1` (`llm_runner.py:340-361`) | `COHERE_API_KEY` | OK, 0.42 s | 50 pilot calls; failure-mining v3 3,005 cached judgments; concurrency 4 validated (8 → 429 storms) | `command-r-plus-08-2024` |
| Azure OpenAI | OpenAI-compatible Azure v1 endpoint (`llm_runner.py:286-306`) | `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` | OK, 1.13 s | 60 pilot calls; failure-mining v3 3,005 cached judgments; 210-call burst in 22.4 s | `gpt-4.1-mini`; strong tier `gpt-5.4` configured but **never executed** |
| Anthropic | ABSENT (env var checked in `src/rerankers/common.py:177-183`, no client) | — | — | — | — |
| CloudRift | OpenAI-compatible (`llm_runner.py:362-368`) | `CLOUDRIFT_API_KEY` | — | none successful (275/275 legacy failures; 503 history) | — |

All four pilot providers (azure, cohere, fireworks, gemini/Vertex) have verified working credentials, smoke tests, retry/rate-limit handling, token accounting, dedup/resume, and raw-response persistence as of 2026-07-25. **Model discovery/listing is not implemented** for Cohere/Fireworks/Azure (only OpenAI/Gemini probes exist in `utils/llm_api_status.py:34-130`).

---

## 8. Completed Experiment Inventory

Real-model experiments (with outputs located):

| Experiment | Queries | Provider/model | Prompts | Orientation | Judgments/calls | Artifacts |
|---|---|---|---|---|---|---|
| SciDocs pairwise q20→q30→q50 (nested caches, seed 42, k=15, temp 0) | 20/30/50 | OpenAI `gpt-4o-mini` | 1 (`prompts/pairwise_comparison.txt`) | **none** | 2,100 / 3,150 / 5,250 | `outputs/openai_scidocs_real_pairwise_q{30,50}_k15/`, `outputs/openai_scidocs_real_run_q20_k15/` |
| SciDocs pointwise q20 | 20 | OpenAI `gpt-4o-mini` | 1 | n/a | 300 calls | `outputs/openai_scidocs_real_pointwise_q20_k15/` |
| SciDocs listwise (RankGPT-style) q20 | 20 | OpenAI `gpt-4o-mini` | 1 | n/a | 20 calls | `outputs/openai_scidocs_real_listwise_q20_k15/` |
| HotpotQA pairwise q10/q20 | 10/20 | OpenAI `gpt-4o-mini` | 1 | none | 450/900 | `outputs/openai_hotpotqa_real_run_q{10,20}_k15/` |
| FiQA pairwise (target 20) | **10 processed** | OpenAI `gpt-4o-mini` | 1 | none | 46 | `outputs/openai_fiqa_real_run_q20_k15/` (partial) |
| Gemini SciDocs pilot | 2 (stopped by quota) | `gemini-3.1-flash-lite-preview` | 1 | none | 380 judgments / 307 calls | `outputs/gemini_scidocs_real_pilot/` |
| LLM SciDocs pilot comparison | — | OpenAI | 1 | — | 9,500 cached | `outputs/llm_scidocs_pilot_comparison/` |
| Failure-mining v3 | ≤25/dataset (69 query_ids), fiqa/hotpotqa/bright | Azure `gpt-4.1-mini` + Cohere `command-r-plus-08-2024` | 1 family | **yes** (6,010 ab + 6,010 ba) | 22,008 prompt-log records; 2×3,005 caches (2026-07-09) | `reports/failure_mining_llm_v3/` |
| Selector LLM extension | — | Azure + Cohere | 1 | — | 985+992 cached, 3,925 prompt records (2026-07-10) | `reports/selector_llm_extension/` |
| Multi-provider robustness pilot | **2** SciDocs queries × 4 docs | Azure `gpt-4.1-mini` 60, Cohere `command-r-plus-08-2024` 50, Fireworks `gpt-oss-120b` 40, Vertex `gemini-2.5-flash` 50 | `legacy_v1` full + 3 partial | **yes** (100 ab / 100 ba) | exactly 200 new calls; 91,720 prompt + 3,730 completion tokens; stopped at `global_call_ceiling` | `reports/multi_provider_llm_robustness_20260725T200000Z/` |
| Local cross-encoder baseline | 500 SciDocs | `cross-encoder/ms-marco-MiniLM-L-6-v2` (local) | — | — | — | `outputs/final_modern_baselines/scidocs/` (nDCG 0.8977) |

Synthetic/proxy experiment series completed 2026-07-25 (no API calls): linear-extension extraction (final `...T191500Z`), reliability-aware repair (Outcome C), adaptive acquisition (Outcome B, 18 policies), prior-robust (Outcome D, 8 seeds × 6 priors × 3 judges × 10 policies), policy selection (Outcome F, 16 gate modes × 12 held-out cells). Earlier completed evidence packages: exact-ILP repair (1,025 queries), Task 1–10 final-revision reports (2026-07-14/15), full_calibrated_core, pub-vote suites (proxy graphs).

---

## 9. Duplicate and Overlap Findings

From the duplication scan (hashes verified where stated):

1. **Nested judgment caches:** SciDocs q20 ⊂ q30 ⊂ q50 by exact record-set inclusion — the q50 cache is the superset all downstream work should reference (linear-extension configs already point at q50).
2. **Duplicate metric helpers:** canonical `evaluation.py:31/170` (`kendall_tau`, `ndcg_at_k`) reimplemented privately in ~12 scripts (`run_real_experiment.py:420/476`, all `run_openai_real_*.py`, `run_gemini_scidocs_pilot.py`, `run_modern_baselines.py`, …) and `_topk_jaccard` in 3 packages (`production_runner.py:330`, `prior_robust/evidence_stability.py:29`, `anytime_metrics.py`).
3. **Multiple default definitions:** safety floor 0.15 in `production_config.py:34` (authoritative) plus hardcoded in `policy_mixture.py:13,18,31,42,65` and the experiment script; `min_evidence_fraction_to_stop=0.2` in `production_config.py:58` duplicated at `safe_fallback.py:52`; probe budget 3 in 4 places; "alpha" means damping 0.85 in `pagerank_ranking` but teleport 0.15 in `markov_graph_ranking` (same name, different semantics).
4. **Near-clone script families:** `run_openai_real_{pilot,pairwise_q30,pointwise,listwise}.py` differ mainly in judgment mode + hardcoded sizes; `run_fas_balance_*.py` differ by grid. Paper copies under `papers/.../anonymous_supplementary/scripts/` are byte-identical (sha256 match).
5. **Superseded report directories:** linear-extension `T150000Z`/`T151500Z`/`T152000Z` are early, superseded by `T190000Z` and final `T191500Z`; `policy_selection_20260726T025426Z` (quick, Outcome A) superseded by `T030500Z` (Outcome F). Both policy dirs share an identical `INCOMPLETE.md` (sha256 48115f62…).
6. **Duplicated data copies:** raw ↔ processed qrels/queries byte-identical for scidocs/fiqa/hotpotqa (BRIGHT queries differ); `outputs/real_full/*/qrels/bootstrap/*.csv` share one hash across 4 datasets (likely stubs); `data/processed/beir/fiqa/pairwise/preferences.jsonl` is empty.
7. **Paper-tree duplication:** `papers/JDIQ_2026/submission/final_anonymous/` vs `final_submission_materials/anonymous_supplementary/` contain dozens of byte-identical files; paper `task_reports/` are slimmed, *edited* snapshots of `reports/final_revision_task*` (FINAL_REPORT.md hashes differ for tasks 1–5).
8. **Temp files at repo root:** 6 `IMG_52*.png` screenshots + 4 UUID-named PNGs, untracked/unreferenced.
9. **Stale docs contradicting code:** `AUDIT_LOCAL_BRANCH.md` describes the pre-remediation defaults (now fixed) — historical, should be labeled as such; `docs/related_work_positioning_note.md:32-36` claims listwise is unimplemented though `llm_listwise.py` + completed run exist; obsolete TODO at `run_real_experiment.py:443`.
10. **Frozen decision-file provenance drift** (found by this audit's re-run): `reports/policy_selection_20260726T030500Z/{summary,decision}.json` contain `interim_safety_floor`, `interim_safeguards`, `decision_rationale` keys the current script no longer emits (numeric payload reproduces exactly).

Nothing was deleted or consolidated during this audit.

---

## 10. Experimental Feature-Schema Defect (`evidence_fraction`)

Verified directly in code and artifacts:

1. **Root cause.** `src/consistency_ranker/policy_selection/gate_features.py:241` and `:275` read `summary.get("evidence_fraction") or 0.0`, but `evidence_fraction_summary` (`src/consistency_ranker/prior_robust/prior_dependence.py:161-185`) returns only `n_acquired`, `n_inferred`, `n_prior_only`, `n_prior_agree_among_acquired`, `n_prior_contradict_among_acquired`, `prior_agreement_rate`. The correct coverage quantity exists separately as `topk_evidence_coverage(...).fraction_acquired` (`prior_dependence.py:129-158`).
2. **Constant features (artifact-verified).** In `reports/policy_selection_20260726T030500Z/rows.jsonl` (48 rows) and `...T025426Z/rows.jsonl` (24 rows): `evidence_only_stability_proxy` = 0.0 in **all** rows; `preliminary_g_prior` = 1.0 in **all** rows. A third feature, `stability_correctness_warn` (online stage), degenerates to `q_hat >= 0.55` because `ev_frac < 0.25` is always true.
3. **Constant during training, calibration, and test** — the constancy holds across every serialized row in both report dirs, i.e., across train/val/test splits.
4. **Reports do not claim they vary.** `FINAL_REPORT.md`/`AUDIT_POLICY_GATE.md` discuss probe informativeness generically; `REMEDIATION_REPORT.md:256` (§9 item 3) explicitly documents the bug. No report describes these two features as informative.
5. **Serialized models are entangled.** All calibration models pin `"schema_version": "policy_gate_features_v1"` and list both feature names. `model_logistic.json` (T030500Z) carries weight **−0.2672** on `preliminary_g_prior` (acting as a constant bias offset, since the feature never varies) and 0.0 on `evidence_only_stability_proxy`. Changing feature semantics without a version bump would silently invalidate these weights; loaders reject mismatched versions (`gate_features.py:90-94`, `policy_calibration.py:96-99`), so a **versioned schema (`legacy_v1` → `coverage_v2`) is the correct fix path** and is technically supported by the existing version-check machinery.
6. **Production is unaffected.** `production_runner.py:187-196` computes coverage via `topk_evidence_coverage` directly; the production UHT path never consults the broken gate features.
7. **Tests needed for a fix** (list only, not implemented): lock `evidence_fraction_summary`'s return schema; freeze `legacy_v1` dead semantics for replay; assert `coverage_v2` uses `fraction_acquired`; version-mismatch rejection both directions; replay loads only matching schema; `stability_correctness_warn` behavior under v2; production invariance; calibration retrain/migration path.
8. **Future experiments must exclude legacy models** trained on `policy_gate_features_v1` from any comparison that uses corrected features; the historical constant-feature vectors should be kept as-is for Outcome F replay compatibility.

---

### 6.8 Routing / predictive baselines (H)

| Item | Status | Notes |
|---|---|---|
| QPP / Q̂ (`estimate_prior_quality`) | IUAN + EC (negative as hard gate) | Predicts **prior-ranking credibility**, not absolute quality or P(UHT optimal) (`prior_quality.py:137-201`, weights 0.55/0.15/0.15/0.10/0.05). Distinct from calibration target `uht_optimal` (`policy_benchmark.py:321-322`) |
| Query clarity / entropy | IUAN | `prior_score_entropy` |
| Score variance / margin | IMPLEMENTED | `gate_features.py:104-181` |
| Ranking stability | PI (gate feature degenerate) | `evidence_only_stability_proxy` always 0.0 (§10); acquisition-side `expected_stability_gain` is real |
| Graph cyclicity / weighted cyclic mass | IMPLEMENTED (+ EC in repair-selector) | `failure_mining/graph_features.py`; `scc_cycle_burden` |
| Hodge cyclic energy | ABSENT | — |
| Prior–graph / prompt / provider disagreement | IMPLEMENTED / PI | contradiction rate; orientation consistency; cross-prior Kendall; multi-provider descriptive only |
| Embedding / RouteLLM routers | ABSENT | Cross-encoder is a reranker, not a router |
| Logistic regression | FIV + EC | `policy_calibration.py`; Outcome F |
| Gradient boosting | EC in `repair_selector_mining` only | Not in `policy_selection` |
| Random routing matched-rate | PI / degenerate | `random` mode with `rng_u=0` → always UHT; byte-identical to `always_uht` in Outcome F (`summary.json:234-249`) — **not** a valid matched-escalation control |
| P(UHT optimal) | FIV + EC | Actual learned-gate target; accuracy ≈ majority class |
| Regret prediction | FIV + EC | `policy_regret.py`; `regret_model_*.json` |
| Catastrophic-error prediction | INV | Tracked; risk-coverage empty/NaN in recorded run |
| Selective prediction / abstention / risk control | IMPLEMENTED; risk control not validated | `is_formal_guarantee=False`; selective abstain_rate 0.83, still loses to always-UHT |

### 6.9 Statistics and evaluation (I)

FIV: nDCG, MRR, recall, feedback-arc objective, cycle weight, top-k Jaccard, call count, token cost, latency, corrected utility, oracle regret, sign-flip permutation tests, bootstrap (percentile/basic/BCa/studentized), Holm + BH + BY corrections, standardized effect size, calibration curves, Brier, ECE, nested/leave-one-regime held-out splits, grouped/per-query pairing. IUAN: pairwise upset → `n_violations`; query-clustered bootstrap → per-query paired deltas. PI: MAP consumed as column, no `evaluation.py` function. ABSENT: Wilcoxon. **Independence:** no significance test treats provider/prompt/orientation/repeats as independent units; bootstrap collapses to one delta per `query_id` first. Caveat: `build_llm_bootstrap_summaries.py:86` last-wins if multiple rows share `(query_id, method)`, discarding rather than inflating. Multi-provider report correctly refuses significance claims at N=2.

---

## 11. Safeguard Cost and Small-Budget Findings

| Question | Finding |
|---|---|
| Where is the 12-cell production-UHT vs plain-UHT comparison? | **Nowhere except `REMEDIATION_REPORT.md:255`.** Grep for 0.225/0.208 and the (n=16, budget=8, seed=1) cell finds no CSV/JSON artifact. The comparison was an unsaved in-session measurement. |
| Can `gate_rows.json` reconstruct it? | **No.** The 12 `always_uht` rows have `n_calls=16`, `probe_calls=0`, `n_items∈{20,21}`, `seed∈{20,21}` — research-benchmark plain UHT with `enable_fallback=False`, not `run_production_uht`. |
| Do production tests cover the quality comparison? | **No.** `tests/test_production_operating_point.py` asserts execution/reservation (n∈{8,10}, budgets 8–20), never paired quality vs plain UHT. |
| Mechanistic cost | Floor reserves `ceil(0.15·budget)` (≥2 mandatory actions) (`production_config.py:76-90`); at budget 8 that is 2–3/8 calls (25–37%). Weak-evidence stop fires on essentially every synthetic query (coverage 0.0–0.08; `REMEDIATION_REPORT.md:257`). |
| Isolated vs pattern | Unknown — only one adverse cell reported, and the mean (+0.017 Jaccard) is from the same unsaved session. |

**Recommended description of production safeguards:** **diagnostically recommended but not yet empirically validated**, and **minimum-budget constrained**. Always-on as a *safety* mechanism (enforced + unit-tested), but not “always enabled with proven net quality benefit.” Do not change production behavior until a saved synthetic paired comparison at Outcome-F scale (and later a real-query check) exists.

---

## 12. Remaining Scientific Gaps

1. **No validated real-query criterion for when repair / robust routing helps** (C2/C11) — Outcome F is synthetic and predictor-negative; oracle gap still motivates the question.
2. **Matched multi-factor real-LLM factorial absent** (C4/C13) — components exist separately (§6.7).
3. **Production safety-floor net quality effect unquantified** (§11) — blocks strong “production OP helps” claims.
4. **Feature-schema defect** (§10) — blocks any honest retrain of experimental gates until `coverage_v2`.
5. **Degenerate `random` gate baseline** — not rate-matched; cannot support “beats random routing” claims.
6. **Hodge cyclic energy / personalized PageRank / Plackett–Luce / RankZephyr** still absent — low priority given C9/C10/C3 coverage.
7. **FiQA real OpenAI run incomplete** (10/20 queries); TREC DL not downloaded.
8. **Legacy JudgmentCache provenance hazard** still in production paths outside the new multi-provider store.
9. **Process gap:** entire post-JDIQ stack uncommitted (F-004).

---

## 13. Prioritized Next Work

### P0 — required before another strong scientific claim

| # | Task | Why existing work is insufficient | Reuse | Do not rerun | New data | Paid calls? | Pilot / stop | Deliverable |
|---|---|---|---|---|---|---|---|---|
| P0.1 | Commit/review-boundary pass for Outcome F + remediation | No reviewable diff; 1,163 untracked files | — | — | none | No | Scoped `git add` of library/tests/scripts; exclude bulky reports or LFS | Feature-branch commits with clean diff |
| P0.2 | Save a synthetic plain-UHT vs `run_production_uht` paired quality table | Claim exists only in prose | `production_runner`, `run_named_policy`, Outcome F grid shape | Frozen Outcome F `gate_rows` | write new report dir only | No | 12–48 synthetic cells incl. budget∈{8,16,24}; stop when mean Δ + worst-cell characterized with CIs | `reports/safeguard_cost_* /FINAL_REPORT.md` |
| P0.3 | Feature-schema versioning design (implement only if retrain planned) | `v1` vectors are historically constant | version guard already in `gate_features.py:29,90-94` | Do not mutate `v1` semantics | none | No | Spec `legacy_v1` vs `coverage_v2` + test list §10.7 | Design note; optional patch later |

### P1 — materially answers reviewers

| # | Task | Why insufficient now | Reuse | Do not rerun | New data | Paid? | Pilot → expand → stop | Deliverable |
|---|---|---|---|---|---|---|---|---|
| **P1.0 (SELECTED)** | Offline real-query repair/routing utility replay | C2/C11 lack real-query evidence; caches already hold oriented multi-provider + large SciDocs pairwise | `failure_mining_llm_v3` caches; SciDocs q50; multi-provider `judgment_records.jsonl`; greedy/exact/unrepaired extractors; `statistical_inference` | Do not regenerate OpenAI q50; do not re-smoke providers | none if caches suffice | **No** | Start SciDocs q50 unrepaired vs greedy vs exact nDCG + cycle metrics; add failure-mining oriented subsets; stop when multiplicity-corrected table exists or power is clearly inadequate | Decision table + negative/positive result report |
| P1.1 | Fill only missing cells of 30–40×2×2×orientation | Joint factorial absent | multi_provider stack; prefer Azure+Cohere | Do not redo Stage0 smokes; do not re-call legacy_v1 cells already in `judgment_records.jsonl` | new calls for uncovered (query,provider,prompt,orient) | Yes | Pilot 10 queries × 2 providers × 2 prompts × 2 orients ≈ 80 unordered-pair cells × C(k,2); expand only if offline P1.0 is promising but underpowered | Provenance store append + FINAL_REPORT |
| P1.2 | Manuscript alignment for C1/C3/C14 | Framing/citation gaps, not code gaps | Task 9 closure matrix | — | — | No | — | Response-to-reviewers draft |

### P2 — wait for P0/P1

- True online policy switching; matched-rate random routing control; Hodge cyclic-energy features; FiQA completion; TREC DL download; RankZephyr-style local models; USD pricing tables; CombMNZ productization (already DO_NOT_ADD).

---

## 14. Repository Maintenance Recommendation

| Need | Assessment |
|---|---|
| Commit / review-boundary pass | **Yes — urgent.** Branch has 0 unique commits; remediation is unreviewable (F-004). |
| Report cleanup | **Yes.** Superseded linear-extension `T15*`, policy `T025426Z`; label `AUDIT_LOCAL_BRANCH.md` historical. |
| Generated-artifact cleanup | **Yes.** Root `IMG_*.png` / UUID PNGs; consider not tracking bulky `reports/` binaries. |
| Duplicate-script consolidation | **Useful later** (`run_openai_real_*.py`, `_ndcg_at_k` copies) — not blocking science. |
| Feature-schema versioning | **Yes before any gate retrain** (§10). |
| Configuration centralization | **Yes** for 0.15 / probe=3 / α-semantics docs. |
| Documentation reconciliation | **Yes** — stale listwise-unimplemented note; AUDIT vs REMEDIATION contradiction. |
| Provenance manifests | **Partial** — new multi-provider store is good; legacy caches remain hazardous. |
| Test organization | Adequate (781 passing); add safeguard-cost regression once P0.2 exists. |
| Archive structure | **Yes** — `reports/archive/superseded/` for early linear-extension + Outcome A quick run. |

**Next Cursor task type:** **commit/review preparation** (scoped, no science), immediately followed by the scientific P1.0 offline replay. A further read-only audit is unnecessary for the same reviewer list. Controlled cleanup can share the commit pass. Documentation/manuscript alignment is P1.2 after P1.0 numbers exist.

---

## 15. Selected Next Task

**Title:** Offline real-query repair-and-routing utility replay on existing caches (zero new API calls).

**Precise implementation objective (do not implement in this audit):**

1. Build a read-only evaluation harness that, for each eligible cached query:
   - reconstructs the preference graph from stored judgments (SciDocs OpenAI q50 pairwise; failure-mining azure/cohere oriented judgments; multi-provider provenance records where pair coverage is complete);
   - produces rankings under **unrepaired**, **greedy repair**, and **exact SCIP repair** with at least Copeland and weighted-balance extractors (already in `baseline_ranking.py` / `mwfas_solver.py`);
   - where acquisition traces exist or can be simulated from the same judgment pool, scores **plain UHT vs challenger/robust** utilities without calling providers;
   - evaluates nDCG@k / top-k Jaccard / FAS weight / cycle count with **query-clustered** sign-flip or bootstrap tests (`statistical_inference.py`), never treating orientation or provider as independent units.
2. Emit a per-query decision table and a multiplicity-corrected summary answering: *On real cached judgments, when (if ever) does repair help retrieval, and when does a non-UHT policy beat always-UHT on corrected utility?*
3. Write results to a **new** timestamped `reports/` directory; do not modify `reports/policy_selection_20260726T030500Z/` or any legacy cache.
4. If and only if power is inadequate **and** specific (query,provider,prompt,orientation) cells are missing, draft a minimal P1.1 call plan that reuses Stage0-smoked Azure+Cohere models and skips already-cached keys.

**Why this maximizes reviewer coverage per unit cost:** it jointly advances C2, C4, C11, and C13 using data already paid for; it does not re-implement C5–C10 baselines; it does not treat Outcome F’s failed synthetic gate as proof that selection is impossible; it preserves historical Outcome F artifacts; paid calls are not required.

**Out of scope for this task:** mutating `policy_gate_features_v1`, changing production defaults, implementing HodgeRank/RankZephyr, regenerating Outcome F, or committing (that is P0.1, a separate Cursor task).

---

*End of audit. Only this file was created; no source, tests, or experiment artifacts were modified.*

