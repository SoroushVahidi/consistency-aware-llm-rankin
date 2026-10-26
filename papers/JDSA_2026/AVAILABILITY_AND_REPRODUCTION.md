# Availability and reproduction boundaries

The project code URL is https://github.com/SoroushVahidi/consistency-aware-llm-rankin. It remains **PRIVATE** (authenticated metadata); an unauthenticated GET returns 404. MIT licensing of original code is not public access or clearance of the repository's confidential history. No visibility change occurred.

The detailed [resource and claim matrix](RESOURCE_PROVENANCE_MATRIX.md) covers original/converted datasets, original and adapted code, models, derived outputs, source versions, access evidence, all central tables/figures and reconstruction limits. [Permissions](PERMISSIONS_AND_RESOURCE_RIGHTS.md) distinguishes verified notices from pending source/provider applicability. The copy-ready manuscript declaration and Online Resource 1 follow these limits.

Public resources already published, without creating another publication:

- [Consistency-Aware Judgments v1, scientific revision f9317638ca1cc422661f704168335576d36ca995](https://huggingface.co/datasets/SoroushVahidi/consistency-aware-judgments/tree/f9317638ca1cc422661f704168335576d36ca995): four heterogeneous record classes, 56,332 records; author Soroush Vahidi; recorded CC BY-SA 4.0 in the pinned card/CFF. Not a query count or complete current experiment input. Excludes FiQA, Cohere, source text and October prospective responses.
- [Ranking-pool nDCG outputs, revision 4d6d9d372c24e541875990923ab5569454b6b44b](https://huggingface.co/datasets/SoroushVahidi/ranking-pool-ndcg-results/tree/4d6d9d372c24e541875990923ab5569454b6b44b): 93,504 author-derived numeric measurements, 342 query identities, 66 configurations, 1,056 summary rows; CC BY 4.0 results/MIT original validation code. This separate release provides processed-output checks, not a full reconstruction of this paper.
- [Related MWFAS metrics](https://huggingface.co/datasets/SoroushVahidi/mwfas-heuristic-metrics/tree/5b6cd5620ca0a1c9b3be5e8d996bf8e3c467e79f) and [extension](https://huggingface.co/datasets/SoroushVahidi/mwfas-benchmark-extension/tree/117cd82e5b863238377c5effe7430ce771062cf4): existing structural research lineage, not additional retrieval observations.

Every pinned resource above returns HTTP 200 without authentication; scientific revisions, card metadata and redirects are recorded in `audit/RESOURCE_ACCESS_20261026.json`. The [earlier retrieval preprint](https://doi.org/10.21203/rs.3.rs-9335700/v1) and [published ranking algorithm](https://doi.org/10.1007/s11227-026-08852-4) remain prior disclosures. No dataset DOI was established from the inspected records, and no DOI is invented.

Public ranking-output check: download the pinned release files into a separate directory, keep the Hub's `.gitattributes` transport file outside that directory (it is not part of the release checksum ledger), and run `python3 validation/validate_public.py`. The unmodified validator passes with 21 release files, 20 checksummed payloads, 93,504 comparison rows and 1,056 stored means. A literal full Hub checkout fails membership because of that extra transport file; the adjustment and successful result are recorded in `audit/PUBLIC_RANKING_VALIDATION_20261026.json`. It does not recompute original nDCG from qrels/rankings or reproduce corrected35 inference.

Confidential executable evidence: `packages/JDSA_Confidential_Processed_Evidence.zip`, SHA-256 `c31fff08567d3fc0504e0a303a2328067175b8820541746588c30cfee484f7b3`, is the exact byte copy of the prior **final** 35-file reviewer archive, not the older `anonymous_supporting_evidence.zip`. The prior guide conflated those names. The selected final archive excludes raw/provider text, qrels, full permutations, complete envelope inputs, third-party implementations and model weights. It remains ignored and local; no public hosting is claimed. See [reviewer access instructions](REVIEWER_ACCESS.md) for commands and delivery **PENDING** through a confirmed non-public journal attachment category.

Fresh isolated execution independently reproduces all 35 corrected comparisons from 34,783 paired processed observations, with 342/290 query units, zero Holm rejections and maximum numerical reference difference 0.0. Direct graph checks confirm 1,025 records split 646/379 and saved greedy feasibility/cost. Python 3.12.3/NumPy 2.3.5 were used; the quick check is standard-library only. No GPU, optimizer, external corpus, API credentials or network connection is needed after dependency provisioning. No research experiment is rerun. Other families' saved p-values and exact statuses are preservation checks, not fresh statistical inference or optimality certificates.

Not currently reconstructible from public resources or the final review copy: original historical ranking/scoring, selected-cache grade-profile attribution and complete six-graph optimum-envelope generation. Some records exist privately but are excluded for source/provider rights; other historical revisions/conversions are incompletely pinned. The displayed saved evidence and complete-input reconstruction are different verification levels.

Document reproduction: the authoritative scientific snapshot is `53083f31a2f698ecc29ba284f8eb7d070567aefd`; use this PR's final commit for the JDSA editorial sources. Install TeX Live with pdfLaTeX, BibTeX, TikZ, algorithmicx, booktabs/tabularx, seqsplit and xurl. Run:

```sh
bash papers/JDSA_2026/manuscript/build.sh
python papers/JDSA_2026/scripts/package_sources.py
python papers/JDSA_2026/scripts/validate_package.py
```

The source archive's `build.sh` produces equivalent identified and anonymous PDFs after extraction. Packaging editorial artifacts requires the separately prepared ignored `editorial/` files; ordinary manuscript builds and validation do not require experiment inputs. Full code installation (`pip install -e '.[exact]'`) is unnecessary for document or reviewer checks. Historical `docs/REPRODUCTION_CANONICAL.md` describes a narrower score-derived program and does not override the corrected estimand or current input-access limits.
