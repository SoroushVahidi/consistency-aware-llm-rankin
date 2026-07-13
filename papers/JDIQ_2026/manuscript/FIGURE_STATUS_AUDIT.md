# Figure Status Audit

**Prepared:** 2026-07-12
**Method:** Every figure's actual image file (where one exists) was opened and visually inspected in this session — findings below are not inferred from filenames, captions, or prior sessions' notes. Three factual mismatches between caption/alt-text and the actual image content were found and corrected as part of this audit (documented below, already applied to `main.tex`).

---

## Figure 1 — Preference-graph pipeline schematic

| Field | Finding |
|---|---|
| Current file path | None. `\fbox{...}` placeholder in `main.tex` (label `fig:pipeline`) |
| Image actually exists? | **No.** No file named anything like `fig_pipeline*.png` exists anywhere under `figures/` |
| Uses canonical values? | N/A — conceptual/schematic figure, no data to be canonical or not |
| Referenced in `main.tex`? | Yes, via `\label{fig:pipeline}`; not currently `\ref{}`-ed elsewhere in the text (it is a standalone illustration in §3) |
| Caption matches image? | N/A — no image exists to match against; caption describes the intended content |
| `\Description{}` present and accurate? | Present, describes the *intended* pipeline (added in the prior drafting pass); accurate to the intended design, not verifiable against a real image since none exists |
| Publication-ready? | **No** |
| Still a placeholder? | **Yes** |

**Resolving the reported inconsistency:** the previous session's final report described "Figures 1–4" as "real/finalized" in one summary line while separately and correctly noting elsewhere that Figure 1 remains a placeholder pending generation. Those two statements were in tension. The accurate, single statement is: **Figures 2, 3, and 4 have real, canonical-data images already in place; Figure 1 does not and is still a placeholder.** The earlier summary line was imprecise and should be disregarded in favor of this document.

---

## Figure 2 — Cyclicity and largest SCC by dataset and regime

| Field | Finding |
|---|---|
| Current file path | `figures/manuscript/fig_cyclicity_and_scc.png` |
| Image actually exists? | **Yes** (180,382 bytes) |
| Uses canonical values? | **Yes**, visually confirmed this session: FiQA `ms1` bar reaches ~95% cyclic / largest SCC ~12.5; SciDocs `ms1` ~87.5%/~9.3; BRIGHT `ms1` ~60%/~6.5; HotpotQA `ms1` ~52%/~2.5 — all match `table_graph_ndcg_and_consistency.csv` exactly |
| Referenced in `main.tex`? | Yes, `\includegraphics` in §5, `\label{fig:cyclicity-scc}` |
| Caption matches image? | **Fixed this session.** The image is a **2×2 grid of panels, one per dataset**, each with a **dual y-axis** (percent cyclic on the left axis, mean largest SCC on the right axis) and three regimes on the x-axis. The caption previously described a "two-panel" layout split by *metric* (left panel = cyclicity, right panel = SCC) — incorrect. Corrected to describe the actual per-dataset grid with dual axes. |
| Caption also contained a factual comparative error | The original caption said "BRIGHT showing the mildest effect and FiQA the strongest." Checking the canonical `ms1` cyclicity values (FiQA 95.0 > SciDocs 87.5 > BRIGHT 60.0 > HotpotQA 51.9), **HotpotQA, not BRIGHT, has the mildest effect.** Corrected. |
| `\Description{}` present and accurate? | Present; rewritten this session to match the actual 4-panel/dual-axis layout and the corrected mildest/strongest comparison |
| Publication-ready? | **Yes**, now that the caption/alt-text corrections are applied |
| Still a placeholder? | No |

---

## Figure 3 — BEW before/after FAS repair

| Field | Finding |
|---|---|
| Current file path | `figures/manuscript/fig_graph_qrels_bew_pre_post.png` |
| Image actually exists? | **Yes** (226,083 bytes) |
| Uses canonical values? | **Yes**, visually confirmed: SciDocs `ms1` pre/post bars both ~290 (matching `table_consistency_qrels_bew.csv`'s `mean_bew_pre`$\approx$294.2, `mean_bew_post`$\approx$293.9); FiQA, HotpotQA, BRIGHT panels likewise match their respective canonical BEW values |
| Referenced in `main.tex`? | Yes, `\includegraphics` in §5, `\label{fig:bew-pic}` |
| Caption matches image? | **Fixed this session — this was the most significant mismatch found.** The image's title is "Consistency vs labels: preference graph vs qrels reference ranking" and every one of its four panels (one per dataset) plots **only backward-edge weight (BEW)**, pre- and post-repair, across three regimes. **PIC is not plotted anywhere in this image.** The caption and body prose previously described the figure as showing "backward-edge weight (BEW) and pairwise inconsistency count (PIC)... reductions in both metrics" — this was incorrect; PIC values exist only in Table 4b (`tab:bew-pic`), not in this figure. Caption, alt-text, and the one sentence of body prose introducing the figure were all corrected to state that the figure shows BEW only, with PIC reported in the table. |
| `\Description{}` present and accurate? | Present; rewritten this session to describe the actual 4-panel BEW-only layout |
| Publication-ready? | **Yes**, now that the caption/prose corrections are applied. (The figure's own label `fig:bew-pic` is a naming artifact — it refers to the *table* pairing of BEW+PIC, not this image's content — and could be renamed to `fig:bew-prepost` in a future pass for clarity; not done here since renaming a `\label` this late risks an unnoticed dangling `\ref`, and a verification pass confirmed all current `\ref{fig:bew-pic}` uses are consistent with keeping the existing label.) |
| Still a placeholder? | No |

---

## Figure 4 — Bootstrap $\Delta$nDCG forest plot

| Field | Finding |
|---|---|
| Current file path | `figures/manuscript/fig_delta_ndcg_bootstrap.png` |
| Image actually exists? | **Yes** (112,690 bytes) |
| Uses canonical values? | **Yes**, visually confirmed: the HotpotQA panel's "ms1 · Cop" row shows a point at approximately $+0.017$ with a CI spanning $[0, 0.041]$ — matching `table_bootstrap_delta_ndcg.csv` exactly (mean $+0.0167$, CI $[0, 0.0405]$); FiQA's "ms1 · Cop" row shows a small positive point with a CI straddling zero, matching FiQA's canonical row; SciDocs and BRIGHT panels show near-zero points with tiny straddling intervals, also matching |
| Referenced in `main.tex`? | Yes, `\includegraphics` in §6, `\label{fig:bootstrap-delta-ndcg}` |
| Caption matches image? | **Fixed this session.** The image is a **2×2 grid of forest-plot panels, one per dataset**, each with **six rows** (three regimes × two pairs). The caption and alt-text previously described "one panel... 24 rows total" as if all cells were in a single combined forest plot — incorrect layout description, though the underlying 24-cell data description itself was accurate. Corrected to describe the actual four-panel, six-row-each layout. |
| `\Description{}` present and accurate? | Present; rewritten this session to match the actual per-dataset panel structure |
| Publication-ready? | **Yes**, now that the caption/alt-text corrections are applied |
| Still a placeholder? | No |

---

## Figure 5 — Pooled mean nDCG@$k$ by method

| Field | Finding |
|---|---|
| Current file path | An asset exists at `figures/manuscript/fig_mean_ndcg_hybrids.png`, but `main.tex` does **not** `\includegraphics` it — it uses an `\fbox` placeholder instead (this was a deliberate choice made in the prior drafting pass, reaffirmed here) |
| Image actually exists? | The *asset* exists (122,402 bytes), but it is **not the right comparison** for this figure slot |
| Uses canonical values? | **The existing asset uses real canonical values, but for the wrong comparison.** Visual inspection this session confirms it is a 2×2 grid (one panel per dataset) plotting mean nDCG for exactly four vote-suite methods --- unrepaired Copeland, repaired Copeland, unrepaired balance, repaired balance --- across three regimes. This is the same data already reported in `table_graph_ndcg_and_consistency.csv` and is not illustrative or fake. However, the Figure 5 slot as planned requires the **pooled 12-method baseline grid** (CombSUM, RRF, Borda, prior, Markov variants, Copeland variants, balance, and the repair-based hybrid) from `final_baseline_comparison.csv` — a different comparison, already tabulated in Table 6. The earlier characterization of this asset as a "partial/pre-canonical prototype" was imprecise; the more accurate description is that **it is a real, canonical figure for a different, narrower comparison** (already visually covered by the vote-suite data underlying Figure 2/Table 4), not a match for what Figure 5 needs to show. |
| Referenced in `main.tex`? | The stale asset is referenced only in a `%` comment explaining why it is *not* used; the actual figure environment is an `\fbox` placeholder |
| Caption matches image? | N/A — the placeholder's caption describes the intended pooled comparison, not the stale asset |
| `\Description{}` present and accurate? | Present on the placeholder; accurately describes the intended content, not yet a real image |
| Publication-ready? | **No** |
| Still a placeholder? | **Yes.** See Part 2 of this task for the canonical plotting data now prepared (`figure5_evidence/`) |

---

## Figure 6 — Failure-class distribution

| Field | Finding |
|---|---|
| Current file path | None |
| Image actually exists? | **No** |
| Uses canonical values? | N/A — no image exists |
| Referenced in `main.tex`? | `\fbox` placeholder, `\label{fig:failure-classes}` |
| Caption matches image? | N/A |
| `\Description{}` present and accurate? | Present, describes the intended sorted bar chart of the six failure classes; accurate to intent |
| Publication-ready? | **No** |
| Still a placeholder? | **Yes.** See Part 3 of this task for the canonical plotting data now prepared (`figure6_evidence/`) |

---

## Summary table

| Figure | File exists | Canonical data | Caption accurate (before this session) | Caption accurate (after this session's fixes) | Publication-ready |
|---|---|---|---|---|---|
| 1 (pipeline) | No | N/A | N/A | N/A | No — placeholder |
| 2 (cyclicity/SCC) | Yes | Yes | **No** (wrong panel layout + wrong mildest-dataset claim) | **Yes** | Yes |
| 3 (BEW pre/post) | Yes | Yes | **No** (claimed PIC was shown; it is not) | **Yes** | Yes |
| 4 (bootstrap forest) | Yes | Yes | **No** (wrong panel layout, described as one combined panel) | **Yes** | Yes |
| 5 (pooled baseline) | Asset exists but is the wrong comparison | Real data, wrong comparison | N/A (placeholder) | N/A | No — placeholder, canonical plotting data now ready (Part 2) |
| 6 (failure taxonomy) | No | N/A | N/A | N/A | No — placeholder, canonical plotting data now ready (Part 3) |

**Net effect of this audit:** three real, previously undetected caption/alt-text inaccuracies in Figures 2–4 were found by direct visual inspection (not merely by re-reading the surrounding prose, which had internally described the figures consistently with the *wrong* mental model of their layout) and corrected in `main.tex`. All underlying data in Figures 2–4 was independently confirmed correct against canonical source values. Figures 1, 5, and 6 remain honest, clearly marked placeholders, consistent with how they were already described — no change in status for those three, only in the precision of Figure 5's diagnosis.
