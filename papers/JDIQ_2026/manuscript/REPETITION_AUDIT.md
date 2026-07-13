# Repetition Audit

**Prepared:** 2026-07-12
**Scope:** Identify repeated claims across Abstract, Introduction, Results (§5–9), Discussion, Limitations, and Conclusion; decide keep-both/shorten/remove/cross-reference for each; apply the recommended edits. Edits already applied to `main.tex` are marked **[APPLIED]** below; all others were reviewed and judged appropriate to keep as-is, with the reasoning stated.

---

## 1. Structural consistency does not imply retrieval improvement (the central thesis)

**Where it appears:** Abstract; Introduction (three paragraphs); Background (§2, "Why structural repair need not improve retrieval quality"); every Results section (§5–9, as the running finding); Discussion (§11, as the organizing frame); Limitations (§12, as scope); Conclusion (§13).

**Decision: keep in all locations.** This is the paper's central thesis, not an incidental claim — a thesis is expected to appear in the Abstract (stated), Introduction (motivated and previewed), Background (explained mechanically), Results (evidenced empirically, once per section as the section's own finding), Discussion (synthesized across sections), and Conclusion (summarized). Removing it from any of these locations would leave that section unable to stand on its own, which is a stronger defect than the mild redundancy of restating a running thesis. The function differs meaningfully at each location: Background explains *why* the decoupling is mechanically possible (a conceptual argument); Results shows *that* it happens (empirical); Discussion explains *what it means* (interpretation); Conclusion states *what follows* (implication). No edit applied.

---

## 2. CombSUM/RRF outperforming repair-based methods

**Where it appears:** §6 Downstream Results (full statement with numbers, Table 6); §13 Conclusion (one-sentence summary).

**Decision: keep both, function differs, no shortening needed.** Two occurrences only, not excessive. §6 is the evidentiary location (with exact means and the pooled-protocol caveat); §13 restates the finding at summary grain without repeating numbers. No edit applied.

---

## 3. Repair inactivity

**Where it appears:** §5 (structural cause: near-acyclic regimes remove negligible weight); §6 (retrieval consequence: 20 of 24 cells null); §7 (failure-class name and definition, Table 7, Figure 6 placeholder); §9 (cost without benefit); §11 Discussion (mechanism synthesis); §13 Conclusion (summary).

**Decision: keep, but this is the most-repeated single idea in the paper and was checked most carefully.** Each location adds a distinct fact rather than restating the same sentence: §5 gives the structural precondition (near-zero weight removed), §6 gives the retrieval-level count (20/24), §7 gives the *labeled category* and its share of the pooled corpus (63.9%), §9 gives the efficiency angle (cost without benefit), §11 explains the causal chain connecting all three, §13 restates only at the one-sentence summary level. No two locations state the same fact in the same terms. No edit applied, beyond the general de-duplication already performed in Part 4 of this pass (removing repeated "canonical" framing language that surrounded several of these mentions).

---

## 4. Limited real-LLM evidence

**Where it appears:** Introduction (§1, one paragraph); §4.7 (scope-setting before the real evidence); §8 (full evidence + mandatory limitations paragraph); §11 Discussion (not separately restated — checked, absent); §12 Limitations (restated as a limitation).

**Decision: keep, with one trim applied. [APPLIED]** The original §12 Limitations paragraph re-derived the "dataset-dependent way not explained by cyclicity severity alone" phrase (which belongs to finding #1/Discussion, not to the real-LLM limitation specifically) inside its real-LLM-adjacent "no claim of universal external validity" paragraph, conflating two distinct limitations into one repeated phrase. Trimmed to a direct cross-reference to Section 11 instead of re-deriving the mechanism. See the diff: "No claim of universal external validity" paragraph in §12 now reads "The central findings summarized in Section~\ref{sec:discussion} are established on four datasets..." instead of restating the cyclicity-severity clause in full.

---

## 5. Absence of a validated selector / predictive criterion

**Where it appears:** §7 (one sentence, "not a validated predictive rule for deciding in advance..."); §11 Discussion (two sentences, explaining what a predictive criterion would require and that attempts give only modest signal); §12 Limitations (one sentence, restated as a limitation).

**Decision: keep all three — function differs and none restates the others verbatim.** §7's sentence is a narrow disclaimer attached to the taxonomy itself (the taxonomy is not a selector); §11's two sentences are the paper's only discussion of *what a predictive criterion would need to look like* (a distinct, forward-looking analytical point, not a restatement); §12's sentence is the shortest possible restatement for the Limitations list format, consistent with every other item in that list being a one-paragraph, self-contained restatement of a limitation already established elsewhere (by design — see `FULL_DRAFT_EVIDENCE_MAP.md`'s note that Limitations restates rather than introduces). No edit applied; the three serve the taxonomy, the theory, and the limitations-list format respectively.

---

## 6. CARB release

**Where it appears:** Introduction (§1, contribution list item 5); §10 (full description); §12 Limitations (licensing constraint only, not the full description); §13 Conclusion (one sentence); Data Availability (§ following Conclusion, availability-statement framing).

**Decision: keep all five — each is the minimum needed for its section to be self-contained, and none repeats CARB's full description.** Introduction previews it as a contribution (one clause); §10 is the only place with the full description (scope, provenance, statistics, release plan); §12 mentions only the licensing angle, not CARB generally; §13 restates at one-sentence grain; Data Availability states only the availability-relevant fact (not yet public). No two locations restate the same CARB fact in the same terms. No edit applied.

---

## Abstract vs. Conclusion: the one substantive redundancy found

**Finding:** the Abstract and Conclusion, considered as whole paragraphs, are structurally parallel (both cover: scope, structural-improves, retrieval-doesn't-reliably-follow, baselines-beat-graph-methods, failure-taxonomy, CARB, and a closing "we do not claim... structural consistency and retrieval X are separable/distinct" sentence) — and their **closing sentences were, before this audit, near-verbatim restatements of each other** ("We make no claim that structural repair is a generally superior retrieval strategy; the evidence instead supports treating structural consistency and retrieval quality as related but distinct measures..." vs. "We do not claim that structural repair is a generally superior retrieval strategy; the evidence assembled here supports a narrower and, we think, more useful conclusion: structural consistency and retrieval utility are separable dimensions of data quality...").

**Decision: keep both paragraphs' overall parallel structure (this is expected and correct for an Abstract/Conclusion pair — both are whole-paper summaries by design), but rewrite the Conclusion's closing sentence so it is not a near-copy of the Abstract's. [APPLIED]** The Conclusion's final sentence now ends on a distinct, practitioner-facing framing ("a practitioner deciding whether to add graph repair... should budget for that distinction rather than assume the two travel together") rather than repeating the Abstract's more declarative "we make no claim" phrasing. The underlying idea (don't overclaim repair as a retrieval strategy) is preserved in both places, as it should be, but the sentences are no longer interchangeable copies.

---

## Summary of edits applied

1. §12 Limitations: shortened the "no claim of universal external validity" paragraph to cross-reference Section 11 instead of re-deriving the cyclicity-severity clause.
2. §13 Conclusion: rewrote the closing sentence to remove near-verbatim overlap with the Abstract's closing sentence, while preserving the same underlying claim.

No other repetition found across the six required themes was judged excessive; in every other case, the repeated idea served a distinct function at each location (evidentiary vs. interpretive vs. summary vs. scope-limiting), consistent with standard journal-article structure rather than repository-report-style restatement.
