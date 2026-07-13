"""Real-LLM judgment integrity audit for the JDIQ manuscript.

Reads only already-stored API requests/responses/logs (no new API calls).
Reuses the repo's own graph/repair/nDCG pipeline (process_query_record) so
every recomputation is done with the exact same code that produced the
committed/local outputs, just fed different (re-parsed) preference edges.

Provenance:
- Committed data/code comes from the origin/main checkout at this worktree's
  HEAD (see PROVENANCE.txt written alongside this script).
- Local-only raw LLM data (Cohere/Azure prompt+response logs, never
  committed to origin/main) is read from ../../_local_uncommitted_snapshot,
  which is an exact copy of reports/failure_mining_llm_v3 (and sibling
  versions) from the primary working tree as of this audit's start.
- The failure_mining package and three modified source files
  (baseline_ranking.py, llm_pairwise.py, utils/llm_api_status.py) were
  overlaid into this worktree's src/ tree at runtime ONLY so the existing
  process_query_record() pipeline could be imported and reused; these
  overlays are never staged/committed by this audit (see step 16 of the
  task spec -- commit only the audit directory).
"""
from __future__ import annotations

import csv
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict, namedtuple
from pathlib import Path

WT = Path("/tmp/real_llm_audit_worktree")
SNAP = WT / "_local_uncommitted_snapshot"
AUDIT_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(WT / "src"))
sys.path.insert(0, str(WT))

from consistency_ranker.failure_mining.query_processor import process_query_record  # noqa: E402
from consistency_ranker.pairwise_prefs import Preference  # noqa: E402

QrelRow = namedtuple("QrelRow", ["doc_id", "relevance"])

TOP_K = 10  # matches run metadata: max_candidates=10 for the v3 corpus
RNG_SEED = 42
N_BOOTSTRAP = 2000

V3 = SNAP / "reports" / "failure_mining_llm_v3"

POLICIES = ["P0", "P1", "P2", "P3", "P4"]
POLICY_NAMES = {
    "P0": "current_parser",
    "P1": "ambiguous_to_abstain",
    "P2": "discard_ambiguous",
    "P3": "exact_A_or_B_only",
    "P4": "retry_success_only",
}


def log(msg: str) -> None:
    print(f"[audit] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Response classification (shared by parser audit, ambiguity quant, position
# bias, forward/reverse, and the P0-P4 reparse policies).
# ---------------------------------------------------------------------------

def classify_response(raw_response: str | None) -> tuple[str, str]:
    """Return (category, current_parser_label).

    category in {"exact", "verbose_valid", "contains_only", "ambiguous",
                 "malformed", "empty"}
    current_parser_label reproduces src/rerankers/llm_pairwise.py::_parse_winner
    exactly (always "A" or "B" -- this function never raises/aborts).
    """
    if raw_response is None:
        return "empty", "A"
    text = raw_response.strip().upper()
    if text == "":
        return "empty", "A"
    has_a = "A" in text
    has_b = "B" in text
    if text.startswith("A"):
        return ("exact" if text == "A" else "verbose_valid"), "A"
    if text.startswith("B"):
        return ("exact" if text == "B" else "verbose_valid"), "B"
    if has_a and not has_b:
        return "contains_only", "A"
    if has_b and not has_a:
        return "contains_only", "B"
    if has_a and has_b:
        return "ambiguous", "A"  # current parser's dead "return A" fallback
    return "malformed", "A"  # neither letter present anywhere


FALLBACK_CATEGORIES = {"ambiguous", "malformed", "empty"}


def label_under_policy(category: str, current_label: str, policy: str) -> str | None:
    """Return 'A'/'B' or None (no usable label) for one raw response under a policy."""
    if policy == "P0":
        return current_label
    if policy == "P1":  # ambiguous (incl. malformed/empty) -> abstain (this direction only)
        return None if category in FALLBACK_CATEGORIES else current_label
    if policy == "P2":  # discard-ambiguous: same per-direction signal as P1;
        # pair-level discarding is enforced by the caller (combine_pair)
        return None if category in FALLBACK_CATEGORIES else current_label
    if policy == "P3":  # exact A/B only
        return current_label if category == "exact" else None
    if policy == "P4":  # retry-success only -- applied at query level by caller,
        # per-direction label is the current parser's label
        return current_label
    raise ValueError(policy)


def combine_pair(ab: tuple[str, str] | None, ba: tuple[str, str] | None, policy: str) -> tuple[str | None, str]:
    """Combine (category,label) for the ab and ba directions of one pair into
    (winner, reason). winner in {"A","B",None}; reason explains an exclusion:
    "ok", "response_quality" (a direction was ambiguous/malformed/empty), or
    "fwd_rev_disagreement" (both directions individually clean but the
    forward and reverse presentations disagree, so a straight default-to-A
    would hide real position sensitivity rather than resolve it).
    """
    ab_fallback = bool(ab) and ab[0] in FALLBACK_CATEGORIES
    ba_fallback = bool(ba) and ba[0] in FALLBACK_CATEGORIES
    ab_lbl = label_under_policy(*ab, policy) if ab else None
    ba_lbl = label_under_policy(*ba, policy) if ba else None

    if policy == "P2" and (ab_fallback or ba_fallback):
        return None, "response_quality"

    if ab_lbl is None and ba_lbl is None:
        return None, "response_quality"
    if ab_lbl is not None and ba_lbl is None:
        return ab_lbl, "ok"
    if ab_lbl is None and ba_lbl is not None:
        return ("B" if ba_lbl == "A" else "A"), "ok"

    # both directions produced a label: reproduce the production
    # unanimity-for-B rule (P0), or treat disagreement as abstain for P1-P4
    # (see PARSER_AUDIT.md: P0's default-to-id_a-on-split is itself an
    # audited bias, not replicated here).
    ab_vote_b = 0 if ab_lbl == "A" else 1
    ba_vote_b = 1 if ba_lbl == "A" else 0
    total_b = ab_vote_b + ba_vote_b
    if policy == "P0":
        return ("A" if total_b < 2 else "B"), "ok"
    if total_b == 0:
        return "A", "ok"
    if total_b == 2:
        return "B", "ok"
    return None, "fwd_rev_disagreement"


# ---------------------------------------------------------------------------
# Load raw prompt/response log and index it.
# ---------------------------------------------------------------------------

def load_prompt_log(path: Path) -> list[dict]:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def index_prompt_log(rows: list[dict]) -> dict:
    """index[(provider, query_id, frozenset({doc_a,doc_b}))][direction] = row"""
    idx: dict = defaultdict(dict)
    for r in rows:
        if r.get("direction") not in ("ab", "ba"):
            continue  # skip pure cache-hit marker rows if present
        key = (r["provider"], r["query_id"], frozenset({r["doc_a_id"], r["doc_b_id"]}))
        idx[key][r["direction"]] = r
    return idx


def index_prompt_log_full(rows: list[dict]) -> dict:
    """index[(provider, query_id, frozenset({doc_a,doc_b}))] = {"ab":row?, "ba":row?, "cached":row?}"""
    idx: dict = defaultdict(dict)
    for r in rows:
        d = r.get("direction")
        if d not in ("ab", "ba", "cached"):
            continue
        if d == "cached":
            key = (r["provider"], r["query_id"], frozenset({r["doc_a_id"], r["doc_b_id"]}))
        else:
            key = (r["provider"], r["query_id"], frozenset({r["doc_a_id"], r["doc_b_id"]}))
        idx[key][d] = r
    return idx


def load_cache_lookup(provider_dir_name: str) -> dict:
    path = V3 / "llm_cache" / provider_dir_name / "llm_pairwise_judgments.jsonl"
    out = {}
    with path.open() as f:
        for line in f:
            d = json.loads(line)
            key = (d["query_id"], frozenset(d["doc_ids"]))
            out[key] = (d["winner"], d["loser"])
    return out


PROVIDER_DIRS = {"cohere": "cohere_command-r-plus-08-2024", "azure": "azure_gpt-4.1-mini"}


def load_query_level_records() -> list[dict]:
    with (V3 / "query_level_full_records.jsonl").open() as f:
        return [json.loads(line) for line in f]


def load_llm_call_records() -> list[dict]:
    with (V3 / "llm_call_records.jsonl").open() as f:
        return [json.loads(line) for line in f]


def build_llm_prefs_for_record(
    qm: dict,
    provider: str,
    policy: str,
    cache_lookup: dict,
    prompt_idx: dict,
    retry_ok_query_ids: set,
) -> tuple[list, dict]:
    """Build Preference list for one (query_level record, provider, policy).

    Returns (prefs, coverage) where coverage counts pair outcomes.
    """
    cand = qm["candidate_doc_ids"]
    qid = qm["query_id"]
    cov = Counter()
    prefs = []
    n = len(cand)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = cand[i], cand[j]
            pair_key = (qid, frozenset({a, b}))
            cov["pairs_expected"] += 1

            if provider not in cache_lookup:
                continue
            cached_winner = cache_lookup[provider].get(pair_key)
            if cached_winner is None:
                cov["pairs_missing_from_cache"] += 1
                continue

            if policy == "P4":
                if qid not in retry_ok_query_ids:
                    cov["pairs_excluded_retry_policy"] += 1
                    continue

            log_key = (provider, qid, frozenset({a, b}))
            entry = prompt_idx.get(log_key, {})
            has_raw = "ab" in entry and "ba" in entry

            if policy == "P0":
                winner, loser = cached_winner
                cov["pairs_used"] += 1
                prefs.append(Preference(winner, loser, 1.0))
                continue

            if policy == "P4":
                # No per-pair retry granularity available; query already
                # passed the retry_count==0 gate above, so reuse the cached
                # (=P0) outcome for included queries.
                winner, loser = cached_winner
                cov["pairs_used"] += 1
                prefs.append(Preference(winner, loser, 1.0))
                continue

            # P1 / P2 / P3 require raw response text to reclassify.
            if not has_raw:
                cov["pairs_excluded_no_raw_text"] += 1
                continue

            ab_row, ba_row = entry["ab"], entry["ba"]
            ab_cls = classify_response(ab_row.get("raw_response"))
            ba_cls = classify_response(ba_row.get("raw_response"))
            # ab_row's doc_a_id/doc_b_id define what "A"/"B" meant for that call.
            # combine_pair expects ab in terms of (id_a,id_b) == (ab_row doc_a,doc_b)
            id_a, id_b = ab_row["doc_a_id"], ab_row["doc_b_id"]
            winner_label, reason = combine_pair(ab_cls, ba_cls, policy)
            if winner_label is None:
                cov[f"pairs_excluded_{reason}"] += 1
                continue
            winner = id_a if winner_label == "A" else id_b
            loser = id_b if winner_label == "A" else id_a
            cov["pairs_used"] += 1
            prefs.append(Preference(winner, loser, 1.0))

    return prefs, cov


def compute_retry_ok_query_ids(llm_call_records: list[dict], provider: str) -> set:
    """query_ids where this provider's record had retry_count == 0 (all records
    in this corpus have retry_count==0 or None/gemini; kept general on purpose)."""
    ok = set()
    for r in llm_call_records:
        if r.get("provider") != provider:
            continue
        if r.get("retry_count") == 0:
            ok.add(r["query_id"])
    return ok


def run_policy_for_all_records(
    records: list[dict],
    provider: str,
    policy: str,
    cache_lookup: dict,
    prompt_idx: dict,
    retry_ok_query_ids: set,
) -> list[dict]:
    out = []
    for rec in records:
        qm = rec["query_metadata"]
        prefs, cov = build_llm_prefs_for_record(
            qm, provider, policy, cache_lookup, prompt_idx, retry_ok_query_ids
        )
        row = {
            "dataset": qm["dataset"],
            "vote_regime": qm["vote_regime"],
            "query_id": qm["query_id"],
            "provider": provider,
            "policy": policy,
            "n_candidates": qm["n_candidates"],
            **{k: cov.get(k, 0) for k in (
                "pairs_expected", "pairs_used", "pairs_missing_from_cache",
                "pairs_excluded_no_raw_text", "pairs_excluded_response_quality",
                "pairs_excluded_fwd_rev_disagreement", "pairs_excluded_retry_policy",
            )},
        }
        if len(prefs) < 2:
            row.update({
                "usable": False, "is_cyclic": None, "n_sccs": None,
                "largest_scc_size": None, "n_edges_removed": None,
                "unrepaired_ndcg": None, "repaired_ndcg": None, "delta_ndcg": None,
                "help": None, "harm": None, "inactive": None,
            })
            out.append(row)
            continue

        qrels_for_query = [QrelRow(d, rel) for d, rel in qm["qrels"].items()]
        result = process_query_record(
            dataset=qm["dataset"],
            vote_regime=qm["vote_regime"],
            query_id=qm["query_id"],
            query_text=qm.get("query_text"),
            split=qm.get("split", "test"),
            qrels_for_query=qrels_for_query,
            prefs=prefs,
            score_prior_sets=[],
            top_k=TOP_K,
            doc_snippets=qm.get("doc_snippets"),
        )
        if result is None:
            row.update({
                "usable": False, "is_cyclic": None, "n_sccs": None,
                "largest_scc_size": None, "n_edges_removed": None,
                "unrepaired_ndcg": None, "repaired_ndcg": None, "delta_ndcg": None,
                "help": None, "harm": None, "inactive": None,
            })
            out.append(row)
            continue

        gs = result["graph_stats"]
        mo = result["method_outputs"]
        fl = result["failure_labels"]
        unrep = mo.get("markov_graph", {}).get("ndcg_at_k")
        rep = mo.get("markov_graph_repaired", {}).get("ndcg_at_k")
        delta = (rep - unrep) if (rep is not None and unrep is not None) else None
        row.update({
            "usable": True,
            "is_cyclic": gs.get("is_cyclic"),
            "n_sccs": gs.get("n_sccs"),
            "largest_scc_size": gs.get("largest_scc_size"),
            "n_edges_removed": result["repair_info"].get("n_edges_removed"),
            "unrepaired_ndcg": unrep,
            "repaired_ndcg": rep,
            "delta_ndcg": delta,
            "help": fl.get("repair_helps_vs_unrepaired"),
            "harm": fl.get("repair_harms_vs_unrepaired"),
            "inactive": fl.get("repair_inactive_vs_unrepaired"),
        })
        out.append(row)
    return out


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fn = fieldnames or list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def cohens_kappa(pairs: list[tuple[bool, bool]]) -> float | None:
    n = len(pairs)
    if n == 0:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    p_a1 = sum(1 for a, _ in pairs if a) / n
    p_b1 = sum(1 for _, b in pairs if b) / n
    pe = p_a1 * p_b1 + (1 - p_a1) * (1 - p_b1)
    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def bootstrap_ci(values: list[float], n_resamples: int, rng: random.Random) -> tuple[float, float, float]:
    if not values:
        return (float("nan"), float("nan"), float("nan"))
    mean = statistics.mean(values)
    if len(values) == 1:
        return (mean, mean, mean)
    boots = []
    n = len(values)
    for _ in range(n_resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        boots.append(statistics.mean(sample))
    boots.sort()
    lo = boots[int(0.025 * n_resamples)]
    hi = boots[min(int(0.975 * n_resamples), n_resamples - 1)]
    return (mean, lo, hi)


def main() -> None:
    from scipy.stats import binomtest

    rng = random.Random(RNG_SEED)

    log("loading query-level records, call records, caches, prompt log")
    records = load_query_level_records()
    llm_call_records = load_llm_call_records()
    cache_lookup = {p: load_cache_lookup(d) for p, d in PROVIDER_DIRS.items()}
    prompt_rows = load_prompt_log(V3 / "llm_prompt_call_log.jsonl")
    prompt_idx = index_prompt_log_full(prompt_rows)
    retry_ok = {p: compute_retry_ok_query_ids(llm_call_records, p) for p in PROVIDER_DIRS}

    # dataset lookup per query_id (for joining prompt-log rows, which lack dataset,
    # to a dataset via the query_level records' candidate sets)
    qid_dataset_by_candset: dict = {}
    for rec in records:
        qm = rec["query_metadata"]
        key = (qm["query_id"], frozenset(qm["candidate_doc_ids"]))
        qid_dataset_by_candset[key] = qm["dataset"]

    def dataset_for_pair_row(row: dict) -> str | None:
        # best-effort: any record whose query_id matches and whose candidate
        # set contains both doc ids resolves the dataset unambiguously in
        # this corpus (doc ids are dataset-specific strings).
        for (qid, cset), ds in qid_dataset_by_candset.items():
            if qid == row["query_id"] and row["doc_a_id"] in cset and row["doc_b_id"] in cset:
                return ds
        return None

    # ------------------------------------------------------------------
    # Section 5/6: parser audit + response-quality quantification over
    # every raw (ab/ba) response with preserved text.
    # ------------------------------------------------------------------
    log("classifying raw responses (parser audit + response quality)")
    parsed_audit_rows = []
    quality_counter = defaultdict(Counter)  # (provider, dataset) -> Counter(category)
    fr_pairs_by_group = defaultdict(list)  # (provider,dataset) -> list[(ab_bool, ba_bool)]
    ab_ba_rows_by_pairkey = defaultdict(dict)
    for row in prompt_rows:
        if row.get("direction") not in ("ab", "ba"):
            continue
        ds = dataset_for_pair_row(row)
        category, label = classify_response(row.get("raw_response"))
        parsed_audit_rows.append({
            "provider": row["provider"], "model": row.get("model"), "dataset": ds,
            "query_id": row["query_id"], "doc_a_id": row["doc_a_id"], "doc_b_id": row["doc_b_id"],
            "direction": row["direction"], "from_cache": row.get("from_cache"),
            "raw_response": row.get("raw_response"), "category": category,
            "current_parser_label": label, "stored_parse_error": row.get("parse_error"),
            "prompt_tokens": row.get("prompt_tokens"), "completion_tokens": row.get("completion_tokens"),
        })
        quality_counter[(row["provider"], ds)] += Counter([category])
        pk = (row["provider"], row["query_id"], frozenset({row["doc_a_id"], row["doc_b_id"]}))
        ab_ba_rows_by_pairkey[pk][row["direction"]] = (row, category, label)

    write_csv(AUDIT_DIR / "parsed_response_audit.csv", parsed_audit_rows)
    log(f"wrote parsed_response_audit.csv ({len(parsed_audit_rows)} rows)")

    # response_quality_summary.csv
    rq_rows = []
    for (provider, ds), c in sorted(quality_counter.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        total = sum(c.values())
        fallback = sum(c.get(k, 0) for k in FALLBACK_CATEGORIES)
        rq_rows.append({
            "provider": provider, "dataset": ds, "total_responses": total,
            "exact": c.get("exact", 0), "verbose_valid": c.get("verbose_valid", 0),
            "contains_only": c.get("contains_only", 0), "ambiguous": c.get("ambiguous", 0),
            "malformed": c.get("malformed", 0), "empty": c.get("empty", 0),
            "fallback_used_count": fallback,
            "fallback_rate": round(fallback / total, 4) if total else None,
        })
    write_csv(AUDIT_DIR / "response_quality_summary.csv", rq_rows)

    # ------------------------------------------------------------------
    # Section 8: position bias (exact-only vs fallback-included), by provider/dataset
    # ------------------------------------------------------------------
    log("computing position bias")
    pb_groups = defaultdict(lambda: {"A": 0, "B": 0})  # (provider,dataset,scope) -> counts
    for row in parsed_audit_rows:
        provider, ds, cat, lbl = row["provider"], row["dataset"], row["category"], row["current_parser_label"]
        pb_groups[(provider, ds, "all_current_parser")][lbl] += 1
        if cat == "exact":
            pb_groups[(provider, ds, "exact_only")][lbl] += 1
        if cat in FALLBACK_CATEGORIES:
            pb_groups[(provider, ds, "fallback_only")][lbl] += 1

    pb_rows = []
    for (provider, ds, scope), counts in sorted(pb_groups.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]), kv[0][2])):
        a, b = counts["A"], counts["B"]
        total = a + b
        if total == 0:
            continue
        test = binomtest(a, total, 0.5)
        pb_rows.append({
            "provider": provider, "dataset": ds, "scope": scope,
            "n": total, "a_count": a, "b_count": b,
            "a_rate": round(a / total, 4), "b_rate": round(b / total, 4),
            "binomial_p_two_sided": test.pvalue,
        })
    write_csv(AUDIT_DIR / "position_bias_summary.csv", pb_rows)

    # ------------------------------------------------------------------
    # Section 9: forward/reverse consistency (fresh pairs only, both dirs present)
    # ------------------------------------------------------------------
    log("computing forward/reverse consistency")
    fr_rows = []
    kappa_pairs_by_group = defaultdict(list)
    for pk, dirs in ab_ba_rows_by_pairkey.items():
        if "ab" not in dirs or "ba" not in dirs:
            continue  # missingness case, counted separately below
        (ab_row, ab_cat, ab_lbl), (ba_row, ba_cat, ba_lbl) = dirs["ab"], dirs["ba"]
        provider = ab_row["provider"]
        ds = dataset_for_pair_row(ab_row)
        # "reference item" = the document shown as doc_a in the ab call
        ref_id = ab_row["doc_a_id"]
        ref_wins_ab = ab_lbl == "A"
        ref_wins_ba = ba_lbl == "B"  # in the ba call, ref_id was shown as "B"
        agree = ref_wins_ab == ref_wins_ba
        fr_rows.append({
            "provider": provider, "dataset": ds, "query_id": ab_row["query_id"],
            "doc_a_id": ab_row["doc_a_id"], "doc_b_id": ab_row["doc_b_id"],
            "ab_category": ab_cat, "ba_category": ba_cat,
            "ab_label": ab_lbl, "ba_label": ba_lbl,
            "ref_wins_forward": ref_wins_ab, "ref_wins_reverse": ref_wins_ba,
            "agree": agree,
            "either_fallback": (ab_cat in FALLBACK_CATEGORIES) or (ba_cat in FALLBACK_CATEGORIES),
        })
        kappa_pairs_by_group[(provider, ds)].append((ref_wins_ab, ref_wins_ba))
        kappa_pairs_by_group[(provider, "__ALL__")].append((ref_wins_ab, ref_wins_ba))

    write_csv(AUDIT_DIR / "forward_reverse_consistency.csv", fr_rows)

    n_total_fresh_pairs = len({pk for pk, d in ab_ba_rows_by_pairkey.items()})
    n_both_dirs = sum(1 for d in ab_ba_rows_by_pairkey.values() if "ab" in d and "ba" in d)
    n_missing_one_dir = n_total_fresh_pairs - n_both_dirs

    log("Phase 1 (response classification, position bias, forward/reverse) complete")

    # Stash intermediate state for later phases via module globals (simple script, single process)
    globals().update(dict(
        records=records, llm_call_records=llm_call_records, cache_lookup=cache_lookup,
        prompt_rows=prompt_rows, prompt_idx=prompt_idx, retry_ok=retry_ok,
        parsed_audit_rows=parsed_audit_rows, rq_rows=rq_rows, pb_rows=pb_rows,
        fr_rows=fr_rows, kappa_pairs_by_group=kappa_pairs_by_group,
        n_total_fresh_pairs=n_total_fresh_pairs, n_both_dirs=n_both_dirs,
        n_missing_one_dir=n_missing_one_dir, quality_counter=quality_counter,
        dataset_for_pair_row=dataset_for_pair_row, rng=rng,
    ))


def run_all_policies(records, cache_lookup, prompt_idx, retry_ok, limit=None):
    all_rows = []
    recs = records[:limit] if limit else records
    for provider in PROVIDER_DIRS:
        for policy in POLICIES:
            log(f"  policy {policy} x provider {provider} over {len(recs)} records")
            rows = run_policy_for_all_records(
                recs, provider, policy, cache_lookup, prompt_idx, retry_ok[provider]
            )
            all_rows.extend(rows)
    return all_rows


def phase2_and_reports():
    log("phase 2: full P0-P4 x cohere/azure reparse over all 200 records")
    policy_rows = run_all_policies(records, cache_lookup, prompt_idx, retry_ok, limit=None)
    write_csv(AUDIT_DIR / "policy_sensitivity_full.csv", policy_rows)
    for policy in POLICIES:
        sub = [r for r in policy_rows if r["policy"] == policy]
        d = AUDIT_DIR / f"policy_{policy}_{POLICY_NAMES[policy]}" / "query_level_results.csv"
        write_csv(d, sub)
    log(f"wrote policy_sensitivity_full.csv ({len(policy_rows)} rows) and per-policy dirs")

    # common-query set: queries usable (>=2 prefs -> a graph was built) under
    # EVERY policy, for both providers -- the only queries where policies are
    # directly comparable apples-to-apples.
    usable_by_policy_provider = defaultdict(set)
    for r in policy_rows:
        if r["usable"]:
            usable_by_policy_provider[(r["policy"], r["provider"])].add(
                (r["dataset"], r["vote_regime"], r["query_id"])
            )
    common_keys = None
    for k, s in usable_by_policy_provider.items():
        common_keys = s if common_keys is None else (common_keys & s)
    common_keys = common_keys or set()
    common_rows = [
        r for r in policy_rows
        if (r["dataset"], r["vote_regime"], r["query_id"]) in common_keys
    ]
    write_csv(AUDIT_DIR / "policy_sensitivity_common_queries.csv", common_rows)
    log(f"common-query set size: {len(common_keys)} (of 200); wrote policy_sensitivity_common_queries.csv")

    # bootstrap CI per (provider, dataset, policy) over delta_ndcg, on the
    # FULL per-policy usable set (not just common queries, since usable-N
    # itself is part of what's being audited for sensitivity)
    log("bootstrapping delta_ndcg CIs (2000 resamples) per provider/dataset/policy")
    boot_rows = []
    groups = defaultdict(list)
    for r in policy_rows:
        if r["usable"] and r["delta_ndcg"] is not None:
            groups[(r["provider"], r["dataset"], r["policy"])].append(r["delta_ndcg"])
    for (provider, ds, policy), vals in sorted(groups.items()):
        mean, lo, hi = bootstrap_ci(vals, N_BOOTSTRAP, rng)
        cyclic_n = sum(
            1 for r in policy_rows
            if r["provider"] == provider and r["dataset"] == ds and r["policy"] == policy
            and r["usable"] and r["is_cyclic"]
        )
        usable_n = len(vals)
        help_n = sum(1 for r in policy_rows if r["provider"] == provider and r["dataset"] == ds
                     and r["policy"] == policy and r["usable"] and r["help"])
        harm_n = sum(1 for r in policy_rows if r["provider"] == provider and r["dataset"] == ds
                     and r["policy"] == policy and r["usable"] and r["harm"])
        inactive_n = sum(1 for r in policy_rows if r["provider"] == provider and r["dataset"] == ds
                          and r["policy"] == policy and r["usable"] and r["inactive"])
        boot_rows.append({
            "provider": provider, "dataset": ds, "policy": policy,
            "usable_queries": usable_n, "cyclic_pct": round(100 * cyclic_n / usable_n, 2) if usable_n else None,
            "mean_delta_ndcg": mean, "ci95_low": lo, "ci95_high": hi,
            "help": help_n, "harm": harm_n, "inactive": inactive_n,
        })
    write_csv(
        AUDIT_DIR / "policy_sensitivity_bootstrap_summary.csv", boot_rows,
        fieldnames=["provider", "dataset", "policy", "usable_queries", "cyclic_pct",
                    "mean_delta_ndcg", "ci95_low", "ci95_high", "help", "harm", "inactive"],
    )
    log(f"wrote bootstrap summary ({len(boot_rows)} rows)")

    globals().update(dict(policy_rows=policy_rows, boot_rows=boot_rows, common_keys=common_keys))


if __name__ == "__main__":
    main()
    log("phase 1 done")
    phase2_and_reports()
    log("phase 2 done -- all numeric outputs written")
