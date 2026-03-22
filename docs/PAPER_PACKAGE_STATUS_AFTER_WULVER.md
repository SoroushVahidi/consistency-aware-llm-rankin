# Paper Package Status After Wulver

## Short answer

Yes: SciDocs, HotpotQA, FiQA, and BRIGHT are all now represented in one finished new paper package under `outputs/pub_vote_cmp_all4/`.

What is true now:

- all four datasets have fresh publication-vote outputs under `outputs/pub_vote_cmp_all4/`
- all four datasets are represented in:
  - `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv`
  - `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv`
  - `outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv`
- the old committed package under `outputs/pub_vote_cmp_v2/paper_package/` still exists, but there is now a new four-dataset package root as well

## Dataset-by-dataset status

- `scidocs`
  - represented in fresh publication-vote outputs under `outputs/pub_vote_cmp_all4/scidocs/`
  - all three vote variants completed
- `hotpotqa`
  - represented in fresh publication-vote outputs under `outputs/pub_vote_cmp_all4/hotpotqa/`
  - all three vote variants completed
- `fiqa`
  - now represented in fresh publication-vote outputs under `outputs/pub_vote_cmp_all4/fiqa/`
  - all three vote variants completed
  - this is a genuine improvement over the prior package state
- `bright`
  - represented in fresh publication-vote outputs under `outputs/pub_vote_cmp_all4/bright/`
  - all three vote variants completed

## What evidence tables / reports now exist

Fresh new package-level outputs under `outputs/pub_vote_cmp_all4/paper_package/`:

- tables
  - `table_graph_ndcg_and_consistency.csv`
  - `table_bootstrap_delta_ndcg.csv`
  - `table_consistency_qrels_bew.csv`
- plots
  - `fig_cyclicity_and_scc.png`
  - `fig_delta_ndcg_bootstrap.png`
  - `fig_graph_qrels_bew_pre_post.png`
  - `fig_mean_ndcg_hybrids.png`
- summary
  - `MANUSCRIPT_SUMMARY.md`

Fresh new upstream evidence under `outputs/pub_vote_cmp_all4/`:

- per-query CSVs for all four datasets and all three vote variants
- summary CSVs for all four datasets and all three vote variants
- experiment-summary JSONs for all four datasets and all three vote variants
- vote JSONL files for all four datasets
- analysis JSON files for all four datasets and all three variants

## Is the paper package stronger than before?

Yes.

It is stronger in these ways:

1. FiQA is now part of the publication path rather than excluded.
2. BRIGHT is now present in the same fresh four-dataset package instead of only being code-supported or partially materialized.
3. The paper-package builder and summary scripts now handle the broader dataset set.
4. The exact MWFAS path is no longer a stub: the repo now has a real Gurobi-backed exact solver plus tests.

## Top remaining gaps for journal submission

1. Decide whether `outputs/pub_vote_cmp_all4/` should become the journal-facing canonical package in git, or remain a local regeneration alongside the older committed `pub_vote_cmp_v2` package.
2. Resolve the unstable MiniLM stack if you want a three-ranker publication package instead of the stable lexical two-ranker package built here.
3. Optionally add a manuscript-facing real-data exact-vs-greedy comparison artifact now that the exact Gurobi solver is real and tested.

## Most concrete next step

If you want to print the final four-dataset summary table again:

```bash
python scripts/summarize_publication_vote_suite.py --root outputs/pub_vote_cmp_all4
```
