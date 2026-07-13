# CYCLICITY_SOURCE_AUDIT

Two separate graphs are in scope, and they must not be conflated (see
PROVIDER_COUNT_RESOLUTION.md):

## 1. The manuscript's actual 200-record graph (mechanical)

`reports/failure_mining_llm_v3/query_level_full_records.jsonl`'s
`markov_graph`/`markov_graph_repaired` pair -- the one the "62/69/69" numbers
describe -- is built entirely from mechanical `bm25`/`tfidf`/`minilm`-derived
vote regimes. **0% of its cyclicity is attributable to any LLM response
(valid, fallback, or ambiguous)**, because no LLM response ever enters this
graph's edge set. Its cyclicity is determined entirely by the vote-regime
protocol:

| Dataset | Regime | n | Cyclic | Cyclic % |
|---|---|---|---|---|
| fiqa | ms1 | 25 | 21 | 84.0% |
| fiqa | ms2 | 23 | 0 | 0.0% |
| fiqa | ms1_drop_mutual | 25 | 1 | 4.0% |
| hotpotqa | ms1 | 19 | 13 | 68.4% |
| hotpotqa | ms2 | 19 | 0 | 0.0% |
| hotpotqa | ms1_drop_mutual | 19 | 0 | 0.0% |
| bright | ms1 | 25 | 19 | 76.0% |
| bright | ms2 | 20 | 0 | 0.0% |
| bright | ms1_drop_mutual | 25 | 1 | 4.0% |

`ms1` (minimum support 1 -- a single ranker's disagreement is enough to
create an edge) is highly cyclic everywhere; `ms2` (requires 2-ranker
agreement) is never cyclic; `ms1_drop_mutual` is near-never cyclic. This
pattern is identical regardless of which (or whether any) LLM provider's
output happens to be attached to the same record, which is the direct,
measured confirmation that provider/LLM-response-quality plays no causal role
in this graph's cyclicity.

## 2. This audit's newly-constructed LLM-only graphs (Cohere-only, Azure-only)

For the graphs this audit built directly from raw LLM judgments
(POLICY_SENSITIVITY_REPORT.md), cyclicity **is** attributable to response
quality, and the P0->P2 policy contrast isolates how much:

| Provider | Dataset | P0 cyclic % (incl. fallback + disagreement defaults) | P2 cyclic % (fallback + disagreement discarded) | Cyclicity attributable to fallback/disagreement-defaulted edges |
|---|---|---|---|---|
| azure | bright | 30.9% | 0.0% | 30.9 pts (100% of it) |
| azure | fiqa | 50.7% | 4.1% | 46.6 pts (92%) |
| azure | hotpotqa | 57.9% | 5.3% | 52.6 pts (91%) |
| cohere | bright | 32.4% | 0.0% | 32.4 pts (100%) |
| cohere | fiqa | 61.6% | 0.0% | 61.6 pts (100%) |
| cohere | hotpotqa | 57.9% | 0.0% | 57.9 pts (100%) |

**91-100% of the cyclicity observed in a graph built directly from these
LLM judgments disappears once fallback-defaulted and forward/reverse-
disagreement-defaulted edges are removed.** In other words: almost none of
the apparent intransitivity in the raw LLM-judgment graphs reflects genuine,
independently-confirmed intransitive preferences by the model; it is
overwhelmingly an artifact of (a) the parser's silent default-to-`"A"` on
unparseable responses and (b) the debias combination rule's silent
default-to-first-shown-document on forward/reverse disagreement. This is
consistent with, and quantifies, the position-bias and forward/reverse
findings in POSITION_BIAS_REPORT.md and FORWARD_REVERSE_REPORT.md.

## Implication

If a future manuscript revision wants to report cyclicity/repair statistics
computed *from* Cohere/Azure judgments (rather than the mechanical graph the
current 62/69/69 numbers actually use), the P0 numbers in that hypothetical
analysis would be substantially inflated relative to what a cleanly-parsed,
order-consistent version of the same judgments would show. This is
independent of, and does not affect, the manuscript's current mechanical-graph
numbers, which need no correction on cyclicity grounds.
