# JIS editorial summary (for human authors)

Concise orientation after freezing evidence in **`outputs/final_jis_package/`** and **`reports/jis_final_tables/`**. **No new experiments** were run to produce this summary.

---

## 1. Recommended official paper angle

Frame the submission as a **measurement and diagnostics** study of **vote-graph construction**, **greedy cycle repair**, and **hybrid retrieval reranking** on **four BEIR datasets**: show **when repair is structurally active**, **when it is retrieval-inactive**, and **when bootstrap ΔnDCG is heterogeneous** across datasets—**without** claiming universal retrieval gains. Emphasize the **decoupling** of **qrels-aligned structural metrics** from **nDCG movement**.

---

## 2. Recommended canonical result package

**`outputs/final_jis_package/`** (mirror of **`outputs/pub_vote_cmp_all4`** aggregates).  
Use **`reports/jis_final_tables/T01`–`T03`** as the **only** main-result CSV set for real data.

**Explicitly retire** (for main-text numbers) **`outputs/pub_vote_cmp_v2`**, **`outputs/q1_journal_package`**, and **`reports/paper_tables/table_01` / `table_05`** unless the paper **commits** to v2 as a **separate historical run** and **never** blends it with all4.

---

## 3. Top 5 strongest supported claims

1. **Vote construction controls cyclicity and SCC structure** across SciDocs, FiQA, HotpotQA, BRIGHT (`T01`, Fig. cyclicity/SCC in package).
2. **Repair is retrieval-inactive** (ΔnDCG bootstrap means **0**, CIs **degenerate at zero**) for **`ms2` and `ms1_drop_mutual`** across tabulated dataset rows (`T02`).
3. **Repair moves qrels-aligned BEW/PIC** (and removes FAS weight) in **`ms1`** regimes where cycles are prevalent (`T03` / `T01` structural columns).
4. **Copeland ΔnDCG under `ms1` is dataset-dependent** (near-zero negative straddling CI on SciDocs; positive straddling on FiQA; HotpotQA positive mean with CI **anchored at zero** on the low side; BRIGHT tiny effects—`T02`).
5. **Balance hybrids are retrieval-neutral** under the bootstrap reporting in `T02` (all **zero** rows).

---

## 4. Top 5 risky claims to avoid

1. **“Significant harm on SciDocs ms1 Copeland”** while citing **all4** — the **committed all4 CI straddles zero**; that language fits **v2**, not the canonical bundle.
2. **Universal improvement** (or universal harm) from repair across datasets or metrics.
3. **LLM pairwise** framing for this evidence chain—preferences are **score-derived** in the documented publication pipeline.
4. **“Lower BEW/PIC implies better nDCG.”** The repo shows **structural reduction coexisting with mixed retrieval deltas**.
5. **Merging tables** from **`q1_journal_package`** / **`reports/paper_tables/table_01`** with **all4** **without** stating **two different runs**.

---

## 5. What is still missing before writing

- **Single author-facing “results section outline”** that **only** pulls numbers from **`T01`–`T03`** (minimizes copy/paste errors).
- **Explicit manuscript footnote** documenting **v2 vs all4** for any prior drafts that used q1/v2 language.
- **Figure finalization:** package includes **five PNGs**; ensure captions state **vote definitions** and **hybrid α** (from scripts) consistently.
- **Optional:** Regenerate **`outputs/q1_journal_package/`** with `--pub-root outputs/pub_vote_cmp_all4` **if** authors still want narrative Markdown tables—but **`T01`–`T03`** already suffice.

---

## 6. Whether new experiments appear necessary

**Not** for a conservative JIS submission **if** authors accept **diagnostic / heterogeneity** framing on **four datasets**.  
**Yes** (outside this task) **if** authors insist on **LLM-judge** claims, **strict cross-benchmark** generalization, or **exact MWFAS** real-data superiority—**not** evidenced in the canonical bundle.

---

## 7. Suggested positioning for *Journal of Information Science*

A **methods-aware empirical note** at the intersection of **information retrieval aggregation**, **graph consistency**, and **evaluation practice**: valuable to JIS as **evidence about when structural repair touches rankings and when it does not**, with **transparent bootstrap reporting** and **explicit caution** about **qrels-aligned diagnostics**. This fits **information science** emphasis on **measurement validity** and **methodological consequences** better than a **pure “new SOTA ranker”** claim.

---

*Evidence details: `reports/jis_claims_mapping.md`, `docs/jis_paper_scope.md`, `docs/jis_reproducibility.md`.*
