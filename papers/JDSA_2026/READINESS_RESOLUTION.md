# Submission-readiness resolution — 27 October 2026 UTC

**Readiness: NOT_READY.** This is a bounded follow-up to the [final audit](FINAL_SUBMISSION_READINESS_AUDIT.md), not another scientific revision. Preparation, scientific verification, permission, delivery and author approval are separate states. No experiment, model response, data acquisition, research optimizer campaign, journal submission/contact or prospective-experiment modification is performed.

## Source and integration authority

Fetched original main: `efef450a349770a79cfb21fe956890d7e8a66bc2`. PRs #52 (`2c69f331fa4add10ce577c17516afb997b630dfe`) and #54 (`af03da5900e61a3683de352172c96b96dd8a1d66`) are already in that ancestry. The latest audited revision, PR #55 (`494439340df22fb818e0b6b1eb7b2fed3f1b007b`), is a direct descendant and contains those scientific dependencies. Its diff consists of bounded contribution/citation/access wording, document checks and related documentation; no provider inputs or prospective artifacts are integrated.

The canonical [LATEST_MANUSCRIPT.pdf](../../LATEST_MANUSCRIPT.pdf) builds from the audited 20-page revision with a final availability-only correction. Live GitHub metadata reports PUBLIC, contrary to the prior private-state records; this task did not change visibility. Main, SI and declarations now distinguish repository access from availability/clearance of excluded evidence instead of asserting the repository is private. No new reviewer availability is promised. The updated manifest pins the PDF; the preceding audited PDF SHA-256 was `baef3494c3cb6c29965f4f3981c2371c2df984d95c840b160ad3c472dd4a1c56`. Scientific results, attribution, inference and Professor Ioannis Koutis's acknowledgment are preserved.

There is **one designated compiled manuscript PDF and 100 PDFs in total**; the other 99 are necessary/supporting figures or retained unrelated documentation. No further PDF deletion is needed. The supplement remains source-reproducible (38 pages), with an identified local copy retained outside Git. The historical integration log and validation receipts retain their original scope. No restricted input, correspondence, private submission identifier or confidential overlap attachment is added to Git.

## Evidence recovered and prepared

| Issue | Verified progress | Remaining limit |
|---|---|---|
| M05, related version | Existing publisher correspondence independently confirms the separate MWFAS submission. The 25-page prepared candidate's package and PDF identities/checksums were rechecked; the current main and SI were compared against it. No identical whole table/PDF artwork or normalized 12-word body window was found. | Neither receipt binds uploaded bytes. Exact submitted-version identity remains **UNVERIFIED**, and literal screening does not clear paraphrase or unseen versions. A truthful confidential draft comparison is prepared locally, not delivered. |
| M06, Cohere | An author-specific award was recovered; it directly links the official Program FAQ. This improves the earlier missing-award finding. The [current FAQ](https://cohere.com/research/grants) generally dispenses with publication approval outside its safety exception. | Complete historical accepted terms, approved project scope and linkage of July calls to the grant remain unverified. Do not presume either blanket prohibition or mandatory new approval. Conclusions/aggregate publication: **CONDITIONAL**; new numeric reviewer sharing/public redistribution: **UNKNOWN**. See [assessment](COHERE_PERMISSION_ASSESSMENT.md). |
| M06, source inputs | The actual proposed payload was minimized: numeric grades/masks/ideals, saved permutations, weighted graphs/gains and reference records; anonymous stable keys preserve pairing. No raw passages/responses or original query/document identifiers. | FiQA-derived judgments and all provider-linked projections still need a content-specific sharing basis. Source attribution/license requirements remain. A private rights matrix distinguishes publication, confidential sharing and public redistribution; UNKNOWN is never CLEARED. |
| M04, central reproduction | A private local extension was prepared and isolated verification reproduces 213 identities/426 branches/6,816 fields, all composition strata and six graphs/241,920 orders/eight optimum repairs. Maximum errors: 2.22e-16 and 1.11e-16 respectively; seven existing tests pass. | **NOT CLEARED FOR DISTRIBUTION; NOT DELIVERED.** It does not replace/alter the existing 35-file ZIP, regenerate original acquisition or establish availability. See [reviewer guide](REVIEWER_ACCESS.md). |
| SNCS exclusivity | Existing sent correspondence proves a formal withdrawal request. A later customer-service message acknowledges receipt only. | **WITHDRAWAL_REQUESTED_UNCONFIRMED.** No definitive closure found in scoped accessible records. A request or automated receipt cannot support an exclusivity attestation. |
| H01, submission preparation | Current official instructions/publishing route rechecked; main/SI and cover/declaration drafts prepared privately for author review. | Journal-specific review model and a genuinely non-public reviewer attachment route remain unconfirmed. No portal object, upload, author signature or new approval is created. |
| Repository visibility | Live authenticated GitHub metadata reports PUBLIC. No visibility mutation was made by this task. Stale private-repository assertions were removed from the current manuscript. | Author must establish intended visibility; earlier history/redistribution cleanup is not certified by a public setting. Confidential candidate inputs remain outside Git. |

## Required closure actions

| Gate | Exactly missing | Can Codex close it now? | Minimum author/document/decision action |
|---|---|---|---|
| Concurrent consideration | Definitive SNCS withdrawal/closure evidence | No, absent a pre-existing accessible confirmation | Supply the prior journal's explicit confirmation or documentary portal closure before any new submission. No follow-up is sent on this task's authority. |
| Historical rights applicability | Approved Catalyst scope, accepted dated/incorporated terms and non-secret July-call/grant linkage | Award recovered; remaining evidence not found | Supply those existing records and any exception/amendment. Determine exception applicability and exact publication/sharing conditions; obtain an assessment or inquiry only if separately authorized and necessary. |
| Numeric input sharing | Lawful basis and conditions for provider-linked graph/ranking and source-derived grade payloads, especially FiQA | Candidate prepared; no legal grant inferred | Resolve exact content/recipient terms, preserve required notices; then explicitly authorize the cleared copy for confidential review. Public redistribution is a separate decision. |
| Reviewer access | An actual confidential reviewer-accessible delivery route and later authorized delivery | Public instructions do not confirm a category | Author verifies the journal's handling or provides existing documentary guidance. Ordinary publishable SI is insufficient. No transfer until sharing and route are cleared. |
| Related manuscript | Exact uploaded MWFAS PDF/version and any subsequent revisions | Best prepared candidate and receipts checked; byte binding absent | Provide saved submitted PDF and uploaded-file/portal record; compare that exact version. Until then disclose the precise uncertainty rather than claim complete clearance. Editorial acceptance of distinction is not an author/agent decision. |
| Final author approval | Approval of the final PDFs, cover letter, disclosures and actual interface attestations | Cannot be invented from earlier attestations | Author reviews the rebuilt 20/38-page files, approves the final wording/file selection and personally completes declarations in a later authorized workflow. |
| Visibility intent | Author decision on the observed public setting and any existing release-remediation evidence | No visibility change without a decision | Confirm whether PUBLIC is intended or authorize restoration to PRIVATE; public exposure alone does not clear historical materials or numerical sharing. No new broad history audit is started. |

The unknown anonymity model is a handling question with identified/anonymous fallbacks, not proof of scientific invalidity. Public code release, more prospective data, a new optimizer, extra citations, and SpringRank license reconciliation for code not included are optional/out-of-scope improvements, not substitutes for the actual gates above.

## Rebuild and checks

From repository root:

```sh
bash papers/JDSA_2026/manuscript/build.sh
python papers/JDSA_2026/scripts/validate_scientific_revision.py
python -m unittest discover -s papers/JDSA_2026/scripts -p test_selected_composition.py -v
PYTHONPATH=src make repo-ready validate-claims validate-clarity check-portability
```

Use the available project virtual environment (set `VENV` for make if it is outside this worktree). Builds stay in ignored `papers/JDSA_2026/manuscript/build/`; `supplement.pdf` may be copied privately as `ESM_1.pdf` for later approval. The source-only archive contains no compiled main/SI document or private inputs. Current sanitized verification is recorded in `audit/READINESS_RESOLUTION_VALIDATION.json`; full private evidence, rights matrix, exact-version report, candidate and unsent drafts remain outside Git.

The user prohibits new experiments. The full canonical core release tier also launches a synthetic quick-start experiment, so it is not rerun for this manuscript/documentation follow-up. The existing clean-worktree core/solver PASS receipts remain historical evidence for unchanged research implementations. Only the document validator changes to certify one exact access sentence rather than exempting the whole evidence section. Fresh relevant offline tests, maintained checks, source/document preservation and private verifier reconstruction are run without treating a restricted/skipped workflow as a new full-tier PASS.
