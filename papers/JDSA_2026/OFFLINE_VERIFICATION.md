# Offline reconstruction procedures and input access

These two original standard-library verifiers accompany the manuscript sources. They are not new ranking methods. They contain no experimental payload, original identifiers, benchmark passages, provider transcripts or third-party implementation. The project MIT notice accompanies their source-archive copies as `LICENSE_VERIFICATION_CODE.txt`.

The recovered inputs remain private pending applicable sharing clearance. Their absence is intentional; the manuscript source ZIP alone cannot execute these checks. These scripts and privately validated numeric projections do not constitute a newly cleared reviewer-package release. The existing 35-file package is unchanged.

Use Python 3.11+ without external dependencies, from separate fresh input/output directories. Outputs must not already exist. Both procedures write computed results before opening expected scientific results. Verify the corresponding authorized input hashes before use.

## Selected-cache relevance attribution

```sh
python3 verify_relevance_profiles.py --input inputs/numeric_inputs.json \
  --reference inputs/references.json --output attribution_output
```

Input schema is a JSON object with `schema: "numeric-profile-inputs-v1"` and `units`. Each unit has:

- `unit`: anonymous unique linkage key; it is not an additional query.
- `grades`: evaluation grades indexed by query-local integer document index.
- `judged`: Boolean mask distinguishing explicit grades from unjudged evaluation zeros.
- `full_ideal_top10`: descending highest ten grades from the complete original query relevance map, including out-of-pool judgments.
- `rankings`: full permutations of all integer document indices under `none`, `greedy` and `scip_exact`.

The historical projection contains 213 units with 15 candidates each. Relabeling maps the original baseline order bijectively to integers and preserves all saved branch permutations. Reference records identify unit/repair and the saved classification/indicator/metric fields used by the verifier. No reference classification is used to compute a class. `COMPUTED_WITHOUT_REFERENCE.json` precedes reference checks. Validation reconstructs the 426 branch records, moved-document and top-ten membership/profile indicators, and full-query nDCG, without regenerating graph repair or model judgments. `VALIDATION.json` states comparison counts and tolerance.

## Six-graph optimum envelope

```sh
python3 verify_optimum_envelope.py --input inputs/numeric_inputs.json \
  --reference inputs/reference_results.json --output envelope_output
```

Input directory also contains `CHECKSUMS.json` binding `numeric_inputs.json` and `reference_results.json` to their SHA-256 hashes. Input is a list of six graph records with:

- `graph_id`, `nodes` (exactly eight), directed `edges` as `[u,v,positive_rational_weight]`.
- `candidate_gains`: original `2**grade - 1` values by integer node.
- `ideal_gains`: descending full-query ideal top-ten gains.
- `historical_removed_indices`: historical selected deletion set, used only after independently finding the optimum family.

Integer labels preserve the original lexicographic tie order. The verifier enumerates all 8! orders per graph, minimizes scaled-integer backward-edge cost, deduplicates optimal deletion sets, checks retained-DAG feasibility and reconstructs fixed unweighted Copeland rankings and nDCG. Strictly positive costs are required; zero-cost extra deletions would need a different enumeration and are rejected. Reference optimum costs/sets are opened only after `COMPUTED_BEFORE_REFERENCE.json` is written. Expected records contain optimum/utility extrema, counts and per-repair removed indices, ranks and utilities. `VERIFICATION.json` records numerical differences and scope.

This is complete finite reconstruction conditional on the authentic six processed graphs, metric inputs and fixed extraction. It neither recreates historical model serving nor establishes a fresh SCIP/MIP certificate. The original MIP status logs remain saved-evidence checks.

## Verified state and distribution boundary

Fresh isolated execution with Python 3.12.3, empty PYTHONPATH, isolated HOME and user site disabled reproduces attribution (6,816 comparisons, maximum error 2.22e-16) and envelope (241,920 orders, eight optimal repairs, maximum error 1.11e-16). File/network traces show zero network connections and no research-workspace reads. Exact original-source and projection mappings remain in private preservation records. The sanitized receipt and detailed limits are in `REPRODUCIBILITY_GAP_RESOLUTION.md` and `audit/RECOVERY_VERIFICATION_20261026.json`.

No public or unrestricted input license is inferred from removing text or relabeling identifiers. An applicable sharing basis and confirmed confidential delivery category are required before those projected inputs are added to a reviewer copy. The original 35-file package independently reproduces the corrected statistical family without these inputs.

## Scientific-revision composition analysis

A third data-free procedure, `stratify_selected_cache.py`, adds the fixed dataset × provider-availability × judged-positive descriptive decomposition. It reuses the original relevance-profile reconstruction, retains original query identities privately and requires an enriched projection. See STRATIFIED_ATTRIBUTION.md for the complete schema, commands, output dispositions, tests and access limits. The independent sample remains 213 queries, not 426 repair records. This procedure adds descriptive counts only; it does not rerun inference or generate rankings.
