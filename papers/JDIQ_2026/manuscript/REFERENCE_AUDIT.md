# Reference and Citation Audit

**Prepared:** 2026-07-12
**Scope:** Every citation in `main.tex` checked against `references.bib`; every citation context checked for whether it supports the sentence it appears in; citation-group size checked; metadata checked for fabrication; stale keys checked; misuse (a reference cited for a method/claim it does not actually introduce) checked.

---

## Bibliographic completeness

- **16 entries in `references.bib`; 16 unique keys `\cite{}`-d in `main.tex`.** Verified programmatically this session: `cited - bib_keys = {}` (nothing cited is missing from the bibliography) and `bib_keys - cited = {}` (nothing in the bibliography goes unused). No orphaned entries, no missing entries.
- **Maximum citation-group size: 4** (`\cite{dwork2001rank,ailon2008aggregating,kenyon2007fewerrors,fagin2003comparing}`, in Background, on the sentence about prior FAS-based rank-aggregation work focusing on the algorithmic side of the problem). This is at, not over, the four-reference limit — compliant.
- **No stale citation keys remain.** `burges2010ranknet` and `su2025bright` were identified as incorrect in an earlier integrity pass and replaced with `burges2005learning` and `su2024bright` respectively; neither stale key appears anywhere in the current `main.tex` or `references.bib` (re-verified this session).

---

## Per-citation context check (does the citation support the sentence?)

| Key | Context | Supports sentence? |
|---|---|---|
| `liu2011learning`, `burges2005learning`, `sun-etal-2023-chatgpt`, `qin-etal-2024-large` | Introduction: rankers "operating in pointwise, pairwise, or listwise comparison modes... aggregated rather than as a final answer" | **Yes** — LTR textbook, original pairwise LTR paper, and two LLM-reranking papers directly support the claim that reranking spans classical and LLM-based paradigms |
| `dwork2001rank`, `ailon2008aggregating`, `negahban2017rankcentrality` | Background: preference graphs as "standard in rank aggregation and pairwise-comparison ranking" | **Yes** — all three are foundational rank-aggregation-from-pairwise-data papers |
| `ailon2008aggregating`, `kenyon2007fewerrors` | Background: FAS repair "producing a graph that is... more internally consistent" | **Yes** — both are FAS-based rank-aggregation papers |
| `dwork2001rank`, `ailon2008aggregating`, `kenyon2007fewerrors`, `fagin2003comparing` | Background: "prior work on feedback-arc-set-based ranking has focused on the algorithmic side" | **Yes** — all four are classical rank-aggregation/FAS-approximation papers, directly on-topic |
| `dwork2001rank`, `ailon2008aggregating` | Background: majority cycles in aggregated preferences, "the same structural phenomenon that produces majority cycles in social-choice aggregation" | **Yes** |
| `ailon2008aggregating`, `kenyon2007fewerrors` | Methodology: "classical in rank aggregation," FAS formulation | **Yes** |
| `ailon2008aggregating` (alone) | Methodology: "is NP-hard in general" (appears twice, Background and Methodology) | **Yes** — Ailon, Charikar, and Newman (2008) is exactly the paper establishing NP-hardness of weighted FAS on tournaments; a single, precise citation for a single, precise claim is correct practice, not under-citation |
| `cormack2009rrf` (four occurrences) | Methodology (candidate pooling, hybrid prior), Experimental Setup (rankers, baselines) | **Yes** — all four uses describe reciprocal rank fusion, which is exactly what this paper is |
| `cohan2020scidocs`, `maia2018fiqa`, `yang2018hotpotqa`, `su2024bright` | Introduction (dataset list) and Experimental Setup (per-dataset domain description) | **Yes** — each citation is placed immediately adjacent to its own dataset's name, not cross-attached to a different dataset |
| `thakur2021beir` | Experimental Setup: "SciDocs, FiQA, and HotpotQA additionally appear in the BEIR... benchmark suite" | **Yes** |
| `fox1994combination` | Experimental Setup: "CombSUM~\cite{fox1994combination}" | **Yes** — verified in a prior integrity-audit pass against the primary TREC-2 source itself |

**No citation was found supporting a claim it does not actually make, and no citation was found misattributed to the wrong method or dataset.**

---

## Metadata fabrication check

Re-inspected all 16 `references.bib` entries this session:

- No entry contains a DOI, page range, volume, or number that was not already present in either (a) the verified IJCS source bibliography (11 entries), or (b) an independently fetched primary source this workspace's integrity audit already performed (`burges2005learning`, `su2024bright`, `fox1994combination`, `cormack2009rrf`, `thakur2021beir`).
- `burges2005learning` has no `address` field (correctly left absent rather than guessed).
- `su2024bright` is an arXiv preprint and correctly carries `eprint`/`archivePrefix`/`primaryClass` fields rather than a fabricated DOI or page range.
- `thakur2021beir` is a NeurIPS Datasets and Benchmarks track paper and correctly has no `pages`/`publisher` fields (that venue does not assign them in the same way a proceedings volume does) rather than fabricated ones.
- `fox1994combination` correctly has no DOI (confirmed absent from the NIST catalog record, not merely omitted) and cites the stable NIST URL instead.

**No fabricated metadata found.**

---

## Technical reports / arXiv papers labeled accurately in prose?

- `su2024bright` (arXiv) is never described in the prose as peer-reviewed or as appearing in a specific proceedings venue; the text only ever writes "BRIGHT (reasoning-intensive retrieval)~\cite{su2024bright}," which makes no venue claim beyond what the citation itself carries. **Accurate.**
- No other bibliography entry is a technical report or preprint requiring a similar check (`burges2005learning` is a full ICML 2005 proceedings paper with a DOI, not a technical report — this is distinct from the earlier, now-removed `burges2010ranknet`, which *was* a Microsoft Research technical report).

---

## No speculative references added

No reference was added to `references.bib` in this revision pass purely to broaden the bibliography. The one reference added earlier in this workspace's history beyond the IJCS-inherited set (`fox1994combination`) was added because it was actually needed to correctly cite an existing claim (CombSUM), not to pad the reference count.

---

## Overall disposition

**No corrections required in this pass.** The reference list was already brought to a clean, fully verified state during the prior integrity-audit task (`integrity_audit/COMBSUM_REFERENCE_VERIFICATION.md`, `integrity_audit/EXTERNAL_SOLVER_IDENTITY.md`), and this session's independent re-check found no regressions, no new stale keys, no fabricated metadata, and no misattributed citations introduced by the intervening style-revision edits (Parts 1–6 of this task).
