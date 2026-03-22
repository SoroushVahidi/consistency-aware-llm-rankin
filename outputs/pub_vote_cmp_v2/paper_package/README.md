# Publication evidence (SciDocs & HotpotQA, vote constructions ms2 / ms1 / ms1_drop_mutual)

Artifacts in this directory are **manuscript-facing** summaries of runs under
`outputs/pub_vote_cmp_v2/` (large score/vote/per-query CSVs are gitignored).

**Regenerate**

```bash
python scripts/run_publication_vote_suite.py --root outputs/pub_vote_cmp_v2
python scripts/build_paper_evidence_package.py --root outputs/pub_vote_cmp_v2
```

See `MANUSCRIPT_SUMMARY.md` for interpretation.
