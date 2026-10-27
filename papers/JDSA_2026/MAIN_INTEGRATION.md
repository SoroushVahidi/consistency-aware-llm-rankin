# Canonical manuscript and supporting PDF policy

> This is the historical main-integration record and its original PDF identity. A later [readiness audit](FINAL_SUBMISSION_READINESS_AUDIT.md) makes narrowly documented prose/presentation corrections in its own draft branch; `audit/FINAL_READINESS_MANIFEST.json` pins that branch's current PDF without changing scientific results.

The authoritative compiled document is [LATEST_MANUSCRIPT.pdf](../../LATEST_MANUSCRIPT.pdf) at repository root. It is the exact 20-page identified main PDF from scientific revision `af03da5900e61a3683de352172c96b96dd8a1d66`, SHA-256 `d709713feb231ed241de50e45b22ba7c772efa4020acb374487a877e95990abf`. It includes the 213-query stratified attribution, corrected statistical interpretation, current citations and Professor Ioannis Koutis acknowledgment. No scientific source, result or relevance record changes in this integration.

## Integration and retention

The source revision contains the full PR #52 ancestry and PR #54 revision. The fetched original main, `8f9b3c4db0ed00afed6942a8deccc98cde562378`, is its ancestor; integration preserves that history without a squash, force-push or discarded intervening commits. PR #53's experiment is excluded; no experiment files, results or Wulver jobs are accessed or modified. Repository visibility remains private. This work does not submit the manuscript or resolve its outstanding access, rights, overlap-version or author-approval gates.

There is **one authoritative compiled manuscript**, but **100 tracked PDFs overall**. The other 99 are 92 supporting figure/graphical-abstract PDFs, two publisher sample/manual PDFs, and five pre-existing historical submission-support PDFs. They are not alternate manuscript versions. All retained PDFs are byte-identical to the source revision, including the five JDSA figure assets. Existing supporting documents are retained as historical material, not newly published or inferred to reflect current submission status.

The complete 113-PDF source inventory and per-file disposition are in `audit/MAIN_INTEGRATION_MANIFEST.json`. Fourteen old output paths are removed: the canonical main's former location, four other JDSA identified/anonymous/supplement outputs, the earlier stand-alone opportunity-audit PDF, two SNCS main versions, four JDIQ main/supplement versions and two archival duplicate main PDFs. Only generated document outputs are removed. LaTeX, bibliography, figures, scripts, research data and original historical evidence remain. All removed versions are recoverable through ordinary Git history; the exact revision branch remains unchanged.

The frozen `audit/finalized_IJIT_source.zip` remains an original scientific-preservation snapshot, not an alternate current manuscript download. The active editable source ZIP is source-only: no compiled main or supplement PDFs, private reviewer inputs or editorial documents. Earlier dated validation receipts describe their original layouts and remain historical records.

## Rebuild without creating tracked alternates

From repository root:

```sh
bash papers/JDSA_2026/manuscript/build.sh
python papers/JDSA_2026/scripts/package_sources.py
python papers/JDSA_2026/scripts/validate_scientific_revision.py
python -m unittest discover -s papers/JDSA_2026/scripts -p test_selected_composition.py -v
```

All generated PDFs and logs remain in ignored `papers/JDSA_2026/manuscript/build/`. The identified supplement is `build/supplement.pdf` (38 pages). Its source, bibliography, tables and figure inputs remain tracked. Anonymous main/supplement fallbacks are also rebuilt locally, without becoming authoritative repository downloads. The verification build never overwrites the root canonical artifact automatically. Future approved scientific revisions must deliberately update the root PDF and its provenance.

A private copy of the 38-page supplement and both anonymous fallbacks was preserved outside every Git worktree before cleanup. For later submission preparation, copy the rebuilt supplement to an author-chosen private directory and name it `ESM_1.pdf` if required. A filesystem location is not reviewer delivery or permission clearance.

## Validation boundary

`audit/MAIN_INTEGRATION_DOCUMENT_VALIDATION.json` checks canonical identity, all four builds, references/citations, original numerical invariants, 99 retained PDF hashes, deleted output paths, unchanged scientific sources and source-only archive completeness. The integration follows the repository's ordinary core/solver validation policy; exact run state is recorded in the handoff rather than assumed from old receipts. No new LLM calls, data collection or optimizer research campaign is performed.

## Completed pre-push validation

Validated candidate: `764884e0c330fefa57ea5bd4abd97005c7540d92`, with clean worktrees and no dirty-tree override. Core: **1337 passed, 25 expected solver-related skips, 64 deselected**, all 18 steps PASS. Solver: **1362 passed, zero skipped, 64 deselected**, all 15 steps PASS. Both canonical cloud-validation receipts independently pass `--verify-run`. The final follow-up adds this validation record only, with no code or PDF changes.

All **198** document/source/preservation checks and **7** selected-composition software tests pass. The 52-file source-only ZIP independently rebuilds all four PDFs with identical extracted text; it contains no compiled manuscript documents. All **835** protected historical files retain their recorded hashes. The README download link resolves to the exact source-revision blob. Real-data tests are deselected because no dataset loaders or candidate-pool code changes; no new data acquisition is required. Full raw test logs remain local and are not committed; sanitized totals and receipt hashes are in `audit/MAIN_INTEGRATION_TESTS.json`.
