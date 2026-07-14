# Pre-Submission Critical Review — JDIQ Simulation

**Method:** Three independent reviewer personas read `main.tex` cold, exactly as
submitted, with **no repository access** — only what a real JDIQ reviewer would
see. Findings below are anchored to specific sentences/line locations in the
current manuscript. This document does not modify the manuscript; per
instruction, no figures were touched and no edits were made.

---

# 1. Reviewer 1 — Senior IR Researcher (rank fusion, LTR, evaluation, BEIR/TREC, statistics)

## Summary
The paper argues that preference-graph feedback-arc-set (FAS) repair effects
are not invariant to how the underlying preference graph is constructed from
heterogeneous ranker scores, and that after correcting an unstable raw-margin
weighting scheme with per-query/per-ranker min-max normalization, no
repaired-vs-unrepaired retrieval improvement survives paired testing and
multiplicity correction across four BEIR-family/adjacent benchmarks.

## Strengths
- The BM25-dominance diagnosis (0.988 → 0.512 conditional weight share) is a
  concrete, well-quantified motivating observation.
- Statistical discipline is genuinely strong: paired permutation tests,
  bootstrap CIs, Holm/BH correction, leave-one-out and influence-removal
  analysis are all present and consistently applied.
- Honest null-result framing; the paper does not oversell a negative finding,
  which is refreshing and appropriate for a data-quality venue.
- CombSUM and RRF are retained as comparators throughout rather than dropped
  once graph methods are introduced.

## Weaknesses

### Major
1. **The paper is explicitly framed as a revision of an unnamed, uncited "original study."** The
   phrase "the original study" (and variants "original narrative," "the
   manuscript's earlier raw-margin version," "the manuscript's original
   title") appears at least nine times, including in the Abstract, the
   Introduction, the Discussion, and twice in the Conclusion — and it is
   **never cited or identified**. As a reviewer with no access to any prior
   version, I cannot assess what has changed, how large the contribution is
   relative to that baseline, or whether this is a resubmission I should have
   been given context for. This alone makes "novelty" and "relative
   contribution" impossible to evaluate rigorously as written.
2. **Single metric family.** Every quantitative result in the paper is nDCG.
   For a paper this focused on statistical robustness, the absence of MRR,
   MAP, or Recall@k as at least a robustness cross-check is a real gap —
   especially since the paper's own central claim ("no effect survives
   correction") would be more convincing if it also held under a
   binary-relevance metric family, not just graded nDCG.
3. **No modern reranking baseline.** Prior/RRF/CombSUM/Borda are all
   classical fusion methods contemporaneous with early 2000s TREC. There is
   no cross-encoder, no learned reranker, and no LLM-based reranking baseline
   in the main comparison (the LLM material is explicitly bounded/exploratory
   and excluded from the main evidence). For a 2020s retrieval venue, the
   practical-significance argument ("simple baselines remain strong") would
   land harder against at least one modern learned baseline.
4. **HotpotQA's usable query count (n=52) is thin** for the paired,
   multiplicity-corrected inferential framework applied here, and it is the
   dataset most discussed as a "positive point estimate" case before being
   walked back by influence analysis. The paper acknowledges this in
   Limitations ("statistical power... remain limiting factors") but the
   headline structure of §6.1–6.2 still spends a full page building up and
   then deflating the HotpotQA result, which reads as more dramatic than the
   n=52 sample size supports.

### Minor
5. Table 9 reports Prior and RRF as separate rows differing "only" in
   tie-breaking, yet their exact rankings match in just 216 of 6,156
   comparable cases (§6.3) — this is presented almost as a footnote, but it
   is a surprisingly large practical divergence for what is described as a
   near-duplicate implementation detail, and deserves at least one sentence
   of explanation for why tie-breaking alone produces that much disagreement.
6. The candidate-pool RRF parameter $k=60$ is used three separate times
   (pooling, Prior, RRF baseline) with no citation or ablation for why 60 was
   chosen specifically.
7. Figure 10's per-panel $y$-axis rescaling is disclosed in the caption, but
   a reader skimming figures only (as many will) could easily misread
   cross-dataset bar-height comparisons; consider a shared note directly on
   the figure, not only in prose.

## Questions for authors
- What is "the original study"? If it cannot be named for anonymity, please
  say so explicitly (standard double-blind phrasing exists for this) rather
  than referring to it as if the reader already knows.
- Do the paper's conclusions (no robust repaired-vs-unrepaired effect) hold
  under MRR/MAP/Recall, or only under nDCG?
- Why $k=60$ for RRF specifically?

## Confidence: 4/5
## Score: 5/10
## Recommendation: **Weak Reject** (would move to Weak Accept if the unnamed-prior-work issue is resolved and at least one additional metric family is reported)

---

# 2. Reviewer 2 — Senior Algorithms Researcher (graph algorithms, FAS, tournaments, approximation, optimization)

## Summary
The paper formalizes a weighted preference graph, the minimum weighted
feedback arc set (MWFAS) objective, a greedy cycle-peeling heuristic used for
all main experiments, and a supplementary exact-ILP robustness check on the
same instances. It is explicitly not proposing a new algorithm.

## Strengths
- The MWFAS objective (Eq. 9) is stated correctly and the paper is unusually
  careful — better than most applied papers in this space — about *not*
  calling the greedy heuristic "exact" anywhere in the main results.
- The exact-vs-greedy robustness check (open-source SCIP MILP, 1,025/1,025
  queries solved to proven optimality, cross-checked against brute-force
  enumeration on 49 instances) is genuinely well-executed empirical due
  diligence that most applied FAS papers skip entirely.
- The mutual-pair vs. nontrivial-cycle decomposition (§3.6) is a clean,
  useful structural distinction that is not always made in this literature.

## Weaknesses

### Major
1. **MWFAS's NP-hardness is never stated or cited.** Karp's classical
   NP-completeness result for feedback arc set is foundational to any paper
   invoking "exact minimum-weight feedback arc set" as an optimization
   target; its absence is a real gap for an audience that includes
   algorithms researchers, and it undersells *why* a heuristic is used at
   all in the main experiments.
2. **The greedy heuristic is not related to prior FAS heuristic literature.**
   "Repeatedly find a cycle, remove its minimum-weight edge" closely
   resembles — but is not identical to — the well-known Eades–Lin–Smyth
   greedy FAS heuristic and its many descendants. Neither that line of work
   nor any approximation-ratio discussion (even a negative one, i.e. "no
   known worst-case bound applies to this exact variant") is cited. A
   reviewer in this subfield will read "greedy cycle peeling" and
   immediately ask "how does this relate to the classical greedy heuristics
   for this exact problem," and the paper does not answer that question
   anywhere.
3. **The exact-ILP formulation itself is never shown.** §4.4 states that an
   MILP solver was used to solve MWFAS exactly but never presents the
   formulation (e.g., a linear-ordering/precedence-variable encoding) or
   reports model size (variables/constraints as a function of $n$) or solve
   times. For an algorithms audience, "we solved it exactly with SCIP" without
   showing the encoding is under-specified; even three lines of formulation
   (as the notation table's own $F_{\text{opt}}$ definition invites) would
   resolve this.
4. **The Markov/Rank-Centrality score's ergodicity is asserted, not
   established.** §3.9 states the Markov score is "the stationary
   distribution of a Rank-Centrality-style Markov chain with damping 0.15,"
   applied to both repaired (acyclic) *and* unrepaired (possibly cyclic,
   possibly disconnected) graphs. A stationary distribution is guaranteed to
   exist and be unique only under ergodicity (irreducibility + aperiodicity);
   the damping term likely provides this (as in PageRank), but the paper
   never says so, and it is ambiguous whether "damping 0.15" denotes the
   teleportation probability or its complement. This should be a single
   clarifying sentence, not a hidden assumption.

### Minor
5. The notation table defines $u \succ v$ ("pairwise preference: $u$ ranked
   ahead of $v$") but this symbol is never used again anywhere in the paper's
   body — it is dead notation and should be removed or actually used.
6. "Kemeny-style objectives" is invoked twice (Introduction, §2) but Kemeny's
   original work is never cited — only later papers that build on it
   (Dwork et al., Ailon et al., Kenyon-Schudy, Fagin et al.). A reviewer
   in rank aggregation will notice the eponym without the citation.
7. The noisy-pairwise-comparison-ranking related-work paragraph (§2) cites
   only Rank Centrality; the Bradley–Terry/Plackett–Luce family, arguably
   the more classical reference point for "noisy pairwise preferences," is
   absent.
8. Eq. 9's $\arg\min$ is not guaranteed unique; the paper implicitly resolves
   this by reporting "a" removal set $F$, which is fine, but a one-clause
   note would remove ambiguity for a theory-minded reader.

## Questions for authors
- What is the ILP formulation actually used (variables, constraints), and
  what were typical solve times as a function of $n$?
- Is the Markov chain provably ergodic on unrepaired (possibly cyclic,
  possibly disconnected) graphs under the stated damping value, and which
  direction does "damping 0.15" apply?
- How does "greedy cycle peeling" relate to the Eades–Lin–Smyth heuristic
  and its descendants — is it a reimplementation, a variant, or unrelated?

## Confidence: 5/5
## Score: 6/10
## Recommendation: **Borderline** (the algorithmic content is secondary to the paper's actual contribution, but the paper invokes graph-theoretic framing prominently enough — MWFAS, exact solvers, NP structure — that omitting standard context here will draw exactly this kind of criticism from any algorithmically literate reviewer)

---

# 3. Reviewer 3 — Senior Reproducibility / Data-Quality Researcher

## Summary
A methodologically self-aware data-quality paper about preference-graph
construction, with an unusually candid limitations section and a genuinely
good-faith audit of a secondary LLM-judgment corpus that the authors
correctly decline to treat as confirmatory evidence.

## Strengths
- The retention-matching methodology explicitly states it is "an
  experimental control... not a claim about optimal threshold selection"
  and explicitly flags an unperformed sensitivity analysis rather than
  omitting it or claiming it was done — exactly the right way to handle an
  acknowledged gap.
- The real-LLM section is a model of "here is exactly what is wrong with
  this secondary data and why we don't use it as evidence" — parser default
  rates, opposite-direction position bias, forward/reverse disagreement, and
  a quantified demonstration that most of a naive LLM-judgment graph's
  cyclicity is a pipeline artifact. This is better practice than the vast
  majority of papers that use LLM judges without auditing them at all.
- Terminology precision: the paper explicitly disclaims that "calibration"
  in this paper is not the probabilistic sense (Platt scaling, isotonic
  regression) — a real, easy-to-miss precision issue that most papers in
  this space get wrong silently.
- The Limitations section (§9) is unusually thorough: ten distinct,
  specifically-named limitations rather than a generic paragraph.

## Weaknesses

### Major
1. **No anonymized repository link.** "For double-blind review, the
   repository identity and URL are withheld; an anonymized or
   author-provided artifact will be made available to reviewers upon
   request" (§4.6, §11) is markedly weaker than current norms at
   reproducibility-focused venues, which increasingly expect an anonymized
   mirror (e.g., an anonymous.4open.science link) submitted alongside the
   paper, not "upon request" after the fact. For a paper whose entire
   contribution is a *methodological* correction to someone else's protocol,
   reviewers cannot verify a single reported number without this.
2. **The unnamed "original study" is also a reproducibility/provenance
   problem, not just a novelty problem.** If this paper corrects a specific
   predecessor's methodology, provenance norms require that predecessor be
   identifiable — even under anonymization conventions (e.g., "our prior
   work, citation withheld for review"). As written, a reader cannot tell
   whether "the original study" is the authors' own earlier work, a
   third-party paper being critiqued, or an internal baseline that was never
   published at all. This is a transparency failure independent of the
   novelty concern raised by Reviewer 1.
3. **No stated random seeds.** §4.5 says "it uses fixed seeds for bootstrap
   and permutation analysis" but never states what those seeds are. For a
   paper this focused on statistical reproducibility, the actual seed
   values belong in the text (or at minimum the appendix), not just the
   claim that seeds were fixed.
4. **Query-exclusion is suspiciously asymmetric and unexplained.** Table 2
   shows zero queries excluded for SciDocs (120→120), FiQA (120→120), and
   BRIGHT (50→50), but 18 of 70 excluded for HotpotQA (70→52) — a 26%
   exclusion rate on exactly the dataset that later drives the paper's most
   discussed (and ultimately non-robust) positive point estimate. The paper
   never explains why HotpotQA's eligibility filter bites so much harder
   than the other three, which invites a reviewer to wonder whether this
   asymmetry interacts with the influence-sensitive HotpotQA result
   discussed at length in §6.2.

### Minor
5. Terminology inconsistency undercuts the terminology-precision strength
   above: the Abstract and Introduction write "min-max normalization" (plain
   hyphen) while every other section (Methodology, Results, Discussion,
   Limitations, Conclusion) writes "min--max" (en dash) — a small but very
   visible inconsistency in a paper whose title itself foregrounds
   "Normalization" as the precise term.
6. Similarly, "TF--IDF" (en dash) appears once (§5.1) against eight other
   instances of "TF-IDF" (hyphen) elsewhere.
7. No software environment/dependency manifest (e.g., a pinned
   requirements file or container) is referenced in-text beyond "Python
   3.12.3 using networkx" — reasonable for the mechanical pipeline, but
   thin for a reproducibility-focused reviewer.
8. The real-LLM section's precise statistics (1.1% parser default rate,
   53–58%/61–70% position bias, 59–85% forward/reverse agreement) are
   reported to a level of numerical precision that a reviewer without
   artifact access cannot verify at all, for data the paper itself says is
   not canonical evidence — consider whether this level of quantitative
   detail belongs in the main text versus an appendix, given its explicitly
   bounded evidentiary status.

## Questions for authors
- Can an anonymized repository mirror be provided for review rather than
  "upon request"?
- What are the actual bootstrap/permutation seed values?
- Why is HotpotQA's query-exclusion rate (26%) so much higher than the
  other three datasets (0% each), and does this interact with HotpotQA's
  influence-sensitive positive point estimate?

## Confidence: 5/5
## Score: 6/10
## Recommendation: **Borderline** (methodologically the most careful of the paper's dimensions, but the provenance/anonymization gap around "the original study" and the absence of an anonymized artifact link are real barriers to a confident accept from a reproducibility-focused reviewer)

---

# 4. Area Chair Meta-Review

## Genuine consensus across all three reviewers
- **All three independently flagged the unnamed "the original study" /
  "the manuscript's original title" framing** as a real problem, from three
  different angles (novelty assessment, provenance, and general reader
  comprehension). This is the single strongest, least disputable finding in
  this review round precisely because three reviewers with non-overlapping
  expertise converged on it without prompting each other.
- All three reviewers rate the statistical/methodological discipline
  (multiplicity correction, influence analysis, retention-matching honesty)
  as a genuine strength, not a coincidence — this is a well-executed paper
  *within* its own stated scope.
- All three flagged minor dash/hyphen inconsistencies independently
  surfacing as a symptom of the same underlying issue: prose written across
  multiple revision passes without a final normalization pass.

## Disagreements
- Reviewer 1 (IR) wants a modern reranking baseline and additional metrics;
  Reviewer 2 (algorithms) is largely indifferent to this and instead wants
  more graph-theoretic grounding (NP-hardness, approximation context, the
  ILP formulation itself). Reviewer 3 (reproducibility) cares about neither
  of these specifically but wants provenance and artifact-access fixes.
  These are genuinely orthogonal asks, not competing ones — none of them
  contradicts another, which makes them easier to address in one revision
  pass than if reviewers disagreed on substance.
- Reviewer 2's score (6/10, Borderline) is more generous than might be
  expected given four "Major" items, because the missing graph-theoretic
  context is a **contextualization gap**, not a correctness error — nothing
  Reviewer 2 found suggests the reported numbers are wrong, only that the
  algorithmic framing is under-cited for this specific audience.

## Overreactions to discount
- Reviewer 1's HotpotQA sample-size complaint (Major #4) is really a
  presentation-emphasis issue, not a validity issue — the paper *does*
  correctly walk the result back via influence analysis and explicit Holm/BH
  non-significance. The complaint is really "don't build up a page of
  narrative around a result you're about to deflate," which is a structural
  suggestion, not a statistical flaw.
- Reviewer 3's Minor #8 (real-LLM section precision) is a stylistic
  preference about section placement (main text vs. appendix), not a
  correctness concern; the paper is already maximally explicit that this
  data is non-canonical.

## Reviewer misunderstandings
- None identified. All three reviews are grounded in specific, quotable
  sentences from the manuscript as submitted; no reviewer appears to have
  misread a claim the paper does not actually make.

## Most likely editorial decision
**Major Revision.** The core empirical and statistical content is sound and
none of the three reviewers identified a correctness error in a reported
number or a methodological flaw that invalidates the central conclusion.
But the unnamed-prior-work issue is serious enough, and flagged
independently by all three reviewers, that no reasonable AC would recommend
Accept or Minor Revision until it is resolved — it currently makes the
paper's novelty and provenance impossible to fully evaluate as written. The
fix is almost entirely textual (Category A/B below), which is exactly the
profile of a Major-Revision-then-Accept trajectory rather than a Reject.

---

# 5. Author Rebuttal Analysis

For every Major criticism above, how it can realistically be resolved:

| # | Criticism | Reviewer(s) | Resolution type |
|---|---|---|---|
| 1 | Unnamed "original study" / "original title" never cited or identified | R1, R3, AC | **A. Rewriting** — either add a proper (possibly anonymized-placeholder) citation, or remove all "original study/earlier version" framing and present the protocol on its own terms |
| 2 | Only nDCG reported, no MRR/MAP/Recall | R1 | **E. Small analysis already possible from existing data** — the underlying per-query pipeline already computes rankings; recomputing MRR/MAP/Recall from stored rankings requires no new experiment, only new aggregation (this exact recomputation was already performed and verified once earlier in this project's history) |
| 3 | No modern/learned reranking baseline | R1 | **F. Requires a genuinely new experiment** — a cross-encoder or LLM reranking baseline would need new inference runs; not fixable from existing artifacts alone |
| 4 | HotpotQA narrative arc reads as more dramatic than n=52 supports | R1 | **A/B. Rewriting/reorganizing** — compress §6.1–6.2's HotpotQA build-up, lead with the influence-sensitivity caveat rather than trailing it |
| 5 | Prior/RRF 216/6,156 divergence under-explained | R1 | **D. Adding explanation** — one sentence on why tie-breaking alone produces this much rank churn |
| 6 | RRF $k=60$ unjustified | R1 | **C/D. Citation + explanation** — cite the source of this default (if inherited from the unnamed prior work, this again ties back to issue #1) |
| 7 | MWFAS NP-hardness not stated/cited | R2 | **C. Adding citation** — one sentence + Karp (1972) |
| 8 | Greedy heuristic not related to Eades–Lin–Smyth literature | R2 | **C/D. Citation + explanation** — one paragraph relating the two |
| 9 | ILP formulation not shown | R2 | **D. Adding explanation** — the formulation already exists in the artifact and can be added as a short equation block; no new experiment needed |
| 10 | Markov chain ergodicity/damping direction unstated | R2 | **D. Adding explanation** — one clarifying sentence |
| 11 | Dead notation ($u \succ v$) | R2 | **A. Rewriting** — remove or use it |
| 12 | Kemeny original work uncited | R2 | **C. Adding citation** |
| 13 | Bradley–Terry/Plackett–Luce uncited | R2 | **C. Adding citation** |
| 14 | No anonymized repository link | R3, AC | **B. Reorganizing/process fix** — provide an anonymized mirror at submission (not a text edit, but not a new experiment either) |
| 15 | No stated random seeds | R3 | **D. Adding explanation** — state the actual seed values already used |
| 16 | HotpotQA's asymmetric exclusion rate unexplained | R3 | **D. Adding explanation** — one sentence on why 18/70 HotpotQA queries fail eligibility versus zero elsewhere |
| 17 | min-max / min--max and TF-IDF / TF--IDF dash inconsistency | R3, AC | **A. Rewriting** — a global find-and-normalize pass |

**No criticism above requires abandoning or re-running the core experiments.**
The only genuinely new-experiment item is #3 (a modern reranking baseline),
and even that is optional rather than blocking, since the paper's claim is
about repair-vs-no-repair among graph methods, not "graph methods beat
everything."

---

# 6. Rejection Risk Analysis (highest to lowest)

| Risk | Real rejection risk? | Rationale |
|---|---|---|
| **Unnamed prior work / provenance** | **Yes — highest** | Independently flagged by all 3 reviewers from different angles; blocks confident novelty assessment |
| **No anonymized artifact link** | **Yes — high** | Reproducibility-focused venue; "upon request" is below current norm |
| **Single-metric evaluation (nDCG only)** | **Yes — moderate** | A real, fixable gap that a skeptical reviewer could hold the paper on |
| **Novelty concerns (measurement paper, not new method)** | **Partially** | JDIQ explicitly values data-quality/measurement contributions; this is a venue-fit strength, not weakness, *if* the paper is framed as standalone (which requires fixing #1 above) |
| **Weak/dated baselines (no modern reranker)** | **Moderate** | Real, but the paper's claim scope (repair vs. no-repair) doesn't strictly require it |
| **Limited datasets (4, one small)** | **Low-moderate** | Already disclosed candidly in Limitations; reviewers are more likely to note than reject over this alone |
| **Normalization choice (min-max, not learned)** | **Low** | Already extensively caveated as "a design choice, not a proven optimum"; unlikely to be a rejection driver given the caveat quality |
| **Retention matching** | **Low** | Already correctly scoped as an experimental control with an honestly flagged untested sensitivity gap |
| **Heuristic (not exact) repair in main results** | **Very low** | Directly and convincingly addressed by the exact-ILP robustness check; this is now a strength, not a risk |
| **LLM section scope** | **Very low** | Explicitly bounded/exploratory and clearly labeled; unlikely to draw a rejection on its own |
| **Figure clarity** | **Very low** | Just polished in a dedicated pass; no reviewer in this simulation flagged a figure-legibility issue |
| **Related-work completeness (Kemeny, Bradley-Terry, Eades et al.)** | **Low** | Real gaps (R2), but citation-only fixes, not structural risk |
| **Terminology (calibration vs. normalization)** | **Very low** | Already proactively disclaimed in-text; residual dash-inconsistency is cosmetic |
| **Statistical interpretation** | **Very low** | This is a genuine strength across all three reviews; no reviewer found a statistical error |
| **External validity** | **Low** | Already candidly scoped in Limitations |

**Bottom line:** the only two risks that plausibly drive a Reject rather than
Major Revision are the unnamed-prior-work framing and the missing
anonymized-artifact link — both fixable without new experiments.

---

# 7. Final Action List

## Category A — Critical, must fix before submission
1. **Resolve the "original study" / "original title" / "earlier raw-margin version" framing throughout** (Abstract, Introduction ×2, Discussion, Conclusion ×2, §4.4). Either (a) add a proper anonymized-placeholder citation consistent with double-blind norms ("our prior work, withheld for anonymous review"), or (b) remove the comparative framing entirely and present the calibrated protocol as this paper's own standalone contribution without repeatedly gesturing at an unnamed predecessor. This is the single highest-leverage fix in the entire manuscript.
2. **Provide an anonymized repository/artifact mirror at submission time**, not "upon request." This is a process action, not a text edit, but it is a precondition for a confident Accept from any reproducibility-minded reviewer.
3. **Fix the min-max/min--max and TF-IDF/TF--IDF dash inconsistencies** (a mechanical find-and-normalize pass; 2 + 1 occurrences respectively).

## Category B — Worth fixing (writing/presentation only)
4. Add MRR/MAP/Recall as at least a robustness cross-check to the main nDCG results (recomputable from already-stored per-query rankings, no new experiment).
5. Add one sentence citing Karp's NP-hardness result for feedback arc set.
6. Add one sentence relating the greedy heuristic to the Eades–Lin–Smyth line of work.
7. Show the exact-ILP formulation briefly (a few lines) rather than only naming the solver.
8. Clarify the Markov chain's ergodicity/damping direction in one sentence.
9. Remove or actually use the dead $u \succ v$ notation.
10. Add a Kemeny (1959) citation and a Bradley–Terry/Plackett–Luce citation to the related-work paragraphs that already invoke those concepts by name.
11. State the actual bootstrap/permutation random seed values.
12. Add one sentence explaining HotpotQA's disproportionate query-exclusion rate (18/70 vs. 0 elsewhere).
13. Add one sentence explaining the RRF $k=60$ choice and the Prior/RRF 216/6,156 tie-break divergence.
14. Compress the HotpotQA build-up in §6.1–6.2 so the influence-sensitivity caveat isn't structurally delayed to the very end.

## Category C — Do not change, current manuscript is stronger
- The exact-ILP robustness check and its framing (Table 4, §4.4, Limitations) — already a genuine strength; do not weaken or remove it.
- The real-LLM audit section's candor and quantitative specificity — already correctly scoped and disclaimed; do not soften it or hide the numbers, despite Reviewer 3's stylistic placement preference.
- The retention-matching honesty ("an experimental control, not a claim about optimal threshold selection... we have not evaluated... this is a recommended, not yet performed, sensitivity analysis") — do not remove this candor to appear more complete; it is exactly the right way to handle an acknowledged gap and reviewers explicitly praised this pattern.
- The Limitations section's length and specificity — do not compress it in the name of "sounding confident"; all three reviewers read it as a strength, not a weakness.
- The statistical-testing pipeline (permutation + bootstrap + Holm/BH + influence analysis) — no changes; this is the paper's best-executed dimension.

---

# 8. Sentence-Level "Pause and Doubt" Pass

Read cold, as if by an unrelated group, start to finish. Every sentence that
caused a stop, a re-read, or a doubt — quoted exactly, with the reason and a
rewrite.

> **"...evaluation pipeline as the original study while replacing its unstable raw-margin weighting..."** (Abstract)
Why it stops the reader: "the original study" is not identified anywhere in
the paper, yet the entire abstract is framed as a correction to it. A reader
has no way to judge the delta.
Rewrite: *"...evaluation pipeline used in our prior mechanical vote-based
protocol (citation withheld for anonymous review), while replacing its
unstable raw-margin weighting..."* — or remove the comparative frame
entirely and state the protocol as this paper's own.

> **"This paper revisited a narrower question than the manuscript's original title implied..."** (Conclusion, opening sentence)
Why it stops the reader: this is the single most confusing sentence in the
paper. The title on page 1 ("Score Normalization and Vote Construction
Govern...") does not imply anything broad — it is already narrow and
carefully hedged. This sentence appears to be a leftover artifact from an
internal revision process, referencing a title the reader was never shown.
Rewrite: *"This paper asks a narrower question than 'does preference-graph
repair help retrieval': namely, how that answer depends on the
graph-construction protocol used to define pairwise evidence in the first
place."*

> **"...support a more specific conclusion than the manuscript's earlier raw-margin version..."** (Discussion, opening sentence)
Why it stops the reader: same issue as above — references a version of this
manuscript the reader has not seen and will never see.
Rewrite: *"...support a conclusion that is more specific than a naive
'repair either helps or it doesn't' framing would suggest:..."*

> **"The revised study has a clearer limitations profile than the earlier raw-margin version, but it still has important boundaries."** (Limitations, opening sentence)
Why it stops the reader: third occurrence of the same pattern; by this point
a careful reviewer is actively wondering whether they were supposed to have
read a different, earlier paper first.
Rewrite: *"This study's limitations fall into several categories, detailed below."*

> **"...its conditional mean weight share was approximately 0.988, versus approximately 0.512..."** (Abstract)
Why it stops the reader: "approximately" paired with three-decimal precision
reads as an internal inconsistency — either the number is exact enough to
state plainly, or it is approximate enough that the precision should be
reduced.
Rewrite: *"...its conditional mean weight share was $0.988$, versus $0.512$
under the calibrated primary protocol"* (drop "approximately"; the precision
already communicates that these are measured means, not round targets).

> **"...cyclic-query prevalence is approximately $0.3495$ before mutual-pair deletion and $0.1100$ afterward."** (§5.3)
Why it stops the reader: same approximately-plus-four-decimals mismatch as
above.
Rewrite: *"...cyclic-query prevalence is $0.3495$ before mutual-pair deletion
and $0.1100$ afterward."*

> **"...not combining commensurate evidence from BM25, TF--IDF, and MiniLM."** (§5.1)
Why it stops the reader: "TF--IDF" (en dash) breaks the pattern of "TF-IDF"
(hyphen) used everywhere else in the paper, including three sentences
earlier in the same paragraph family.
Rewrite: *"...not combining commensurate evidence from BM25, TF-IDF, and MiniLM."*

> **"...per-query, per-ranker min-max normalization followed by retention-matched vote and edge thresholds."** (Abstract) and **"...per-query, per-ranker min-max normalization followed by retention-matched thresholding."** (Introduction)
Why it stops the reader: both instances use a plain hyphen ("min-max") while
every other occurrence in the paper (10+ times) uses an en dash ("min--max"),
including the paper's own title-adjacent framing.
Rewrite: normalize both to "min--max" (or normalize the whole paper the other
direction — either is fine, but pick one).

> **"...the balance-family zero-delta pattern in this study reflects propagation failure through the ranking pipeline rather than a theorem that balance-based repair can never matter."** (Discussion)
Why it stops the reader: "a theorem that... can never matter" is an unusual,
slightly awkward construction for a claim that is really just "this is an
empirical pattern in this study, not a general impossibility result."
Rewrite: *"...reflects propagation failure through the ranking pipeline in
this study, not a general impossibility result for balance-based repair."*

> **"...its conditional mean weight share was approximately 0.988... The threshold-scale audit further shows that the fixed raw thresholds were not semantically comparable across rankers..."** (§5.1)
Why it stops the reader: "the threshold-scale audit" is referenced as if it
were a previously introduced, named artifact, but no such audit has been
defined or shown anywhere in the paper before this sentence — it reads like
a dangling reference to an analysis that either got cut or was never
included.
Rewrite: *"A supporting analysis of the raw fixed thresholds (not shown)
further indicates they were not semantically comparable across rankers..."*
— or, better, actually show the analysis if it exists, since it is
referenced as supporting evidence for a load-bearing claim.

No further sentences triggered a stop on this pass; the remainder of the
paper reads as internally consistent prose once the "original study" /
"revised version" framing and the two dash inconsistencies are set aside.

---

# 9. Output Summary

## Acceptance probability estimate
**~30-35%** as currently written (Major Revision is the modal outcome, not
Accept or Reject). **~70-75%** after Category A fixes are applied, since none
of the identified issues touches the correctness of a reported number or the
validity of the statistical pipeline — they are entirely provenance,
citation, and consistency issues.

## Top ten remaining weaknesses
1. Unnamed, uncited "original study" the entire paper is framed against (Abstract, Intro, Discussion, Conclusion).
2. Dangling self-reference to "the manuscript's original title" in the Conclusion's opening sentence.
3. No anonymized repository/artifact link provided at submission.
4. Single metric family (nDCG only); no MRR/MAP/Recall cross-check.
5. No modern learned/LLM reranking baseline in the main comparison.
6. MWFAS's NP-hardness and the greedy heuristic's relationship to classical FAS heuristics (Eades–Lin–Smyth) never discussed.
7. Exact-ILP formulation named but never shown.
8. HotpotQA's 26% query-exclusion rate vs. 0% elsewhere is unexplained, on exactly the dataset driving the most-discussed (later-deflated) positive result.
9. Random seeds never stated numerically.
10. Dash/hyphen inconsistencies ("min-max" vs. "min--max"; "TF-IDF" vs. "TF--IDF") between Abstract/Introduction and the rest of the paper.

## Top ten strengths
1. Statistical rigor: paired permutation tests + bootstrap CIs + Holm/BH correction + influence/leave-one-out analysis, applied consistently.
2. Honest null-result framing; does not oversell a negative finding.
3. The BM25 scale-dominance diagnosis (0.988→0.512) is concrete, well-quantified, and genuinely motivates the whole paper.
4. The exact-ILP-vs-greedy robustness check is unusually thorough due diligence (full 1,025-query coverage, cross-checked against brute force), rare in applied FAS papers.
5. Mutual-pair vs. nontrivial-cycle decomposition is a clean, useful, underused structural distinction.
6. The real-LLM audit is a model of candor about a corpus's evidentiary limits rather than silently using it as confirmatory evidence.
7. Explicit terminology disclaimer distinguishing "calibration" (this paper's shorthand) from probabilistic calibration.
8. Ten distinct, specifically-named limitations rather than a generic disclaimer paragraph.
9. Retention-matching is correctly scoped as an experimental control with an honestly flagged, unperformed sensitivity analysis, rather than oversold or silently skipped.
10. Simple baselines (CombSUM, RRF) retained as first-class comparators throughout rather than dropped once graph methods are introduced.

## Exactly what should still be changed before submission
See Category A (3 items) and Category B (11 items) in §7 above. All are
writing/citation/consistency fixes or a process action (anonymized repo
link); none requires a new experiment except the optional modern-baseline
addition, which is not blocking.

## Final readiness score: **68 / 100**
Strong empirical and statistical core (would score 85+ on that dimension
alone), pulled down substantially by the unresolved provenance/citation gap
around "the original study," the missing anonymized artifact link, and a
handful of related-work/notation completeness gaps that are each individually
minor but collectively signal a manuscript that has not yet had a full,
cold, "would a stranger understand this" pass.

---

## Overnight status note (2026-07-13)

Retention-target sensitivity is **no longer** an untested gap: an existing policy sweep was integrated into Methods/Limitations. Do not reinstate the "not yet performed" phrasing.
