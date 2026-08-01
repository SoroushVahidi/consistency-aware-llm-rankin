# Stage 6 Reviewer-Style Audit Report

Date: 2026-07-31
Reviewer stance: skeptical Reviewer #2 audit for unsupported claims,
overstatement, ambiguity, and scope creep.

## Main Issues Found and Fixed

1. **LLM pilot provider count**

   The Results section described the bounded real-large-language-model pilot as
   using five providers. Repository evidence and the provider-usage file show
   four providers in the pilot used here: Azure, Gemini, Cohere, and Fireworks.
   The manuscript now says four providers.

2. **Ranker-scope description**

   The External Validity section described "three classical and one dense base
   ranker." The actual main score-derived evidence uses BM25, TF-IDF, and
   MiniLM: two lexical rankers and one dense ranker. The limitation now states
   that scope correctly.

3. **Acyclicity overstatement**

   The Results section said the conservative `ms2` regime was acyclic "by
   construction." That is stronger than the evidence needed. The manuscript now
   says it was acyclic in the observed evidence.

4. **Conclusion scope**

   The new Conclusion answers RQ1--RQ4 directly while preserving the central
   negative/conditional result. It distinguishes structural improvement from
   retrieval improvement and avoids claiming that repair never helps.

5. **Exact repair framing**

   The conclusion and abstract describe exact SCIP repair only as a
   methodological control on heuristic suboptimality, not as a scalable
   production method or new solver contribution.

6. **Acknowledgements and funding**

   The acknowledgements and funding declaration now include only support with
   evidence of relevance to this work: Cohere Labs Catalyst Grant Program,
   Google Cloud Research Credits Program, Microsoft Azure for Students, and AMD
   AI Developer Program through Fireworks AI credits. A DeepInfra credit request
   thread was found but did not provide support and is not acknowledged.

## Reviewer Risk After Edits

- A reviewer may still ask for broader real-LLM evidence. The manuscript already
  states that the real-LLM pilot is directional only and not confirmatory.
- A reviewer may ask whether small nDCG effects are ruled out. The Results,
  Discussion, Limitations, and Conclusion all preserve the power-analysis caveat:
  small effects below the corrected detectable scale remain possible.
- A reviewer may ask whether exact repair scales. The manuscript explicitly
  limits exact repair to a bounded diagnostic role.
- A reviewer may ask whether graph-free baselines are state of the art. The
  manuscript states they are controlled baselines, not a state-of-the-art claim.

## Verdict

No new scientific claim was introduced during Stage 6. The remaining claims are
bounded to the frozen evidence and stated cautiously enough for review.
