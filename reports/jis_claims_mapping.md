# JIS claim-to-evidence mapping (canonical: `outputs/final_jis_package` / `pub_vote_cmp_all4`)

**Evidence root:** `outputs/pub_vote_cmp_all4/paper_package/tables/*.csv` (mirrored under `outputs/final_jis_package/tables/`).  
**Claim strength legend:** **primary** = suitable for core narrative if framed carefully; **secondary** = supporting or contextual; **cautionary** = cite only with explicit limits, mixed CIs, or protocol sensitivity.

Unless stated otherwise, **do not** cite `outputs/pub_vote_cmp_v2` or `outputs/q1_journal_package` for the same numerical sentence—their **SciDocs / HotpotQA** rows **conflict** with all4 (see `reports/repo_publication_audit.md`).

---

## 1. Supported primary claims

| Claim ID | Exact claim statement | Strength | Evidence source file(s) | Table/Figure | Dataset(s) | Effect direction | Significance evidence | Notes / limitations |
|----------|----------------------|----------|-------------------------|--------------|------------|------------------|----------------------|---------------------|
| P1 | Vote construction (`ms2` vs `ms1` vs `ms1_drop_mutual`) strongly controls whether preference graphs are cyclic and how large strongly connected components are, under the publication vote-suite protocol. | primary | `table_graph_ndcg_and_consistency.csv` | Fig. `fig_cyclicity_and_scc.png` (package) | SciDocs, FiQA, HotpotQA, BRIGHT | N/A (structural prevalence) | N/A (descriptive aggregates) | Magnitudes differ from v2 on overlapping cells; cite all4 only for the four-dataset paper. |
| P2 | Under `ms2` and `ms1_drop_mutual`, greedy FAS repair removes **negligible** edge weight and leaves bootstrap mean ΔnDCG at **0** with **degenerate CI [0,0]** for Copeland and balance pairs tabulated—i.e., repair is **inactive** for retrieval deltas in those regimes. | primary | `table_bootstrap_delta_ndcg.csv`; `table_graph_ndcg_and_consistency.csv` (`mean_fas_weight_removed`) | `fig_delta_ndcg_bootstrap.png` | All four datasets (per table rows) | neutral (Δ≈0) | CIs reported as point mass at zero where applicable | “Inactive” is **operational** (bootstrap on committed per-query pipeline), not a proof of bitwise identical lists for every query. |
| P3 | Under `ms1`, where cycles are prevalent for most datasets, FAS removes **positive** mean weight and reduces **mean BEW** and **mean PIC** (qrels-aligned) relative to pre-repair for several dataset rows—i.e., repair **does** change measured graph–reference inconsistency. | primary | `table_consistency_qrels_bew.csv`; `table_graph_ndcg_and_consistency.csv` (delta columns) | `fig_graph_qrels_bew_pre_post.png` | SciDocs, FiQA, HotpotQA, BRIGHT (see per-row `n_queries`) | positive for structural reduction where Δ>0 | N/A for structure (not bootstrap); see retrieval rows separately | BEW/PIC use the **same qrels** as nDCG; not an independent external validity metric. |
| P4 | The **direction and magnitude** of mean bootstrap ΔnDCG (repaired − unrepaired Copeland) **depend on dataset** under `ms1` (e.g., SciDocs near-zero negative with straddling CI; FiQA positive mean with straddling CI; HotpotQA positive mean with CI bounded below at 0.0 in CSV; BRIGHT tiny mean near zero with straddling CI). | primary | `table_bootstrap_delta_ndcg.csv` | `fig_delta_ndcg_bootstrap.png`, `fig_ndcg_copeland_ms1_four_datasets.png` | Four datasets | **mixed** | See per-row `ci95_low`, `ci95_high` | Central **heterogeneity / regime** claim; avoid universal “harm” or “help.” |
| P5 | For **balance** hybrid pairs in the committed bootstrap table, mean ΔnDCG is **0** with **CI [0,0]** for all listed dataset×variant rows—balance repair is **retrieval-neutral** under this hybrid definition. | primary | `table_bootstrap_delta_ndcg.csv` | — | All listed rows | neutral | Intervals degenerate at zero | Extremely small effects may be masked by rounding/reporting; still conservative for “no meaningful gain.” |

---

## 2. Weaker contextual observations (secondary)

| Claim ID | Exact claim statement | Strength | Evidence source file(s) | Table/Figure | Dataset(s) | Effect direction | Significance evidence | Notes / limitations |
|----------|----------------------|----------|-------------------------|--------------|------------|------------------|----------------------|---------------------|
| S1 | Mean nDCG for unrepaired vs repaired Copeland hybrids can be **visually compared** across datasets for `ms1` using aggregate means. | secondary | `table_graph_ndcg_and_consistency.csv` | `fig_mean_ndcg_hybrids.png`, `fig_ndcg_copeland_ms1_four_datasets.png` | Four datasets | mixed | N/A | Descriptive; inferential step requires bootstrap file (S2/P4). |
| S2 | SCC-stratified bootstrap rows (`copeland_scc_high` / `copeland_scc_low`) exist where `n_queries > 0`; means can differ **without** strict “significant harm” language on SciDocs in all4. | secondary | `table_bootstrap_delta_ndcg.csv` | — | Per-row | mixed | Several CIs **straddle** zero | Median split is **post-hoc**; weaker in all4 than in v2 narrative—see `reports/claim_support_matrix.csv` C8. |
| S3 | Synthetic multiseed and noise-sweep tables support **internal** claims about **synthetic** ranking behavior (Kendall τ, baselines vs greedy FAS), **not** the real-data vote-graph headline. | secondary | `reports/jis_final_tables/A01_appendix_synthetic_multiseed_stability.csv`, `A02_appendix_synthetic_noise_sweep.csv` | — | Synthetic | varies | As per those tables | **Do not** elide synthetic and real-data claims. |

---

## 3. Cautionary claims (use only with heavy qualification)

| Claim ID | Exact claim statement | Strength | Evidence source file(s) | Table/Figure | Dataset(s) | Effect direction | Significance evidence | Notes / limitations |
|----------|----------------------|----------|-------------------------|--------------|------------|------------------|----------------------|---------------------|
| C1 | “FAS repair **significantly harms** Copeland nDCG on SciDocs under `ms1`.” | cautionary | **Not supported** by all4 `table_bootstrap_delta_ndcg.csv` row `scidocs,ms1,copeland` (CI straddles zero). **Supported** only if the manuscript **explicitly** adopts **v2** (`outputs/pub_vote_cmp_v2/...`) as a **separate archived run**. | v2: `table_bootstrap_delta_ndcg.csv`; all4: same filename under `pub_vote_cmp_all4` | SciDocs | negative point estimate in all4 but **not** significant at 95% in committed CI | **Mixed across packages** | **Pick one package**; all4 is canonical here. |
| C2 | “Repair **improves** HotpotQA Copeland nDCG under `ms1`.” | cautionary | `table_bootstrap_delta_ndcg.csv` | — | HotpotQA | positive mean | CI in committed CSV: `ci95_low=0.0`, `ci95_high≈0.0405` | Lower bound **on mean Δ** is exactly zero in file—avoid “strictly significant gain” wording without re-deriving p-values. |
| C3 | “FiQA shows **clear retrieval benefit** from repair under `ms1`.” | cautionary | `table_bootstrap_delta_ndcg.csv` | — | FiQA | positive mean, CI **straddles** | Not significant in two-sided bootstrap CI sense | Report as **inconclusive** or **exploratory**. |

---

## 4. Claims we should **not** make (unsupported or contradicted)

| Claim ID | Statement | Why unsafe |
|----------|-----------|------------|
| N1 | “Cycle repair **universally improves** retrieval quality / nDCG.” | Contradicted by inactive rows + heterogeneous `ms1` Copeland effects; see `table_bootstrap_delta_ndcg.csv`. |
| N2 | “Lower BEW/PIC **implies** better nDCG.” | Same regime can show structural reduction **without** retrieval gain (and mixed ΔnDCG); see P3 vs P4. |
| N3 | “We evaluate **LLM pairwise** preferences.” | Publication suite uses **score-derived votes** (BM25 / TF-IDF / MiniLM-style signals in pipeline docs)—no committed LLM-judge pairwise suite for this bundle. |
| N4 | “Exact **ILP MWFAS** beats greedy on real data.” | Solver stub / not evidenced for BEIR runs (`docs/Q1_CLAIM_EVIDENCE_MAP.md`). |
| N5 | “Results **generalize** broadly across **all** BEIR benchmarks.” | Four datasets here; FiQA/BRIGHT rows must be reported **as observed**, not extrapolated. |
| N6 | “We are **state of the art** on retrieval.” | No head-to-head SOTA leaderboard claim is evidenced in this package. |
| N7 | Blended sentences mixing **v2** significance with **all4** descriptive prose **without** naming two runs. | **Numerical contradiction** on SciDocs ms1 Copeland bootstrap (audit files). |

---

## Unsafe or unsupported claims to avoid in the JIS manuscript

- **Universal improvement** from structural repair or from any single vote rule.
- **LLM-centric framing** unless the manuscript **limits** claims to score-derived proxies or adds **new** LLM-pairwise experiments (not in this repo state).
- **“Statistically significant harm” on SciDocs `ms1` Copeland** while citing **`outputs/pub_vote_cmp_all4`**—the committed bootstrap CI **does not** lie strictly below zero.
- **Silent merger** of `q1_journal_package` / `reports/paper_tables/table_01_repair_effects.csv` with all4 tables.
- **Novelty superlatives** (“first”, “unique”, “SOTA”) not tied to a specific, citable comparison in this repository.
- **Production readiness** (latency, SLA, scaling) beyond committed synthetic timing tables—not evidenced for the hybrid vote pipeline at web scale.

---

*Cross-references: `docs/jis_paper_scope.md`, `reports/jis_editorial_summary.md`, `reports/claim_support_matrix.csv`, `reports/repo_publication_audit.md`.*
