# Anonymous artifact upload instructions

Local scrubbed packages are ready under `anonymous_review_bundle/`.

## Still required (manual / interactive)

1. Create an `https://anonymous.4open.science` (or equivalent) project.
2. Upload `anonymous_review_artifact.zip` **or** a fresh git-export with no remotes/history.
3. Confirm reviewers cannot see author IP tracking and that clone URL does not redirect to identifying GitHub.
4. Re-scan the hosted copy for: Git history, remotes, commit authors, README identity, package metadata, PDF metadata, absolute local paths, author names, badges, user-specific URLs.
5. Insert only the verified anonymous URL into the manuscript Data Availability section after it exists.
6. Do **not** put `github.com/SoroushVahidi/...` in the anonymous PDF.

## What this overnight job produced

- Local anonymous bundle (tar.gz + zip)
- Identity needle scan report
- SHA256 manifest
