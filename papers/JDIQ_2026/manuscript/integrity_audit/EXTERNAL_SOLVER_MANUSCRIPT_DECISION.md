# External Solver Manuscript Decision

**Prepared:** 2026-07-12
**Scope:** Part A5 — evaluate Options A-E for how `main.tex` Table 4 ("Repair Variants Compared") should treat `exact_scc_dp20`, `lrta_external`, `wmsf_external`, and `ipsns_external`, given the facts established in `EXTERNAL_SOLVER_IDENTITY.md` and `EXTERNAL_SOLVER_EXECUTION_TRACE.md`.

---

## The fact that dominates this decision

`minimum-weighted-fas-heuristics` is public, MIT-licensed, and genuinely usable by a third party who clones it to the right path — so far this looks like an ordinary "external dependency" disclosure problem. **It is not, because the repository is registered on GitHub under the account `SoroushVahidi`, the real name of this JDIQ manuscript's actual (currently anonymized) author.** Citing this package by name, URL, or author in the anonymous-review version of `main.tex` would **directly deanonymize the submission** — worse than a generic reproducibility caveat, this is a double-blind-review integrity issue. `JDIQ_GUIDELINE_SUMMARY.md` §5's anonymization checklist already instructs "Remove repository URLs that expose author identity"; this is exactly such a URL. Every option below is scored with this constraint as a hard requirement, not a soft preference.

A second fact narrows the stakes considerably: the pooled, Results-facing "stronger repair does not improve retrieval" claim (Table 6, `best_stronger_repair`) is already computed from `exact_small_greedy_hybrid`, which is **fully in-repository** (`EXTERNAL_SOLVER_EXECUTION_TRACE.md`, confirmed via `REPAIR_COMPARISON_FINAL_REPORT.md` line 7). The four external-dependent methods are a **secondary, bounded (n=100) robustness check**, not the evidentiary basis for any central claim. This means the anonymity risk can be resolved without weakening the paper's main argument.

---

## Option scoring

| Option | Scientific value | Reproducibility | Reviewer risk | Implementation confidence | Page cost | Impact on conclusions if removed |
|---|---|---|---|---|---|---|
| **A — Keep in main paper as a fully reproducible public baseline** | Medium (adds a second, harsher-looking robustness check) | **Fails.** Cannot be called "fully reproducible" — it depends on a sibling repo at a hardcoded local path, not installable via `pip` or a documented public reference | **Severe** — as currently worded (an unnamed "$\dagger$" external dependency with no citation), a reviewer who investigates could independently discover the GitHub repo and the author's identity through the method names alone (LR-TA, WMSF, IPSNS are distinctive enough to search for) | High (code verified to run and produce complete results) | Low (already 3 rows in an existing table) | None — this option doesn't remove anything |
| **B — Keep in main paper with a clear non-public dependency disclosure** | Medium | Honest about the gap, but the disclosure itself is the anonymity risk if it names the package | **Severe if the disclosure names the package or shows the GitHub URL/path**; **low if the disclosure is deliberately anonymized** (e.g., "an author-maintained external solver package, withheld from citation during double-blind review") | High | Low | None |
| **C — Move to supplementary material** | Medium (same content, different location) | Same reproducibility gap, just relocated | **Same anonymity risk as A/B if named in the supplement** — supplementary material for an anonymous submission must be anonymized too; moving it doesn't solve the deanonymization problem, only the page-budget one | High | Removes ~3 rows + prose from main paper; adds to supplement | None (still reported, just elsewhere) |
| **D — Replace with in-repository exact DP** | Low-Medium (loses SCC 11-20 coverage unless new DP code is written; see `external_solver_replacement_options.csv`) | **Solves the reproducibility and anonymity problem completely** — zero external dependency | None | Medium (new code would need to be written for exact SCCs 11-20; verified this session that exact_fas.py + exact_min_fas_dp agree on a toy instance, so the algorithm is well-understood, but the SCC-11-20 code does not yet exist in this repository) | Low (same table shape, one row relabeled/reimplemented) | None to the central claim (already carried by `exact_small_greedy_hybrid`); would lose the specific "even a state-of-the-art bounded exact/heuristic search still doesn't help nDCG" data point unless the new DP code is written |
| **E — Remove entirely** | Low (loses the robustness-check angle entirely) | N/A (nothing to reproduce) | None | N/A | Lowest (frees ~3-4 table rows + prose) | None to the central claim |

---

## Recommendation

**Adopt a combination of Option D (immediate) and Option B, anonymized (if the four rows are kept at all) — do not adopt Option A as currently worded.**

Answering the task's specific questions directly:

1. **Does the external solver add a real contribution?** No new *scientific* contribution to this JDIQ paper — it is a secondary robustness check confirming (with an even more negative nDCG delta) the same qualitative conclusion already established by the fully in-repository `exact_small_greedy_hybrid` comparison. It adds diagnostic breadth (four different algorithms, not one), not a different conclusion.
2. **Does it change any central conclusion?** No. The central "stronger/exact repair does not improve retrieval" claim is carried entirely by `exact_small_greedy_hybrid` (in-repository, n=1,020, no external dependency). Removing the four external-dependent rows changes zero sentences in the manuscript's argument.
3. **Is it independently reproducible?** No, not by a third party, and — this is the operative fact — also not safely *citable* by name in this specific anonymous submission without a serious deanonymization risk, since the reproducing package is registered under the real author's GitHub identity.
4. **Is there a cleaner substitute?** Partially. `exact_small_greedy_hybrid` already substitutes for the "exact" story on SCCs ≤10 (the common case) using code already in this repository. A new ~30-line bitmask-DP function (Option D, `external_solver_replacement_options.csv` row 2) would close the SCC 11-20 gap with zero external dependency, but does not exist yet and is out of scope to write during this investigation.
5. **Should it remain in Table 4?** **Recommended: remove the four `$\dagger$`-marked rows from the main-paper Table 4** and keep only `Greedy` and `Exact (brute-force) + greedy fallback` (both already fully in-repository, both already covering the full 1,020-query canonical package rather than a 100-query bounded sample). This is Option E for the *main paper* specifically — not because the external package lacks scientific merit, but because (a) it isn't needed for any conclusion the paper makes, and (b) it cannot be disclosed by name without a real anonymity risk.
6. **Should the $\dagger$ footnote remain?** Only in a strictly anonymized form, and only if the four rows are retained anywhere (e.g., a future supplement). If the rows are removed per (5), the footnote should be removed too, since there is nothing left in the main paper for it to annotate.
7. **What exact wording should appear in the manuscript?** See the patch text below.

### Recommended manuscript wording (for the next drafting pass, not applied to `main.tex` in this task)

Replace Table 4's four `$\dagger$`-marked rows and the paragraph disclosing them with:

> Table 4 reports only repair procedures fully reproducible from this repository: the greedy cycle-peeling heuristic used throughout the main experiments, and an exact-for-small-components variant (exact brute-force search on strongly connected components of at most 10 nodes, with greedy fallback on larger components). A bounded robustness check against several additional exact and metaheuristic feedback-arc-set solvers — run on a fixed 100-query sample of cyclic queries — showed the same qualitative pattern (stronger or exact repair does not translate into improved nDCG) with no recorded failures; because those additional solvers depend on a separate, author-maintained software package withheld from citation during double-blind review, we report this check qualitatively here rather than as a numbered table row, and will provide the full citation, package identity, and quantitative results in the camera-ready version and supplementary material.

This wording: (a) makes no unverifiable claim, (b) discloses the existence and outcome of the robustness check honestly, (c) does not name or link the package, (d) commits to full disclosure post-anonymity (camera-ready), which is standard practice and will not read as evasive to reviewers who are used to double-blind conventions, and (e) keeps the central claim's evidentiary basis exactly where it already is — `exact_small_greedy_hybrid`, fully in-repository.

### If the authors instead prefer Option B (keep the rows, anonymized)

Table 4 could retain the four rows with algorithm names only (Exact/SCC-bounded, LR-TA-style, WMSF, IPSNS) and a footnote reading:

> $\dagger$ Depends on a separate, author-maintained solver package withheld from citation during double-blind review; full citation and public repository link will be provided upon acceptance.

This is defensible and not uncommon in anonymized submissions (citing "our related work, details withheld for review" is an accepted convention), but it is a materially higher reviewer-attention item than simply not including the rows, for no corresponding gain in the paper's central argument. **Our recommendation remains the removal option above**, with this as an acceptable fallback if the authors judge the four-algorithm robustness angle worth defending explicitly.

Do not adopt Option A's current wording (as of the previous drafting pass, which used unanonymized-adjacent phrasing like "a separate, non-public solver library located outside this repository" without yet flagging the deanonymization risk specifically) — it discloses the dependency but does not yet address the anonymity conflict identified in this audit.
