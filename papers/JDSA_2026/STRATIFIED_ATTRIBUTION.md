# Descriptive selected-cache composition: reproducible procedure

This revision analyzes preserved observations, not new model outputs or newly optimized rankings. The population is exactly 213 selected dataset/query identities with two dependent branches each. It is separate from the canonical 342-query population, six-graph diagnostic and separately scheduled replication. No significance tests or new inferential family are introduced.

## Input and identity contract

Python 3.11+ standard library only. The original private source manifest contains 219 files: 213 task checkpoints, four frozen relevance maps, the original selection-metrics CSV and the original derivation script. All 219 hashes match. Every chosen checkpoint permutation, per-candidate grade, explicit-judgment flag and full-query ideal grade was checked against the recovered numeric projection. The original attribution CSV binds dataset/query, checkpoint hash, selection line and two branch records. The metadata linkage retains these original identities privately. No raw benchmark text or provider response is needed for this arithmetic.

The new input JSON has `schema: "selected-composition-inputs-v1"` and `units`. Each unit has the fields documented for `numeric-profile-inputs-v1` in OFFLINE_VERIFICATION.md, plus:

- `dataset`: exactly `scidocs`, `fiqa`, `bright` or `hotpotqa`.
- `query_id`: the original nonempty string within that dataset. Dataset/query pairs must be unique; anonymous numeric linkage keys must also be unique.
- `providers`: integer 2 or 4, reflecting saved provider availability, not randomized assignment.
- `cyclic`: Boolean from the saved pre-repair aggregate graph.

The complete `none`, `greedy` and `scip_exact` permutations, evaluation grades, judged mask and full-query ideal grades are required. Candidate positions are relabeled bijectively to query-local integers; original query identities remain in this enriched private projection. Missing labels are evaluation zeros; the judged mask preserves the distinction from explicit zero grades. Original saved differences use a `1e-12` zero tolerance. The separate reference JSON is a list of the original unit/repair attribution fields, not an input to reconstruction.

## Fixed descriptive groups and denominators

The script computes all-query, four dataset, two availability and two judged-positive-availability marginals, plus all 16 dataset × availability × judged-positive cells, including empty cells. Every cell reports both branches. Counts are distinct queries within one branch; the two branches and overlapping marginals must never be added as independent observations. `cyclic_positive` means cyclic and at least one judged-positive candidate. An empty or small cell is reported as such. The original selection rule is unchanged; there is no post-hoc favorable selection.

The mutually exclusive partition is: unchanged ranking; changed ranking/zero-positive pool/zero metric; changed ranking/positive pool/fixed profile/zero metric; changed ranking/positive pool/different profile/zero metric; metric changed. Utility signs further split changes into gains and harms. Different profiles with equal metrics remain a supported residual category, even though none occurs in these records. Unchanged metric is not semantic equivalence. No provider effect, dataset efficacy comparison or query-population prevalence is estimated causally.

## Run with authorized inputs only

From the repository root, using fresh private output directories:

```sh
python3 papers/JDSA_2026/scripts/stratify_selected_cache.py \
  --input /private/authorized/composition_inputs_PRIVATE.json \
  --reference /private/authorized/composition_references_PRIVATE.json \
  --output /private/new-composition-output \
  --render-dir /private/rendered-tables
python3 -m unittest discover -s papers/JDSA_2026/scripts \
  -p test_selected_composition.py -v
```

In the flat source ZIP, omit the `papers/JDSA_2026/scripts/` prefix and use `python3 -m unittest test_selected_composition -v`. The seven unit tests are explicitly synthetic software fixtures, not manuscript observations. They cover full-query normalization, profile invariance versus harm, zero-positive accounting, paired query denominators, empty cells, identity collisions and malformed/nonfinite inputs. The historical contract must fail on a mismatched population rather than forcing consistency.

The script writes `COMPUTED_BEFORE_REFERENCE.json` before opening reference classifications. `COMPOSITION_VALIDATION.json` contains the complete aggregate results and numerical-comparison receipt. `WORKED_EXAMPLE_IDENTITY_PRIVATE.json` preserves C1's original query linkage. All row-level outputs and input projections must remain private. `--render-dir` produces only the two aggregate TeX tables and a minimal derived observed-case narrative. Copying those files into the manuscript requires author review of the descriptive content; it does not authorize publication of inputs.

C1 is chosen among greedy positive-pool fixed-profile cases with all moved documents unjudged and at least one movement in the evaluated prefix. Minimize the number of moved positions, then sort dataset/query identity. This fixed illustrative selection is not random sampling or an efficacy endpoint. Its original identity and source hashes remain in the private linkage record. The public narrative exposes no raw text, provider response or full ranking.

## Verified findings and access limitation

Fresh reconstruction matches all 426 branch records / 6,816 reference fields with maximum absolute discrepancy `2.22e-16`. All marginal counts are additive and reproduce the original changed-rank/metric/gain/harm totals: greedy `180/37/15/22`; exact `160/25/16/9`. Dataset totals are `77/76/42/18`; availability totals `110/103`; positive/zero-positive pools `134/79`. The sanitized receipt is `audit/SCIENTIFIC_REVISION_EVIDENCE.json`.

Source ZIPs contain code, schemas, aggregate tables and the minimal derived case, not recovered inputs, original identities, relevance maps, complete permutations or model responses. Input sharing permissions and confidential reviewer delivery remain unresolved. A local reconstruction and a data-free script do not resolve M04 or M06. The unchanged 35-file reviewer archive still supports its existing processed-statistical workflows without these extra inputs.
