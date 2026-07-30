"""Query-clustered re-analysis of the three real-multi-provider-LLM studies
(``repair_frontier``, ``extraction_study``, ``repair_diagnostic``).

See ``reports/<canonical_reanalysis_dir>/canonical_analysis_protocol.md`` for
the statistical protocol these modules implement, and
``reports/ir_evidence_audit_review_20260729T235053Z/FINAL_META_AUDIT_REVIEW.md``
for why this re-analysis is needed: all three studies report "n=120"
observations that decompose to only 6 independent underlying queries
replicated across ~20 provider/construction variants each. Every function
here treats ``query_id`` as the independence cluster.
"""
