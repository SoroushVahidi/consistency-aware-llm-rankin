# External Solver Identity

**Prepared:** 2026-07-12
**Scope:** Part A1 — identify the package referenced via `sys.path.insert(0, "/home/soroush/minimum-weighted-fas-heuristics/src")` in this repository's audit scripts. Every fact below cites the exact local evidence (file, line, or command run in this session).

---

## Headline finding

The "external solver" is **not a third-party package**. It is the same author's (Soroush Vahidi's) own separate, MIT-licensed research repository, `minimum-weighted-fas-heuristics`, developed for a different, currently-unpublished manuscript (declined once at COAP, being retargeted to SN Computer Science). It is genuinely public on GitHub (verified live, not just from local config — see below), but it is **not pip-installed** anywhere, is **not vendored** into this repository, and its GitHub identity would **deanonymize the JDIQ submission's author** if cited by name/URL during double-blind review. This last point is the most important fact for the manuscript decision (Part A5).

---

## A1 facts, each with exact evidence

| Fact | Value | Evidence |
|---|---|---|
| Repository name | `minimum-weighted-fas-heuristics` | Directory name `/home/soroush/minimum-weighted-fas-heuristics`; `setup.py` `name="mwfas"` |
| Import/module name | `mwfas` (subpackages `mwfas.exact`, `mwfas.lrta`, `mwfas.wmsf`, `mwfas.ipsns`) | `experiments/method_improvement_audit_20260711_205733/run_method_improvement_audit.py:1042-1066` — `from mwfas.exact import exact_min_fas_from_dimacs`, `from mwfas.lrta import paper_fas_ranking_from_dimacs_fast`, `from mwfas.wmsf import wmsf_ranking_from_dimacs_fast`, `from mwfas.ipsns import lns_merge_wmsf_lr_best_incumbent` |
| Local absolute path | `/home/soroush/minimum-weighted-fas-heuristics/src` | Same file, line 1042: `sys.path.insert(0, "/home/soroush/minimum-weighted-fas-heuristics/src")` (repeated at each of the four `elif`/`if` branches, lines 1042/1047/1052/1057) |
| Author | Soroush Vahidi (ORCID `0000-0003-1934-6282`) — **the same author as this JDIQ manuscript** | `/home/soroush/minimum-weighted-fas-heuristics/CITATION.cff` lines 6-9; `git log` author field (see below) |
| Associated paper | **None accepted/published.** Historical target *Computational Optimization and Applications* (COAP) — **declined**. Active target *SN Computer Science* (SNCS) — draft, "not submission-ready." No arXiv preprint found. | `/home/soroush/minimum-weighted-fas-heuristics/README.md` lines 3-14: "COAP status: declined / closed"; "SN Computer Science... not yet ready for final journal upload". `CITATION.cff` line 22: `notes: "Manuscript prepared for submission; not yet published."` (this note is itself stale relative to the README's more current "declined" status — a discrepancy between the package's own two metadata sources, noted for completeness, not resolved by us). `grep -rln "arxiv" paper_sncs/ paper_coap/` in that repository returned only `.bst` bibliography style files, no actual preprint reference. |
| Package version / commit | `setup.py`: `version="0.1.0"`. Git: commit `40209c26966247d9bf9ad34764de4ac4181f98c2` on branch `main`, confirmed pushed (`git status -sb` shows `## main...origin/main` with no ahead/behind delta) | Commands run in this session: `git rev-parse HEAD`, `git branch --show-current`, `git status -sb`, all inside `/home/soroush/minimum-weighted-fas-heuristics` |
| License | MIT | `/home/soroush/minimum-weighted-fas-heuristics/LICENSE` (full text read; standard MIT, copyright "Soroush Vahidi 2026") |
| Publicly available? | **Yes, verified live**, not only from local git config | `curl -s https://api.github.com/repos/SoroushVahidi/minimum-weighted-fas-heuristics` (unauthenticated, run in this session) returned HTTP 200 with `"private": false` |
| Installed in the current environment? | **No.** Not pip-installed in this repository's virtualenv; accessed only via a hardcoded `sys.path.insert` to an absolute local path that happens to exist on this machine. | `cd /home/soroush/consistency-aware-llm-rankin && .venv/bin/pip freeze \| grep -i mwfas` returned nothing (checked this session) |
| Copied anywhere inside this repository (`consistency-aware-llm-rankin`)? | **No.** No vendored copy, no requirements.txt entry, no submodule. | `grep -rln "mwfas" --include="*.py" .` inside `consistency-aware-llm-rankin` (repeated from a prior session) matched only the two audit scripts that `sys.path.insert` to the external path; `requirements.txt` in this repo does not list `mwfas`. |
| Redistributable? | Yes in principle (MIT license permits redistribution/vendoring), but not currently redistributed with this repository. | MIT LICENSE text; absence of vendoring confirmed above. |

---

## Algorithm identities (resolved with primary-source precision, not inferred from names alone)

Per task instruction A1 ("Do not infer package identity from method names alone"), the following were read directly from the external repository's own source and documentation, not guessed from the method labels used in `consistency-aware-llm-rankin`:

| Method label (as used in `consistency-aware-llm-rankin`) | External module / function | Full name (verified) | Prior-art attribution (verified) |
|---|---|---|---|
| `exact_scc_dp20` | `mwfas.exact.exact_min_fas_from_dimacs` | Exact minimum-weighted FAS via **bitmask dynamic programming** (Held-Karp-style subset DP), `O(n\cdot2^n)`, restricted to `n \le 20` | Standard exact technique; no external citation needed beyond acknowledging bitmask DP. `mwfas/exact.py` docstring: "dp[S] = maximum total forward weight achievable with vertices in S..." |
| `lrta_external` | `mwfas.lrta.paper_fas_ranking_from_dimacs_fast` | **L**ocal-**R**atio **T**opological **A**dd-back (LR-TA) | Novel part: the "Topological Add-Back" phase (Phase 2). Prior-art part: the local-ratio framework, attributed to **Bar-Yehuda, R., Geiger, D., Naor, J., & Roth, R. M. (1998). Approximation algorithms for the feedback vertex set problem with applications to constraint satisfaction and Bayesian inference. *SIAM Journal on Computing*, 27(4), 942-959.** (`docs/baselines_and_datasets_references.md` lines 133-145 in the external repository) |
| `wmsf_external` | `mwfas.wmsf.wmsf_ranking_from_dimacs_fast` | **W**eighted **M**inimum **S**panning **F**orest (WMSF) heuristic | "Reimplementation of pipeline from predecessor paper (paper049)" — an internal reference code for the author's own unpublished predecessor work, not resolvable to a citable title/venue from local evidence. `docs/baselines_and_datasets_references.md` line 153. |
| `ipsns_external` | `mwfas.ipsns.lns_merge_wmsf_lr_best_incumbent` | **I**ncumbent-**P**rotected **SCC**-**N**eighborhood **S**earch (IPSNS) | The external repository's own stated **primary novel contribution**: "IPSNS... an SCC-local destroy-and-repair heuristic integrated with LR-TA and WMSF-style seeds... IPSNS is the new integrated framework." (`README.md` line 25) |

**Correction to a claim made in an earlier drafting pass of `main.tex`:** that draft parenthetically glossed IPSNS as "large-neighborhood search." That guess is now confirmed **imprecise** — IPSNS internally *uses* a large-neighborhood-search-style local move (the module docstring says "improves via Large Neighborhood Search (LNS) applied to one SCC at a time"), but the acronym IPSNS itself expands to "Incumbent-Protected SCC-Neighborhood Search," not "large-neighborhood search." The current `main.tex` (as of the previous session) already removed the guessed expansion and left the name unexpanded with a disclosed-uncertainty footnote, which was the right call; this document now supplies the verified expansion for Part D's patch recommendations.

---

## Gurobi/ILP cross-check

The external repository's own documentation independently confirms what was found in `consistency-aware-llm-rankin`: **Gurobi is not used anywhere in either repository's actual results.** `docs/baselines_and_datasets_references.md`'s "Not Used / Explicitly Excluded" table lists: `Gurobi-based solvers | Gurobi not installed`. This corroborates the correction already made in `main.tex` §4.6 (that the in-repo `mwfas_solver.solve(method="ilp")` Gurobi path exists but was not the solver behind any committed result table).

---

## Open items not resolved in this document

- The exact identity of "paper049" (WMSF's predecessor-paper internal reference code) was not resolved to a citable title/author/venue from local evidence in either repository. If a citation for WMSF specifically (beyond IPSNS/LR-TA) is needed in the JDIQ manuscript, this remains a TODO.
- Whether the discrepancy between `CITATION.cff` ("not yet published") and `README.md` ("declined / closed") reflects a simple staleness in `CITATION.cff` or something else was not investigated further — it does not affect the JDIQ manuscript decision either way, since neither status supports citing an accepted publication.
