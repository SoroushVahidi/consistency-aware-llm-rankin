# FORWARD_REVERSE_REPORT

No committed pairwise run used for the current manuscript evidence preserves forward/reverse paired prompts.

- All auditable OpenAI primary-pilot configs set `debias_position=false`.
- The partial Gemini pilot also sets `debias_position=false`.
- Therefore semantic agreement, contradiction, order sensitivity, missingness, and Cohen's kappa for A→B vs B→A cannot be computed from the committed snapshot.
