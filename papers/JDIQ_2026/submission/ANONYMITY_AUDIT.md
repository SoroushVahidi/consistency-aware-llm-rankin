# Anonymous Submission Hygiene Audit

## Clean (verified directly, not assumed)

- `main.tex`: author block is `Anonymous Author(s)` / `Institution redacted
  for review`; `\begin{acks}\end{acks}` is empty; `grep`'d for "soroush",
  "vahidi", "njit.edu", and `/home/soroush` across `main.tex` and
  `references.bib` — zero matches in all cases.
- Compiled `main.pdf`: `pdfinfo` shows no Author field, Title is the paper
  title only, Producer/Creator are generic LaTeX/XeTeX toolchain strings
  (no username or hostname); `strings main.pdf | grep` for the same terms
  above plus the machine hostname (`al-khwarizmi`) — zero matches.
- `papers/JDIQ_2026/submission/{SUPPLEMENTAL_PACKAGE.md, SUBMISSION_CHECKLIST.md,
  COVER_LETTER.md, FIGURE_INVENTORY.md, SUBMISSION_FREEZE_MANIFEST.json,
  FIGURE_DATA_VERIFICATION_REPORT.md}` and `docs/REPRODUCTION_CANONICAL.md`:
  zero absolute local paths (`/home/soroush`) — all path references are
  repo-relative; the freeze-manifest builder deliberately extracts only
  `qrels_hash`/`source_score_hashes` from per-cell manifests, not their
  `generation_script`/`output_files` fields (which do contain absolute
  paths — see below).
- The internal `TASK 6 TODO`/`FIGURE TODO` comments that referenced
  internal `reports/...` directory paths were already scrubbed in Task 4/5
  and re-verified clean in this pass (the one remaining reference,
  `main.tex`'s figure-sensitivity-range note, was rewritten in this task
  to close it out rather than leave it as an actionable internal TODO).

## Found and must be handled when building `final_anonymous/` (step 12)

- **204 per-cell `manifest.json` files** under
  `reports/full_calibrated_core/outputs/calibrated_all4/{protocol_runs,pool_runs}/`
  contain absolute local paths in their `generation_script` and
  `output_files` fields (e.g.
  `/home/soroush/consistency-aware-llm-rankin/reports/.../run_independent_protocols.py`).
  This is expected and correct provenance for the *private working
  repository* (per this task's explicit instruction not to erase
  provenance there) but must not be copied as-is into the anonymous
  submission package. Decision for step 12: the anonymous package includes
  the canonical *aggregate* tables (`reports/*/tables/*.csv`, which contain
  no paths) and a representative note pointing to the reproduction guide,
  rather than all 204 raw per-cell manifests; if per-cell manifests are
  wanted for full transparency, they must be path-scrubbed first (replace
  the repo-root prefix with a relative marker) before inclusion.
- **Git history**: commit authorship (`Soroush Vahidi <sv96@njit.edu>`) is
  real and present in this repository's git log, as expected for the
  private working repository. The anonymous submission package is a plain
  file bundle (manuscript source, figures, tables, docs), not a copy of
  `.git/`, so this is not a leak risk as long as step 12 never includes the
  `.git` directory in the ZIP — confirmed as an explicit exclusion below.
- **Internal planning/audit docs** under `papers/JDIQ_2026/` (e.g.
  `PROJECT_STATUS.md`, `CANONICAL_PAPER_STORY.md`, and the various
  `*_AUDIT.md` files marked superseded in Task 4) were not individually
  re-audited for author-identifying content in this pass, because they are
  explicitly excluded from the anonymous package by category (superseded
  planning documents) regardless of their content — see step 12's
  exclusion list.

## Explicit exclusions for `final_anonymous/` (per this task's own instructions)

- No `.git/` directory or git metadata of any kind.
- No historical/superseded PDFs (there is exactly one `main.pdf`; no
  alternate dated copies exist in `papers/JDIQ_2026/manuscript/`).
- No temporary LaTeX build files (`.aux`, `.log`, `.fls`, `.fdb_latexmk`,
  `.bbl`, `.blg` — these are excluded by build convention and were not
  found tracked in the manuscript directory as stale artifacts).
- No local logs containing paths (none of the `/tmp/latex_build*.log`
  files used during this session's own verification are part of the
  manuscript directory; they are session-scratch and already outside the
  repository).
- No superseded planning documents (`papers/JDIQ_2026/*.md` other than the
  manuscript's own `main.tex`/`references.bib`/figure assets).
- No raw third-party document collections (this repository never stores
  SciDocs/FiQA/HotpotQA/BRIGHT's raw document text, only stored ranker
  scores and qrels derived from the public datasets, consistent with
  `main.tex`'s own Data Availability statement).
- No author-identifying repository metadata.

## Verdict

No author-identifying information was found in the manuscript, its
compiled PDF, or the submission documentation authored in this task. The
one real risk — absolute local paths inside per-cell `manifest.json`
provenance files — is confined to files that are not planned for inclusion
in `final_anonymous/` in their raw form; this is handled by selection, not
by editing files in the private repository.
