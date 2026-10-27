# Reproducibility-gap resolution — 26 October 2026

This follow-up checks the underlying preserved records. It does not treat an earlier audit's access limitation as proof that original inputs were lost. No research experiment, scorer/model inference, optimizer campaign or canonical-result overwrite was performed. The finalized scientific archive and 835 protected IJIT files remain authoritative and unchanged.

## Resolution by component

| Component | Recovered authentic evidence | Verification level now established | Remaining limit |
|---|---|---|---|
| A: historical BM25/TF-IDF/MiniLM scoring | All 12 saved score files; all four original canonical processed qrel files; all 12 canonical protocol manifests; existing graph/scalar records and historical scorer source object | **Independently verified processed-evidence provenance:** 36/36 score-to-manifest matches and 12/12 qrel-to-manifest matches | **Not reconstructed:** exact original scorer execution, immutable MiniLM weights/tokenizer, historical corpus export/conversion identity and unsaved exact-ranking permutations. No new scoring campaign substitutes for them. |
| B: selected-cache relevance-profile attribution | Complete 213 selected task checkpoints and branch permutations, four full frozen qrel maps, selection metrics, derivation source and source-line/hash linkage | **Reconstructed from processed evidence:** 426 branch records; all 6,816 reference fields agree; maximum numeric error 2.22e-16 | Original provider comparison and graph/repair generation are not regenerated. Numeric input projection is private pending sharing clearance. |
| C: complete six-graph optimum envelope | Six full weighted graphs, complete global relevance assignments, historical ranks/deletions, all alternative outputs, configuration, frozen implementation and checkpoints | **Fully reconstructed finite diagnostic conditional on authentic processed inputs:** 241,920 orders; all eight optimal repairs/rankings and all six ranges agree; maximum error 1.11e-16 | Historical judgments/corpus acquisition not regenerated. Original MIP termination/certificate records are saved checks, not new solver proofs. Projection remains private pending sharing clearance. |

The existing **35-file reviewer ZIP remains unchanged**: SHA-256 `c31fff08567d3fc0504e0a303a2328067175b8820541746588c30cfee484f7b3`. Its corrected35/statistical and canonical graph checks remain independently executable. Newly recovered components are not silently represented as included in that ZIP. No revised cleared reviewer package was created; no data were uploaded.

## A. Historical scoring and ranking generation

The canonical code consumes score exports at `experiments/method_improvement_audit_20260711_205733/inputs/<dataset>/scores_{bm25,tfidf,minilm}.jsonl`. Original protocol manifests reside in the preserved primary `primary_minmax_retention_matched` run, with score hashes, qrel hashes, thresholds, query rosters, source commit and exclusions. All three score hashes match each dataset's three regime manifests. Original canonical qrel files match the hashes retained in the final review package's `provenance/canonical_source_receipts.csv`.

| Dataset | Canonical processed-qrel SHA-256 |
|---|---|
| SciDocs | `a29baca79a3af24010bdd6e69301d6c3d6887bc3bccf036b05c495f203af234e` |
| FiQA | `1fa546a24a7e720952e690e11e29e0b71efc00225517527ebd2e8bb523673474` |
| HotpotQA | `666299b0bdbcc1f965267aa020bd8c5d001e4855ab3af5aa1e2f875d3ace2ef4` |
| BRIGHT | `3bd1961f79baa3212f9d275862344b67be21c73fd1066d3962f5544bab0237e7` |

The source scorer `scripts/generate_score_file.py` matches its historical Git object at canonical manifest commit `c8f6f41e656ecc552736f3f6154cf1c34a416043` (code SHA-256 `a7d726b4320ecda418a260c6b46a5640a1a5fc8b754f88459e4925380e13a0b3`). Its local lexical implementations use lowercase alphanumeric tokenization, title/newline/body text, BM25 k1=1.5/b=0.75 and its recorded cosine TF-IDF procedure. The MiniLM branch loads `sentence-transformers/all-MiniLM-L6-v2`, normalizes document/query embeddings and takes float32 dot products; no immutable model revision is supplied by that historical code. A later source commit does not prove the exact original execution tree or cached weight revision.

The primary protocol serializes 1,026 query--regime records. Direct roster comparison with the exact study identifies its single historically omitted empty graph; the exact study's 1,025-record population is unchanged. The source `query_records.jsonl` stores graph edges and scalar method metrics, not complete method ranking permutations. The exact-study driver constructs greedy/exact method rankings in memory and writes scalar paired metrics; full exact permutation output is not recovered. Regenerating rankings by newly solving or rerunning the pipeline would not recover the historical selected tied solutions.

Processed corpora/queries still exist locally, but their current presence does not retroactively establish original corpus export/conversion hashes. The newer BEIR pins are not substituted. Earlier `outputs/real_full/PROVENANCE.md` labels those different outputs as synthetic proxy data; they are explicitly excluded from reconstruction. The October replay's frozen qrel files are different byte projections and are not substituted for canonical qrel files.

Affected evidence: four-benchmark construction/scaling and canonical retrieval sections, main Tables 2/3 and Figures 2/3, SI canonical threshold/cost/retrieval/robustness contracts, and the original paired values feeding corrected35. Corrected35 inference already reconstructs from paired processed observations; hash recovery is not a new Level 1 score-generation reproduction.

## B. Relevance-profile attribution

Underlying source manifest SHA-256: `a37cd59cdce755d24c5ec3aa36288ad6c15eb44a079cea577aa5df0d715e6d16`. Its **219/219** file checks pass: 213 checkpoints, four frozen qrel maps, the original selection-metrics CSV and derivation code. The attribution CSV remains SHA-256 `b34a38ca0f5d6650c634737abfba68e98ecb7daaff34866f6db0b5a65f5c3b77`.

The original selection is reapplied to saved metrics: real-LLM CAAR, strict agreement, aggregate graph, fixed Copeland, unrepaired branch and no insertion-order seed. There are exactly 213 distinct dataset/query units. Checkpoint identity fields and original CSV source lines match. Each checkpoint contains the complete 15-document unrepaired, greedy and exact permutations. The full query qrel maps establish candidate grade, explicit-judgment status and full-query IDCG, including positives outside the pool.

The new data-free verifier `scripts/verify_relevance_profiles.py` independently recomputes document movements, top-ten membership, grade-sequence equality, full-query nDCG and attribution classes. It computes the zero-effect classification from reconstructed metrics, rather than trusting saved flags or deltas. Computed output is written before opening reference classifications. Every field in its 426-reference-record comparison agrees at tolerance 1e-12.

| Existing attribution outcome | Greedy | Exact |
|---|---:|---:|
| Unchanged complete ranking | 33 | 53 |
| Changed ranking, zero-positive pool | 69 | 61 |
| Changed ranking, positive pool, same evaluated top-ten profile | 74 | 74 |
| Changed measured metric | 37 | 25 |
| Equal-profile cases whose moved documents are all unjudged | 55 | 58 |
| Equal-profile cases with a moved positive document | 6 | 5 |

These are the unchanged existing scientific counts. Both branches share 213 queries; the two 74-case subsets are not 148 independent observations. Recovering the profile arithmetic does not make unjudged evaluation zeros true irrelevance or establish extractor-general/candidate-general repair efficacy.

Affected claims: abstract's 74-case statement; main relevance-profile subsection and Table 5, selected-cache portions of Table 2 and Discussion; SI cached-evidence attribution/movement narrative. The 6,816-field check also reproduces metric signs and saved values within floating-point tolerance. Source-to-integer projection mapping remains private; no benchmark text or raw provider response is needed for this numerical check.

## C. Six-graph complete optimum envelope

Complete original `inputs/graphs.json` remains SHA-256 `6714a107b6d80967264981d39b7778d27045871aac6a09433a78380d74f2a5a3`. The frozen manifest is `09ef717e34ae127653ef93d959ab454485a4d9067e039f50554701463e643881`; **42/42** frozen files, **22/22** staged inputs/original source copies and **18/18** order/MIP/result checkpoint hashes match. Each of six unit/qrel maps and historical selected rank/deletion records matches its original graph record. Original code, parameters, runtime record and dirty/orchestration provenance are retained; a Git commit alone is not represented as the full runtime tree.

The new data-free `scripts/verify_optimum_envelope.py` uses exact rational/scaled-integer weights and visits all six 8! order spaces. For positive costs, every optimum deletion set equals the backward-edge set of a retained-DAG topological order: otherwise removing only that backward set would cost less. Deduplicating optimum backward sets therefore finds all optima for these six positive-weight inputs. Zero-cost supersets would require additional enumeration; the verifier rejects such inputs rather than silently missing them.

Independently computed results:

- Six graphs; four have one optimum and two have two, giving **eight distinct optimal repairs**.
- One graph has varying utility; width **0.0060602693906083305**.
- Mean utility range **[0.8817498644543745, 0.8827599093528092]**.
- Mean improvement range **[0, 0.0010100448984347032]**.
- Every historical selected repair is utility-best within the complete optimum family; no query's minimum is below its unrepaired utility.

All deletion sets, induced fixed-Copeland rankings and metrics match saved evidence, with maximum error 1.11e-16. Expected optimum costs/sets are not optimization inputs. This is a complete finite processed-input reconstruction, not a rerun of historical provider judgments or a new MIP certificate. The independent deletion-MIP terminal statuses and 33 original fixture outcomes remain saved-output checks.

Affected claims: main optimum-choice subsection/Table 6 and its qualified conclusion, six-query ranking-response description, SI complete-optimum definitions and diagnostics. Original six-row utility CSV remains SHA-256 `359ee73fc1b48eb19d0a8ec0e6397704ee4d6d13c827acc3c36c5d2f8583b947`.

## Offline procedures, isolation and permission boundary

`OFFLINE_VERIFICATION.md` specifies both numeric input schemas and commands. Data-free verifiers/documentation are included in the flat manuscript source archive. Fresh isolated execution uses Python 3.12.3 and the standard library only, with no user-site/PYTHONPATH dependency. Both procedures exit 0; traces show **zero network connections and zero research-workspace reads**. Independent outputs are compared with originals only after computation. The original numerical results are not changed or overwritten.

The smallest sufficient projections replace original document identifiers with query-local integer labels, retain saved permutations/explicit-judgment distinctions, and supply candidate/full-ideal gains or grades. This removes text/transcripts and unnecessary identifiers, but does not itself license provider-derived graphs or transformed relevance annotations. Input distribution remains **CONDITIONAL**, separate from scientific reconstructibility. Until an applicable sharing basis is established, those projections stay private and are not added to the reviewer ZIP or Git. The public Catalyst publication guidance is assessed separately in `COHERE_PERMISSION_ASSESSMENT.md`.

The public HF resources continue to support their documented processed observations/output checks; they do not supply these recovered private complete-input projections. The exact unresolved step is sharing clearance followed by packaging and fresh validation of an authorized reviewer extension, not recovering data that are already present. A private test component is not a cleared publication or delivery artifact.

## Verification categories retained

- **Fully reconstructed:** the finite six-graph optimum/deletion/ranking/utility diagnostic from frozen processed graph and relevance inputs.
- **Independently verified from processed evidence:** all selected-cache attribution records/metric arithmetic, corrected35 inference, canonical graph checks and historical score/qrel hash linkage.
- **Saved-output checks only:** other historical p-values, original exact-solver/MIP statuses and fixture logs, and historical timing/certificate claims not rerun here.
- **Not reconstructible from recovered inputs without substituting a new execution:** exact original model-serving/scoring deployments, absent canonical historical exact permutations and unresolved original corpus conversion identities. No recreation using present corpora/models is represented as historical reproduction.

## Scientific revision: composition without expanded access claims

The new fixed descriptive composition reuses all 213 original selected query identities / 426 paired branch records and independently rechecks their arithmetic before reading reference classifications. All 219 original source hashes match. The enriched dataset/provider-availability/cyclicity linkage remains private; all original totals match and no additional testing family is created. STRATIFIED_ATTRIBUTION.md and audit/SCIENTIFIC_REVISION_EVIDENCE.json document code, schemas, counts, error tolerance and source identities. Only aggregate tables and a minimal derived observed example are added to the manuscript. This strengthens local verification but does not resolve central reviewer access, sharing permissions, exact historical model identity or the incomplete legacy preprint execution bridge. The earlier reviewer ZIP remains unchanged.
