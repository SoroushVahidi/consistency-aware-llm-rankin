# REAL_LLM_INTEGRITY_FINAL_REPORT

## Executive summary

- Resolved: the committed `origin/main` snapshot contains auditable OpenAI real-LLM evidence for pairwise, pointwise, and listwise runs, plus a small Gemini pairwise pilot.
- Threatens conclusions: the manuscript's Cohere/Azure corpus claims are unsupported by any committed auditable artifacts in the current anonymous snapshot.
- Harmless but document: pairwise and pointwise raw response texts are not preserved, which prevents retrospective ambiguity/fallback auditing and reparsing-policy sensitivity beyond P0.
- Harmless but document: no auditable forward/reverse debias runs are present in the committed analyzed pairwise evidence.

## Provider inventory

- OpenAI primary pairwise pilot: SciDocs 50, HotpotQA 20, FiQA 10 usable queries.
- OpenAI auxiliary scope checks: pointwise/listwise on SciDocs 20 and HotpotQA 10; small SciDocs robustness checks.
- Gemini pilot: SciDocs 2 usable queries; partial and quota-limited.
- Cohere/Azure: no committed auditable records found.

## Provider-count resolution

- The current repository snapshot does not support any version of the manuscript's '200 records' Cohere/Azure claim.

## Parser audit

- Pairwise parser defaults any unrecognized response to `A`.
- Pointwise parser defaults to score `5.0` if no integer is found in non-strict mode.
- Listwise parser is permissive and appends missing indices in original order.
- Pairwise raw texts are absent, so fallback-to-`A` frequency cannot be measured retrospectively.

## Ambiguity statistics

- Pairwise: not auditable from committed artifacts.
- Pointwise: not auditable from committed artifacts.
- Listwise: auditable; committed runs preserve raw ranking strings.

## Position bias

- Final parsed A/B outcome rates are auditable from pairwise cache orderings and are reported in `position_bias_summary.csv`.
- Exact-response-only and fallback-only splits are not auditable.

## Forward/reverse agreement

- No committed forward/reverse debiased pairwise runs were available for analysis.

## Policy sensitivity

- P0 is reproducible from committed per-query outputs.
- P1–P4 are not reproducible from committed artifacts because raw pairwise response texts were not preserved.

## Manuscript corrections required

1. Remove or replace unsupported Cohere/Azure corpus claims.
2. Restrict the real-LLM evidence statement to auditable OpenAI primary-pairwise evidence and explicitly bounded auxiliary pointwise/listwise checks.
3. Add a limitation that raw pairwise response texts were not preserved, preventing retrospective ambiguity and fallback audits.
4. Remove any implication that order-bias mitigation was audited in the committed primary-pairwise corpus.

## New API calls scientifically necessary?

No new API calls are necessary to reproduce the committed OpenAI/Gemini end results already stored in the repository. However, new API calls would be necessary to create a fresh ambiguity-sensitive reparsing audit only if no raw provider-side response logs can be recovered from outside the current repository snapshot.

## Issue classification

- `resolved`: OpenAI primary-pairwise counts and bootstrap-facing summary are reproducible from committed outputs.
- `harmless but document`: pairwise raw-text absence for parser auditing.
- `changes numerical results`: none demonstrated from current committed artifacts, because alternative reparsing policies are not reproducible.
- `threatens conclusions`: current manuscript claims about a committed Cohere/Azure corroborative corpus.
- `requires new experiments`: no for reproducing current OpenAI results; yes only if the authors want a fresh, ambiguity-sensitive reparsing study without recovering missing raw logs.
