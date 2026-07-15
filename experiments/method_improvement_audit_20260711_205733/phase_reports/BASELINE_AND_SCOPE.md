# Baseline And Scope

Generated: 2026-07-11 21:11:50

## Canonical Current Evidence

- Canonical package: `outputs/pub_vote_cmp_all4/paper_package/`.
- Canonical manuscript freeze clone: `outputs/final_jis_package/`.
- Historical but conflicting package: `outputs/pub_vote_cmp_v2/paper_package/`.
- The audit uses current canonical tables only for baseline claims and never mixes `pub_vote_cmp_v2` values into canonical summaries.

## Canonical Pipeline Details

- Dataset package: SciDocs, FiQA, HotpotQA, BRIGHT.
- Vote constructions: `ms2`, `ms1`, `ms1_drop_mutual`.
- Rankers used to build votes: BM25, TF-IDF, MiniLM.
- Canonical query subset generator: `scripts/run_publication_vote_suite.py`.
- Candidate retrieval depth per ranker: SciDocs 50, FiQA 50, HotpotQA 35, BRIGHT 50.
- Candidate graph top-k for vote construction: SciDocs 20, FiQA 20, HotpotQA 10, BRIGHT 20.
- Repair method in canonical package: greedy weighted feedback arc set (`greedy_fas`).
- Canonical graph extractors in manuscript tables: unrepaired/repaired Copeland and balance hybrids with RRF prior.
- Canonical fusion formula in manuscript package: min-max normalized prior + alpha * min-max normalized graph component, with alpha=0.3 for `hybrid_rrf_*_a03`.
- Canonical statistical procedure in manuscript package: paired bootstrap delta summaries from `outputs/pub_vote_cmp_all4/analysis/*.json`.

## Exact Canonical Scope By Dataset

- bright: n_queries by variant {"ms1": "50", "ms1_drop_mutual": "50", "ms2": "34"}
- fiqa: n_queries by variant {"ms1": "120", "ms1_drop_mutual": "120", "ms2": "117"}
- hotpotqa: n_queries by variant {"ms1": "52", "ms1_drop_mutual": "52", "ms2": "52"}
- scidocs: n_queries by variant {"ms1": "120", "ms1_drop_mutual": "120", "ms2": "119"}

## Historical, Stale, Or Conflicting Evidence

- `outputs/pub_vote_cmp_all4/analysis/`: final supporting analysis; conflicts_with=none if interpreted as all4-only
- `outputs/pub_vote_cmp_v2/paper_package/`: final but superseded for breadth; conflicts_with=Headline SciDocs ms1 ΔnDCG & cyclicity stats differ from all4 (same names not same run)
- `outputs/q1_journal_package/`: final narrative package; conflicts_with=Stale vs four-dataset story: built from v2 tables unless regenerated with --pub-root all4
- `outputs/real_full/`: exploratory / supplementary; conflicts_with=Different preference-source (qrels vs votes_file); not comparable headline Δ to pub suite
- `docs/tables/*.csv`: mixed; conflicts_with=May reference older experiment IDs; cross-check dates
- `reports/paper_tables/`: exploratory / drafting; conflicts_with=none
- `outputs/noise_sweep_*`: exploratory committed; conflicts_with=none
- `outputs/margin_multiseed_*`: exploratory committed; conflicts_with=none
- `outputs/pub_vote_cmp_all4/SUMMARY.md`: final companion; conflicts_with=none
- `outputs/real_full/PROVENANCE.md`: metadata; conflicts_with=—

## Manuscript Claim Support Snapshot

- C2: Vote construction strongly controls cycle incidence (ms2 vs ms1 vs ms1_drop_mutual) [strongly_supported]
- C3: FAS repair reduces graph–reference BEW/PIC when repair removes weight (esp. ms1 cyclic regimes) [strongly_supported]
- C6: Repair is inactive (ΔnDCG=0) when graphs are near-acyclic (ms2 / ms1_drop_mutual) [strongly_supported]
- C7: Effect of repair on nDCG depends on vote construction and dataset [strongly_supported]
- C10: Greedy FAS structural repair changes rankings without guaranteed retrieval gain [strongly_supported]

## Canonical Tables Used For Claims

- `outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv`
- `outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv`
- `outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv`

## Audit Scope For This Workspace

- Phase 0 uses canonical committed aggregates only.
- Phases 1–6 regenerate a fully logged workspace-local rerun under canonical query subsets and rankers so per-query diagnostics can be computed without touching canonical directories.
- Canonical baseline claims remain tied to `pub_vote_cmp_all4` / `final_jis_package`; workspace reruns are diagnostic and must not overwrite or silently replace the canonical package.

## Source Audit Note

> Key sentence from `reports/repo_publication_audit.md`: `outputs/pub_vote_cmp_all4/paper_package/` is the recommended canonical package.

