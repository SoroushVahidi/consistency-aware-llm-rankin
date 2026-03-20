# Theoretical Foundation: Conflict-Aware Selective Repair

This document formalizes the problem setting, defines key concepts, states propositions, and provides a unified theoretical framework for upgrading the work to Q1 journal level.

---

## 1. Formal Problem Setting

### 1.1 Multi-Scorer Ranking

**Definition 1 (Multi-Scorer Ranking Instance).** For a query \( q \), a multi-scorer ranking instance consists of:

- **Candidate set** \( C_q \subseteq \mathcal{D} \): a finite set of items (documents) to be ranked.
- **Scoring functions** \( \{s_1, \ldots, s_m\} \): each \( s_k : C_q \to \mathbb{R} \) assigns a score to each candidate. Higher score means more preferred.
- **Induced preference graph** \( G_q = (V, E, w) \): a weighted directed graph derived from the scorers (defined below).

We assume \( |C_q| \geq 2 \) and \( m \geq 2 \).

### 1.2 Weighted Directed Preference Graph

**Definition 2 (Preference Graph).** The preference graph \( G_q = (V, E, w) \) is a weighted directed graph where:

- \( V = C_q \) (nodes are candidates).
- For each unordered pair \( \{i, j\} \subseteq C_q \), at most one directed edge is present: either \( (i, j) \) or \( (j, i) \), indicating the aggregate preference.
- \( w : E \to \mathbb{R}_{>0} \) assigns a positive weight to each edge.

**Edge weights** depend on the aggregation mode:

**Summed margin.** For each pair \( (i, j) \), let \( \Delta_{ij} = \sum_{k=1}^{m} (s_k(i) - s_k(j)) \) over scorers that rank both. If \( \Delta_{ij} > 0 \), add edge \( (i, j) \) with \( w(i,j) = \Delta_{ij} \); if \( \Delta_{ij} < 0 \), add \( (j, i) \) with \( w(j,i) = |\Delta_{ij}| \). Ties are skipped.

**Majority vote.** For each pair \( (i, j) \), count scorers preferring \( i \) over \( j \) vs \( j \) over \( i \). The majority direction wins; weight = number of votes for the winner. Ties are skipped.

**Vote-plus-margin.** Direction from majority; weight = votes + mean margin among agreeing scorers.

### 1.3 Backward Edge Weight (BEW)

**Definition 3 (Ranking).** A ranking \( \pi \) over \( C_q \) is a bijection \( \pi : C_q \to \{0, 1, \ldots, n-1\} \) where \( \pi(i) < \pi(j) \) means \( i \) is ranked above \( j \). We write \( \pi \) as an ordered list \( [d_1, d_2, \ldots, d_n] \) with \( d_1 \) best.

**Definition 4 (Backward Edge Weight).** Given a preference graph \( G = (V, E, w) \) and a ranking \( \pi \), the **backward edge weight** of \( \pi \) with respect to \( G \) is

\[
\mathrm{BEW}(\pi, G) = \sum_{(u,v) \in E \,:\, \pi(v) < \pi(u)} w(u, v).
\]

That is, BEW is the sum of weights of edges \( (u, v) \) where \( u \) is preferred over \( v \) in the graph, but \( v \) is ranked above \( u \) in \( \pi \). These edges "point backward" relative to the ranking.

---

## 2. What FAS Does in Our Pipeline

We use a greedy FAS heuristic followed by topological sort. The behavior differs by graph structure.

### 2.1 Cyclic Graphs

**Regime A: Cyclic graphs.** If \( G \) contains at least one directed cycle:

1. **Greedy FAS:** Iteratively find a cycle, remove the minimum-weight edge in that cycle, repeat until the graph is acyclic. Let \( G' \) be the resulting DAG and \( R \) the set of removed edges.
2. **Topological sort:** Compute a topological ordering \( \pi_{\mathrm{FAS}} \) of \( G' \).
3. **Output:** \( \pi_{\mathrm{FAS}} \).

Here, FAS performs **minimum (greedy) feedback arc set removal**: it deletes edges to break cycles. The output ranking is a topological order of the *reduced* graph \( G' \), not the original \( G \).

### 2.2 Acyclic Graphs

**Regime B: Acyclic graphs.** If \( G \) is already a DAG:

1. **Greedy FAS:** No cycles exist; no edges are removed. \( G' = G \), \( R = \emptyset \).
2. **Topological sort:** Compute a topological ordering \( \pi_{\mathrm{FAS}} \) of \( G \).
3. **Output:** \( \pi_{\mathrm{FAS}} \).

Here, FAS performs **selection of a topological ordering** only. No edges are removed. The output is one of possibly many topological orders of \( G \).

### 2.3 Two Distinct Regimes

| Regime | Graph | FAS action | Output |
|--------|-------|------------|--------|
| A | Cyclic | Remove edges to break cycles; topological sort on reduced graph | Ranking consistent with \( G' \subset G \) |
| B | Acyclic | No edge removal; topological sort on original graph | Ranking consistent with \( G \) |

---

## 3. Theoretical Interpretation of BEW

### 3.1 BEW Measures Ranking Disagreement with the Graph

BEW quantifies how much a ranking \( \pi \) **violates** the preference structure encoded in \( G \). Each backward edge \( (u, v) \) represents a preference "\( u \) over \( v \)" that \( \pi \) reverses. The weight \( w(u,v) \) reflects the strength of that preference. Thus, BEW is a weighted count of violations.

### 3.2 Relation to Kendall Tau

Let \( \tau(\pi, \sigma) \) denote the Kendall tau distance (number of discordant pairs) between rankings \( \pi \) and \( \sigma \). For a graph \( G \), any topological order \( \sigma \) of \( G \) satisfies \( \mathrm{BEW}(\sigma, G) = 0 \) (Proposition 1 below). Thus:

- **BEW of \( \pi \)** can be viewed as the *weighted* disagreement between \( \pi \) and the graph's preference structure. Unlike Kendall tau (which compares two full rankings), BEW compares a ranking to a directed graph; it uses edge weights, so high-weight violations contribute more.
- If all edge weights are 1, BEW counts backward edges. This differs from Kendall tau distance, which counts discordant pairs between two complete rankings.

**When BEW is expected to be high:**

- Scorers disagree strongly (many high-weight edges in conflicting directions).
- The ranking \( \pi \) (e.g., from RRF) does not follow the aggregate preference structure.
- The graph has many edges, and \( \pi \) is "far" from any topological order.

---

## 4. Propositions

**Proposition 1.** *If \( \pi \) is a topological ordering of \( G \), then \( \mathrm{BEW}(\pi, G) = 0 \).*

*Proof.* A topological ordering satisfies: for every edge \( (u, v) \in E \), \( \pi(u) < \pi(v) \) (i.e., \( u \) appears before \( v \)). Thus, no edge has \( \pi(v) < \pi(u) \), so no edge is backward. Hence \( \mathrm{BEW}(\pi, G) = 0 \). ∎

**Proposition 2.** *If a ranking \( \pi \) has high BEW, it violates many high-weight preferences.*

*Proof.* By definition, \( \mathrm{BEW}(\pi, G) = \sum_{(u,v) \in E \,:\, \pi(v) < \pi(u)} w(u,v) \). Each term is a positive weight. So high BEW implies either (a) many backward edges, or (b) some backward edges with large weights, or (c) both. In all cases, \( \pi \) violates preferences that the graph encodes as strong (high \( w \)). ∎

**Proposition 3.** *In a cyclic graph \( G \), let \( F \subseteq E \) be a feedback arc set and \( G' = (V, E \setminus F) \) the resulting DAG. For any topological order \( \pi \) of \( G' \), \( \mathrm{BEW}(\pi, G) = \sum_{(u,v) \in F} w(u,v) \). The minimum achievable BEW over all rankings is \( \min_{F \in \mathrm{FAS}(G)} \sum_{(u,v) \in F} w(u,v) \), i.e., the minimum weight of a feedback arc set.*

*Proof.* For a topological order \( \pi \) of \( G' \), every edge in \( E \setminus F \) is forward (by definition). For each \( (u,v) \in F \): since \( F \) breaks all cycles, the cycle containing \( (u,v) \) had a path from \( v \) to \( u \) other than \( (u,v) \). That path remains in \( G' \), so \( \pi(v) < \pi(u) \). Thus \( (u,v) \) is backward in \( \pi \), and \( \mathrm{BEW}(\pi, G) = \sum_{(u,v) \in F} w(u,v) \). No ranking can achieve lower BEW, because any ranking must violate at least one edge per cycle. The minimum is attained by a minimum-weight FAS. ∎

*Remark.* Our greedy FAS is a heuristic; it does not guarantee a minimum-weight FAS. So in practice, BEW after FAS may be larger than the theoretical minimum.

---

## 5. Theoretical Explanation of Selective Repair

**Idea:** Apply FAS (or graph-consistent ordering) only when the current ranking is highly inconsistent with the graph.

**Low BEW.** If \( \mathrm{BEW}(\pi_{\mathrm{base}}, G) \) is low, then \( \pi_{\mathrm{base}} \) (e.g., RRF) already agrees with most of the graph's preferences. Replacing it with a topological order may:
- Change the ranking substantially (different topological orders exist when the graph has multiple orderings).
- Hurt retrieval if \( \pi_{\mathrm{base}} \) was already a good compromise (e.g., RRF) and the topological order is suboptimal for relevance.

**High BEW.** If \( \mathrm{BEW}(\pi_{\mathrm{base}}, G) \) is high, then \( \pi_{\mathrm{base}} \) violates many high-weight preferences. The graph encodes strong aggregate signal that \( \pi_{\mathrm{base}} \) ignores. Replacing it with a graph-consistent ranking (via FAS + topological sort) may:
- Resolve inconsistencies that harm relevance.
- Surface items that were incorrectly demoted by \( \pi_{\mathrm{base}} \).

**Selective repair policy:** Apply FAS when \( \mathrm{BEW}(\pi_{\mathrm{base}}, G) \geq \theta \) (e.g., top 25% by BEW), else keep \( \pi_{\mathrm{base}} \). The threshold \( \theta \) can be chosen by validation.

---

## 6. Unified Framework

**Unified interpretation:** *We replace a ranking with a graph-consistent ranking when inconsistency (BEW) is high.*

- **Graph-consistent rankings:** Rankings \( \pi \) with \( \mathrm{BEW}(\pi, G') = 0 \) for some DAG \( G' \) obtained from \( G \) (either \( G' = G \) if acyclic, or \( G' = G \setminus F \) for a feedback arc set \( F \) if cyclic).
  - **Cyclic \( G \):** \( G' \) is obtained by removing a feedback arc set. Graph-consistent rankings are topological orders of \( G' \).
  - **Acyclic \( G \):** \( G' = G \). Graph-consistent rankings are topological orders of \( G \).

- **Replacement:** Replace \( \pi_{\mathrm{base}} \) with a graph-consistent ranking when BEW is high. In both regimes, the output is a topological order of a DAG (either \( G \) or a reduced \( G' \)).

- **Single principle:** *When the base ranking strongly violates the aggregated preference structure (high BEW), replace it with a ranking that respects that structure (topological order). When violation is low, keep the base ranking.*

This applies to both cyclic and acyclic graphs. The only difference is whether the DAG is obtained by edge removal (cyclic) or is the original graph (acyclic).

---

## 7. Theoretical Insights Section (Paper Draft)

### 7.1 Paragraph 1: Problem and BEW

We formalize multi-scorer ranking as follows. For each query, we have a candidate set \( C \) and \( m \) scoring functions. Aggregating scores yields a weighted directed preference graph \( G = (V, E, w) \), where an edge \( (u, v) \) with weight \( w(u,v) \) indicates that the aggregate preference favors \( u \) over \( v \). Given a ranking \( \pi \), the backward edge weight (BEW) is the sum of weights of edges \( (u, v) \) such that \( v \) is ranked above \( u \) in \( \pi \). BEW measures how much \( \pi \) violates the preference structure encoded in \( G \). By Proposition 1, any topological ordering of \( G \) (or of an acyclic subgraph obtained by removing a feedback arc set) has BEW zero with respect to that subgraph.

### 7.2 Paragraph 2: Two Regimes and Unified View

Our pipeline applies a greedy feedback arc set (FAS) heuristic followed by topological sort. In cyclic graphs, FAS removes edges to break cycles; in acyclic graphs, no edges are removed and we simply compute a topological ordering. In both cases, the output is a ranking consistent with a DAG. We unify these regimes under a single principle: when the base ranking (e.g., RRF) has high BEW—i.e., it strongly violates the aggregated preferences—we replace it with a graph-consistent ranking (a topological order). When BEW is low, we keep the base ranking. Thus, selective repair replaces the base ranking with a graph-consistent one when inconsistency is high.

### 7.3 Paragraph 3: Why Selective Repair Helps

Proposition 2 states that high BEW implies the ranking violates many high-weight preferences. In such cases, the graph encodes strong aggregate signal that the base ranking ignores; replacing it with a graph-consistent ranking may improve relevance. Conversely, when BEW is low, the base ranking already agrees with most preferences, and forcing a topological order can introduce arbitrary choices (multiple topological orders exist) that may hurt retrieval. Empirically, we find that applying FAS only when BEW exceeds a threshold (e.g., top 25%) outperforms both always-FAS and never-FAS on FiQA, SciDocs, and HotpotQA, supporting this theoretical intuition.
