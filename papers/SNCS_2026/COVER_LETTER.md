# Cover Letter

Dear Editor-in-Chief,

Please consider “Structural Consistency Does Not Reliably Predict Retrieval Utility: An Exact-and-Heuristic Audit of Preference-Graph Repair for Multi-Ranker Retrieval” as an Original Research article in *SN Computer Science*.

The manuscript is a controlled empirical audit of the assumption that repairing cycles in a derived preference graph should improve downstream retrieval ranking. On four public benchmarks, with three score-derived rankers, three construction regimes, and paired query-level inference with Holm correction, it factorizes construction, structural repair, extraction, and evaluation. Exact SCIP minimum-weight feedback-arc-set repair is used only as an identification control on greedy suboptimality for the stated edge-deletion objective—not as a new solver or ranking algorithm, and with no state-of-the-art performance claim.

The central finding is protocol-conditional. Repair is structurally active, and exact repair removes less edge weight than greedy repair, but no repaired-versus-unrepaired nDCG comparison survives Holm correction in the canonical, larger-pool, or exact-repair families. Absence of Holm-corrected evidence is not proof of equivalence. The reusable contribution is the factorized audit itself.

An earlier public preprint on Research Square (DOI: 10.21203/rs.3.rs-9335700/v1; CC BY 4.0; posted 2026-06-17) is disclosed; it is not an active journal submission. The present manuscript supersedes that preprint’s retrieval interpretation where the revised exact and multiplicity-corrected protocol changes the conclusion. The work has not been published elsewhere and is not under consideration elsewhere (no dual submission). Funding, generative-AI, competing-interest, and data/code disclosures are complete in the manuscript.

Code and compact processed artifacts: https://github.com/SoroushVahidi/consistency-aware-llm-rankin. Raw provider payloads from the bounded LLM pilot are excluded as stated in the manuscript.

Thank you for considering this submission.

Sincerely,

Soroush Vahidi  
ORCID: https://orcid.org/0000-0003-1934-6282  
Ying Wu College of Computing  
New Jersey Institute of Technology  
sv96@njit.edu
