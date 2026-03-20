# Literature Alignment: Critical Review for Q1 Submission

This document provides a strict, reviewer-level alignment between our method and prior work. It identifies overclaims, clarifies novelty, and positions the contribution precisely.

---

## 1. What Algorithm Are We Actually Using for FAS?

### 1.1 Our Algorithm

We use a **greedy cycle-removal heuristic**:

1. Find *any* cycle (via `nx.find_cycle`)
2. Remove the minimum-weight edge in that cycle
3. Repeat until acyclic
4. Topological sort on the resulting DAG

**Key properties:**
- The cycle chosen at each step is **arbitrary** (whatever NetworkX returns first)
- The order of cycle removal affects the final FAS and ranking
- **No approximation guarantee**; no known bound on solution quality
- Complexity: O(C · (n + e)) where C = number of cycles removed (at most e)

### 1.2 Relation to Known Heuristics

| Heuristic | What it does | Relation to ours |
|-----------|--------------|------------------|
| **Eades-Lin-Smyth (1993)** | O(m) vertex linear-ordering heuristic; computes FAS from vertex ordering | **Different.** We do cycle-based removal; Eades-Lin-Smyth does not iterate over cycles. |
| **Demetrescu-Finocchi (DF03)** | Local-ratio combinatorial algorithm; approximation ratio bounded by longest cycle length | **Different.** DF03 uses a local-ratio technique; we use naive "min-edge-per-cycle" removal. |
| **Berger-Shor** | O(mn) algorithm with better bounds | **Different.** More sophisticated. |
| **Our heuristic** | "Remove min-weight edge from some cycle" | A **folklore** or **textbook** greedy; no citation of a specific source. It is a natural but weak heuristic. |

**Conclusion:** Our FAS algorithm is a simple greedy heuristic with **no known approximation guarantee** and **no relation to DF03 or Eades-Lin-Smyth**. We should not claim algorithmic novelty for the FAS solver. We should cite standard FAS references (e.g., Garey & Johnson for NP-hardness; Wikipedia or survey for the problem) and describe our heuristic as a "simple greedy cycle-removal heuristic."

---

## 2. Comparison to Known Ranking Objectives

### 2.1 Minimizing BEW

**BEW(π, G) =** sum of weights of edges (u,v) where v is ranked above u in π.

**Minimizing BEW over π** is equivalent to: find a ranking π that minimizes the total weight of violated preferences. The set of backward edges for any ranking π forms a feedback arc set. So:

**Minimizing BEW ≡ Minimum Weighted Feedback Arc Set (MWFAS)**

The ranking that minimizes BEW is a topological order of G' where G' = G minus a minimum-weight FAS.

### 2.2 Relation to Kemeny Optimal Aggregation

**Kemeny:** Minimize sum of Kendall tau distances to input rankings.

**Equivalence:** For a graph built from **majority vote** (weight = number of rankings preferring u over v), minimizing BEW is **equivalent** to Kemeny optimal aggregation. (Each violated preference contributes its weight; Kemeny counts violations with weight 1 per ranking.)

**Our setting:** We use **summed_margin** (weight = sum of score differences across scorers). So we are **not** solving Kemeny. We are solving a **weighted rank aggregation** problem with a specific weight scheme. The closest formulation is:

- **Weighted Kemeny** or **weighted rank aggregation** with margin-based weights
- **MWFAS** on a graph with summed-margin edge weights

**Conclusion:** Our objective is MWFAS / weighted rank aggregation. We should not claim equivalence to Kemeny unless we use majority-vote weights. With summed_margin, we are in a well-known family of objectives (weighted feedback arc set for ranking).

### 2.3 Closest Known Formulation

**Minimum Weighted Feedback Arc Set for Ranking:** Given a directed graph with edge weights, find a ranking (linear order) that minimizes the sum of weights of edges pointing backward. This is exactly our BEW minimization. It is a standard formulation; see, e.g., Ailon et al. (2008) on aggregating inconsistent information, and the recent arxiv 2412.16181 (Vahidi & Koutis, 2024) on MWFAS for ranking from pairwise comparisons.

---

## 3. Novelty: What Is NEW?

### 3.1 FAS Literature

**Novelty: NONE.** We use a trivial greedy heuristic. We do not contribute a new FAS algorithm or approximation.

### 3.2 Rank Aggregation Literature

**Novelty: LIMITED.** The objective (minimize BEW = MWFAS) is standard. Our weight scheme (summed_margin) is a reasonable choice but not novel. The application to multi-scorer retrieval (BM25 + dense + cross-encoder) is a natural use case, not a methodological contribution.

### 3.3 Learning-to-Rank / Fusion Methods

**Novelty: SELECTIVE REPAIR.** The **only** clear novelty is:

**Selective application of FAS (or graph-consistent ordering) based on an inconsistency signal (BEW or disagreement).**

Prior work typically applies a single fusion method (RRF, Borda, Kemeny, FAS) to all queries. We propose: *apply FAS only when BEW (or disagreement) is high; otherwise keep RRF.* This is a **conditional** or **selective** fusion policy. We are not aware of prior work that explicitly proposes this for rank aggregation in retrieval.

**Caveats:**
- Thresholding on a scalar signal (BEW, disagreement) is simple; the idea of "apply method A when signal X is high, else method B" is a common pattern (e.g., confidence-based routing, gating).
- We do not prove that BEW is the optimal signal; we show empirically that it works.
- The contribution is **empirical and conceptual**, not theoretical.

### 3.4 Summary: Strict Novelty Statement

**We contribute:** A selective repair policy—apply FAS (or graph-consistent ordering) only when BEW or disagreement exceeds a threshold—that empirically improves over both always-FAS and never-FAS on FiQA, SciDocs, and HotpotQA. We do **not** contribute a new FAS algorithm, a new rank aggregation objective, or a theoretical guarantee.

---

## 4. Position of Selective Repair

### 4.1 Is It Equivalent to…?

| Concept | Equivalent? | Explanation |
|---------|-------------|-------------|
| **Thresholding on disagreement** | Partially | We use BEW or disagreement as the threshold signal. BEW and disagreement are correlated but not identical. We could have used disagreement alone; BEW adds a graph-specific signal. |
| **Mixture-of-experts over rankers** | No | We do not blend RRF and FAS. We choose one or the other per query. |
| **Meta-ranking** | Loosely | We are choosing between two rankers (RRF vs FAS) based on a signal. This is a form of gating or switching, not learning a meta-model. |
| **Confidence-based routing** | Similar | "Use FAS when inconsistency is high" is analogous to "use expert A when confidence in B is low." The framing is related. |

### 4.2 New Perspective?

**Yes, in the following limited sense:** Prior rank aggregation work typically applies one method globally. We show that **conditioning on inconsistency** (BEW, disagreement) improves over both always-FAS and never-FAS. The idea of "repair only when needed" is intuitive but had not, to our knowledge, been applied explicitly to FAS-based rank aggregation in retrieval. We provide empirical support across three datasets and two graph regimes (cyclic and acyclic).

---

## 5. Closest 3–5 Papers

### 5.1 Cormack, Clarke, Büttcher (SIGIR 2009): Reciprocal Rank Fusion

**What they do:** Propose RRF for combining rankings from multiple IR systems. RRF score(d) = Σ 1/(k + rank(d)). No score normalization; robust to outliers.

**How we differ:** We use RRF as the base fusion. We add a **selective** step: replace RRF with FAS output when BEW is high. We do not modify RRF itself.

**Weaker/stronger:** We build on RRF; we do not outperform RRF in all settings. We outperform RRF only when selectively applying FAS on high-conflict queries.

### 5.2 Vahidi & Koutis (arXiv 2412.16181, 2024): MWFAS for Ranking from Pairwise Comparisons

**What they do:** Connect ranking from pairwise comparisons to MWFAS. Show that combinatorial MWFAS algorithms outperform learning-based approaches (He et al., ICML 2022) on ranking benchmarks.

**How we differ:** They focus on the MWFAS objective and algorithms. We focus on **selective** application: when to use FAS vs RRF. We use a weaker greedy heuristic; they may use stronger solvers. Our contribution is the selective policy, not the FAS algorithm.

**Weaker/stronger:** They may have stronger FAS solvers. Our novelty is selective repair, not FAS itself. If this paper is by the same author (Vahidi), we must clearly differentiate and avoid self-citation that overstates novelty: they do MWFAS algorithms; we do *selective* application of FAS + RRF.

### 5.3 Ailon, Charikar, Newman (STOC 2005 / JACM 2008): Aggregating Inconsistent Information

**What they do:** Study rank aggregation and clustering under inconsistency. Show connections to feedback arc set, Kemeny, and approximation algorithms.

**How we differ:** They provide theoretical foundations. We apply FAS heuristics to retrieval and add selective repair. We do not contribute to the theory.

**Weaker/stronger:** They are stronger theoretically. We are an applied, empirical contribution.

### 5.4 Dwork et al. (rank aggregation), Schalekamp & van Zuylen (FAS approximations)

**What they do:** Rank aggregation theory; approximation algorithms for FAS.

**How we differ:** We use a simple heuristic and focus on **when** to apply FAS, not **how** to solve FAS optimally.

### 5.5 He et al. (ICML 2022) or similar: Learning to Rank from Pairwise Comparisons

**What they do:** Learning-based ranking from pairwise comparisons.

**How we differ:** We are learning-free. We use combinatorial FAS + RRF. Our contribution is selective application, not learning.

---

## 6. Suggested Related Work Paragraph (Publication-Ready)

> Rank aggregation combines multiple rankings into one. Classical methods include Borda count, Kemeny optimal aggregation (which minimizes the sum of Kendall tau distances to input rankings), and Reciprocal Rank Fusion (RRF) (Cormack et al., 2009), which avoids score normalization by using rank-based fusion. The minimum weighted feedback arc set (MWFAS) problem is equivalent to finding a ranking that minimizes the total weight of violated pairwise preferences (Ailon et al., 2008; Vahidi & Koutis, 2024). Solving MWFAS yields a topological ordering of the graph after removing a minimum-weight set of cycle-breaking edges. We use a simple greedy heuristic that iteratively removes the minimum-weight edge from an arbitrary cycle until the graph is acyclic, then apply topological sort. This heuristic has no known approximation guarantee and is distinct from the Eades-Lin-Smyth (1993) and Demetrescu-Finocchi (2003) algorithms. Our contribution is not a new FAS algorithm but a **selective repair policy**: we apply FAS (or graph-consistent ordering) only when the base ranking (RRF) has high backward edge weight (BEW) or scorer disagreement, and keep RRF otherwise. To our knowledge, prior work has not proposed conditioning FAS application on an inconsistency signal for multi-scorer retrieval. We show empirically that this policy improves over both always-FAS and never-FAS on FiQA, SciDocs, and HotpotQA.

---

## 7. Flagged Overclaims

### 7.1 Current Wording That May Overclaim

| Claim | Issue | Correction |
|-------|-------|------------|
| "FAS repair" | Implies we have a sophisticated repair method | Say "FAS-based ranking" or "greedy FAS heuristic + topological sort" |
| "Minimum-weight feedback-arc-set" | Implies we find the minimum | We use a heuristic; we do not guarantee minimum. Say "greedy feedback arc set heuristic" |
| "BEW measures cycle-based inconsistency" | On HotpotQA, graphs are acyclic; BEW measures ranking violation, not cycles | Already corrected in audit; keep distinction |
| "Conflict-aware selective repair" | "Conflict-aware" is fine; avoid implying we invented FAS or BEW | Clarify that BEW and FAS are standard; our contribution is the selective policy |
| "Up to 6.5% NDCG@10" | Modest gain; ensure we do not oversell | Keep; it is accurate. Do not claim "substantial" or "significant" without statistical testing |
| "Diagnostic + repair layer" | "Repair" may imply we fix cycles; on HotpotQA we do not | Use "graph-consistent reordering" for acyclic case |
| "Novel" or "first" | Do not use unless we have done a thorough literature search | Use "to our knowledge" and "we are not aware of prior work" |

### 7.2 Implied But Not Strictly Correct

1. **We solve MWFAS:** We approximate it with a greedy heuristic. We do not solve it exactly.
2. **BEW is our invention:** BEW is the standard "backward edge weight" or "violation cost" in FAS/ranking literature. We use the standard definition.
3. **Selective repair is theoretically justified:** We have an intuitive argument (high BEW → replace; low BEW → keep). We do not have a formal theorem that this policy is optimal.
4. **Our method beats dense:** It does not. We beat RRF. Dense remains best on FiQA/SciDocs.

### 7.3 Recommended Wording Adjustments

- Replace "FAS repair" with "FAS-based ranking" or "graph-consistent ranking (via greedy FAS + topological sort)" where appropriate.
- Replace "minimum-weight feedback arc set" with "greedy feedback arc set heuristic" when describing our algorithm.
- Add a sentence: "Our FAS heuristic has no known approximation guarantee and is used for efficiency; stronger solvers (e.g., ILP) could be substituted."
- In contributions, lead with "selective repair policy" and do not claim algorithmic novelty for FAS.

---

## 8. Summary: Honest Positioning

**What we do:** Use RRF as the base fusion. When BEW (or disagreement) is high, replace RRF with the output of a greedy FAS heuristic + topological sort. When low, keep RRF.

**What we contribute:** The idea and empirical validation of **selective** application—apply graph-consistent ranking only when the base ranking is highly inconsistent with the aggregated preference graph.

**What we do not contribute:** A new FAS algorithm, a new rank aggregation objective, a theoretical guarantee, or a method that beats dense retrieval.

**For Q1 submission:** The contribution is narrow but clear. Emphasize the selective policy, the two-regime analysis (cyclic vs acyclic), and the empirical gains. Avoid overclaiming the FAS algorithm or the objective. Be explicit about limitations.
