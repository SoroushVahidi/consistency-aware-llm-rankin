# Safe Claims for Manuscript Submission

> **Purpose:** Enumerates every claim that is directly supported by committed
> experimental artifacts. Use this document as a checklist before submitting
> or revising the manuscript.
>
> **Grounding rule:** A claim appears here only if it can be traced to a
> committed CSV, JSON, or summary file in this repository. All results are
> labeled with their evidence type using the four-tier system:
> `real completed run` | `pilot run` | `dry-run validation` | `pending`.
>
> The final section — **Do Not Claim** — lists statements that are explicitly
> prohibited because they are unsupported, misleading, or circular.

---

## Part A — Safe Claims (supported by real evidence)

---

### Claim S1 — Vote construction is the dominant factor controlling graph cyclicity

**Statement:**  
The choice of vote-aggregation strategy determines cycle prevalence more
strongly than any downstream repair algorithm. Majority-filtered aggregation
(ms2: min_support=2, margin ≥ 0.1) yields near-acyclic graphs on SciDocs
(0% cyclic queries). Per-ranker inclusion (ms1: min_support=1) yields high
cyclicity (SciDocs: 87.5% cyclic, avg largest SCC 9.3). A post-filter that
drops mutual 2-cycles (ms1_drop_mutual) restores near-acyclicity while
retaining more edges than ms2.

**Evidence type:** real completed run  
**Artifact:** `reports/jis_final_tables/T01_main_real_vote_graph_ndcg_structural_metrics.csv`  
**Key values (SciDocs):**

| Variant | % cyclic | Avg largest SCC | Avg edges |
|---------|----------|-----------------|-----------|
| ms2 | 0.0% | 1.0 | 46.6 |
| ms1 | 87.5% | 9.3 | 195.4 |
| ms1_drop_mutual | 0.0% | 1.0 | 178.2 |

---

### Claim S2 — FAS repair measurably reduces structural inconsistency

**Statement:**  
Greedy MWFAS repair reduces backward-edge weight (BEW) and pairwise
inconsistency count (PIC) relative to a qrels-derived reference ranking
under high-cyclicity vote construction (ms1). The effect is negligible under
near-acyclic constructions (ms2, ms1_drop_mutual).

**Evidence type:** real completed run  
**Artifact:** `reports/jis_final_tables/T01_main_real_vote_graph_ndcg_structural_metrics.csv`  
**Key values:**

| Dataset | Variant | BEW pre | BEW post | ΔBEW | PIC pre | PIC post | ΔPIC |
|---------|---------|---------|---------|------|---------|---------|------|
| SciDocs | ms1 | 294.22 | 293.88 | 0.33 | 94.18 | 89.93 | 4.25 |
| FiQA | ms1 | 224.81 | 224.34 | 0.47 | 99.36 | 93.14 | 6.22 |
| HotpotQA | ms1 | 91.82 | 91.78 | 0.03 | 18.85 | 18.35 | 0.50 |
| BRIGHT | ms1 | 882.69 | 882.45 | 0.23 | 55.56 | 52.80 | 2.76 |

---

### Claim S3 — FAS repair does not uniformly improve retrieval quality (nDCG@k)

**Statement:**  
Under ms1 vote construction on SciDocs, the repaired Copeland hybrid shows
mean per-query ΔnDCG = −0.0001 (95% CI [−0.0008, +0.0006], 2000 bootstrap
replications, n=120 queries). The CI includes zero; the effect is inactive.
Under ms2 and ms1_drop_mutual, ΔnDCG = 0 exactly (no cycles to repair).
Under HotpotQA ms1, the effect is weakly positive: ΔnDCG = +0.017
(95% CI [0.000, +0.041]).

**Evidence type:** real completed run  
**Artifact:** `reports/jis_final_tables/T02_main_real_bootstrap_delta_ndcg_pairs.csv`

---

### Claim S4 — Harm from repair concentrates in high-SCC queries

**Statement:**  
On SciDocs ms1, queries with largest SCC ≥ median show more negative mean
ΔnDCG (copeland_scc_high: −0.00048, CI [−0.0016, +0.0006], n=64) compared
to low-SCC queries (copeland_scc_low: +0.00028, CI [−0.0004, +0.0014], n=56).

**Evidence type:** real completed run  
**Artifact:** `reports/jis_final_tables/T02_main_real_bootstrap_delta_ndcg_pairs.csv`  
**Caveat:** Difference between scc_high and scc_low CIs overlaps; this is a
directional observation, not a statistically significant split.

---

### Claim S5 — Balance hybrid is retrieval-neutral to repair

**Statement:**  
Repaired vs unrepaired balance hybrid shows ΔnDCG = 0 under all vote
constructions and all four datasets. CI is [0, 0] throughout.

**Evidence type:** real completed run  
**Artifact:** `reports/jis_final_tables/T02_main_real_bootstrap_delta_ndcg_pairs.csv`

---

### Claim S6 — Cross-encoder provides a strong text-aware external reference

**Statement:**  
A pre-trained cross-encoder (ms-marco-MiniLM-L-6-v2) achieves nDCG@k of
0.8977 (SciDocs, top-20), 0.9499 (HotpotQA, top-10), and 0.8877 (BRIGHT,
top-20) when ranking the same candidate pools from document text alone.

**Evidence type:** real completed run  
**Artifact:** `outputs/final_modern_baselines/{dataset}/summary.csv`

---

### Claim S7 — Tournament aggregation with qrels preferences reaches nDCG = 1.0

**Statement:**  
Bradley–Terry MLE, win-rate, and Markov-chain aggregation all recover
nDCG = 1.0 on SciDocs, HotpotQA, and BRIGHT when given exact qrels-derived
pairwise preferences. Tournament sort achieves 0.81 / 1.00 / 0.70 on the
same datasets.

**Evidence type:** real completed run  
**Artifact:** `outputs/final_modern_baselines/{dataset}/summary.csv`  
**Caveat:** nDCG = 1.0 results follow trivially from perfect preferences;
they illustrate preference-quality ceiling, not aggregation superiority.

---

### Claim S8 — FAS repair outperforms parametric aggregation under preference noise

**Statement:**  
Under 15% synthetic noise flip probability, FAS-balance significantly
outperforms Bradley–Terry on two datasets:

| Comparison | Dataset | Δ nDCG | 95% CI |
|------------|---------|--------|--------|
| FAS-balance vs BT MLE | SciDocs | +0.049 | [+0.044, +0.054] |
| FAS-balance vs BT MLE | HotpotQA | +0.264 | [+0.246, +0.282] |

**Evidence type:** real completed run (2000 bootstrap replications)  
**Artifact:** `outputs/bootstrap_modern/` and `outputs/noise_sensitivity/`

---

### Claim S9 — Score-sum and Borda are most noise-robust

**Statement:**  
Score-sum and Borda maintain nDCG = 1.0 at 30% noise on SciDocs. Borda
achieves Kendall τ = 0.756 (mean, 5 seeds) at 20% noise in synthetic
experiments (n=20, margin weights).

**Evidence type:** real completed run (noise sensitivity) + real completed run (synthetic)  
**Artifacts:**  
- `outputs/noise_sensitivity/` summary CSVs  
- `reports/jis_final_tables/A01_appendix_synthetic_multiseed_stability.csv`

---

### Claim S10 — Synthetic rankings are stable across seeds at moderate noise

**Statement:**  
Borda achieves Kendall τ mean = 0.756 (std = 0.035) across 5 seeds at
n=20, noise = 0.20, margin weights. Score-sum achieves mean = 0.688
(std = 0.061). Greedy-FAS-topological achieves mean = 0.282 (std = 0.103),
confirming that topological extraction alone is least stable.

**Evidence type:** real completed run (5 seeds × 3 methods)  
**Artifact:** `reports/jis_final_tables/A01_appendix_synthetic_multiseed_stability.csv`

---

### Claim S11 — FAS repair effect on nDCG depends on vote construction regime

**Statement:**  
FAS repair is inert (ΔnDCG = 0) under near-acyclic constructions across all
four datasets. Under high-cyclicity construction (ms1) the effect ranges
from weakly positive (HotpotQA: CI includes +0.04) to neutral (FiQA, BRIGHT)
to trivially negative with CI near zero (SciDocs). No configuration shows a
strongly positive and statistically significant retrieval benefit.

**Evidence type:** real completed run  
**Artifact:** `reports/jis_final_tables/T01_main_real_vote_graph_ndcg_structural_metrics.csv`
and `T02_main_real_bootstrap_delta_ndcg_pairs.csv`

---

## Part B — Do Not Claim

The following statements must NOT appear in the manuscript because they are
either (a) unsupported by committed evidence, (b) circular / misleading,
or (c) contradicted by actual results.

---

### DN1 — "FAS repair reliably improves retrieval quality"

**Reason:** Bootstrap evidence shows the effect is neutral or weakly negative
across most configurations. No configuration shows a robustly positive result
with CI strictly above zero.

---

### DN2 — "Our method outperforms Borda / score-sum"

**Reason:** On real data, score-sum achieves nDCG = 1.0 under clean
preferences; FAS-based methods do not exceed this. On synthetic data,
score-sum and Borda consistently outperform greedy-FAS-topological.

---

### DN3 — "BEW / PIC improvement implies retrieval improvement"

**Reason:** BEW and PIC are measured against a qrels-derived reference
ranking, not an independent ground truth. Reducing BEW means the repaired
graph is structurally closer to the qrels ordering, but this does not
guarantee improved nDCG because nDCG is itself computed from those same
qrels. The two measures are not independent.

---

### DN4 — "Results generalise to LLM-generated preferences"

**Reason:** All real-data experiments use BM25 / TF-IDF / MiniLM-score-derived
pairwise votes. No experiment uses LLM-generated pairwise preferences. The
LLM reranking modules (`src/rerankers/llm_*.py`) are implemented but have
not been executed (no API key).

---

### DN5 — "Results generalise to more than four datasets"

**Reason:** Only SciDocs, FiQA, HotpotQA, and BRIGHT are evaluated. FiQA
results are partially excluded (grade-1 qrels only). No other domain or
collection has been tested.

---

### DN6 — "We reproduce / outperform RankGPT / PRP / specific named paper"

**Reason:** LLM listwise and pairwise modules are implemented but not run.
No result from those modules exists in this repository. Do not compare to
or claim parity with specific published LLM-reranking systems.

---

### DN7 — "The ILP MWFAS solver provides better results on real data"

**Reason:** The ILP backend is not functional (requires Gurobi). Exact vs
greedy comparison exists only on synthetic data (n ≤ 10). No real-data
ILP result is committed.

---

### DN8 — "α = 0.3 is an optimised hyperparameter"

**Reason:** The α sweep is conducted only on synthetic data. No validation-set
tuning or cross-validation on real data is documented.

---

### DN9 — "The method is efficient for production / large-scale use"

**Reason:** Only n ≤ 100 items per query tested in synthetic experiments.
Real-data experiments run on 20–500 queries with small candidate sets.
No analysis of batch throughput, latency at scale, or memory requirements
for production-sized corpora.

---

### DN10 — "LLM-pointwise / pairwise / listwise baselines confirm our advantage"

**Reason:** These baselines are not yet run. Any comparison to them is
speculative. They must be labeled explicitly as `pending` in any discussion.

---

## Part C — Conditional Claims (claims that are safe only with qualifiers)

---

### CC1 — "Repair can harm nDCG under specific conditions"

**Safe version:** "Under high-cyclicity ms1 vote construction on SciDocs,
repaired Copeland hybrid shows ΔnDCG = −0.0001 (CI [−0.0008, +0.0006]);
the harm signal is present in the point estimate but the CI includes zero."  
**Unsafe version (do not use):** "Repair consistently harms nDCG" — this
overgeneralises. The earlier version of the repository reported a more negative
value from a pilot run that was subsequently corrected.

---

### CC2 — "FAS-balance is superior under preference noise"

**Safe version:** "Under 15% preference noise, FAS-balance outperforms
Bradley–Terry MLE with 95% CI strictly positive on SciDocs and HotpotQA."  
**Qualifier required:** This comparison uses synthetic noise injected into
qrels-derived preferences, not naturally occurring LLM preference noise.

---

### CC3 — "Vote construction controls cyclicity"

**Safe version:** "ms2 aggregation produces near-acyclic graphs on all four
datasets; ms1 aggregation produces graphs with 52–95% cyclic queries across
four datasets."  
**Qualifier required:** This finding is specific to the three-ranker ensemble
(BM25, TF-IDF, MiniLM-L6) used here. Different ranker compositions may yield
different cycle rates.
