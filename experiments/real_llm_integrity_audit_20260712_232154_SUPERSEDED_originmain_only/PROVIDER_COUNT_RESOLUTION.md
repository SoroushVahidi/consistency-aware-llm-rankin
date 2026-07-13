# PROVIDER_COUNT_RESOLUTION

## Resolution

From committed `origin/main` artifacts, the auditable provider totals are:

- OpenAI primary pairwise pilot: 80 usable queries across SciDocs, HotpotQA, and FiQA; 6196 stored pairwise judgment records.
- Gemini pilot: 2 usable queries; 491 stored pairwise judgment records; partial and not treated as analyzed manuscript evidence.
- Cohere: 0 committed auditable records found.
- Azure OpenAI: 0 committed auditable records found.

## Contradiction outcome

The repository snapshot does **not** support either of the manuscript interpretations:

1. "Cohere contributes 200 records."
2. "Azure contributes 200 records."
3. "Cohere and Azure together contribute 200 records."

Instead, the current anonymous `origin/main` snapshot contains **no committed auditable Cohere or Azure records at all**. The manuscript's provider-count claims therefore cannot be verified from the stored artifact set used for this audit.

## Exact manuscript sentence that must change

The sentence beginning:

> "Each protocol-distinct corroborative provider contributes 200 query×regime records across FiQA, HotpotQA, and BRIGHT."

must be removed or replaced. On the current anonymous `origin/main` snapshot, no committed Cohere/Azure corpus is available to support that statement.
