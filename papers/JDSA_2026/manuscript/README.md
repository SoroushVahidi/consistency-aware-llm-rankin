# JDSA editable manuscript sources

The sole authoritative compiled manuscript is [LATEST_MANUSCRIPT.pdf](../../../LATEST_MANUSCRIPT.pdf) at the repository root. It is the exact approved 20-page identified PDF from scientific revision `af03da5900e61a3683de352172c96b96dd8a1d66`. Build verification never replaces it automatically.

`main.tex` uses the official Springer Nature class with `iicol`; `supplement.tex` produces the 38-page Online Resource 1. All editable dependencies, bibliography, native figure source and five build-critical PDF figure assets remain here. The publisher class and bibliography style are unmodified.

From repository root:

```sh
bash papers/JDSA_2026/manuscript/build.sh
python papers/JDSA_2026/scripts/package_sources.py
python papers/JDSA_2026/scripts/validate_scientific_revision.py
python -m unittest discover -s papers/JDSA_2026/scripts -p test_selected_composition.py -v
```

All four generated documents stay in ignored `build/`: `main.pdf`, `supplement.pdf`, `main_anonymous.pdf` and `supplement_anonymous.pdf`. They are verification/submission-preparation artifacts, not additional tracked canonical versions. The identified supplement is the Online Resource 1 PDF; name a private submission copy `ESM_1.pdf` if required by the journal. The anonymous fallbacks remain reproducible; they do not guarantee unlinkability.

The source-only `packages/JDSA_sources.zip` contains editable dependencies, compiled BBLs, data-free verifiers and their schema/test documentation. It excludes compiled main/supplement PDFs and all private experimental/editorial inputs. The five figure PDFs are supporting inputs, not manuscript versions. A frozen earlier scientific-source ZIP under `audit/` remains a historical preservation artifact, not a current download.

No new experiment or prospective replication result is incorporated. Reviewer access, rights, version-specific overlap and final author approval remain open as documented in the submission checklist.
