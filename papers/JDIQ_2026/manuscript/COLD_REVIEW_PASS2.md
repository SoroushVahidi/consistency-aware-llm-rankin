# Cold External Reviewer Simulation — Finalization Pass 2

This document simulates three JDIQ-style reviewers reading the manuscript
independently, after the Pass 2 revisions to the Introduction, contributions,
Related Work, Discussion, Limitations, and Conclusion. For each reviewer:
strongest point, weakest point, and likely criticism, followed by the
revision made (if any) in response.

---

## Reviewer A — Information Retrieval researcher

**Strongest point.** The paper isolates a real and underexamined confound in
multi-ranker retrieval evaluation: that a weighted preference graph built
from heterogeneous ranker scores can be dominated by whichever ranker has the
largest native score range (BM25 conditional edge-weight share of 0.988
raw vs. 0.512 normalized). This is a concrete, reproducible diagnostic that
generalizes past this paper's specific repair method to any score-fusion
pipeline, and the paper says so explicitly.

**Weakest point.** All graph-independent baselines (Prior, RRF, CombSUM,
Borda) and all graph-dependent extraction rules (Copeland, balance, Markov)
are classical, unlearned combination rules. A reader whose mental model of
"strong IR baseline" includes cross-encoder rerankers or learned fusion may
read the paper's central claim — "simple fusion baselines remain strong" —
as true only within a comparison set that already excludes the strongest
modern alternatives.

**Likely criticism.** "Why should a reader care that feedback-arc-set repair
does not reliably beat RRF/CombSUM, when production retrieval systems
increasingly rely on cross-encoder or LLM rerankers rather than either
method? Is this a null result about a narrow corner of the design space?"

**Revision made.** The Limitations section now contains an explicit bullet,
"The evaluated methods do not include learned fusion, cross-encoder
rerankers, or online evaluation," naming this scope boundary directly rather
than leaving a reader to infer it from the baseline table. Section 3.6
(`sec:baselines`) already stated that establishing "absolute retrieval
leadership against modern cross-encoder or LLM rerankers... would require a
different experimental design"; the Limitations bullet now makes the same
point in the section reviewers check first, and adds that a learned-fusion
comparator specifically could absorb the scale-comparability problem
automatically, so the paper does not claim graph repair is competitive with
that class of method. We did not add a new experiment, per the task
constraint that experiments are out of scope for this pass.

---

## Reviewer B — Graph algorithms researcher

**Strongest point.** The exact-vs-greedy robustness check is unusually
rigorous for an empirical retrieval paper: an open-source MIP solver (SCIP)
is run to proven optimality on 1,025 of 1,026 query-regime graphs, cross-checked
against brute-force enumeration on 49 held-out graphs, and the paper reports
that greedy cycle-peeling selects a different removed-edge set than the exact
solution on 87.9% of cyclic queries while removing 26.3% less weight on
average — a real, quantified sub-optimality bound that most FAS-adjacent
empirical papers do not attempt.

**Weakest point.** The paper explicitly disclaims any algorithmic
contribution to feedback arc set itself: no new solver, no new approximation
bound, no structural characterization of which instances are hard. From a
graph-algorithms standpoint, the FAS problem is used purely as a downstream
tool, and the paper's substantive contribution is measurement methodology,
not graph theory.

**Likely criticism.** "This reads as an empirical measurement paper that
happens to use feedback arc set as one processing stage, not a paper with a
graph-algorithms contribution. Is a data-quality journal (JDIQ) the right
venue, or would a reviewer expecting algorithmic novelty be disappointed by
the framing?"

**Revision made.** This criticism is substantially pre-empted by design
rather than something to patch: the paper's contribution list (Introduction)
and Related Work opening paragraph both state directly that "we do not
introduce a new feedback-arc-set solver, a new retrieval ranker, or a new
fusion rule," and the CCS concepts and keywords are already anchored on data
cleaning, data quality, and retrieval/ranking rather than combinatorial
optimization. No change was needed beyond the Pass 2 contribution-list
rewrite, which sharpens this same disclaimer into an explicit itemized list
so a graph-algorithms reviewer encounters the scope boundary in the first
page rather than inferring it from the body text.

---

## Reviewer C — Data quality researcher

**Strongest point.** The paper's separation of "intrinsic graph diagnostics"
(cyclicity, mutual-pair rate, SCC size, removed weight) from "qrels-anchored
diagnostics" (BEW, PIC) is exactly the kind of derived-artifact audit a
data-quality venue should reward, and the empirical finding that these two
families move independently — a graph can change on 119/120 queries while
nDCG changes on only 8 — is a well-evidenced, non-obvious data-quality
result in its own right.

**Weakest point (pre-revision).** Despite using "data quality" in the title
framing and CCS concepts, the manuscript's Related Work did not connect its
own intrinsic/extrinsic diagnostic split to the established data-quality
dimensions literature. A JDIQ reviewer steeped in that literature would
likely ask why the paper reinvents vocabulary (cyclicity, mutual pairs)
without anchoring it to prior data-quality frameworks.

**Likely criticism.** "The paper claims a data-quality contribution but
does not cite the foundational data-quality dimensions literature (e.g.,
intrinsic vs. contextual data quality). Without that anchor, 'data quality'
reads as a label of convenience rather than an engaged research tradition."

**Revision made.** Added Wang and Strong's foundational data-quality
dimensions paper (*Beyond Accuracy: What Data Quality Means to Data
Consumers*, JMIS 1996) to the Related Work "Derived-artifact data quality"
paragraph, explicitly mapping this paper's intrinsic graph diagnostics vs.
qrels-anchored diagnostics onto Wang and Strong's intrinsic vs. contextual
data-quality distinction. This is a single, well-targeted citation — not a
bibliography dump — chosen because the paper's own terminology already
aligned with that framework closely enough to make the connection
substantive rather than decorative.

---

## Citations added in Pass 2 (all verified against primary/authoritative
sources before insertion; none fabricated)

| Key | Work | Verified against |
|---|---|---|
| `plackett1975analysis` | Plackett, "The Analysis of Permutations," JRSS-C 24(2), 1975 | Wiley/Oxford Academic, DOI 10.2307/2346567 |
| `luce1959individual` | Luce, *Individual Choice Behavior*, Wiley, 1959 | Standard citation confirmed across multiple academic sources |
| `benham2017risk` | Benham & Culpepper, "Risk-Reward Trade-offs in Rank Fusion," ADCS 2017 | ACM DL, DOI 10.1145/3166072.3166084 |
| `bruch2023analysis` | Bruch, Gai & Ingber, "An Analysis of Fusion Functions for Hybrid Retrieval," ACM TOIS 42(1), 2023 | ACM DL, DOI 10.1145/3596512 |
| `wang1996beyond` | Wang & Strong, "Beyond Accuracy: What Data Quality Means to Data Consumers," JMIS 12(4), 1996 | Taylor & Francis, DOI 10.1080/07421222.1996.11518099 |

No citations were removed. No experiments were changed. All five additions
are cited in text, explained in context, and connected to a specific claim
already present in the manuscript.
