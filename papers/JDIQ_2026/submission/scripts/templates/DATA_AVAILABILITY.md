# Data and Artifact Availability

Reproduced from Section "Data Availability and Reproducibility" of
`main.tex`; see that section for the citation keys.

**Data availability.** SciDocs, FiQA, HotpotQA, and BRIGHT are publicly
available from their original sources. This paper redistributes no raw
third-party document collection.

**Artifact availability.** The pipeline is packaged as a reproducible
code-and-data artifact. This double-anonymous package does not include an
author-identifying public repository URL, and no verified anonymized
mirror URL is claimed here. A scrubbed anonymous artifact is attached
through the venue submission system, not distributed by email request.
The package contains stored ranker scores, query-ID manifests, qrels/score
hashes, primary normalized and raw-ablation outputs, tables/figures, and
commit manifests (see `SUBMISSION_FREEZE_MANIFEST.json`). The primary
evidence set is the normalized retention-matched package; the raw-margin
package is an ablation only.

**Reproducibility.** Mechanical results regenerate from stored
intermediates with the seeds, solver settings, and eligibility rule
recorded in `REPRODUCIBILITY.md`. Upstream retrieval and paid APIs need
not be rerun. Stored LLM records support protocol-quality checks only, not
the primary mechanical evaluation. `REPRODUCIBILITY.md` lists the
dependency versions and exact commands used for mechanical regeneration.
