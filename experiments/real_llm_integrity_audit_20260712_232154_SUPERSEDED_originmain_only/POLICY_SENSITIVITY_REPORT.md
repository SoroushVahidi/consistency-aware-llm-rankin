# POLICY_SENSITIVITY_REPORT

## Outcome

- P0 was reproducible from committed per-query repaired/unrepaired outputs.
- P1–P4 were **not** reproducible from committed artifacts because raw pairwise response texts and retry histories were not preserved.

## Questions answered

- Does default-A fallback change conclusions? Not auditable from the committed snapshot; raw pairwise texts needed for reparsing were not preserved.
- Does abstaining change conclusions? Not auditable from the committed snapshot.
- Does any policy change confidence intervals? Only P0 intervals could be reconstructed; alternative-policy intervals are unavailable.
- Are provider conclusions robust? OpenAI primary-pilot conclusions are reproducible at P0. Cross-provider robustness claims are not auditable because the manuscript's Cohere/Azure corpus is absent and Gemini is a 2-query partial pilot.
