# Confidential reviewer evidence — delivery PENDING

The selected local artifact is `packages/JDSA_Confidential_Processed_Evidence.zip`, an unchanged byte copy of `IJIT_2026_FINAL_Anonymous_Reviewer_Package.zip` from the preserved prior preparation. Its internal root retains that historical name; this does not indicate an IJIT submission. It has **35 files**, **2,187,471 bytes**, SHA-256 **`c31fff08567d3fc0504e0a303a2328067175b8820541746588c30cfee484f7b3`**. It is ignored by Git and excluded from the public-safe source archive.

The older `anonymous_supporting_evidence.zip` is a different, broader inspection archive and must not be substituted. It contains materials intentionally excluded from the final review copy. The former availability guide incorrectly attached the final copy's checksum to that older filename; that reference is superseded.

Proposed exact access method: after journal-submission authorization, use a journal-confirmed **non-public reviewer-accessible attachment category** in the JDSA portal. Do not select ordinary publishable Supplementary Information for this ZIP. Confirm the category's handling and review anonymity before attaching; retain its supplied anonymous root if required. No verified download URL exists and no file was delivered. If the portal cannot provide confidential reviewer access, obtain an approved confidential channel before delivery. This guide does not authorize editor contact or upload.

Editor-only handling note and identified provenance remain outside Git in `editorial/` and the private audit directory. Do not forward those administrative records as anonymous reviewer evidence. Online Resource 1 (`ESM_1.pdf`) is the separately prepared publishable supplement; it is not this confidential ZIP.

Reviewer instructions, once received:

1. Check the ZIP SHA-256 above and extract into a fresh directory.
2. Read `00_START_HERE.md`, `LIMITATIONS.md` and `reproduction/INSTRUCTIONS.md` inside the root.
3. Use Python 3.11+ and pre-provision NumPy 2.3.5 with `python3 -m pip install -r configs/requirements-full.txt` before offline execution. The standard-library quick check needs no NumPy.
4. Run the three commands from the extracted root; choose fresh sibling output directories:

```sh
python3 reproduction/quick_verify.py
python3 reproduction/verify_available_offline.py --output ../offline_output
python3 reproduction/independent_statistics.py --package . --output ../independent_output
```

The 26 October fresh-extraction rerun used Python 3.12.3, NumPy 2.3.5, a dedicated environment, a separate HOME and no user-site/PYTHONPATH dependencies. All three exited 0. File/network traces showed no research-workspace reads and zero network connections. Initial testing with system Python found that its NumPy was only in user-site and unavailable under isolation; the dedicated environment resolves that installation issue without modifying package code.

`FILE_MANIFEST.csv`, `provenance/CHECKSUMS.sha256` and `provenance/SOURCE_CHECKSUMS.csv` anchor membership, bytes and transformations. The processed canonical files match their recorded source hashes. The package includes original review-use verification utilities and text-free author-generated score-derived measurements, not third-party implementations. The content-specific inherited rights rationale applies to proposed confidential review, not unrestricted public publication. No raw provider responses, source text, qrels, historical ranking permutations, weights or paid/API dependencies are included.

What is independently reproduced: 35/35 corrected tests from 34,783 paired processed observations; 28 tests on 342 queries and seven on 290; zero Holm rejections; maximum numerical reference error 0.0. Direct graph checks yield 1,025 inputs, 646 acyclic and 379 cyclic, 316 query identities cyclic in at least one regime, and 1,025 acyclic saved greedy after-graphs. The 399 cell counts/means are reconstructed, while their historical p-values and other families remain saved-output checks. Saved exact status/cost checks are not fresh optimality proofs.

What is not independently reconstructed: original scoring from rankings/qrels, selected-cache relevance-profile attribution, the six-graph complete-optimum envelope, provider judgments or prospective generation. Their complete historical inputs are excluded or unavailable. Checks on their displayed saved tables do not replace reconstruction. No human independent-peer-review certificate is claimed.
