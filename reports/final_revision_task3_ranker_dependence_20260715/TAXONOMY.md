# Data-Quality Conflict Taxonomy (JDIQ Task 3)

Operational taxonomy distinguishing why two rankers disagree on a pair, and
whether that disagreement should be read as a construction artifact, genuine
evidence conflict, a coverage/representation limitation, or a repair-induced
change. Each category lists an observable diagnostic (how to detect it in
this pipeline), a failure mode (what goes wrong if it is mistaken for
something else), and a mitigation/reporting requirement (what this
manuscript now does about it).

## A. Construction-induced artifacts

Disagreement that exists only because of how scores were combined, not
because the underlying rankers substantively disagree.

| Instance | Observable diagnostic | Failure mode | Mitigation / reporting requirement |
|---|---|---|---|
| Incompatible score scales | `raw_score_distribution_summary.csv`: BM25 unbounded (7.9-652), TF-IDF/MiniLM roughly bounded to [0,1] | Raw cross-ranker margin correlation looks weak/strong purely from scale, not agreement | Report raw-space correlations as scale-sensitive diagnostics only; use `minmax_query_ranker`-normalized margins (`directional_agreement_margin_correlation.csv`, `normalized_*_margin_correlation`) as the scale-controlled comparison |
| Missing-score handling | `coverage_aggregate.csv` `mean_missing_abstention_fraction`; MiniLM canonical coverage 44-71% vs BM25/TF-IDF 90-96% | A ranker's silence on a doc could be misread as a "vote" for either direction | Confirmed: canonical pipeline abstains (no vote) rather than imputing a synthetic loss for missing scores (`build_query_vote_artifacts`, `full_calibration_utils.py:588-590`); the legacy `build_votes_file.py` path's default floor-imputation behavior is flagged as a divergent, non-canonical alternative and is not used for manuscript numbers |
| Manufactured tie directions | `coverage_aggregate.csv` `mean_tie_abstention_fraction_of_eligible` (near 0 for BM25/TF-IDF, up to 0.42 for MiniLM at larger pools) | Breaking a genuine score tie by document ID manufactures a directional preference the ranker never expressed | Canonical pipeline abstains on genuine ties (`direction_a == direction_b: continue`); `rank_percentile_independent` calibration exists specifically to avoid percentile-transform tie-manufacturing (see `full_calibration_utils.py:87-95`) |
| Parser/threshold defaults | Vote-margin threshold, min_support, aggregate_threshold (`ThresholdConfig`) | An unreported or silently-reused threshold changes retained-edge counts without being visible in the manuscript | This task's leave-one-out and pre/post-normalization studies use one fixed, disclosed threshold policy each (see manifests), never silently reusing another construction's tuned thresholds |
| Candidate-dependent normalization | `pre_post_normalization_structural_summary.csv`; removed-edge Jaccard overlap 0.75-1.0 across all dataset/pool/regime cells | Min-max normalization computed after pool restriction could make graph structure partly an artifact of which candidates were selected, not ranker disagreement | Measured directly (section 6): pre-pool vs. post-pool min-max normalization produce nearly identical structural statistics and no Holm-significant retrieval differences at the tested pool sizes -- normalization order is not a material driver of the pool-size effects documented in Task 1 |
| Unreported threshold choices | `choose_threshold_config` `notes` field; this task's `quantile_independent_q0p5` policy | Retention-matching one protocol's thresholds against a different protocol's baseline can silently bias a "fair" comparison | Every threshold policy used in this task states its derivation before results were inspected (see per-script manifests) |

## B. Genuine evidence conflict

Disagreement that reflects two rankers producing substantively different,
individually defensible orderings of the same document pair.

| Instance | Observable diagnostic | Failure mode | Mitigation / reporting requirement |
|---|---|---|---|
| Two valid rankers genuinely disagreeing | `rank_correlation_summary.csv`: moderate (not extreme) Kendall's tau-b across all three ranker pairs (0.14-0.56); `directional_agreement_margin_correlation.csv` (57-82% agreement, never near 100%) | Treating moderate correlation as either "redundant" or "independent" without a number | Report exact tau-b/rho/agreement-rate per dataset/pair rather than a qualitative label |
| Direct mutual contradiction from opposing valid signals | `mutual_pair_attribution_summary.csv`: dominant configuration is `single_voter_vs_single_voter` (67-94% of mutual pairs), not the reviewer-hypothesized `lexical_pair_vs_minilm` bloc (3-27%) | Assuming mutual pairs mean "BM25+TF-IDF vs MiniLM" without checking | This task empirically rejects that hypothesis as the dominant mechanism; report per-dataset variation honestly, including that BRIGHT does not even show BM25-TF-IDF as the most-correlated pair |
| Longer-cycle nontransitivity after artifact controls | `leave_one_out_structural_summary.csv`: cyclicity persists (and varies by dataset, not by a single "lexical" mechanism) even after leaving one ranker out | Assuming all cyclicity is an artifact of one specific ranker or pairing | No single two-ranker variant eliminates cyclicity; the pattern is dataset-dependent (e.g. `pair_bm25_tfidf` has the *most* mutual pairs on FiQA/SciDocs but the *fewest* on HotpotQA), consistent with distributed genuine disagreement rather than one dominant redundant pair |

## C. Coverage / representation limitations

Disagreement (or apparent agreement) that is really a byproduct of which
documents each ranker was able to score at all.

| Instance | Observable diagnostic | Failure mode | Mitigation / reporting requirement |
|---|---|---|---|
| Rankers scoring different document subsets | `coverage_aggregate.csv`: MiniLM candidate-pool coverage 44-71% vs BM25/TF-IDF 90-96% | MiniLM's lower apparent influence on the graph could be misread as "MiniLM disagrees less" rather than "MiniLM was asked about fewer pairs" | Report per-ranker `pairwise_eligibility_fraction` and `missing_abstention_fraction` alongside every dependence/attribution statistic |
| Small candidate pools | `pair_funnel_aggregate.csv`, Task 1's `P>k` findings | Small pools understate true pairwise disagreement / structural complexity | This task reruns every diagnostic at both the canonical pool and the Task 1 larger pool, and reports both |
| Correlated rankers | `rank_correlation_summary.csv`: BM25-TF-IDF is the most-correlated pair in 3 of 4 datasets, but not BRIGHT | A single blanket "two lexical signals, one dense signal" framing overstates the effective number of independent voices in most, but not all, cases | Report the per-dataset exception explicitly rather than a single averaged claim |
| Incomplete qrels | Task 2's qrels-pair eligibility work (`qrels_reference.py`); FiQA/BRIGHT have zero eligible judged pairs in canonical pools | Qrels-conditioned diagnostics silently degrade to zero-signal for some datasets | Already handled in Task 2; this task does not re-derive qrels-conditioned reference orders |

## D. Repair-induced changes

Changes attributable to the greedy FAS repair step itself, not to the raw
evidence conflict.

| Instance | Observable diagnostic | Failure mode | Mitigation / reporting requirement |
|---|---|---|---|
| Graph-internal consistency improvement | `leave_one_out_structural_summary.csv` `cyclic_query_pct_after_repair` (always 0.0 in this task's records) vs. `repair_active_fraction` (0.73-1.0) | Assuming repair "fixes" the underlying evidence conflict rather than just removing enough edges to break cycles | Report structural before/after repair separately from retrieval before/after repair |
| Changes that fail to propagate to ranking | `leave_one_out_retrieval_summary.csv` `unchanged_query_count` frequently a large share of queries despite `repair_active_fraction` near 1.0 | Assuming "repair was active" implies "ranking changed" | Report both `repair_active_fraction` and helped/harmed/unchanged query counts side by side |
| Ranking changes that fail to alter the metric | `leave_one_out_active_family_holm.csv`, `pre_post_normalization_active_family_holm.csv`: 0 Holm-significant cells across every family in this task | Assuming any observed helped/harmed asymmetry is reliable evidence of improvement | Holm-corrected active-family testing remains primary, per Task 2's statistical framework; this task adds two more pre-specified families (leave-one-out, pre/post-normalization) and both come back null, consistent with Tasks 1-2 |

## Summary judgment for JDIQ framing

- BM25 and TF-IDF are the most-correlated ranker pair in 3 of 4 datasets, but the correlation is **moderate**, not extreme, and does not hold in BRIGHT.
- Coverage, tie-abstention, and vote-margin-threshold abstention materially shape the graph (documented exhaustively per dataset/pool/ranker/regime) but are not evidence of a hidden bug; they are transparent, disclosed consequences of the stated construction.
- Candidate-pool-dependent normalization is a measured, small effect, not a major confound: pre-pool and post-pool min-max normalization produce nearly identical graphs and no differing Holm-significant retrieval conclusions.
- The reviewer hypothesis "BM25 + TF-IDF vote together against MiniLM" is **not supported** as the dominant mechanism: single-voter-vs-single-voter disagreement dominates mutual pairs in every dataset, and the lexical-pair-vs-dense configuration is a minority.
- `ms2`'s empirical acyclicity is explained by two combined, distinguishable facts: mutual pairs (2-cycles) are **combinatorially impossible** under `ms2`'s support>=2-of-3 rule (both directions would require 4 total votes from only 3 voters), while longer (3+-node) cycles remain theoretically possible under majority consensus but were never observed across this task's full sweep (342 usable queries across all four datasets, each evaluated at both the canonical and Task 1 larger candidate-pool size = 684 dataset-query-pool cells) -- an empirical near-transitivity finding, not a theoretical guarantee.
