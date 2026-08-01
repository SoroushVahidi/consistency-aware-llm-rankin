# Repetition and Redundancy Audit (SNCS 2026)

**Manuscript:** `papers/SNCS_2026/manuscript/main.tex` / `main.pdf`  
**Branch:** `papers/sncs-2026-foundation`  
**Audit date:** 2026-08-01  
**Scope:** Dedicated repetition/redundancy audit only — not a general
proofreading pass. No new experiments; no new scientific claims; no
canonical-result changes.

**Baseline (pre-reduction):** 42 pages; ~15,112 detex body words
(Abstract through Statements, excluding bibliography).

**Method:** Full PDF cold read, then LaTeX inspection. Automated
sentence-level cosine / Jaccard filtering (372 sentences ≥8 words;
17 cross-section near-duplicate pairs at cos≥0.55 or jac≥0.45) used only
to *propose* candidates; every flag below was manually inspected in
context. Ignored: section titles, dataset/method names, formal notation,
standard declarations, necessary cross-references, figure/table labels,
bibliography.

---

## 1. Quantitative summary

| Quantity | Count / estimate | Method |
|---|---|---|
| Exact duplicate sentences (normalized token identity, ≥10 tokens) | **0** | Automated exact match after detex + token normalize; none survived |
| Near-duplicate sentence pairs (cos≥0.55 or jac≥0.45, different sections, manually confirmed) | **14** (of 17 auto-candidates; 3 discarded as caption/table echo or unavoidable parallel definition) | Cosine on bag-of-tokens + Jaccard; manual review |
| Repeated concepts appearing in **≥3 sections** | **11** | Manual high-risk theme map (see §5) |
| Paragraphs that primarily restate tables/figures | **5** | Manual rhetorical review of Results |
| Potentially redundant figures/tables | **2 partly redundant** (none strongly redundant / remove) | Visual + caption audit (§1.D) |
| Estimated pages savable without removing scientific content | **~2–3 pages** (~700–1,200 words) | Conservative; after safe edits (see changelog) |

### Severity rollup (issues, not instances)

| Severity | Count |
|---|---|
| Critical | 3 |
| Major | 8 |
| Moderate | 10 |
| Minor | 6 |
| Necessary (retained) | 12 patterns |

---

## 2. Level A — Exact or near-exact sentence repetition

| ID | First location | Repeated location(s) | Similarity | Necessary? | Severity | Recommended action |
|---|---|---|---|---|---|---|
| A1 | Background §MWFAS: “Exact repair is used here as a *diagnostic control*, not as a proposed practical replacement…” | Methodology §Repair Methods (near-identical paragraph) | Near-exact | No | **Critical** | Keep full statement in Background; Methodology keeps SCIP/version/time-limit details + short cross-ref |
| A2 | Background §MWFAS: greedy cycle-peeling definition | Methodology §Repair Methods: same algorithm restated | Near-exact | Partly (Methodology adds “not Eades–Lin–Smyth”) | **Major** | Keep distinguishing attribution in Methodology; drop algorithm restatement |
| A3 | Background §Extraction: “Each graph-only rule is computed on both \(G_q\) and \(\widetilde{G}_q\)…” | Methodology §Extraction: “Every graph-dependent rule… is computed on both…” | Near-exact | Partly (Methodology adds α-masking reviewer point) | **Major** | Keep unique α-masking sentence; shorten rest to cross-ref |
| A4 | Related Work §Utility closing: “contribution… controlled separation: holding construction explicit, comparing unrepaired/heuristic/exact…” | Discussion §Literature: same contribution sentence | Near-exact | No | **Major** | Keep in Related Work; Discussion cites Related Work in one clause |
| A5 | Related Work §Repair: full preprint-relation paragraph | Discussion §Literature: second full preprint-relation paragraph | Near-exact conceptual | No | **Critical** | Keep full in Related Work; Discussion → 1–2 sentences + cross-ref |
| A6 | Introduction: “Structural repair is genuinely active… no … nDCG comparison survives Holm…” | Discussion §Main Findings: four-finding restatement of same arc | High near-dup | Brief recall OK | **Major** | Discussion should interpret, not re-narrate Results/Intro |
| A7 | Results §LLM: six-query / directional / supporting | Discussion §LLM + Limitations §External + §Statistical | High near-dup | One full + brief recalls | **Major** | Full in Results; brief in Limitations External; delete third/fourth full restatements |
| A8 | Results §Robustness: MDE 0.0036 vs 0.0201 + equivalence minority | Limitations §Statistical: same numbers restated | High | Brief recall OK | **Moderate** | Limitations cite Results; drop number dump |
| A9 | §Data Availability: URL + raw-payload exclusion | Statements §Data/materials/code: same | Near-exact | Journal often wants both | **Moderate** | Declarations → short cross-ref to §Data Availability |
| A10 | Acknowledgments: grant/credit list | Statements §Funding: same list | Near-exact | No (superseded 2026-08-01) | Was flagged Necessary; **relocated** | Credits now Funding-only; Acknowledgments personal only — see `FUNDING_ACK_CHANGELOG.md` |
| A11 | Results §Exact: “greedy… real, non-trivial overestimate…” | Discussion §Exact: same claim restated | High | Brief | **Major** | Discussion interpret only; cite Results |
| A12 | Methodology §Metrics: “three kinds of quantity… restating §Extraction’s closing point” | Already stated in Background §Extraction | Self-acknowledged restatement | No full restatement | **Moderate** | Short operational pointer + cross-ref |
| A13 | Introduction contribution #3 | Abstract Conclusion + Intro finding paragraph + Discussion + Conclusion | Conceptual cascade | Abstract + one body home | **Critical** | Prefer Intro contributions / Discussion synthesis; Conclusion synthesize only |
| A14 | Figure/table captions echoing adjacent prose (esp. BM25 share; cycle decomposition) | Adjacent Results paragraphs | Moderate | Captions need partial self-containment | **Minor** | Leave; do not gut captions |

---

## 3. Level B — Conceptual repetition (multi-section)

| Concept | Sections where it appears in substantive form | Preferred home | Action |
|---|---|---|---|
| Structural consistency ≠ retrieval utility | Abstract, Intro, Related Work, Background, Methods metrics, Results (implicit), Discussion (×3), Limitations construct, Conclusion | **Discussion §Main Findings** (interpretive); formal gap in **Background §Extraction** | Trim Intro/Conclusion/Related Work restatements; keep Abstract |
| Exact repair as diagnostic control | Intro, Background, Methods, Results Exact, Discussion Exact, Limitations Computational, Conclusion | **Background** (definition) + **Results Exact** (evidence) | Methods/Discussion/Limitations → short cross-refs |
| Heuristic suboptimality ruled out | Intro, Background, Methods, Results, Discussion Exact, Conclusion | **Results Exact** (once, with numbers) | Elsewhere: one clause |
| Four-stage separation | Intro, Background open, Related Work, Discussion literature, Conclusion | **Intro** (motivation) + **Methods pipeline** (operational) | Conclusion recall in one sentence |
| Six-query LLM pilot limit | Intro scope, Methods stats, Results LLM, Discussion LLM, Limitations External+Statistical | **Results LLM** + **Limitations External** | Remove Discussion/Statistical duplicates |
| Non-significance ≠ equality / small effects possible | Related Work (Lakens), Results Robustness, Discussion Main Findings, Limitations Statistical | **Results Robustness** (numbers) + **Limitations Statistical** (interpretation) | Discussion keep one careful sentence |
| Not SOTA / not a new solver / not “never helps” | Intro scope, Methods rankers, Methods baselines, Discussion Main Findings, Conclusion | **Intro scope** (once, fully) | Elsewhere: “controlled comparison set” only |
| MWFAS optimizes disagreement, not relevance | Intro, Background MWFAS, Background Extraction, Methods metrics, Discussion mechanism, Limitations construct | **Background §MWFAS + §Extraction** | Discussion mechanism opens with cross-ref, not re-proof |
| Holm correction protocol | Abstract, Intro, Methods stats, Results open, many result sentences, Limitations, Conclusion | **Methods §Statistics** (definition) | Results report outcomes; do not re-explain Holm |
| Preprint vs present study | Related Work, Discussion literature | **Related Work** | Discussion short cross-ref |
| Practical recommendations | Abstract close, Discussion Practical (bullets), Conclusion | **Discussion §Practical** | Conclusion: 2–3 sentence synthesis, not second bullet list |
| Reproducibility / repo URL | Intro contrib #4, Methods Repro, Data Availability, Declarations | **Data Availability** | Methods: tooling only; Declarations: cross-ref |

---

## 4. Level C — Structural / rhetorical repetition

| Pattern | Assessment | Severity | Action |
|---|---|---|---|
| Background fully defines greedy/exact/extraction; Methodology re-defines then instantiates | Methodology should instantiate, not re-teach | **Major** | Cut definitional prose; keep protocol specifics |
| Related Work ends with contribution restatement that mirrors Intro + Discussion literature | Related Work should position literature; contribution already in Intro | **Moderate** | Keep one short “gap this paper fills” in Related Work; cut Discussion duplicate |
| Discussion §Main Findings largely re-narrates Results | Discussion should answer “so what,” not re-list cells | **Critical** | Condense to interpretive synthesis |
| Discussion §Exact Repair re-argues Results Exact | Same | **Major** | Shorten to methodological implication |
| Conclusion walks RQ1–RQ4 like a second Results+Discussion | Conclusion should synthesize | **Major** | Compress RQ walkthrough |
| Results retrieval paragraph lists every family already in `tab:retrieval-holm` | Mild table narration | **Moderate** | Keep one interpretive sentence + point estimates of interest; drop full re-enumeration where table suffices |
| Limitations Statistical re-dumps power/equivalence table | Duplicate of Results Robustness | **Moderate** | Cross-ref |
| Funding list in Acknowledgments and Funding | Dual placement not required; credits moved to Funding only (2026-08-01) | Resolved | See `FUNDING_ACK_CHANGELOG.md` |

---

## 5. Level D — Visual repetition (figures and tables)

| Asset | Classification | Notes |
|---|---|---|
| Fig. 1 pipeline | **Unique and necessary** | Clarifies dual repair branches; not a substitute for Algorithm 1 |
| Fig. 2 BM25 share | **Unique and necessary** | Visualizes raw vs normalized domination |
| Fig. 3 cycle decomposition | **Unique and necessary** | Complements `tab:structural-outcomes`; not a duplicate of the table (table has FAS weight; figure shows before/after mutual) |
| Fig. 4 bootstrap forest | **Unique and necessary** | Shows signed CIs that the Holm table does not |
| Fig. 5 exact vs greedy gap | **Unique and necessary** | Visual companion to `tab:exact-vs-greedy` (bar view of same structural gap) — **partly redundant** with that table, but different encoding (visual comparison across datasets); retain |
| `tab:setup` | Unique and necessary | Protocol only |
| `tab:baselines` | Unique and necessary | Method-family map |
| `tab:structural-outcomes` | Unique and necessary | Primary structural numbers |
| `tab:retrieval-holm` | Unique and necessary | Headline Holm families + baseline means |
| `tab:exact-vs-greedy` | Unique and necessary | Structural gap numbers; caption previously also dumped retrieval Holm counts already in prose → **caption partly redundant** (shorten caption) |
| `tab:robustness` | Unique and necessary | Compact multi-check summary; partly overlaps Results prose by design (table is the compact form) — retain |
| Algorithm 1 | Unique and necessary | Operationalizes construction; Fig. 1 is schematic, not duplicate |

**Potentially redundant count:** 2 (Fig. 5 ↔ `tab:exact-vs-greedy` structural numbers; robustness table ↔ surrounding prose). Neither is a removal candidate; caption trim only.

---

## 6. High-risk statement placement guide

| Statement family | State fully | Brief recall OK | Remove / shorten |
|---|---|---|---|
| Structural consistency is not a reliable surrogate for retrieval effectiveness | Discussion Main Findings; Abstract | Intro thesis sentence; Conclusion one line | Related Work closing + repeated Discussion LLM paraphrase of same thesis |
| Repair changes structure but not general nDCG | Results Retrieval + Exact | Intro finding; Discussion | Conclusion RQ walkthrough length |
| Exact SCIP rules out weak greedy explanation | Results Exact | Intro motivation; Methods one sentence | Background+Methods dual full paragraphs; Discussion Exact essay-length restatement |
| LLM study has only six independent queries | Results LLM | Limitations External; Intro scope | Discussion LLM + Limitations Statistical second full statement |
| Does not claim SOTA retrieval | Intro scope | Methods baselines one clause | Repeated “not SOTA” wherever methods are introduced |
| MWFAS optimizes disagreement, not relevance | Background MWFAS/Extraction | Discussion mechanism open sentence | Methods metrics full restatement; multiple Discussion re-proofs |
| Non-significant ≠ no effect / equality | Results Robustness + Limitations Statistical | Discussion Main Findings one sentence | Duplicate number dumps |
| Construction / repair / extraction / evaluation must be separated | Intro + Methods pipeline | Conclusion one sentence | Discussion literature restating framework as “contribution” again |
| Replicated LLM rows are not independent | Methods Statistics + Results LLM | Limitations Statistical one clause | Third narrative in Discussion |
| Holm correction applied | Methods Statistics | Results opening sentence | Re-explaining Holm in Limitations |
| Controlled empirical study, not new reranking method | Intro | — | Restating in Conclusion at length |

---

## 7. Major-idea placement table

| Major idea | Primary section | Allowed brief repetition | Locations to remove or shorten |
|---|---|---|---|
| Central research gap | Introduction | Abstract Purpose; Related Work one paragraph | Discussion literature contribution restatement |
| Four contributions | Introduction list | Abstract (compressed) | Conclusion (do not re-list as numbered contributions) |
| Exact-repair motivation | Background §MWFAS | Intro motivation; Results Exact evidence sentence | Methodology duplicate paragraph; Discussion Exact; Limitations Computational essay |
| Statistical interpretation (Holm, power, non-equivalence) | Methods §Statistics + Results §Robustness | Limitations Statistical (interpretation only) | Discussion number re-dump |
| LLM scope limitation | Results §LLM | Intro scope; Limitations External | Discussion LLM; Limitations Statistical duplicate |
| Practical implications | Discussion §Practical | Abstract closing sentence; Conclusion 2–3 sentences | Conclusion second bullet-style list |
| Threats to validity | Limitations (all subsections) | — | Do not scatter full threats into Discussion |
| Reproducibility statement | §Data Availability | Methods tooling sentence; Intro contrib #4 one line | Declarations full URL paragraph |
| Preprint relation | Related Work | Discussion one sentence | Second full Discussion paragraph |
| Mechanism (why repair ≠ nDCG) | Discussion §Mechanism (interpretation) | Background formal gap (definition) | Opening of Mechanism that re-proves Background |

---

## 8. Section-by-section redundancy table

| Section | Unique content | Repeats earlier material | Keep | Shorten / move / delete | Est. word savings |
|---|---|---|---|---|---|
| **Abstract** | Structured Purpose/Methods/Results/Conclusion | — | Entire abstract (must be self-contained) | None beyond light polish | 0 |
| **Introduction** | Motivation, gap, scope denials, contributions | Thesis appears again later | Gap, scope, contributions | Slight trim where finding paragraph duplicates contrib #3 | ~40–80 |
| **Related Work** | Literature survey + preprint status | Closing “contribution” ≈ Intro; utility gap ≈ Discussion | Survey + preprint paragraph | Shorten closing contribution; leave preprint here | ~60–100 |
| **Background** | Formal defs, regimes, MWFAS MIP, nDCG vs repair gap | Four-stage echo of Intro | All formal definitions | None essential; primary home for diagnostic-control *definition* | 0 |
| **Methodology** | RQs, pipeline, datasets, SCIP details, stats protocol, AI disclosure | Re-defines greedy/exact/extraction/objective split | Protocol specifics, Algorithm 1, stats, AI disclosure | Cut definitional duplicates of Background | ~180–250 |
| **Results** | All numbers, tables, figures | Mild table narration | Evidence | Tighten retrieval family enumeration; shorten exact-vs-greedy caption | ~80–120 |
| **Discussion** | Mechanisms, practical bullets, literature contrast | Main Findings ≈ Results; Exact ≈ Results; preprint ≈ Related Work; LLM ≈ Results | Mechanism (unique), Practical (unique), Literature contrast (unique parts) | Condense Main Findings, Exact, preprint, LLM | ~350–450 |
| **Limitations** | Validity threats | Statistical dumps Results power; LLM restated; exact role restated | Threat framing | Cross-ref Results for numbers; shorten Computational diagnostic essay | ~120–180 |
| **Conclusion** | Future work | RQ1–4 walkthrough ≈ Results+Discussion; practical ≈ Discussion | Short synthesis + future work | Compress RQ walkthrough and practical echo | ~120–160 |
| **Acknowledgements / Declarations** | Thanks; funding; ethics N/A; contributions | Data availability ≈ §Data Availability; funding ≈ Acknowledgments | Ethics/consent/authors; funding dual placement | Declarations data → cross-ref | ~40–60 |

**Total estimated safe savings:** ~990–1,400 words (~2–3 pages at this template density).

---

## 9. Final reviewer test (pre-edit snapshot)

| Question | Pre-edit answer |
|---|---|
| Central conclusion repeated too often? | **Yes** — Abstract, Intro (×2), Related Work close, Discussion (×3), Conclusion |
| Distinct section purposes? | Mostly, but Discussion and Conclusion bleed into Results restatement |
| Discussion adds interpretation? | Partially — Mechanism and Practical do; Main Findings / Exact mostly do not |
| Conclusion synthesizes? | Weakly — largely RQ recapitulation |
| Limitations stated once clearly? | Mostly localized, but LLM + power + exact-role leak elsewhere |
| Feel like 42 pages of necessary content? | Close, but ~2–3 pages are rhetorical inflation |
| Could an editor call it verbose? | **Yes, moderately** |

**Pre-edit verdict:** **Noticeable repetition** (bordering on Excessive for diagnostic-control and thesis statements).

### Post-edit (after safe reductions)

See [`REPETITION_REDUCTION_CHANGELOG.md`](REPETITION_REDUCTION_CHANGELOG.md) for the edit list and metrics.

| Metric | After reduction |
|---|---|
| Pages | **39** (was 42) |
| Body words | **13,419** (was 15,112; −11.2%) |
| Final repetition verdict | **Acceptable repetition** |

Post-edit reviewer-test answers: Discussion now interprets rather than re-narrating Results; Conclusion synthesizes; limitations are localized; Abstract remains self-contained. Residual repetition is necessary section self-containment, brief cross-references, and required dual funding/data declarations — not thesis looping.
