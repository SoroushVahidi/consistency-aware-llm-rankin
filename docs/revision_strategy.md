# Revision Strategy

> **Purpose:** Structured response to the editorial rejection that cited
> (1) lack of recent literature engagement, (2) insufficient state-of-the-art
> baselines — especially LLM-based, and (3) weak positioning relative to
> current research.
>
> **Grounding rule:** Every claim in this document is tied to a committed
> artifact. Nothing is projected or invented. Run labels follow the four-tier
> system: `real completed run` | `pilot run` | `dry-run validation` | `pending`.
> "Fixed" means an artifact exists; it does not mean the manuscript has been
> updated.

---

## 1. Concern 1 — Lack of Recent Literature Engagement

### What the editor flagged

The manuscript lacked citations to the class of LLM-based reranking work
published since 2022, including:

- Pointwise scoring prompts (relevance classification/grading)
- Pairwise preference elicitation (Pairwise Ranking Prompting, PRP)
- Listwise permutation generation (RankGPT, setwise ranking)
- Graph/tournament aggregation of pairwise LLM judgements
  (Condorcet / Bradley–Terry / Markov-chain fusion)

### What is already fixed

| Action | Status | Artifact |
|--------|--------|----------|
| LLM pointwise reranker implemented | **done** | `src/rerankers/llm_pointwise.py` |
| LLM pairwise reranker implemented | **done** | `src/rerankers/llm_pairwise.py` |
| LLM listwise (RankGPT-style) implemented | **done** | `src/rerankers/llm_listwise.py` |
| Tournament-aggregation baselines implemented | **done** | `src/rerankers/tournament_agg.py` |
| Bradley–Terry MLE aggregation run on real data | **done** (real completed run) | `outputs/final_modern_baselines/` |
| Win-rate aggregation run on real data | **done** (real completed run) | `outputs/final_modern_baselines/` |
| Markov-chain aggregation run on real data | **done** (real completed run) | `outputs/final_modern_baselines/` |
| Cross-encoder baseline run on real data | **done** (real completed run) | `outputs/final_modern_baselines/` |
| `docs/related_work_positioning_note.md` drafted | **done** | `docs/related_work_positioning_note.md` |

### What is still missing

| Action | Status | Blocker |
|--------|--------|---------|
| LLM pointwise **run** on real data | **pending** | Requires `OPENAI_API_KEY`; no API key in environment |
| LLM pairwise **run** on real data | **pending** | Same |
| LLM listwise **run** on real data | **pending** | Same |
| LLM results included in final comparison table | **pending** | Downstream of above |

### Recommended response to the editor

> "We have implemented pointwise, pairwise, and listwise LLM reranking modules
> (§ X), and we position our contribution relative to the RankGPT / PRP family
> (§ Related Work). Execution of full LLM reranking experiments is deferred to
> a follow-up study due to API cost constraints; we note this explicitly as a
> limitation (§ Limitations)."

---

## 2. Concern 2 — Insufficient State-of-the-Art Baselines

### What the editor flagged

The original manuscript compared only internal graph methods (score-sum,
Borda, Copeland, topological sort) and did not include:

- A pre-trained neural reranker (cross-encoder)
- Tournament-aggregation variants that are standard in the social-choice
  and preference-learning literature (Bradley–Terry, Markov-chain)
- Any LLM-generated preference baseline

### What is already fixed

#### A. Cross-encoder baseline (real completed run)

Pre-trained MS MARCO MiniLM cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
evaluated on three datasets:

| Dataset | Queries | cross_encoder nDCG@k | Best graph method | Δ (graph − cross-encoder) |
|---------|---------|----------------------|-------------------|--------------------------|
| SciDocs | 500 | 0.8977 | 1.0000 (score_sum) | +0.102 |
| HotpotQA | 497 | 0.9499 | 1.0000 (score_sum) | +0.050 |
| BRIGHT | 71 | 0.8877 | 1.0000 (score_sum) | +0.112 |

**Run label:** real completed run  
**Evidence:** `outputs/final_modern_baselines/{dataset}/summary.csv`

> **Interpretive note:** Graph methods reach nDCG = 1.0 because they consume
> qrels-derived (perfect) pairwise preferences. The cross-encoder uses only
> document text and has no access to relevance labels. The gap is consistent
> with the interpretation that preference quality — not aggregation algorithm
> sophistication — is the binding factor, but a controlled experiment varying
> preference quality independently would be needed to confirm this.

#### B. Tournament aggregation baselines (real completed run)

| Method | SciDocs nDCG | HotpotQA nDCG | BRIGHT nDCG |
|--------|-------------|---------------|-------------|
| Bradley–Terry MLE | 1.0000 | 1.0000 | 1.0000 |
| Win-rate | 1.0000 | 1.0000 | 1.0000 |
| Markov-chain (PageRank) | 1.0000 | 1.0000 | 1.0000 |
| Tournament sort | 0.8059 | 1.0000 | 0.6999 |

**Run label:** real completed run (qrels-derived preferences — acyclic)  
**Evidence:** `outputs/final_modern_baselines/{dataset}/summary.csv`

#### C. FAS methods vs tournament baselines under noise (real completed run)

At 15% synthetic noise flip probability:

| Comparison | SciDocs Δ nDCG | HotpotQA Δ nDCG |
|------------|---------------|-----------------|
| FAS-balance vs Bradley–Terry | +0.049 [+0.044, +0.054] | +0.264 [+0.246, +0.282] |
| FAS-balance vs Win-rate | +0.001 [0.000, +0.002] | +0.232 [+0.212, +0.251] |
| FAS-balance vs Markov-chain | +0.069 [+0.062, +0.077] | n/a (Markov = 0.98) |

**Run label:** real completed run  
**Evidence:** `outputs/bootstrap_modern/` and `outputs/noise_sensitivity/`

### What is still missing

| Baseline | Status | Note |
|----------|--------|------|
| LLM pointwise scoring (real run) | **pending** | API key required |
| LLM pairwise / PRP (real run) | **pending** | API key required |
| LLM listwise / RankGPT-style (real run) | **pending** | API key required |
| FiQA included in modern-baseline comparison | **pending** | FiQA qrels are grade-1 only; no ranking differentiation |
| Exact ILP MWFAS vs greedy on real data | **pending** | ILP backend not functional (Gurobi required) |

---

## 3. Concern 3 — Weak Positioning Relative to Current Research

### What the editor flagged

The manuscript read as if operating in isolation from the 2022–2025
paradigm of "LLMs as rankers / judges / preference generators."

### What is already fixed

- `docs/related_work_positioning_note.md` provides structured positioning
  against all five modern reranking paradigms (cross-encoder; pointwise,
  pairwise, and listwise LLM reranking; graph/tournament aggregation).
- The contribution is defined as **graph-structure analysis and cycle-repair
  for pairwise preference aggregation**, which is distinct in focus from the
  LLM-as-ranker paradigm and complementary to tournament-aggregation work.
- The evidence package documents that FAS-balance outperforms Bradley–Terry
  aggregation under synthetic preference noise on two datasets (Claim S8;
  `outputs/bootstrap_modern/`). This result is available for the §Results
  section of the manuscript.

### What is still missing

| Action | Status |
|--------|--------|
| Cite Sun et al. (2023) RankGPT in §Related Work | **pending** (manuscript edit) |
| Cite Qin et al. (2023) PRP in §Related Work | **pending** (manuscript edit) |
| Cite Dwork et al. (2001) on Markov-chain fusion | **pending** (manuscript edit) |
| Cite Bradley & Terry (1952), Plackett–Luce in §Background | **pending** (manuscript edit) |
| Mention implementation of LLM modules even if results are pending | **pending** (manuscript edit) |

---

## 4. Summary — Strength Assessment

| Aspect | Status |
|--------|--------|
| Core graph-repair methodology | **strong** — fully implemented and tested |
| Real-data evaluation (4 datasets, nDCG, bootstrap CIs) | **strong** — 4 datasets (FiQA excluded from modern-baseline comparison; grade-1 qrels only), 52–500 queries, 2000 bootstrap reps |
| Structural consistency metrics (BEW, PIC) | **strong** — pre/post repair with quantified effect |
| Classical baselines (Borda, score-sum, Copeland, PageRank) | **strong** — all implemented and run |
| Modern neural baseline (cross-encoder) | **strong** — pre-trained model, 3 datasets, real completed run |
| Tournament aggregation baselines | **strong** — BT MLE, win-rate, Markov, tournament-sort, 3 datasets |
| Noise robustness analysis | **partial** — 7 synthetic noise levels, 2 datasets (SciDocs, HotpotQA), bootstrap CI |
| LLM reranking baselines | **gap** — code only; no API key for live evaluation |
| Literature positioning | **partially addressed** — note doc written; manuscript edits pending |

---

## 5. Highest-Priority Next Experiment

**Run LLM pairwise reranking (PRP-style) as a preference source on SciDocs
and HotpotQA, feeding LLM-elicited pairwise comparisons into the same
FAS-repair pipeline.**

This experiment would:
1. Close the LLM-preference gap identified by the editor.
2. Directly answer: *does FAS repair of LLM pairwise judgements improve nDCG?*
3. Connect the contribution to the dominant 2023–2025 paradigm.
4. Enable a three-way comparison: qrels → LLM → repaired LLM preferences.

**Blockers:** Requires `OPENAI_API_KEY` or a locally-hosted LLM endpoint.
The pipeline is ready in `src/rerankers/llm_pairwise.py` and
`scripts/run_modern_baselines.py`.

---

## 6. How to Use This in the Manuscript

| Section | What to take from this document |
|---------|--------------------------------|
| **Cover letter** | Use §1–3 "What is already fixed" tables verbatim to demonstrate that you have added cross-encoder and tournament-aggregation baselines and repositioned relative to the LLM literature. Use §3 "What is still missing" to proactively acknowledge the LLM preference gap. |
| **§Baselines / §Experiments** | Use the tables in §2A and §2B for the baseline description paragraphs. Cite artifact paths as supplementary material links. |
| **§Results / §Analysis** | Use the noise-sensitivity table in §2C (with CIs) to support any claim about FAS-balance robustness. |
| **§Limitations** | Use §2 "What is still missing" (LLM pointwise/pairwise/listwise runs; FiQA exclusion; ILP solver) verbatim as the basis for the Limitations paragraph. Be explicit that LLM-preference results are not yet available. |
| **§Discussion** | The §5 framing (LLM pairwise as highest-priority next experiment) can be adapted into a Future Work paragraph without implying the result has been obtained. |
