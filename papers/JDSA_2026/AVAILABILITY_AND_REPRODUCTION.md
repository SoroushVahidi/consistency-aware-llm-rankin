# Availability and reproduction boundaries

The manuscript statements in `manuscript/declarations.tex` and Online Resource 1 are the copy-ready availability text. They do not claim public project code. Unauthenticated repository GET returns 404; authenticated GitHub metadata confirms PRIVATE and ADMIN capability.

| Resource | Access verified | What it supports / boundary |
|---|---|---|
| SciDocs: https://github.com/allenai/scidocs | Unauthenticated 200 | Original benchmark entry point; cited SPECTER paper. Hosted BEIR snapshots used for newer cohorts. |
| FiQA: https://huggingface.co/datasets/BeIR/fiqa | Unauthenticated 200 | BEIR snapshot; original FiQA source rights still apply. |
| HotpotQA: https://hotpotqa.github.io/ | Unauthenticated 200 | Original QA dataset; historical retrieval conversion incompletely pinned. |
| BRIGHT: https://huggingface.co/datasets/xlangai/BRIGHT | Unauthenticated 200 | Official retrieval benchmark; exclusions and positive-ID contracts retained. |
| Consistency-Aware Judgments v1, scientific revision `f9317638ca1cc422661f704168335576d36ca995` | Unauthenticated pinned tree 200 | 56,332 heterogeneous records, not query count. Recorded CC BY-SA 4.0, Soroush Vahidi attribution. Excludes FiQA, Cohere, benchmark text and October prospective responses. |
| Ranking-pool nDCG results | Unauthenticated 200 | Existing derived ranking-output resource; not new retrieval observations or complete raw-input reconstruction. |
| MWFAS heuristic metrics / benchmark extension | Unauthenticated 200 | Separate structural research lineage; not additional retrieval evidence in this paper. |
| Project repository | PRIVATE; unauthenticated 404 | Code itself is MIT-licensed at repository root; licensing does not clear third-party or confidential contents of its history. |
| Existing confidential reviewer package | Local, not publicly hosted | 35 files, SHA256 `c31fff08567d3fc0504e0a303a2328067175b8820541746588c30cfee484f7b3`; independent Level 2 saved-observation inference and structural checks previously completed. No new rerun here. |

Original reviewer package remains in the prior worktree at `papers/IJIT_2026/packages/anonymous_supporting_evidence.zip`; it is neither bundled into the public-safe JDSA source archives nor uploaded. Its existing anonymity is retained for the fallback. It excludes raw qrels, full historical permutations, source responses and complete six-graph inputs. A local file path is not reviewer access; confidential routing is unresolved. Source evidence is mapped by the preserved original audit and `audit/SAVED_INVARIANTS.json`.

Versioned manuscript build: use this JDSA branch's final commit; original scientific source snapshot commit is `53083f31a2f698ecc29ba284f8eb7d070567aefd`. Install a TeX Live environment with pdfLaTeX, BibTeX, TikZ, algorithmicx, booktabs/tabularx and xurl. From repository root, run `bash papers/JDSA_2026/manuscript/build.sh`; then `python papers/JDSA_2026/scripts/validate_package.py`. These commands build/check documents only. Run the flat source archive's `build.sh` after extraction for equivalent editable-source builds.

For code installation, existing project instructions are `python -m venv .venv`, activate it, and `pip install -e '.[exact]'` for the canonical SCIP backend; recorded canonical PySCIPOpt is 6.2.1/SCIP 10.0.2. See `docs/REPRODUCTION_CANONICAL.md` for historical score-derived contracts, and current evidence index for later cohorts. Do not execute experiment/provider drivers merely to build documents. A public code checkout alone cannot reconstruct all present findings; historic instructions and old row-based statistics are superseded only for the explicitly corrected family.

The saved paired inputs, model pins, corpus pins and recorded source checksums distinguish verification of processed findings from end-to-end reconstruction. Restricted provider/source material remains withheld until rights are established. Useful derived graphs/tables require item-specific clearance; an available file or an MIT project license is not sufficient proof of redistribution rights.
