# CYCLICITY_SOURCE_AUDIT

## Auditable portion

Observed cyclicity in the committed pairwise pilots is directly attributable to the accepted final pairwise judgment edges stored in `judgments.jsonl` and `judgment_cache/llm_pairwise_judgments.jsonl`.

## Unauditable source decomposition

- Contribution from exact one-letter responses: UNAUDITABLE for pairwise runs because raw texts are not preserved.
- Contribution from ambiguous responses: UNAUDITABLE for pairwise runs because raw texts are not preserved.
- Contribution from parser fallback-to-`A`: UNAUDITABLE because fallback events were not separately logged and raw texts are absent.
- Contribution from forward/reverse disagreement: UNAUDITABLE because the committed analyzed pairwise runs have `debias_position=false` and therefore no stored forward/reverse pairs.

## Practical conclusion

The current artifact snapshot supports measuring cyclicity outcomes, but it does not support a source-level decomposition of that cyclicity into exact, ambiguous, fallback-derived, or order-sensitive components.
