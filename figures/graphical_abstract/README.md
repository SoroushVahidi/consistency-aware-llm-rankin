# Graphical abstract

The image **`graphical_abstract.png`** summarizes the project story at a glance:

1. **Pairwise preferences** from multiple rankers (or LLM) form a **weighted directed graph**.
2. **Cycles** indicate inconsistency; no single ranking satisfies all edges.
3. **MWFAS / FAS repair** removes a minimum-weight feedback arc set to obtain a **DAG**.
4. **Hybrid ranking** combines graph structure with retrieval scores; **nDCG** evaluates against qrels.

Regenerate the curated manuscript figures (including this slot) from publication outputs:

```bash
python scripts/build_manuscript_assets.py --pub-root outputs/pub_vote_cmp_all4/paper_package
```

The graphical abstract PNG is committed for convenience; replace it if you refresh the visual design.
