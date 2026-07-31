# Overnight Continuation Priority Plan

**Parent overnight:** `jdiq-overnight-20260713-225928` (finished too fast; several gaps remain)
**Verified earlier base:** `db6edb61b601ca9c5035fd17fcf53c4dd14d0acc`
**Parent commit after first overnight:** `f1e0abb4bb325d7d46867940b620d49e8dae847c`

## Ranked by reviewer value

1. **Methods ↔ Limitations consistency** — Methods still says retention sensitivity is “not yet performed”; Limitations was updated. Contradiction is worse than the original omission.
2. **Identity-leak fix + rebuild anonymous artifact** — hardcoded `/home/soroush/...` in `processor.py`; scan must go clean.
3. **CombMNZ actually computed** — first pass skipped because qrels paths were wrong (`data/processed/{ds}` vs `beir/` layout). Document decision with numbers; still default do-not-add.
4. **REVISION_SUMMARY / risk list sync** — remove leftover “retention still untested”.
5. **Light presentation hardening** — software-env pointer, Data Availability clarity if pages allow.
6. **Compile / validate / manuscript-scoped commit+push**.

## Hard constraints

- No paid APIs / new LLM reranker experiments
- No fabricated anonymous URLs or metrics
- Do not change verified primary nDCG point estimates
- Soft-fail per phase; soft deadline ~8h with reserve
