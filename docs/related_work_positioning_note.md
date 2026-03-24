# Related Work Positioning Note

> **Purpose:** Describes how this work relates to the dominant modern reranking
> paradigms. Intended to inform the §Related Work section of the manuscript and
> to counter reviewer concern that the paper ignores recent literature.
>
> **Grounding rule:** Baselines are described as "representative modern
> baselines." We do NOT claim exact reproduction of any specific paper's
> experimental setup. We do NOT compare numerical results from our evaluation
> to published numbers from other papers (different datasets, splits, and
> ranker ensembles make such comparisons invalid).

---

## 1. Taxonomy of Modern Reranking Paradigms

The field of learned and LLM-based reranking can be organised into five
paradigms. This work primarily addresses **Paradigm 5** (graph/tournament
aggregation), with implementation scaffolding covering Paradigms 2–4. Executed
experiments exist only for Paradigms 1 and 5.

| Paradigm | Representative approach | Our coverage |
|----------|------------------------|--------------|
| 1. Cross-encoder reranking | BERT/T5 scoring each (query, doc) pair | External reference baseline — run |
| 2. LLM pointwise reranking | Prompt LLM to score each document 1–10 | Code implemented; run pending |
| 3. LLM pairwise reranking | Prompt LLM for (A ≻ B) comparisons | Code implemented; run pending |
| 4. LLM listwise reranking | Prompt LLM to reorder a window of docs | Code implemented; run pending |
| 5. Graph / tournament aggregation | Aggregate pairwise comparisons via social-choice methods | Fully implemented and run |

---

## 2. Paradigm 1 — Cross-Encoder Reranking

### What it is

A cross-encoder reranker scores each (query, document) pair jointly, using
a pre-trained encoder like BERT or a miniLM model fine-tuned on passage-level
relevance (e.g., MS MARCO). The final ranking is determined by score order.

### Representative work

- Nogueira & Cho (2019) — MonoBERT reranker
- Nogueira et al. (2020) — monoT5 pointwise reranker
- MS MARCO training data for passage ranking (Bajaj et al., 2018)

### How we use it

We include `cross-encoder/ms-marco-MiniLM-L-6-v2` as an external reference
baseline to situate our graph-based ranking quality. Results are from a
**real completed run** on SciDocs, HotpotQA, and BRIGHT.

**Our contribution is distinct in focus:** We study the aggregation of pairwise
preference graphs, not the generation of relevance scores from document text.
A cross-encoder and our method operate at different stages of the pipeline and
consume different inputs. Including the cross-encoder contextualises our
graph-method results relative to text-aware reranking, but the two are not
direct competitors.

### How to describe in manuscript

> "As an external reference, we include a pre-trained cross-encoder reranker
> (ms-marco-MiniLM-L-6-v2), which represents the class of text-aware neural
> rerankers that score each query-document pair independently. This model is
> not designed for multi-ranker preference aggregation and is included to
> anchor our results within the broader reranking literature."

---

## 3. Paradigm 2 — LLM Pointwise Reranking

### What it is

An LLM is prompted to assess the relevance of each document independently,
typically producing a score on a 1–10 scale or a binary relevant/not-relevant
label. Documents are then ranked by these scores.

### Representative work

- Liang et al. (2022) — Holistic evaluation of LLMs as rankers
- Zhuang et al. (2023) — "Beyond Yes and No: Improving Zero-Shot LLM Rankers"
- Sun et al. (2023) — RankGPT (includes pointwise ablation)

### Our implementation

`src/rerankers/llm_pointwise.py` implements this paradigm:
- Prompts GPT-class models to score each document on a 1–10 relevance scale
- Aggregates scores into a ranked list

**Run status:** Code implemented; **run pending** (requires `OPENAI_API_KEY`).

### Positioning note

LLM pointwise reranking produces a single-document relevance score, bypassing
preference-graph construction entirely. It is therefore a baseline from a
different paradigm rather than a variant of our approach. If run, it would
inform the question of whether graph-repair methods provide benefit beyond
direct LLM scoring — but that question is not yet answered in this repository.

### How to describe in manuscript

> "LLM-based pointwise reranking (e.g., Zhuang et al., 2023) bypasses
> pairwise comparison altogether and directly scores document relevance.
> We implement this baseline (§Implementation) and note that its
> evaluation requires LLM API access, which is deferred to future work.
> The architectural distinction is that pointwise scoring does not model
> inter-document consistency constraints; our graph-repair framework
> addresses those constraints explicitly within the preference-graph layer."

---

## 4. Paradigm 3 — LLM Pairwise Reranking

### What it is

An LLM is prompted to compare two documents and declare which is more
relevant to the query. These pairwise judgements are then aggregated into
a ranking. This paradigm is sometimes called Pairwise Ranking Prompting (PRP).

### Representative work

- Qin et al. (2023) — "Large Language Models are Effective Text Rankers with
  Pairwise Ranking Prompting" (PRP)
- Zhao et al. (2022) — "Instruction Following for Ranking Tasks"

### Our implementation

`src/rerankers/llm_pairwise.py` implements PRP-style pairwise comparison:
- Collects all pairwise (A vs B) comparisons with position-debiasing
  (bidirectional prompt)
- Aggregates via Copeland score (out-degree minus in-degree)

**Run status:** Code implemented; **run pending** (requires `OPENAI_API_KEY`).

### Positioning note — most directly analogous paradigm

LLM pairwise reranking is the most directly analogous paradigm to our work.
Our pipeline assumes a directed preference graph built from pairwise
comparisons; the source of those comparisons (multi-ranker scoring vs.
LLM prompting) is the main variable. The unanswered question is:

> *If the pairwise comparisons come from an LLM rather than from multi-ranker
> score voting, does FAS repair of the resulting preference graph improve
> retrieval quality?*

This experiment is the **single highest-priority pending run** (see
`docs/revision_strategy.md`). Until it is executed, LLM pairwise is described
as an "implemented but not yet evaluated baseline."

### How to describe in manuscript

> "LLM pairwise reranking (Qin et al., 2023) generates the same type of
> pairwise preference signal our framework consumes. A natural extension of
> this work is to apply FAS repair to LLM-elicited preference graphs,
> replacing score-derived votes with LLM judgements. We have implemented
> this pipeline (§Implementation); evaluation with real LLM preferences
> is deferred to future work due to API access constraints."

---

## 5. Paradigm 4 — LLM Listwise Reranking

### What it is

An LLM is prompted with a window of candidate documents and asked to produce
a permutation (reordered list). A sliding-window strategy allows the method
to scale beyond the context window. RankGPT is the canonical example.

### Representative work

- Sun et al. (2023) — "Is ChatGPT Good at Search? Investigating Large Language
  Models as Re-Ranking Agents" (RankGPT)
- Ma et al. (2023) — "Zero-Shot Listwise Document Reranking with a Large
  Language Model"
- Pradeep et al. (2023) — "RankZephyr / RankVicuna"

### Our implementation

`src/rerankers/llm_listwise.py` implements RankGPT-style sliding window:
- Configurable window size and step size
- Multiple passes supported

**Run status:** Code implemented; **run pending** (requires `OPENAI_API_KEY`).

### Positioning note

Listwise LLM reranking is an end-to-end method that requires no preference
graph and no aggregation step. It produces a ranking directly from document
text via the LLM's in-context ordering ability and does not share our
framework's assumptions (multi-ranker ensemble, preference graph, cycle
repair). If run, it would inform the question of whether explicit
consistency repair provides benefit over a single-model reranking pass.

### How to describe in manuscript

> "Listwise reranking (Sun et al., 2023; Ma et al., 2023) reformulates ranking
> as a direct permutation generation problem, bypassing pairwise consistency
> constraints. This approach does not model inter-ranker inconsistencies
> explicitly. We implement a RankGPT-style sliding-window baseline
> (§Implementation); full evaluation is deferred pending API access."

---

## 6. Paradigm 5 — Graph and Tournament Aggregation

### What it is

Pairwise comparison results (from any source — human judgements, LLM
preferences, retrieval scores) are treated as a tournament and aggregated
using social-choice methods: Copeland scoring, Borda count, Bradley–Terry
MLE, Markov-chain (PageRank), or merge-sort tournament.

### Representative work

- Dwork et al. (2001) — Rank aggregation via Markov chains
- Bradley & Terry (1952) — Paired comparison model
- Condorcet (1785) / Copeland (1951) — Social choice aggregation
- Ammar et al. (2016) — Spectral MLE for ranking from pairwise comparisons
- Zhu et al. (2023) — "Large Language Models are Zero-Shot Rankers for
  Recommendation"
- Jiang et al. (2023) — "LLM-based tournament ranking"

### Our baselines and their run status

| Method | Algorithm | Run status | Evidence |
|--------|-----------|-----------|----------|
| Bradley–Terry MLE | MM algorithm, MLE on pairwise win/loss | real completed run | `outputs/final_modern_baselines/` |
| Win-rate aggregation | win/(win+loss) fraction | real completed run | same |
| Markov-chain (PageRank) | Stationary distribution of preference random walk | real completed run | same |
| Tournament sort | Merge-sort with pairwise comparator | real completed run | same |
| Copeland scoring | Out-degree − in-degree | real completed run | `outputs/real_full/` |
| Borda count | Unweighted out-degree | real completed run | `outputs/real_full/` |

### Positioning note — our core contribution

Our work **extends** graph/tournament aggregation by:

1. **Diagnosing cyclicity** as a structural property of the preference graph
   (BEW, PIC, SCC analysis)
2. **Repairing cycles** using greedy MWFAS before ranking extraction
3. **Analysing when repair helps vs. hurts** (regime analysis by vote
   construction and query subgroup)
4. **Comparing FAS repair to parametric aggregation** (Bradley–Terry,
   Markov-chain) under preference noise

This is a distinct contribution from simply applying a tournament aggregation
method. The question is not "which aggregation formula is best on clean data"
but "how does structural inconsistency in the preference graph interact with
ranking quality, and can repair improve outcomes."

### How to describe in manuscript

> "Graph-based tournament aggregation has a rich theoretical foundation
> (Bradley & Terry, 1952; Dwork et al., 2001; Copeland, 1951). We include
> representative aggregation methods — Bradley–Terry MLE, win-rate,
> Markov-chain, and tournament sort — as baselines evaluated on the same
> preference graphs (§Experiments). Our contribution is the explicit modelling
> and repair of graph-level inconsistencies, which these aggregation methods
> do not address. Under synthetic preference noise at 15% flip probability,
> FAS-balance achieves higher nDCG than Bradley–Terry MLE on both evaluation
> datasets, with 95% CIs strictly above zero (§Results). On clean acyclic
> graphs the two approaches yield equivalent results."

---

## 7. Summary Positioning Table

| Modern paradigm | Our stance | Baseline run status |
|-----------------|-----------|---------------------|
| Cross-encoder reranking | External reference; distinct in focus from our framework | real completed run |
| LLM pointwise | Different paradigm; no preference graph | code only — pending |
| LLM pairwise (PRP) | Closest paradigm; feeds into our pipeline | code only — pending |
| LLM listwise (RankGPT) | End-to-end alternative; no explicit repair | code only — pending |
| Graph / tournament aggregation | Our core contribution extends this class | real completed run |

---

## 8. What "Representative Modern Baselines" Means

We describe our baselines as **representative modern baselines** because:

1. Each implements a distinct algorithmic paradigm (parametric MLE,
   social-choice, neural reranking, graph-theoretic repair).
2. We do not claim to reproduce any specific named paper's experimental
   configuration.
3. Numerical comparisons are valid only within our evaluation protocol
   (same datasets, same candidate pools, same qrels).
4. The goal is to establish relative ordering of methods *within our
   evaluation framework*, not to rank against externally reported numbers
   from different corpora or candidate pools.

---

## 9. Explicit Non-Claims

- We do NOT claim to outperform RankGPT, PRP, or any specific published system
  because we have not run those systems on our datasets.
- We do NOT claim that our cross-encoder results are comparable to published
  cross-encoder results on BEIR or BRIGHT because our evaluation setup
  (candidate pools, k, preprocessing) may differ.
- We do NOT claim generality beyond the three-ranker (BM25, TF-IDF, MiniLM-L6)
  ensemble used to construct preference votes.

---

## 10. How to Use This in the Manuscript

| Manuscript location | What to adapt from this document |
|---------------------|----------------------------------|
| **§Related Work — Neural reranking** | Use §2 "How to describe in manuscript" for the cross-encoder paragraph. One sentence; cite Nogueira & Cho (2019) or similar. |
| **§Related Work — LLM-based reranking** | Use §3, §4, §5 "How to describe" blocks for a three-paragraph treatment of pointwise / pairwise / listwise. Keep each to 2–3 sentences. End each with the "deferred to future work" clause. |
| **§Related Work — Aggregation methods** | Use §6 "How to describe" for the tournament-aggregation paragraph. Cite Bradley & Terry (1952), Dwork et al. (2001), Copeland (1951). |
| **§Implementation / §Baselines** | Reference §1 taxonomy table to justify baseline selection. State explicitly which paradigms have run results and which are pending. |
| **§Limitations / Future Work** | Cite §4 "most directly analogous paradigm" framing as the basis for the Future Work paragraph on LLM preference sources. |
| **Cover letter** | Use §7 "Summary Positioning Table" as a one-paragraph summary of how the paper now engages with the modern literature. |
