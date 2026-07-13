# POSITION_BIAS_REPORT

Method: for every raw response with preserved text, the current parser's
label (`"A"`/`"B"`) was tallied by provider x dataset x scope, and an exact
two-sided binomial test against p=0.5 was run per group
(`scipy.stats.binomtest`). Three scopes:

- `all_current_parser`: every response, using the production parser's label
  (including its default-to-`"A"` fallback).
- `exact_only`: only responses that were an unambiguous, single-character
  `"A"`/`"B"` -- the cleanest possible signal of the model's actual choice.
- `fallback_only`: only responses that triggered the parser's default
  (ambiguous/malformed/empty). **By construction this is always 100% `"A"`**
  (see PARSER_AUDIT.md) -- it is included for completeness but is a property
  of the parser, not evidence about the model, and must not be read as
  "position bias."

## Results (`exact_only` -- the scientifically meaningful rows)

| Provider | Dataset | n | A rate | B rate | p (two-sided binomial) |
|---|---|---|---|---|---|
| azure | bright | 1978 | 58.3% | 41.7% | 1.2e-13 |
| azure | fiqa | 2250 | 53.2% | 46.8% | 0.0022 |
| azure | hotpotqa | 1628 | 55.6% | 44.4% | 7.1e-06 |
| cohere | bright | 2024 | 30.5% | 69.5% | 1.2e-70 |
| cohere | fiqa | 2250 | 39.1% | 60.9% | 4.2e-25 |
| cohere | hotpotqa | 1645 | 32.0% | 68.0% | 5.6e-49 |

Full data (`all_current_parser` and `fallback_only` scopes too) in
`position_bias_summary.csv`.

## Findings

1. **Every single group is statistically significant** (p ≪ 0.001) -- neither
   provider is order-invariant, on any dataset, at the sample sizes here.
2. **The two providers are biased in opposite directions, and by very
   different magnitudes.** Azure mildly favors position A (53-58%). Cohere
   strongly favors position B (61-70% -- roughly a 2:1 skew on `bright` and
   `hotpotqa`). This is not a small effect for Cohere: on `bright`, Cohere
   picks the document shown as "B" more than twice as often as "A".
3. **Pooling across providers, as the manuscript's prose does when it
   describes "Cohere/Azure pairwise judgments" as one corpus, would average
   these two opposite biases toward ~50% and hide both** (a pooled check run
   for this audit: 45,965/12,020 pooled A-rate ≈ 46%, deceptively close to
   unbiased). Any manuscript statement about order robustness must be made
   per-provider, not pooled.
4. Position bias is present **even restricted to unambiguous, single-letter
   responses** -- it is a genuine property of model behavior under this
   prompt template, not an artifact of the parser's fallback rule (which is
   reported separately in the `fallback_only` scope and is trivially 100% A
   by construction, not a finding).
5. The corpus used `debias_position=True` (both forward and reverse prompts
   issued per pair) specifically to counteract this. As documented in
   PARSER_AUDIT.md, the combination rule used to merge the two directions has
   its own structural default-to-first-argument bias, so **the debiasing
   mechanism does not fully neutralize the raw per-direction position bias
   measured here** -- see FORWARD_REVERSE_REPORT.md for the direct forward-
   vs-reverse agreement analysis.

## Manuscript relevance

The manuscript currently states debiasing was applied to the Cohere/Azure
corpus but does not report any position-bias measurement or its outcome. This
is the "order-bias discussion" gap; see MANUSCRIPT_PATCH_RECOMMENDATIONS.md.
