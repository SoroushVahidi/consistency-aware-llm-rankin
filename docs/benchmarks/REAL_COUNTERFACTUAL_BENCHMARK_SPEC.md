# Real Counterfactual Benchmark Specification

Status: **design only** (not executed in the provider-capability audit).
Companion audit: `scripts/audit_provider_capabilities.py`
Cost planner (offline): `scripts/estimate_counterfactual_benchmark_cost.py`

This document defines a gold-core pilot for measuring acquisition-policy and
provider choice on **real** IR queries under matched candidate pools and
budgets. It deliberately separates connectivity smokes from ranking science.

## Core scientific question

For the same real IR query, candidate pool, pairwise evidence opportunity, and
budget:

1. which acquisition policy performs best on qrels-based ranking metrics;
2. which provider/model should judge each selected pair;
3. whether a cheaper policy/provider policy is noninferior to a strong default;
4. whether safe routing can capture part of the oracle pair–provider gap.

Production always-UHT defaults and learned routing are **out of scope** for
the pilot collector until a separate decision freezes them.

## Gold-core pilot (first collection)

Datasets:

- SciDocs
- FiQA
- HotpotQA
- BRIGHT

Pilot scale:

| Knob | Value |
|---|---|
| Queries / dataset | 8–10 |
| Candidate pool size \(P\) | 10 |
| Evaluation cutoff \(k\) | 5 (\(k < P\)) |
| Provider/model families | 4 (one principal model each) |
| Presentation orders | A/B and B/A |
| Repeats | 2 only on a small instability subset |
| Budgets | 2, 4, 6, 8 |
| Fixed policies | 6 |

Do **not** collect a complete pair×provider×orientation matrix for the pilot.
Use a **logged acquisition shell** (selected pairs under a behavior policy) and
replay other policies offline where judgments exist.

## Pair–provider action space

An action is:

```text
(document_i, document_j, provider_model)
```

A future acquisition policy may choose:

- which unordered pair to query;
- which provider/model judges it;
- whether to confirm (second orientation / repeat);
- whether to escalate to a stronger model;
- whether to stop.

## Required baselines

- prior-only
- RRF
- CombSUM
- production UHT
- factorial UHT
- CHALLENGER
- HYBRID
- ROBUST_COMBINED
- random pair selection
- uncertainty-based acquisition
- one top-k bandit baseline
- provider-native reranking where available
- best fixed provider
- best fixed policy
- oracle pair–policy–provider action (upper bound on the logged shell)

## Benchmark record schema (trajectory level)

Each step should record:

- query identity and dataset;
- candidate-pool ID and candidate IDs;
- candidate text hashes (not necessarily full text in frozen packages);
- prior ranking and scores;
- available actions;
- selected pair and provider/model;
- behavior-policy propensity where applicable;
- observed judgment (normalized preference + parse status + response hash);
- graph state summary;
- calls used and remaining budget;
- ranking after the step;
- stopping reason (terminal);
- qrels-based outcomes (**after** execution only);
- modeled cost and latency;
- configuration and provenance (git commit, prompt hash, fixture/pool hash).

## Replay protocols

1. **Frozen-judgment replay** — deterministic reuse of logged normalized judgments.
2. **Stochastic replay** — sample from repeated judgments on the instability subset.
3. **Sparse logged-policy OPE** — off-policy evaluation using recorded propensities.

## Metrics (keep separate)

Retrieval quality: nDCG@k, MRR, recall@k.
Cost: calls, tokens, latency, modeled monetary cost (prices never invented).
Opportunity: regret to oracle, oracle-gap captured.
Reliability: provider disagreement, position sensitivity, degradation probability.
Process: intervention coverage, safeguard execution, noninferiority tests.

## Validity requirements

- qrels used only after execution / for offline evaluation;
- identical candidate pools within a matched policy cell;
- \(P > k\) so top-k set Jaccard is informative when used;
- never present full-pool Jaccard as ranking agreement;
- no missing-qrels coercion to zero utility without an explicit missingness flag;
- query-grouped splits;
- leave-one-dataset-out and leave-one-provider-out evaluation plans;
- record both provider and underlying model/deployment identity;
- explicit missingness; show denominators on every aggregate;
- cost-only improvements must not be described as quality wins.

## Relation to existing modules

Reuse rather than duplicate:

- `multi_provider_eval` — provenance store, orientation aggregation, spending ceilings;
- `provider_capability` — bounded live ledger, smoke schema, sanitization;
- `multifactor_acquisition` / `adaptive_acquisition` / `prior_robust` — policies;
- multifactor evaluation contract — qrels post-hoc metrics;
- experiment manifests / artifact policy — portable provenance.

## What tonight does **not** do

- full benchmark collection;
- selector training;
- production default changes;
- paid batch jobs;
- uploading real corpus text beyond the tiny public synthetic smoke fixture.
