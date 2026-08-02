# Technical Correctness and Statistical Rigor Audit Changelog

Date: 2026-08-02  
Branch: `papers/sncs-2026-foundation`  
Scope: mathematical formulation, greedy/exact repair wording, calibration
transparency, statistical-method accuracy, dependence caveats, exact-repair
claim narrowing, API/data-availability clarification.  
**No table bodies, figure data, Holm cell counts, or claim classifications
changed.**

## Issues found and corrected

1. **Incomplete MIP:** Objective-only display replaced by full linear-ordering
   model (antisymmetry + triangle inequalities + binary vars) matching
   `mwfas_solver.py`.
2. **Greedy description:** Documented NetworkX `find_cycle` selection,
   min-weight deletion, tie-breaking, and empirical **over-removal** vs
   certified optimum (not “under-removal” of weight).
3. **“Under-repair” wording:** Replaced with **greedy suboptimality w.r.t.
   the edge-deletion MWFAS objective** throughout abstract/intro/discussion.
4. **Statistical methods mismatch:** Primary confirmatory families use
   Monte Carlo paired sign-flip (`full_calibration_utils`, 10k, seed 17),
   not exact enumeration. Exact ($m\le 20$ nonzero) + BCa belong to
   `statistical_inference` / Task2–4 analyses. Manuscript now states both
   accurately.
5. **Calibration:** Named unsupervised collection-level protocol
   calibration; clarified no qrel leakage but transductive query-list
   limitation (no held-out split).
6. **Dependence:** Holm controls FWER within families; does not model
   cross-regime/pool/extractor query recurrence (hierarchical future work).
7. **Exact-repair claim:** Narrowed: no claim of proving repair never helps,
   ruling out edge reversal / soft / relevance-aware repair, or utility
   optimality.
8. **API facts:** Data Availability now names Azure/OpenAI-compatible,
   Gemini, Cohere, Fireworks for the pilot only; main results need no paid
   API.

## Verified against canonical evidence (unchanged numbers)

| Claim | Source check |
|---|---|
| Active canonical min Holm $\approx 0.240$ | `table_primary_bootstrap_permutation.csv` → Holm on 20 ms1 cells |
| Full canonical min Holm $\approx 0.720$ | same, 60 cells |
| Larger-pool min Holm $\approx 0.352$ | `pool_cutoff_statistics.csv` active ms1 nDCG 110 cells |
| SciDocs Copeland hybrid raw $p\approx 0.012$ | `paired_permutation_pvalue` 0.011999 |
| Exact $1{,}025/1{,}025$ | prior evidence package (unchanged prose) |

## Algorithm 1

Matches vote construction at the protocol level (normalize → margin votes →
regime support/aggregate → optional mutual drop). Implementation details of
threshold search remain in Methodology prose + Table `tab:thresholds`.

## Funding

Left unchanged. Pilot providers match
`reports/multi_provider_repair_pilot_*/PROVIDER_MODELS.json`. Author should
confirm each named Funding credit materially supported that pilot if
reviewers ask; no NJIT funding claim is present.

## Compile

- Pages: 36 → 36 (transiently 37 during drafting)
- Approx. words: ~10,508 → ~10,524
- Clean `tectonic` build; all `eq:*` labels resolve

## Claim registries

Unchanged: `docs/claim_evidence_registry.yaml`, `result_claims.yaml`,
`EVIDENCE_MAP.md`, `docs/CONTRIBUTIONS.md`.
