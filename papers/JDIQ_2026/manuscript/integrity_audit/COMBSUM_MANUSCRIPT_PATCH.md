# CombSUM Manuscript Patch (Recommendations Only — Not Applied to `main.tex`)

**Prepared:** 2026-07-12
**Scope:** Part B4. Per task instructions, `main.tex` and `references.bib` are **not** edited in this audit. This document specifies exactly what should be changed in a future drafting pass.

---

## Exact BibTeX entry to add to `references.bib`

```bibtex
@inproceedings{fox1994combination,
  author    = {Fox, Edward A. and Shaw, Joseph A.},
  title     = {Combination of Multiple Searches},
  booktitle = {The Second Text REtrieval Conference (TREC-2)},
  editor    = {Harman, Donna K.},
  series    = {NIST Special Publication},
  number    = {500-215},
  pages     = {243--252},
  year      = {1994},
  publisher = {National Institute of Standards and Technology},
  address   = {Gaithersburg, MD, USA},
  url       = {https://trec.nist.gov/pubs/trec2/papers/txt/23.txt}
}
```

Source and verification: `COMBSUM_REFERENCE_VERIFICATION.md`.

---

## Exact sentence for §3 Methodology (Baselines subsection, or wherever CombSUM is first defined)

Replace the current placeholder wording (the `TODO` comment in `main.tex` §4.3) with:

> CombSUM~\cite{fox1994combination} fuses per-ranker scores by summing a per-(query, ranker) min--max normalization of each ranker's score to $[0,1]$; this normalization is an adaptation required by this study's heterogeneous ranker scales (BM25, TF-IDF, a neural cross-encoder) and is not part of Fox and Shaw's original 1994 definition, which we note explicitly rather than presenting as an unmodified reproduction.

This sentence: (a) cites the verified primary source, (b) states the exact formula class (sum of normalized scores), (c) discloses the normalization as an adaptation, matching the same disclosure discipline already used elsewhere in this manuscript (e.g., the BEW/PIC circularity caveat in §3.3) and matching the sibling `minimum-weighted-fas-heuristics` repository's own convention for flagging adapted (not original) baselines.

## Exact sentence for §4 Experimental Setup (where CombSUM currently has a `TODO`)

Replace:

```latex
repair at all: reciprocal rank fusion~\cite{cormack2009rrf}, CombSUM
% TODO(manuscript-authors): CombSUM's original citation ...
(min--max normalized score summation across rankers), a Borda-count
```

with:

```latex
repair at all: reciprocal rank fusion~\cite{cormack2009rrf}, CombSUM~\cite{fox1994combination}
(min--max normalized score summation across rankers; see Section~\ref{sec:baselines}
for the normalization detail), a Borda-count
```

(i.e., simply attach `\cite{fox1994combination}` where the `TODO` comment currently sits, and remove the comment — no other wording change is required, since the surrounding sentence already correctly describes "min–max normalized score summation across rankers.")

## Exact Table 3 row text

Current Table 3 (`tab:baselines`) row:

```
CombSUM & No & --- \\
```

No change to the table row itself is needed — the citation belongs in prose, not in the table, consistent with how RRF and the other baselines are handled in the same table (none of the table's rows carry inline citations). Recommend only adding a table footnote if the editors want normalization details visible at the table level:

```latex
% Optional footnote, if desired:
\footnotetext{CombSUM uses min--max per-(query, ranker) normalization before summation; see Section~\ref{sec:baselines}.}
```

This is optional, not required — the prose sentence above already carries this information once.

## Caveats to preserve when writing Results (§6, not yet drafted)

From `combsum_protocol_alignment.csv`:

1. **CombSUM's score is regime-invariant by construction** (no graph/regime input in the code). When Results reports CombSUM's pooled mean nDCG and CI (e.g., the pooled row `combsum,1020,0.4621594872777186,...`), it should note that the "1,020" denominator triple-counts most underlying queries three times (once per regime label) with numerically identical CombSUM scores, which is arithmetically harmless for the *mean* but may understate CombSUM's *bootstrap CI width* relative to a true 340-ish-independent-query sample. This is a minor statistical footnote, not a validity threat to the ranking comparison (CombSUM vs. RRF vs. repaired Copeland), since every other pooled method is measured under the identical protocol.
2. **FiQA (n=359) and BRIGHT (n=145) are not exact multiples of 3** in the pooled corpus, unlike SciDocs (360) and HotpotQA (156). The root cause was not traced in this session (see `combsum_protocol_alignment.csv` notes); if Results discusses per-dataset CombSUM counts specifically, this should either be explained or simply reported as-is without implying a clean 3x-regime structure for every dataset.
3. **Do not conflate the pooled failure-mining corpus's BRIGHT count (145) with the vote-suite package's BRIGHT count (134 = 34+50+50, Table 2)** — they are different query populations under different eligibility rules, a distinction `main.tex` §4.3 already discloses in general terms; this note only makes the BRIGHT-specific numbers concrete for whoever writes Results.

## Baseline naming: "CombSUM" or a qualified variant name?

**Recommendation: keep the name "CombSUM"** in running prose and table labels (do not rename it to "min-max CombSUM" or similar), because: (a) the fusion *rule* (sum of per-ranker contributions) is unmodified from Fox & Shaw; only the *normalization step feeding into it* is adapted, which is a common and expected adaptation for cross-source score fusion, not a different algorithm; (b) the sibling repository's own convention (`docs/baselines_and_datasets_references.md`) reserves an explicit renamed/qualified label ("a weighted adaptation of Eades (1993)") only for cases where the *core scoring rule itself* was changed, not merely its input normalization — CombSUM's case here is the milder one. The one-sentence disclosure in §3 Methodology (above) is sufficient; renaming the baseline would overstate how much was changed.
