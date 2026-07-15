# Regime Policy Rules

- If the graph is acyclic: choose `prior_only`.
- If a cyclic SCC intersects the prior top-10 and largest SCC >= 3: choose `markov_graph_repaired`.
- Else if largest SCC >= 4: choose `balance_graph_repaired`.
- Else: choose `markov_graph`.
