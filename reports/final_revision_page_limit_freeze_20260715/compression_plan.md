# Compression Plan

Target:

- hard target: `<= 23` body pages excluding references under JDIQ/ACM `acmsmall`

Current starting point:

- current main PDF: 39 pages in repository default build
- Task 10 `acmsmall` check: 40 total pages, references start on page 38, so 37 body pages excluding references

Compression strategy:

1. Replace the current long-form manuscript narrative with a compact journal version centered on:
   - problem and JDIQ framing
   - one compact DQ taxonomy table
   - one compact setup table
   - four decisive figures
   - one compact primary-findings table
   - one compact robustness/power table
   - short discussion, limitations, and conclusion
2. Remove from the main paper and reference only through the supplement:
   - notation table
   - detailed threshold-protocol exposition
   - long ranker-dependence prose
   - candidate-pool-policy detail table
   - raw-vs-normalized sign-flip table
   - dataset-macro baseline table
   - result-to-DQ mapping table
   - practical-implications table
   - detailed exact-solver coverage/timing prose
   - extended LLM protocol-audit detail
   - extended reproducibility inventory prose
3. Keep in the main paper:
   - Figure 1: pipeline / audit schematic
   - Figure 2: BM25 scale dominance
   - Figure 5: cyclicity before/after mutual-pair deletion
   - Figure 7: repaired-vs-unrepaired forest plot
   - Table 1: compact dataset/setup summary
   - Table 2: compact seven-dimension DQ taxonomy
   - Table 3: compact primary findings
   - Table 4: compact robustness / power / exact-repair summary
4. Reuse existing supplement sections A-H for moved detail where possible rather than duplicating evidence.

Expected savings:

- removing 8 of 12 main tables and most long result subsections should recover the bulk of the page budget
- if still over 23 pages after the first rewrite, next cuts will be:
  - trim related work to one page-equivalent
  - shorten method prose further
  - reduce discussion and limitations to one page each
  - remove any remaining redundant table text where a figure already carries the point
