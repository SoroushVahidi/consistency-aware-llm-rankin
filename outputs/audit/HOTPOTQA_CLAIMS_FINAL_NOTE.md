# HotpotQA: Exact Claims (Final Note)

## What HotpotQA SUPPORTS

1. **Selective reordering:** Choosing when to use graph-consistent (topological) ordering vs RRF improves NDCG.
2. **Conflict-aware selection:** BEW (ranking violation of graph) is a useful signal for when to apply.
3. **Generalization:** The selective-repair *policy* generalizes to sparse, acyclic multi-scorer settings.

## What HotpotQA DOES NOT SUPPORT

1. **Cycle repair:** No cycles exist; FAS removes zero edges.
2. **MWFAS / feedback arc set:** FAS is not doing cycle removal on HotpotQA.
3. **Inconsistency resolution:** There is no cycle-based inconsistency to resolve.

## Paper Wording (Recommended)

**Use:**
> "On HotpotQA, preference graphs are acyclic (0% cyclic). FAS does not remove edges; it produces a topological ordering that respects the aggregated preferences. Selective repair (applying this ordering only when BEW is high) improves NDCG over both always-RRF and always-FAS, demonstrating that the conflict-aware selection policy generalizes to sparse, acyclic multi-scorer settings."

**Avoid:**
> "FAS repairs cycles on HotpotQA" or "BEW measures cycle-based inconsistency."

BEW on HotpotQA measures **ranking violation of the graph**, not cycle-based inconsistency.
