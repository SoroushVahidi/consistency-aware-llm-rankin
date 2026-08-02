# Experimental Presentation Strengthening Changelog

Date: 2026-08-02  
Branch: `papers/sncs-2026-foundation`  
Scope: experimental presentation, fairness framing, dataset realism,
statistical motivation, practical interpretation, threats to validity,
figure/table captions. **No numerical result, table body, figure data, or
claim classification changed.**

## Improvements

1. **Baseline roles** clarified in §Baselines: score sources vs graph-free
   fusion anchors vs unrepaired vs repaired extractors; explicit statement
   that omitted modern systems answer different questions.
2. **Base rankers** reframed as controlled heterogeneous substrates, not
   SOTA.
3. **Datasets** expanded with task/domain characterization, offline
   reranking setting, pool realism, and non-generality disclaimer; setup
   table caption tied to RQ2--RQ3.
4. **Fairness** stated after RQs: hold pool/scores/construction/extraction/
   cutoff; vary only repair.
5. **Statistics** motivated: paired design, sign-flip, Holm FWER, bootstrap
   CIs, BH/MDE/TOST as non-substitutes.
6. **Results** subsections each open with the scientific question (RQ1--RQ4
   / robustness / LLM pilot); captions linked to those questions.
7. **Practical implications** state when to evaluate repair, when not to
   treat structural metrics as utility surrogates, and diagnostic use of
   exact repair.
8. **External validity** covers score-derived graphs, shallow pools,
   missing modern baselines as future work / incomparable methods.

## Unchanged

- All table numeric cells and figure PDFs/PNG data
- Holm cell counts and p-values in prose
- `EVIDENCE_MAP.md`, `result_claims.yaml`, `docs/claim_evidence_registry.yaml`

## Compile

- Pages: 36 → 36 (briefly 37 during drafting; trimmed back)
- Approx. words: ~10,575 → ~10,508
- Clean `tectonic` build; no undefined citations
