# Regression Test Report — Stage 1.4

## Bug A: `holm_active_ms1_family == True` pandas trap

**New file**: `tests/test_holm_pvalue_boolean_regression.py` (15 tests, all passing).
**New centralized helper**: `is_significant_pvalue()` in `src/consistency_ranker/statistical_inference.py`.

| Requirement from the brief | Covered by |
|---|---|
| Python `bool` | `test_python_bool_column_is_rejected` — raises `TypeError` |
| NumPy boolean values | `test_numpy_bool_column_is_rejected` (`np.bool_` array) — raises `TypeError` |
| Nullable pandas `BooleanDtype` | `test_nullable_pandas_boolean_dtype_is_rejected` (`pd.array(..., dtype="boolean")`) — raises `TypeError` |
| Missing values | `test_missing_values_are_not_significant` (`NaN`, `None`, `pd.NA`) — all resolve to `False`, no error |
| String-like values that must not silently become true | `test_string_like_true_false_values_are_rejected_not_coerced` (`"True"`/`"False"` strings) — raises via `pandas.to_numeric(errors="raise")`; `test_valid_numeric_strings_are_accepted` confirms genuine numeric strings (e.g. `"0.001"`) are still accepted, so only boolean-looking tokens are rejected, not numbers-as-strings |
| The exact filtering behavior used by the audit code | `test_is_significant_pvalue_matches_manuscript_ground_truth` mirrors `pool_cutoff_statistics.csv`'s actual shape (110 active-family rows, several exact `1.0` values) and confirms `0` significant, matching the manuscript's documented `0/110` |
| Demonstrate the bug itself (not just the fix) | `test_naive_equals_true_is_the_bug_not_the_fix` — shows `p_values == True` flags the p=1.0 row as "significant," the opposite of correct |
| Confirm the genuinely-boolean sibling column is unaffected | `test_genuinely_boolean_significance_column_is_used_directly_not_via_helper` — `holm_significant_at_0.05` (verified `dtype == bool` in the actual tracked CSVs) is deliberately NOT run through the new helper; `== True` remains correct there, and calling the helper on it raises by design |

Boundary-value coverage (`test_is_significant_pvalue_boundary_values`, parametrized over 0.0/0.049/0.05/0.05000001/0.5/1.0) confirms the `< alpha` (strict) boundary matches the manuscript's convention and that `p=1.0` (the exact value that triggered the original bug) is correctly `False`.

## Bug B: `.holm_significant_at_0.05` attribute-parsing trap

**New file**: `tests/test_numeric_threshold_parsing_regression.py` (20 tests, all passing).
**New centralized helper**: `parse_numeric_threshold()` in `src/consistency_ranker/statistical_inference.py`.

| Requirement from the brief | Covered by |
|---|---|
| `.05` | `test_parse_numeric_threshold_accepts_valid_forms[.05-0.05]` |
| `0.05` | same parametrization, `[0.05-0.05]` |
| `5e-2` | same parametrization, `[5e-2-0.05]` (+ `5E-2` uppercase variant) |
| Negative decimals | `[-0.01--0.01]`, `[-.01--0.01]` |
| Malformed expressions | `test_parse_numeric_threshold_rejects_malformed_expressions`, parametrized over `"0.05.05"` (the exact shape of the original typo, as a string), `"abc"`, `""`, `"0.05e"`, `"--0.05"`, `None` — all raise `ValueError`/`TypeError` |
| Forbidden attribute access | `test_dotted_column_name_via_attribute_access_is_a_syntax_error` — uses `ast.parse()` to confirm `df.holm_significant_at_0.05` is a hard `SyntaxError` (verified empirically first: `float(True)`-style silent coercion does NOT happen here; Python refuses to parse the statement at all), and `test_bracket_indexing_is_the_correct_and_only_safe_form` confirms the fix retrieves the correct column |
| Valid numeric threshold expressions already used by the repository | `test_valid_thresholds_already_used_in_this_repository` pins `0.01` (`MEANINGFUL_THRESHOLD`) and `0.05` (Holm `alpha`); `test_run_ir_evidence_audit_meaningful_threshold_constant_is_numeric` imports the **actual** `scripts/run_ir_evidence_audit.py` module and checks its real `MEANINGFUL_THRESHOLD` constant directly, not just a hand-copied literal |

Also covered (not explicitly requested but directly relevant): rejecting `bool` input even though `float(True) == 1.0` would otherwise "succeed" silently (`test_parse_numeric_threshold_rejects_bool_even_though_float_bool_succeeds`), mirroring the same boolean/numeric type-confusion family as Bug A.

## Centralization scope note

Per the brief's "centralize only if this can be done safely and with minimal scope": both new helpers are pure functions added to the one module (`statistical_inference.py`) that already centralizes every other statistical primitive in this codebase (bootstrap CIs, Holm/BH correction, equivalence tests). No existing function in that module was modified. `scripts/run_ir_evidence_audit.py` itself was **not** rewritten to call the new helpers — its existing `< 0.05` comparisons (the already-correct fix) were left exactly as they are, since rewriting a script that currently produces the audited, hand-verified `FINAL_IR_EVIDENCE_AUDIT.md` output was judged out of scope for a hygiene/regression-test stage; the new helpers exist so *future* code (including the pending query-clustered re-analysis, see `updated_evidence_provenance.md`) has a tested, correct building block to call instead of re-deriving the `notna() & (x < alpha)` pattern from scratch.

## Test run evidence

```
$ python3 -m pytest tests/test_holm_pvalue_boolean_regression.py tests/test_numeric_threshold_parsing_regression.py tests/test_manuscript_macro_drift.py -q
36 passed in 1.06s

$ python3 -m pytest -q   # full suite, after all Stage 1 changes
1238 passed, 23 skipped in 168.65s (0:02:48)
```

No test failures, no new skips introduced (the 23 skips are pre-existing and unrelated — mostly optional-solver/provider-credential-gated tests, unaffected by this stage).
