# FORWARD_REVERSE_REPORT

Scope: every pair (query, doc_a, doc_b) with **both** the forward
(`direction="ab"`, doc_a shown first) and reverse (`direction="ba"`, doc_b
shown first) raw responses preserved -- 6,010 such pairs total (3,005/provider).
"Missingness" (a pair with only one direction's raw text preserved) was
**zero**: every fresh pair in this corpus has both directions logged.

For each pair, define the "reference document" as whichever document was
shown as `A` in the forward call. `ref_wins_forward = (forward label == "A")`;
`ref_wins_reverse = (reverse label == "B")` (since the reference document is
shown as `B` in the reverse call). Agreement = these two booleans match.
Cohen's kappa treats the forward call and the reverse call as two raters
judging the same binary question ("does the reference document win?").

## Semantic agreement / contradiction

| Provider | Dataset | n pairs | Agreement rate | Cohen's kappa | Interpretation |
|---|---|---|---|---|---|
| azure | bright | 1,025 | 76.9% | 0.553 | moderate |
| azure | fiqa | 1,125 | 85.3% | 0.706 | substantial |
| azure | hotpotqa | 855 | 72.9% | 0.470 | moderate |
| **azure** | **all** | **3,005** | **78.9%** | **0.586** | **moderate** |
| cohere | bright | 1,025 | 58.9% | 0.273 | fair |
| cohere | fiqa | 1,125 | 71.1% | 0.447 | moderate |
| cohere | hotpotqa | 855 | 62.9% | 0.319 | fair |
| **cohere** | **all** | **3,005** | **64.6%** | **0.350** | **fair** |

(Landis & Koch 1977 bands used for the qualitative labels: <0=poor,
0.00-0.20=slight, 0.21-0.40=fair, 0.41-0.60=moderate, 0.61-0.80=substantial,
0.81-1.00=almost perfect.)

## Missingness

0 of 6,010 fresh pairs are missing a direction. (The corpus's real coverage
gap is elsewhere: 9,988 of 22,008 total pair-directions were cache hits with
no raw text at all, not one-sided misses -- see PARSER_AUDIT.md.)

## Order sensitivity, quantified against the "contradiction" question

- **Cohere's agreement with itself across presentation order is only
  fair-to-moderate (kappa 0.27-0.45).** On `bright`, Cohere flips its
  effective preference on 41.1% of pairs (1 - 0.589) purely because of which
  document was shown first.
- **Azure is more order-consistent but still far from perfect**
  (kappa 0.47-0.71); on `hotpotqa` it still contradicts itself on 27.1% of
  pairs.
- These rates are **larger than the ambiguous/malformed response rates** in
  RESPONSE_QUALITY_REPORT.md (which top out at 3.8%). The dominant source of
  "unreliable" pairwise signal in this corpus is not garbled text -- it is
  genuine order-sensitivity in otherwise well-formed responses.

## Consequence for the `debias_position=True` combination rule

Because the combination rule (PARSER_AUDIT.md) resolves any forward/reverse
disagreement in favor of the first-shown document, and disagreement happens on
21-41% of pairs depending on provider/dataset, a substantial fraction of the
"debiased" Cohere/Azure preference edges in the *existing* cached judgments
(`llm_cache/*/llm_pairwise_judgments.jsonl`, which is what `llm_call_records
.jsonl`'s `parsed_scores`/`parsed_ranking` and `llm_{provider}_pairwise`
method outputs are built from) are not the outcome of a genuine 2/2 agreement
-- they are the fallback-to-first-document outcome. This audit's P1/P3
policies, which treat such disagreements as an abstain rather than a hidden
default, remove a large share of edges as a direct result (see
`pairs_excluded_fwd_rev_disagreement` in `policy_sensitivity_full.csv` and
POLICY_SENSITIVITY_REPORT.md).
