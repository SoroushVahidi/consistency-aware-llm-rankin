# Baseline Extension Audit

> **Generated:** 2026-03-24
> **Purpose:** Audit of accessible papers, code, and feasibility for adding modern
> reranking baselines to the consistency-aware LLM ranking manuscript.

---

## 1. Repository Status

### Current Datasets
| Dataset   | Loader     | Source          | Notes                          |
|-----------|------------|-----------------|--------------------------------|
| SciDocs   | BEIR       | BeIR/scidocs    | Primary evaluation dataset     |
| FiQA      | BEIR       | BeIR/fiqa       | Financial QA                   |
| HotpotQA  | HotpotQA   | hotpot_qa       | Multi-hop QA, top_k=10         |
| BRIGHT    | BRIGHT     | xlangai/BRIGHT  | Challenging reasoning queries  |

### Current Methods (in `run_real_experiment.py`)
- **Graph-free baselines:** score_sum, borda, pagerank, copeland
- **FAS-repair methods:** greedy_fas_topological, greedy_fas_weighted_balance,
  greedy_fas_copeland, greedy_fas_score_augmented_topological,
  fas_balance_score_prior_alpha_beta
- **Hybrid (RRF + repair):** hybrid_rrf_fas_regularized, hybrid_rrf_balance_a05,
  hybrid_rrf_copeland_a03, hybrid_rrf_priority_topo_a03
- **Ablation variants:** repaired vs unrepaired copeland/balance, prior-only

### Current Evaluation Metrics
- nDCG@k (primary), MAP@k, Precision@k, Recall@k
- Pairwise accuracy from relevance labels
- Kendall τ vs qrels reference
- Backward-edge weight (BEW) and pairwise inconsistency count (PIC)
- Bootstrap delta analysis for paired comparisons

### Missing from Current Baselines
The manuscript lacks **any external reranking baselines** — all current methods
operate on the same preference graph using different aggregation/repair strategies.
There is no comparison against:
1. Cross-encoder neural rerankers
2. LLM-based reranking (pointwise, pairwise, or listwise)
3. Tournament-graph or Bradley-Terry aggregation from the same pairwise judgments

---

## 2. Paper Access Audit

### Papers Investigated

| Paper/Method | Accessible? | Source | Notes |
|---|---|---|---|
| RankGPT (Sun et al., EMNLP 2023) | Yes | arxiv.org/abs/2304.09542, github.com/sunnweiwei/RankGPT | Listwise LLM reranking with sliding window |
| Rank-without-GPT (2024) | Yes | paperswithcode.com | Open-source listwise reranking |
| llm-rankers (Zhuang et al.) | Yes | github.com/ielab/llm-rankers | Unified pointwise/pairwise/listwise/setwise |
| PRP — Pairwise Ranking Prompting | Yes | Published 2023 | O(N log N) pairwise sorting |
| BLITZRANK (Agrawal et al., 2026) | Yes | arxiv.org/abs/2602.05448, pypi.org/project/blitzrank | Tournament-graph zero-shot ranking |
| AFR-Rank (2025) | Partial | ScienceDirect abstract only; no code found | Listwise reranking with filtering |
| Reason-to-Rank (2025) | Partial | arxiv abstract; code status unclear | Reasoning-distilled reranking |
| Cross-encoder MS MARCO | Yes | sentence-transformers library | Pre-trained models readily available |
| Bradley-Terry model | Yes | Well-known; trivial to implement from definition | Parametric pairwise aggregation |

### Official Code Access

| Repository | Accessible? | Usable? | Notes |
|---|---|---|---|
| sunnweiwei/RankGPT | Yes | Requires LLM API | Listwise sliding-window reranking |
| ielab/llm-rankers | Yes | Requires LLM API or local model | Comprehensive framework |
| ContextualAI/BlitzRank | Yes (PyPI) | Requires LLM API | Tournament-graph aggregation |
| sentence-transformers | Yes (installed) | Yes, local inference | CrossEncoder models available |
| cambridgeltl/PairS | Yes | Requires LLM API | Pairwise preference framework |

### Key Constraint: LLM API Access

This environment has **no LLM API keys** configured (no OpenAI, Anthropic, or other
API credentials). This means:
- Methods requiring live LLM inference (pointwise/pairwise/listwise LLM reranking)
  cannot produce real judgments in this environment.
- We can implement the full pipeline including prompt templates, caching, and
  evaluation, but actual LLM runs require either:
  (a) API keys added to environment, or
  (b) Pre-cached judgment files provided.

**What we CAN run locally:**
- Cross-encoder reranking (sentence-transformers, fully local)
- Graph aggregation baselines (Copeland, Bradley-Terry, etc.) over any existing
  preference data
- All existing pipeline methods

---

## 3. Feasible Baseline Suite

### Tier A: Faithful implementations / direct integrations

| Baseline | Category | Implementation | Can Run Locally? |
|---|---|---|---|
| Cross-encoder (MS MARCO MiniLM) | Neural reranker | sentence-transformers CrossEncoder | **Yes** |
| Copeland aggregation | Graph aggregation | Already in repo | **Yes** |
| Bradley-Terry MLE | Graph aggregation | Standard implementation | **Yes** |
| Weighted Markov chain (PageRank) | Graph aggregation | Already in repo | **Yes** |

### Tier B: Strong practical baselines (require LLM API for real runs)

| Baseline | Category | Implementation | Can Run Locally? |
|---|---|---|---|
| LLM pointwise scoring | LLM reranking | Custom prompt + caching | Mock/dry-run only |
| LLM pairwise comparison | LLM reranking | Custom prompt + caching | Mock/dry-run only |
| LLM listwise (RankGPT-style) | LLM reranking | Sliding-window prompt | Mock/dry-run only |
| Tournament aggregation | Graph aggregation | Custom from pairwise judgments | **Yes** (from existing preferences) |

### Tier C: Clearly labeled approximations

| Baseline | Category | Notes |
|---|---|---|
| Simulated LLM pairwise (qrels-derived) | LLM proxy | Uses qrels + noise to simulate LLM judge |
| BLITZRANK-style tournament | Tournament | Inspired by BLITZRANK; not official reproduction |

### Not Implementable

| Method | Reason |
|---|---|
| AFR-Rank | No accessible code; paper behind paywall |
| Reason-to-Rank | Requires specialized distilled model not available |

---

## 4. Recommended Final Baseline Set

### Category A: Cross-Encoder Reranking (non-LLM strong baseline)
- **Method:** `cross_encoder_reranker`
- **Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (sentence-transformers)
- **Type:** Tier A — faithful integration of well-known model
- **Provenance:** MS MARCO trained cross-encoder; widely used in IR

### Category B: LLM Pointwise Scoring
- **Method:** `llm_pointwise`
- **Type:** Tier B — standard prompt template, caching, deterministic
- **Status:** Full implementation with mock/dry-run mode; real runs require API key
- **Provenance:** Standard practice (Liang et al., 2022; Sun et al., 2023)

### Category C: LLM Pairwise Comparison
- **Method:** `llm_pairwise`
- **Type:** Tier B — pairwise comparison prompts
- **Status:** Full implementation; produces preference files compatible with existing pipeline
- **Provenance:** PRP (Qin et al., 2023); standard LLM pairwise methodology

### Category D: LLM Listwise Reranking
- **Method:** `llm_listwise`
- **Type:** Tier B — sliding-window listwise prompting (RankGPT-style)
- **Status:** Full implementation with mock/dry-run
- **Provenance:** RankGPT (Sun et al., 2023) sliding-window approach

### Category E: Graph Aggregation from Pairwise Preferences
- **Method:** `bradley_terry` — parametric aggregation via MLE
- **Method:** `tournament_copeland` — tournament Copeland scoring
- **Method:** `tournament_markov` — random-walk / Markov chain ranking
- **Type:** Tier A — well-defined algorithms
- **Provenance:** Bradley & Terry (1952); standard social choice theory

### Category F: Our Method with and without Repair
- Already present in repository (repaired vs unrepaired hybrids)
- Retained and rerun as-is

---

## 5. What This Audit Explicitly Cannot Verify

1. **AFR-Rank internals** — paper is behind ScienceDirect paywall; no code found.
   We do NOT implement this.
2. **Reason-to-Rank model weights** — requires specialized fine-tuned model.
   We do NOT implement this.
3. **BLITZRANK exact algorithm** — while the paper is on arxiv, our implementation
   is labeled as "inspired by" tournament-graph principles, not a faithful reproduction
   of the BLITZRANK package (which requires LLM API).

---

*This audit was produced before any implementation work. All baselines below are
implemented only where the specification is accessible and the implementation is
defensible.*
