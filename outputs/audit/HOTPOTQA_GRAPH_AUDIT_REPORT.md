# HotpotQA Graph Statistics Audit Report

## 1. Verification of Graph Statistics

### BEW (Backward Edge Weight) Definition
BEW of a ranking R against graph G = sum of weights of edges (u,v) in G where v appears **before** u in R.
So BEW measures how much a ranking **violates** the graph's preference structure.

### Key Finding: HotpotQA Graphs Are Acyclic
- **% cyclic:** 0.0
- **Total edges removed by FAS:** 0 (across all 100 queries)
- **FAS is NOT removing any edges** on HotpotQA. The graph is already a DAG.

### Why BEW > 0 Before and BEW = 0 After?

1. **BEW before** = BEW of RRF's ranking on the graph. RRF is not a topological order; it can violate edges.
2. **BEW after** = BEW of the FAS ranking (topological order). A topological order has zero backward edges.
3. **FAS is not 'repairing' cycles** — it is choosing a **different topological ordering** that respects the graph.
4. **FAS changes 99% of rankings** because RRF's order differs from the topological order, not because edges were removed.

### What Is HotpotQA Really Demonstrating?

- **NOT cycle repair:** No cycles exist; no edges are removed.
- **YES:** Selective reordering under sparse/acyclic preference graphs.
- **YES:** Replacing RRF with a graph-consistent ordering (topological sort) can improve or hurt NDCG depending on the query.

## 2. Cross-Dataset Comparison

| Dataset | % cyclic | avg SCCs | avg BEW | BEW_fas | edges_removed | % changed |
|---------|----------|----------|---------|---------|---------------|-----------|
| hotpotqa | 0.0 | 9.9 | 6.56 | 0.00 | 0 | 99.0 |
| fiqa | 98.0 | — | 60.37 | 0.40 | >0 | 100.0 |
| scidocs | 97.0 | — | 71.77 | 0.39 | >0 | 100.0 |

FiQA and SciDocs: cyclic graphs, FAS removes edges, BEW_after > 0 (evaluated on original graph).
HotpotQA: acyclic, FAS removes 0 edges, BEW_after = 0.

## 3. Claims HotpotQA Supports vs Does Not Support

### HotpotQA SUPPORTS:
- **Selective reordering:** Choosing when to use graph-consistent (topological) ordering vs RRF improves NDCG.
- **Conflict-aware selection:** BEW (ranking violation of graph) is a useful signal for when to apply.
- **Generalization:** The selective-repair *policy* (when to apply) generalizes to other domains.

### HotpotQA DOES NOT SUPPORT:
- **Cycle repair:** No cycles exist; no edges are removed.
- **MWFAS / feedback arc set:** The FAS algorithm is not doing cycle removal on HotpotQA.
- **Inconsistency resolution:** There is no inconsistency (cycle) to resolve.

## 4. Recommended Paper Wording

For HotpotQA, use wording such as:

> "On HotpotQA, preference graphs are acyclic (0% cyclic). FAS does not remove edges; it produces a topological ordering that respects the aggregated preferences. Selective repair (applying this ordering only when BEW is high) improves NDCG over both always-RRF and always-FAS, demonstrating that the conflict-aware selection policy generalizes to sparse, acyclic multi-scorer settings."

Avoid:

> "FAS repairs cycles on HotpotQA" or "BEW measures cycle-based inconsistency."

BEW on HotpotQA measures **ranking violation of the graph**, not cycle-based inconsistency.