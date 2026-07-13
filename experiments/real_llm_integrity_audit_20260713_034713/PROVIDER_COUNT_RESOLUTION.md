# PROVIDER_COUNT_RESOLUTION

## The question as posed

> Determine exactly whether Cohere contributes 200 records, Azure contributes
> 200 records, or both providers together contribute 200 records.

## The short answer

**Neither, and the question's own premise needs correcting.** Both Cohere and
Azure each independently and fully cover all 200 query-regime slots (200 each,
not 100+100 and not "200 total split between them" -- see
`provider_record_counts.csv`). But **the 200-record repair/cyclicity/ΔnDCG
classification that the manuscript actually quotes numbers from ("repair is
inactive in all 62 `ms2` records and all 69 `ms1_drop_mutual` records; in
`ms1`, it yields one help case and one harm case among 69 records") uses
neither provider's judgments.** That classification is computed entirely from
the **mechanical** vote-regime preference graph (the same `bm25`/`tfidf`/
`minilm`-derived `ms1`/`ms2`/`ms1_drop_mutual` construction used throughout the
rest of the paper's main mechanical evaluation), before any LLM output is
attached to the record.

## How this was verified (code-level, not inference)

`scripts/run_failure_mining.py` (uncommitted, local-only; the producing script
for `reports/failure_mining_llm_v3/`), lines 243-284:

```python
for regime in active_regimes:
    vote_path = ensure_vote_file(dataset, ds_work, regime, score_files, ...)
    pairwise_index = _load_pairwise_preference_file(vote_path)   # <- mechanical
    for qid in query_ids:
        prefs = _restrict_prefs(pairwise_index.get(qid, []), args.max_candidates)  # <- mechanical
        record = process_query_record(..., prefs=prefs, ...)      # <- graph, cyclicity,
                                                                     #    repair, markov_graph
                                                                     #    vs markov_graph_repaired,
                                                                     #    failure_labels all
                                                                     #    computed HERE, from
                                                                     #    `prefs` above
```

LLM output is attached **only afterward**, lines 288-311, as an extra ranking
column bolted onto the already-built record:

```python
if llm_runner and provider_list != ["none"]:
    for prov in provider_list:
        llm_out = llm_runner.run_pairwise_rerank(provider=prov, ...)
        if llm_out:
            method_name = f"llm_{prov}_pairwise"
            record["method_outputs"][method_name] = {"ranking": llm_out["ranking"], ...}
```

Confirmed empirically against the actual stored data
(`reports/failure_mining_llm_v3/query_level_full_records.jsonl`, 200 records):

- Every record has `method_outputs["markov_graph"]` and
  `method_outputs["markov_graph_repaired"]` (200/200) -- these are the pair the
  manuscript's help/harm/inactive language describes, and they are computed
  from `prefs`, which is the mechanical `pairwise_index`, never from an LLM
  call.
- Every record **also** has `method_outputs["llm_cohere_pairwise"]` (200/200)
  and `method_outputs["llm_azure_pairwise"]` (200/200) -- a same-record,
  additional ranking method, added after `process_query_record()` already
  returned.
- `record["failure_labels"]` (the source of the help/harm/inactive
  classification) is computed **inside** `process_query_record()`, i.e.
  *before* the `llm_{provider}_pairwise` methods are attached, and is never
  recomputed afterward. It is therefore structurally impossible for it to
  depend on either provider's judgments in this corpus.
- The `ms1`/`ms2`/`ms1_drop_mutual` regime names refer to the mechanical
  vote-construction protocol's minimum-support threshold
  (`VOTE_REGIMES = ("ms1", "ms2", "ms1_drop_mutual")`,
  `src/consistency_ranker/failure_mining/data_setup.py`), not to any provider
  or LLM concept.
- Directly measured: mechanical-graph cyclicity is regime-determined and
  provider-independent -- `ms1` is highly cyclic (68-84% across the three
  datasets), `ms2` is 0% cyclic, `ms1_drop_mutual` is near-0% (1-4%), for
  every dataset, regardless of which/whether an LLM provider's output is
  attached to the same record. See `provider_record_counts.csv` and the
  cyclicity table in CYCLICITY_SOURCE_AUDIT.md.

## What Cohere and Azure's judgments actually measure in this corpus

Each provider's `llm_{provider}_pairwise` ranking is one more entrant in the
per-query "which method beats `markov_graph_repaired`'s nDCG" comparison used
for `failure_mining_summary.md`'s "which external baselines most often beat
our method" table -- but even there, `llm_cohere_pairwise`/`llm_azure_pairwise`
are **not** included in `failure_labels`'s `loses_to_*` fields or in
`best_external_baseline`, because (as above) `failure_labels` is finalized
before they're attached. They are pure post-hoc reporting columns in this
version of the pipeline; nothing about "does repair help/harm/stay inactive"
in the current stored output is a function of them.

To give the "what would repair look like if the preference graph were
actually built from Cohere/Azure judgments" question a real, computed answer
(since the manuscript's framing implies this was measured), this audit
additionally built genuine Cohere-only and Azure-only preference graphs
directly from the raw pairwise judgments and ran them through the *same*
`process_query_record()` repair/cyclicity/nDCG pipeline. See
`policy_P0_current_parser/query_level_results.csv` and
POLICY_SENSITIVITY_REPORT.md -- this is new analysis performed by this audit,
not a re-derivation of an existing manuscript number, and it should not be
conflated with the manuscript's current "62/69/69" claim.

## Exact manuscript sentence(s) that must change

1. Limitations section (`main.tex`, "Real-LLM scale" paragraph):
   > "We also analyze a separate 200-record multi-provider failure-mining
   > corpus with Cohere/Azure judgments and BRIGHT coverage, but that corpus
   > uses a different method pair, query sample, and protocol."

   This sentence is misleading by omission: it implies the 200-record corpus's
   repair/cyclicity result is *derived from* Cohere/Azure judgments (merely
   using "a different method pair" than the main pipeline). In the stored
   pipeline, Cohere/Azure judgments play **no role at all** in that corpus's
   repair/cyclicity/help/harm numbers. See MANUSCRIPT_PATCH_RECOMMENDATIONS.md
   for exact replacement text.

2. Real-LLM Evidence subsection (`sec:real-llm-scope`):
   > "Across its 200 query-regime records, repair is inactive in all 62 `ms2`
   > records and all 69 `ms1_drop_mutual` records; in `ms1`, it yields one help
   > case and one harm case among 69 records."

   The 62/69/69/help=1/harm=1 numbers themselves are reproducible and correct
   (independently re-derived by this audit from the stored mechanical
   `markov_graph`/`markov_graph_repaired` fields -- see VALIDATION_CHECKS.md).
   What is wrong is the surrounding framing that attributes this result to
   "Cohere/Azure pairwise judgments" via the preceding sentence and the
   `tab:llm-config` table row descriptions ("Protocol-distinct corroborative
   corpus on FiQA, HotpotQA, and BRIGHT" for each of Cohere and Azure,
   describing the *whole* 200-record analysis as if it were their corpus).

3. Table `tab:llm-config` Cohere/Azure rows describe "Pairwise ... corpus" as
   the role, with no indication that the pairwise judgments are a
   post-hoc auxiliary ranking column rather than the graph-construction input
   for the reported repair statistics.
