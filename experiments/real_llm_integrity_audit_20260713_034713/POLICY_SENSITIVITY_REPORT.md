# POLICY_SENSITIVITY_REPORT

## What this analysis is (and is not)

The manuscript's stored 200-record repair/cyclicity/ΔnDCG numbers do **not**
depend on Cohere or Azure's judgments at all (PROVIDER_COUNT_RESOLUTION.md).
So "does reparsing the LLM responses change the manuscript's 62/69/69
numbers" has a trivial answer: **no, because those numbers never used the LLM
responses in the first place; they are identical under every policy** (a
consistency check for this, not a new finding, is in VALIDATION_CHECKS.md).

The scientifically useful version of "does the parsing policy change the
conclusion" is: **if a preference graph were built directly from Cohere's or
Azure's pairwise judgments** (which the manuscript's prose implies is roughly
what happened, even though it is not what the stored pipeline computed), how
sensitive would repair/cyclicity/ΔnDCG be to the five parsing policies? This
audit built that graph -- for real, from the raw stored judgments, per
provider, per policy -- using the repository's own unmodified
`process_query_record()` (graph build -> greedy-FAS repair -> Markov ranking
-> nDCG), across all 200 query-regime slots. Full per-query output:
`policy_sensitivity_full.csv` (2,000 rows) and per-policy directories
`policy_P{0-4}_*/query_level_results.csv`.

## Policy definitions used

- **P0 (current parser):** exact reproduction of the production parser +
  the debias combination rule (default-to-first-shown-document on
  forward/reverse disagreement). Cross-checked against the persisted
  `llm_cache/*/llm_pairwise_judgments.jsonl` winners as a reproducibility
  check (VALIDATION_CHECKS.md).
- **P1 (ambiguous -> abstain):** a direction classified ambiguous/malformed/
  empty is dropped; if the *other* direction is clean, that direction alone
  decides the pair; if both are clean but disagree, the pair abstains
  (P0's silent default-to-first-document is not replicated -- see
  PARSER_AUDIT.md for why).
- **P2 (discard ambiguous pair):** stricter than P1 -- if *either* direction
  is ambiguous/malformed/empty, the whole pair is discarded, even if the
  other direction is clean.
- **P3 (exact A/B only):** only single-character `"A"`/`"B"` responses count;
  anything else (including well-formed-but-verbose responses) is treated as
  missing for that direction, combined the same way as P1.
- **P4 (retry-success only):** restricted to query-regime records with
  `retry_count == 0`. **All 400 Cohere+Azure records in this corpus have
  `retry_count == 0`**, so P4 is numerically identical to P0 in every row
  below -- there is no retry-driven signal to find in this corpus (confirmed,
  not assumed).

## Results

| Provider | Dataset | Policy | Usable queries | Cyclic % | Mean ΔnDCG | 95% CI (2000-resample bootstrap) | Help | Harm | Inactive |
|---|---|---|---|---|---|---|---|---|---|
| azure | bright | P0 | 68 | 30.9% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 68 |
| azure | bright | P1 | 68 | 0.0% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 68 |
| azure | bright | P2 | 68 | 0.0% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 68 |
| azure | bright | P3 | 68 | 0.0% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 68 |
| azure | bright | P4 | 68 | 30.9% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 68 |
| azure | fiqa | P0/P4 | 73 | 50.7% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 73 |
| azure | fiqa | P1/P2/P3 | 73 | 4.1% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 73 |
| azure | hotpotqa | P0/P4 | 57 | 57.9% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 57 |
| azure | hotpotqa | P1 | 57 | 10.5% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 57 |
| azure | hotpotqa | P2/P3 | 57 | 5.3% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 57 |
| cohere | bright | P0/P4 | 68 | 32.4% | **-0.0058** | [-0.0146, 0.0008] | 3 | 5 | 60 |
| cohere | bright | P1/P2/P3 | 66 | 0.0% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 66 |
| cohere | fiqa | all P | 73 | 0-61.6%\* | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 73 |
| cohere | hotpotqa | P0/P4 | 57 | 57.9% | **-0.0263** | [-0.0526, 0.0000] | 0 | 3 | 54 |
| cohere | hotpotqa | P1/P3 | 57 | 10.5% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 57 |
| cohere | hotpotqa | P2 | 57 | 0.0% | 0.0000 | [0.0000, 0.0000] | 0 | 0 | 57 |

\* fiqa cyclic % drops from 61.6% (P0/P4) to 0% (P1/P2/P3) but ΔnDCG/help/harm
stay 0 throughout -- cyclicity changes without a corresponding repair effect
here (repair on a cyclic-but-otherwise-clean fiqa graph doesn't move nDCG in
either direction; consistent with the manuscript's own "FiQA is low-cyclicity
... [and near-]degenerate at exactly zero" framing for the primary pilot,
though this is a different graph/corpus, see caveat above). Full numeric
table: `_bootstrap_summary.csv`.

## Answers to the posed questions

- **Does default-A fallback change conclusions?** Yes, substantially for
  cyclicity. Discarding fallback-defaulted edges (P0→P2) collapses cyclicity
  from 30-62% down to 0-10% in five of six provider/dataset groups, and to 0%
  in three of them. It also eliminates every help/harm case that P0 finds for
  cohere/bright and cohere/hotpotqa (P0: 3 help + 5 harm on bright, 3 harm on
  hotpotqa; P1/P2/P3: 0/0 everywhere for cohere).
- **Does abstaining change conclusions?** Yes -- P1 alone (softer than P2,
  salvages a clean single direction when the other is fallback/disagreeing)
  already removes essentially all of the cyclicity reduction P2 achieves, and
  removes all of P0's help/harm cases.
- **Does any policy change confidence intervals?** Yes: cohere/bright and
  cohere/hotpotqa have non-degenerate CIs only under P0/P4 (bright:
  [-0.0146, 0.0008], crossing zero; hotpotqa: [-0.0526, 0.0000], touching
  zero at its upper edge). Under P1/P2/P3 the CI collapses to the degenerate
  point [0.0000, 0.0000] because repair becomes inactive for every query --
  not because uncertainty shrank, but because the outcome variable stops
  varying at all.
- **Are provider conclusions robust?** No, and the two providers diverge in
  an interesting, real way even before considering parsing policy: under P0,
  **Azure shows zero help/harm cases in any dataset**, while **Cohere shows
  8 non-inactive cases** (3 help + 5 harm on bright, 3 harm on hotpotqa) even
  though Azure's raw cyclicity rates are comparable to or higher than
  Cohere's in two of three datasets. Repair "doing something" in this
  LLM-only-graph analysis is provider-specific, not just parsing-policy
  specific.
- **P4 (retry-success-only) never differs from P0** in this corpus, because
  no retries occurred. This policy axis is a null result here, not evidence
  that retries don't matter in general.

## Common-query set

196 of 200 query-regime slots were usable (produced a >=2-node graph) under
every policy for both providers simultaneously; `policy_sensitivity_common_
queries.csv` restricts to exactly this set for apples-to-apples comparison
across all 5 policies without confounding usable-N changes with outcome
changes. The 4 excluded slots drop out only under the stricter discard
policies (P2/P3) when a query's already-small candidate set loses too many
edges to form a usable graph.
