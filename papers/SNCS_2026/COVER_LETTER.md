# Cover Letter

Dear Editor-in-Chief,

Please consider the manuscript "Structural Consistency Is Not Retrieval Utility: An Exact-and-Heuristic Audit of Preference-Graph Repair for Multi-Ranker Retrieval" for publication as an Original Research article in SN Computer Science.

The manuscript studies a common assumption in graph-based ranking pipelines: that repairing cycles in a derived preference graph should improve the downstream retrieval ranking. Using four public retrieval benchmarks, three score-derived rankers, three graph-construction regimes, and paired query-level inference with Holm correction, the paper separates graph construction, structural repair, ranking extraction, and retrieval evaluation. It also uses exact SCIP-based minimum-weight feedback-arc-set repair as a methodological control on heuristic repair.

The central finding is deliberately restrained. Repair is structurally active and exact repair removes less edge weight than greedy repair, but no repaired-versus-unrepaired nDCG comparison survives Holm correction in the canonical, larger-pool, or exact-repair comparison families. The paper therefore argues that structural consistency and retrieval utility should be reported as separate quality dimensions.

The manuscript is appropriate for SN Computer Science because it combines information retrieval, graph algorithms, empirical evaluation methodology, and reproducible computational experimentation, all within the journal's broad computer science scope. The contribution is a controlled empirical audit rather than a claim of state-of-the-art reranking performance.

I confirm that the work is original, has not been published before, and is not under consideration elsewhere. The code, fixed query lists, processed intermediates, figure data, and scripts required to reproduce the reported tables and figures are available at https://github.com/SoroushVahidi/consistency-aware-llm-rankin. Raw provider request and response payloads from the bounded LLM pilot are excluded for artifact-policy reasons, as stated in the manuscript.

Thank you for considering this submission.

Sincerely,

Soroush Vahidi
Ying Wu College of Computing
New Jersey Institute of Technology
sv96@njit.edu
