# Repository visibility audit — release held

**Decision: keep PRIVATE.** See [the prepared remediation plan](PUBLIC_RELEASE_REMEDIATION_PLAN.md) for verified private backup, dependencies, ref migration and required future approvals. The original audit below is historical; its unclassified listwise finding is refined by the new content inspection. The visibility change is authorized conditional on safety, but the audit found material explicitly designated confidential in reachable history. No visibility mutation, deletion, purge or history rewrite was performed. Authenticated metadata shows ADMIN permission; this is not an account-permission failure. An unauthenticated GET returns 404.

Concrete blocker:

- Historical `papers/SNCS_2026/UPLOAD_MANIFEST.md`, blob `4443b78c6a3f2bf86283c67caf026f024372f5d7`, labels the cover letter “Confidential to editors” and the reviewer suggestions/opposed-reviewer list “Confidential” (lines 17, 19, 20). Related historical manifest blobs repeat those labels. The marked records point to tracked `COVER_LETTER.md`, `REVIEWER_SUGGESTIONS.md` and `SUBMISSION_METADATA.md`, which remain in `origin/main` or its history. The manifest is reachable through the SNCS lineage, including commits `505761d27c48b2f03909c99d52b7b5e37db34d07` / `1fe1905232570cc447e99dd4cc7cd0506d42cd57`. Removing a current file would not remove historical exposure.
- Historical listwise caches also retain `response_text` fields (35 records across three object versions); they were not newly released. The project's artifact rules prohibit raw provider transcripts in Git. A field name alone does not establish copyright risk, and short index-only responses are different from source text; item-level clearance remains required. The explicit editorial confidentiality blocker already independently prevents release.

Scope and evidence:

| Surface | Inspection |
|---|---|
| Local/remote branches and tags | Fetched origin; 11 remote branches, 3 tags; all local refs and 45 fetched PR heads included. No shared ref was rewritten. |
| Reachable objects/history | 5,812 objects; 3,554 blobs, 488,244,719 bytes; pattern scan over blob bytes and unpacked small archive members. 13 ZIP object versions inventoried. |
| Secret-shaped matches | 22 candidates, all traced to synthetic scanner/provider-leakage test fixtures and duplicate archive copies. No live credential was confirmed. Heuristic scan is not a security guarantee; PDF/image content is not exhaustively semantically audited. |
| LFS | Zero reachable LFS pointer blobs detected. Unreferenced server-side objects cannot be enumerated by this check. |
| Releases / artifacts / deployments / container packages | API inventory: 0 releases, 0 Actions artifacts, 0 deployments, 0 user container packages. Other package types were not exhaustively enumerated. |
| Collaboration | 51 issue API records (includes PR records), 45 PRs, 37 issue comments, 123 inline-review comments scanned; no credential-pattern match. Reviewer review bodies and attachments are not comprehensively cleared. |
| Workflows | 305 runs inventoried; latest three log archives retrieved (one empty), credential-pattern scan negative. Remaining logs were not exhaustively downloaded because a material release blocker was already established. |
| Unauthenticated verification | Repository 404; intended URL is not a verified public repository. Public HF resources independently respond without authentication; see link checks. |

This is a documented **failed release gate**, not an exhaustive clearance certificate. No repository content was exposed for the audit. Full raw inventories/log archives are retained outside Git in the task's private local audit directory; only this redacted finding is versioned.

Safe remediation proposal, requiring a new explicit scope: preserve a private archival mirror; have the author classify and approve any declassification of the exact editorial records, or prepare a reviewed history-filtering plan for every affected branch/tag and GitHub PR/cache reference. Historical content cannot be made safe by deleting HEAD files alone. Review provider responses, third-party source rights, remaining logs/attachments and any non-container package surfaces before final release. Do not execute filtering or force-push without authorization. A separate sanitized public artifact repository could provide reproducibility access while preserving this private history, but would not satisfy restoration of this repository's visibility and has not been created.

## Follow-up content review (26 October 2026)

All 35 historical listwise response_text records are numeric bracketed rankings and separators only; no prose/source passages or full provider envelopes were found. They remain raw-output fields under the artifact policy. Five differ from a simple index-base conversion of the saved parsed indices, so no lossless reconstruction claim is made. The separate editorial-confidentiality blocker remains. A local all-ref bundle and current SNCS tree archive were verified; an off-device copy and destructive scope approval remain pending. No removal, rewrite or visibility change occurred. Exact private evidence and backup receipts are outside Git.
