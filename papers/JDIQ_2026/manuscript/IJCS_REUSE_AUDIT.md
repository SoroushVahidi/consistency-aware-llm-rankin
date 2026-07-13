# IJCS Manuscript Reuse Audit

**Prepared:** 2026-07-12
**Source archive:** `Consistency_Aware_Reranking_via_Preference_Graph_Repair__Structural_Gains_and_Conditional_Retrieval_Effects_IJCS.zip` (repository root), extracted and read in full (`.tex`, `references.bib`).
**Purpose:** Determine what, if anything, from the rejected IJCS submission can be reused as *verified technical material* (notation, formal definitions, method descriptions, related-work references, neutral technical prose) in the new JDIQ manuscript, per the task's evidence hierarchy. The IJCS text is **not** used as a source of framing, contribution claims, or narrative — only canonical repository evidence (`CANONICAL_PAPER_STORY.md` and the `outputs/pub_vote_cmp_all4/` package) governs those.

---

## Headline finding: the IJCS manuscript is numerically consistent with the current canonical package

Before auditing passage-by-passage, one fact changes how this audit should be read: the IJCS manuscript's result tables (Table "Overall Retrieval Performance," "Cyclicity and Structural Effects," "Repair Effect Delta nDCG") were **spot-checked against `outputs/pub_vote_cmp_all4/paper_package/tables/`** and match to the displayed decimal precision — e.g., IJCS reports SciDocs `ms1` Copeland ΔnDCG = −0.000127, CI [−0.000844, 0.000595], identical to the canonical bootstrap table. The IJCS submission was therefore already built on the **all4** four-dataset canonical package, not the deprecated `pub_vote_cmp_v2` two-dataset package. (By contrast, the repository's own `docs/SAFE_CLAIMS_FOR_PAPER.md` — a different, older internal document, not the IJCS manuscript — cites `pub_vote_cmp_v2` numbers for SciDocs, e.g. a strictly negative CI [−0.017, −0.003], which **conflicts** with all4 and must **not** be used; see `CANONICAL_PAPER_STORY.md`'s prohibited-claims table.)

This means the IJCS manuscript's technical descriptions of method and its already-conservative results reporting are **safe to reuse as verified technical material**, subject to the reframing rules below. It also confirms the reviewer criticism was about **framing and contribution strength**, not about data accuracy — consistent with the reconstructed criticism R1 ("main conclusion too natural") in `experiments/reviewer_response_state_audit_20260711_214959/`.

---

## Passage-by-passage audit

### Abstract

**Summary:** States the study evaluates consistency-aware reranking via preference-graph repair on the four-dataset canonical package; finds vote construction dominates cyclicity, repair improves structural diagnostics when active, but nDCG effect is conditional and dataset-dependent; concludes repair is "more reliable as a structural intervention than as a universal mechanism for improving retrieval effectiveness."

- **Reusable:** Yes, as a factual summary of findings.
- **Requires rewriting:** Yes — has no data-quality (DQ) vocabulary at all; frames the contribution purely as a reranking/IR methodology finding. The new abstract must lead with the DQ framing (structural inconsistency as a DQ dimension, repair as a DQ intervention, nDCG as downstream information quality) per `JDIQ_GUIDELINE_SUMMARY.md` §12.
- **Obsolete claim:** None found — the finding itself ("conditional, not universal") is exactly the CANONICAL_PAPER_STORY.md finding.
- **Canonical evidence needed to verify:** `table_graph_ndcg_and_consistency.csv`, `table_bootstrap_delta_ndcg.csv` (already verified above).
- **Disposition:** Reuse the *finding* (decoupling/conditionality) with a DQ-reframed abstract; do not reuse the sentence-level wording verbatim (paraphrase only). New abstract must additionally mention the failure taxonomy and CARB, which the IJCS abstract does not have because those artifacts did not exist yet.

### §1 Introduction

**Summary:** Motivates reranking as a two-stage retrieval refinement; introduces the weighted preference graph as evidence representation; states the central question as "when is graph repair structurally relevant and does its structural effect translate into retrieval gains"; states the main finding is conditional; distinguishes the contribution from learning-to-rank and LLM-reranking papers by studying a downstream structural question rather than proposing a new ranker; gives a one-paragraph roadmap.

- **Reusable:** Partially — the core research question ("when does structural repair translate into retrieval gain") is exactly right and should be preserved conceptually.
- **Requires rewriting:** Yes, substantially. This version (a) never mentions data quality, information quality, or curation — required framing for JDIQ; (b) has no contributions list (JDIQ requires an explicit bullet list per `MANUSCRIPT_OUTLINE.md` §1); (c) does not mention the failure taxonomy, baseline grid, or CARB, all of which are now central contributions; (d) does not address any of the 10 reviewer concerns, since it predates the rejection; (e) does not disclose relationship/overlap to a prior submission (required by JDIQ overlap policy, `JDIQ_GUIDELINE_SUMMARY.md` §6).
- **Obsolete claim:** None — the core empirical claims match canonical evidence.
- **Canonical evidence needed to verify:** `CANONICAL_PAPER_STORY.md` (central hypothesis, sub-hypotheses), `final_claim_support_matrix.csv`.
- **Disposition:** Do not reuse prose. Use only as confirmation that the "conditional, not universal" framing is scientifically sound and pre-dates the DQ reframing. The new Introduction is written from scratch against `CANONICAL_PAPER_STORY.md`.

### §2.1 Related Work — Learning to Rank and Reranking

**Summary:** Positions the paper within two-stage reranking; cites classical LTR (RankNet), fusion methods (RRF, CombSUM-adjacent), and recent LLM reranking paradigms (pointwise/pairwise/listwise/setwise); explicitly disclaims proposing a new reranker or prompting strategy.

- **Reusable:** Yes, largely as-is (paraphrased). This is neutral technical positioning, not a framing claim.
- **Requires rewriting:** Minor — needs a DQ-literature bridge sentence added (Wang & Strong, Batini et al., per `MANUSCRIPT_OUTLINE.md` §2), since IJCS has zero DQ citations.
- **Obsolete claim:** None.
- **Canonical evidence needed to verify:** N/A (literature positioning, not empirical).
- **Disposition:** Reusable as background material for the manuscript's future §2 Related Work (not written in this task). References (`liu2011learning`, `burges2005learning`, `cormack2009rrf`, `nogueira2019passage`, `sun-etal-2023-chatgpt`, `qin-etal-2024-large`, `pradeep2023rankzephyr`, `zhuang2024setwise`, `gangi-reddy-etal-2024-first`, `yoon2024listt5`) carried into `references.bib` for future use even though §2 itself is out of scope for this task. **Correction:** the IJCS source cited `burges2010ranknet` (the 2010 RankNet/LambdaRank/LambdaMART overview report) here; since the manuscript does not discuss LambdaRank or LambdaMART specifically, this was corrected to `burges2005learning` (the original 2005 RankNet paper, which is what the citing sentence actually asserts) — see `README.md`.

### §2.2 Related Work — Preference Modeling and Graph-Based Ranking

**Summary:** Positions preference graphs relative to Bradley-Terry models, Rank Centrality, Hodge-theoretic ranking, and classical rank-aggregation/FAS literature (Dwork, Ailon-Charikar-Newman, Kenyon-Mathieu, Fagin); explicitly narrows the contribution to studying "when does structural inconsistency materially affect the extracted ranking."

- **Reusable:** Yes, as neutral technical positioning and formal-definitions source.
- **Requires rewriting:** None needed for reuse as background; would need the DQ framing added if promoted into the main Related Work section later.
- **Obsolete claim:** None. Matches `docs/LITERATURE_ALIGNMENT.md`'s honest novelty assessment (FAS heuristic is a "folklore" greedy with no approximation guarantee — consistent, not contradicted).
- **Canonical evidence needed to verify:** N/A.
- **Disposition:** Reusable background; references retained in `references.bib`.

### §3.1 Method — Problem Setting

**Summary:** Formalizes $G_q=(V_q,E_q,w_q)$ per query, defines the repair/extraction pipeline abstractly, states the empirical problem as twofold: characterize when the graph is inconsistent, and determine whether repairing it changes the ranking usefully.

- **Reusable:** Yes — this is exactly the kind of formal notation the task explicitly permits reusing ("notation," "formal definitions").
- **Requires rewriting:** None for notation; DQ vocabulary should be layered on top when this becomes §3 Problem Formulation (out of scope here).
- **Obsolete claim:** None.
- **Canonical evidence needed to verify:** `src/consistency_ranker/` (repair, graph metrics) — code-level verification not performed in this task but flagged in `MANUSCRIPT_OUTLINE.md` §3 as the source of truth for metric definitions.
- **Disposition:** Reuse notation ($G_q$, $V_q$, $E_q$, $w_q$) verbatim as mathematical notation (not prose) in future sections.

### §3.2 Method — Preference Graph Construction (vote regimes table + algorithm)

**Summary:** Defines the three vote-construction regimes (`ms2`: min_support=2, min_margin=0.1; `ms1`: min_support=1, min_margin=0.0; `ms1_drop_mutual`: `ms1` with mutual-direction pairs dropped) and gives a compact construction algorithm.

- **Reusable:** Yes, directly — this is a precise, verified technical description of the canonical protocol.
- **Requires rewriting:** None substantively; can be paraphrased into DQ vocabulary (e.g., "regime" → "vote-extraction regime," matching `CANONICAL_PAPER_STORY.md`'s terminology, which is already consistent).
- **Obsolete claim:** None. Regime definitions match `MANUSCRIPT_OUTLINE.md` §4 exactly (min_support/min_margin values agree).
- **Canonical evidence needed to verify:** `table_graph_ndcg_and_consistency.csv` (regime → n_queries mapping already cross-checked in the Figure 4 evidence task).
- **Disposition:** Reuse regime definitions and algorithm sketch (paraphrased) for future §3/§4.

### §3.3 Method — Consistency-Aware Repair and Ranking Extraction

**Summary:** Describes greedy cycle-peeling FAS repair (find a cycle, remove minimum-weight edge, repeat until acyclic; topological sort), explicitly disclaims optimality ("does not claim to solve the minimum-weight feedback arc set problem exactly"); defines Copeland score (out-degree minus in-degree) and weighted balance score; defines the hybrid RRF-style combination $\text{rank}(q)=\operatorname{sort}(s_\text{prior}(q)+\alpha\, s_\text{graph}(q))$.

- **Reusable:** Yes — accurate, appropriately hedged (no algorithmic novelty claimed, consistent with `docs/LITERATURE_ALIGNMENT.md` §7's explicit instruction to say "greedy feedback arc set heuristic," not "minimum-weight feedback arc set").
- **Requires rewriting:** None for the formulas; should be explicitly labeled a "DQ repair operator" when reused in the DQ-framed Problem Formulation section.
- **Obsolete claim:** None.
- **Canonical evidence needed to verify:** Formula for Copeland/balance already matches column semantics of `table_graph_ndcg_and_consistency.csv` (`mean_ndcg_uco/rco`, `mean_ndcg_uba/rba`), confirmed during the Figure 4 evidence task.
- **Disposition:** Reuse formulas and repair algorithm description (Eq. hybrid score, Copeland score, balance score) directly as formal definitions.

### §4 Experimental Setup (datasets, regimes, baselines, metrics)

**Summary:** Describes the four canonical datasets (SciDocs, FiQA, HotpotQA, BRIGHT) with citations, the three-ranker upstream signal (BM25, TF-IDF, MiniLM), the primary UCO/RCO/UBA/RBA comparison family, a broader non-LLM baseline set (Bradley-Terry, win-rate, Markov, tournament sort), a narrower real-LLM supporting stream (SciDocs/HotpotQA/FiQA pilots), nDCG as the effectiveness metric, cyclicity/SCC/FAS-weight-removed/BEW/PIC as structural diagnostics, and paired bootstrap CIs for ΔnDCG.

- **Reusable:** Yes, this is accurate and dataset citations (`cohan2020scidocs`, `maia2018fiqa`, `yang2018hotpotqa`, `su2024bright`, `thakur2021beir`) are directly usable. **Correction:** the IJCS source's `su2025bright` entry cited an unverified ICLR 2025 OpenReview submission; corrected to `su2024bright`, the verified arXiv preprint (see `README.md`).
- **Requires rewriting:** Must add: the pooled baseline grid comparison against CombSUM/RRF (`final_baseline_comparison.csv` — not present in the IJCS version at all, since it predates the `final_method_gap_audit` work) and the failure taxonomy (`failure_class_audit`) — both are new JDIQ contributions absent from IJCS.
- **Obsolete claim:** None found; the IJCS text already correctly separates "primary comparison" (repaired vs unrepaired) from "broader contextual baselines" and already flags the real-LLM stream as narrower/secondary — consistent with reviewer concerns R3/R4/R8 having been reconstructed *from a version of this same argument*, suggesting reviewers wanted **more**, not a correction of an error.
- **Canonical evidence needed to verify:** `outputs/pub_vote_cmp_all4/paper_package/`, `outputs/openai_*` (pilot query counts match: SciDocs 50q, HotpotQA 20q, FiQA 10 processed — consistent with `docs/related_work_positioning_note.md` and `TABLE_PLAN.md` Table 9).
- **Disposition:** Reuse dataset/regime/metric descriptions as verified technical prose; the new manuscript must go further by adding the pooled baseline grid and failure taxonomy that IJCS lacked.

### §5 Results and Discussion (all three subsections + tables)

**Summary:** Reports mean nDCG by dataset/regime/method (Table "Overall Retrieval Performance"), cyclicity/SCC by regime (Table "Cyclicity and Structural Effects"), and bootstrap ΔnDCG for Copeland repaired-vs-unrepaired (Table "Repair Effect Delta nDCG"). Explicitly states repair is inactive in `ms2`/`ms1_drop_mutual`, mixed in `ms1`, and that HotpotQA is the only dataset with a CI that does not include a negative value, described cautiously ("Even this case should be interpreted cautiously... dataset-specific rather than general").

- **Reusable:** The **numbers** are directly reusable (already verified to match canonical all4 tables exactly). The **cautious interpretive language** around HotpotQA is a model of the tone the new manuscript should use — it independently arrived at language very close to `FIGURE4_SPECIFICATION.md`'s "does not cross zero below" framing (see `papers/JDIQ_2026/figure4_evidence/`).
- **Requires rewriting:** Yes — this section entirely lacks the failure taxonomy (why repair is inactive/harmful in specific mechanistic terms), the pooled baseline grid showing CombSUM/RRF beat repaired Copeland, and any CARB material. These are the primary *new* contributions that must be added, not reused from IJCS.
- **Obsolete claim:** None found in the reused numbers.
- **Canonical evidence needed to verify:** Already cross-checked: IJCS Table "Repair Effect Delta nDCG" values match `table_bootstrap_delta_ndcg.csv` row-for-row (SciDocs, FiQA, HotpotQA, BRIGHT × ms2/ms1/ms1_drop_mutual, Copeland pair).
- **Disposition:** Numbers safe to reuse/re-derive from canonical source directly (not by copying IJCS's table, but by re-pulling from `outputs/pub_vote_cmp_all4/` as this task's evidence hierarchy requires) for the future Results sections; interpretive tone is a good model.

### §6 Limitations

**Summary:** States conclusions are conditional (not a universal ranking principle); flags that the greedy FAS heuristic is not exact-optimal; flags that the main preference evidence is score-derived (BM25/TF-IDF/MiniLM), not direct human/LLM judgments; flags the real-LLM evidence is narrower than the canonical package.

- **Reusable:** Yes, as a starting point — three of these four limitations map directly onto reviewer concerns R3 (ranker set too narrow), R4 (real-LLM too small), R6 (greedy FAS not compared to stronger methods).
- **Requires rewriting:** Must be expanded substantially: BEW/PIC qrels-circularity (R12) is **not mentioned at all** in the IJCS limitations section — this is a significant gap the new Threats to Validity section (§11, out of scope here but noted for later) must close, per `docs/THREATS_TO_VALIDITY.md` item 2 and reviewer criticism R12. `ms1_drop_mutual` being ad hoc (R13) is also not explicitly flagged in IJCS.
- **Obsolete claim:** None.
- **Canonical evidence needed to verify:** `docs/THREATS_TO_VALIDITY.md`, `reviewer_criticism_inventory.csv`.
- **Disposition:** Useful skeleton for the future §11 Threats to Validity (out of scope for this task); do not treat as sufficient on its own — it is missing the BEW/PIC circularity caveat that JDIQ reviewers will expect given the venue's DQ/measurement rigor expectations.

### §7 Conclusions and Future Research

**Summary:** Restates the conditional finding; frames preference graphs as "a useful common representation for studying reranking signals"; lists future work (broader real-LLM evaluation, exact-vs-greedy FAS comparison, more systematic preference-construction study, adaptive repair-decision policies).

- **Reusable:** Partially, as a list of legitimate future-work items consistent with what the repository has since partially delivered (exact-vs-greedy comparison now exists in `final_method_gap_audit/task2/`; adaptive policy work exists in `outputs/adaptive_repair_policy/`, labeled exploratory/Discussion-only per `SECTION_EVIDENCE_MAP.csv`).
- **Requires rewriting:** Yes — must be updated to reflect that several of these "future work" items are now *done* (exact-vs-greedy, broader real-LLM across 3 datasets, CARB) and repositioned as completed contributions rather than future work.
- **Obsolete claim:** The future-work framing is itself now partially obsolete (superseded by completed work), not incorrect.
- **Canonical evidence needed to verify:** `experiments/final_method_gap_audit_20260711_221113/task2/`, `outputs/adaptive_repair_policy/`, `experiments/created_data_audit_20260711_232004/`.
- **Disposition:** Do not reuse directly; the new Conclusion (out of scope for this task) should acknowledge these as delivered, not pending.

### Declarations / Acknowledgements / Data availability statement

**Summary:** States AI-assisted drafting with author verification; no funding; no conflict of interest; code repository URL given (`github.com/SoroushVahidi/consistency-aware-llm-rankin`, matching this repository's `origin` remote); data/code available on request.

- **Reusable:** Yes, as a template for the future Data Availability section, but must be **anonymized** for JDIQ double-blind review (remove the named GitHub URL and author identity per `JDIQ_GUIDELINE_SUMMARY.md` §5 anonymization checklist) until camera-ready.
- **Requires rewriting:** Yes — anonymize; add CARB-specific data availability language (not present in IJCS, since CARB did not exist at IJCS submission time).
- **Obsolete claim:** None.
- **Canonical evidence needed to verify:** N/A (administrative).
- **Disposition:** Template only; not reused verbatim in this task since the manuscript skeleton uses `anonymous,review` mode.

### `references.bib` (734 lines, DOI-complete)

**Summary:** A fully-formed, DOI-complete BibTeX file covering rank aggregation theory (Dwork, Ailon-Charikar-Newman, Kenyon-Mathieu, Fagin), preference/comparison models (Bradley-Terry, Luce, Plackett, Mallows), graph/spectral ranking (Rank Centrality, Hodge theory, PageRank, EigenTrust), fusion (RRF, CombSUM-adjacent, Condorcet fusion), classical LTR (RankNet), dataset papers (SciDocs/SPECTER, FiQA, HotpotQA, BRIGHT, BEIR), and modern LLM reranking (RankGPT/PRP-family, RankZephyr, Setwise, FIRST, ListT5, HYRR, DAPR, LitSearch).

- **Reusable:** Yes, directly — this is exactly the kind of "established literature already present in the repository" the task instructs to draw from for `references.bib`.
- **Requires rewriting:** None (entries are well-formed); only a subset actually cited in the new Introduction will be copied over (task instruction: "Only include references actually cited in the Introduction").
- **Obsolete claim:** N/A (bibliography, not claims).
- **Canonical evidence needed to verify:** N/A.
- **Disposition:** Primary source for `references.bib` in this task; entries actually used are listed in that file and cross-referenced in `README.md`.

---

## Summary disposition table

| Section | Reusable? | Needs rewriting? | Obsolete claim found? | Disposition |
|---|---|---|---|---|
| Abstract | Partial (finding only) | Yes, full DQ reframe | No | Paraphrase finding only |
| §1 Introduction | No (framing only) | Yes, full rewrite | No | Not reused; written fresh in this task |
| §2.1 Related Work (LTR/reranking) | Yes | Minor (add DQ bridge) | No | Background for future §2 |
| §2.2 Related Work (preference/graph ranking) | Yes | No | No | Background for future §2 |
| §3.1 Problem Setting (notation) | Yes | No | No | Reuse notation directly |
| §3.2 Preference Graph Construction | Yes | No | No | Reuse regime definitions |
| §3.3 Repair and Extraction (formulas) | Yes | No | No | Reuse formulas directly |
| §4 Experimental Setup | Yes | Yes, add baseline grid + failure taxonomy | No | Extend, don't just reuse |
| §5 Results and Discussion | Numbers yes, prose partial | Yes, add new contributions | No | Re-derive numbers from canonical source |
| §6 Limitations | Partial (skeleton) | Yes, add BEW/PIC circularity, ms1_drop_mutual caveat | No | Skeleton only |
| §7 Conclusions | Partial (future-work list) | Yes, reposition as delivered | Partially (superseded) | Not reused directly |
| Declarations | Yes (template) | Yes, anonymize | No | Template only |
| `references.bib` | Yes | No | N/A | Primary bibliography source |
