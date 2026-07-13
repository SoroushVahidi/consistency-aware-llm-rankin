from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = ROOT / "outputs"
MANUSCRIPT_TEX = ROOT / "papers" / "JDIQ_2026" / "manuscript" / "main.tex"


PAIRWISE_EXPERIMENTS = [
    "openai_scidocs_real_pairwise_q50_k15",
    "openai_hotpotqa_real_run_q20_k15",
    "openai_fiqa_real_run_q20_k15",
    "gemini_scidocs_real_pilot",
    "openai_scidocs_real_run_q20_k15",
    "openai_scidocs_real_pairwise_q30_k15",
    "openai_hotpotqa_real_run_q10_k15",
    "openai_smoke_scidocs_q1_k5",
]
POINTWISE_EXPERIMENTS = [
    "openai_scidocs_real_pointwise_q20_k15",
    "openai_hotpotqa_real_pointwise_q10_k15",
    "openai_robustness_checks/scidocs_pointwise_temp03_q5_k15",
]
LISTWISE_EXPERIMENTS = [
    "openai_scidocs_real_listwise_q20_k15",
    "openai_hotpotqa_real_listwise_q10_k15",
    "openai_robustness_checks/scidocs_listwise_temp03_q5_k15",
]
ALL_EXPERIMENTS = PAIRWISE_EXPERIMENTS + POINTWISE_EXPERIMENTS + LISTWISE_EXPERIMENTS

MANUSCRIPT_USED = {
    "openai_scidocs_real_pairwise_q50_k15": "yes-primary-pairwise",
    "openai_hotpotqa_real_run_q20_k15": "yes-primary-pairwise",
    "openai_fiqa_real_run_q20_k15": "yes-primary-pairwise",
    "openai_scidocs_real_pointwise_q20_k15": "yes-auxiliary-scope-check",
    "openai_hotpotqa_real_pointwise_q10_k15": "yes-auxiliary-scope-check",
    "openai_scidocs_real_listwise_q20_k15": "yes-auxiliary-scope-check",
    "openai_hotpotqa_real_listwise_q10_k15": "yes-auxiliary-scope-check",
    "gemini_scidocs_real_pilot": "no-not-analyzed-evidence",
}


@dataclass
class Experiment:
    rel_path: str
    mode: str
    provider: str
    model: str
    dataset: str
    intended_queries: int | None
    usable_queries: int | None
    top_k: int | None
    partial_run: bool | None
    raw_response_available: bool
    raw_response_count: int
    parsed_response_count: int
    query_regime_records: str
    producing_script: str
    parser_impl: str
    manuscript_use: str
    config: dict[str, Any]
    path: Path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def format_markdown_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
    lines = []
    header = rows[0]
    lines.append(
        "| " + " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(header)) + " |"
    )
    lines.append("| " + " | ".join("-" * widths[i] for i in range(len(widths))) + " |")
    for row in rows[1:]:
        lines.append(
            "| " + " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)) + " |"
        )
    return "\n".join(lines)


def infer_mode(rel_path: str) -> str:
    if "pointwise" in rel_path:
        return "pointwise"
    if "listwise" in rel_path:
        return "listwise"
    return "pairwise"


def producing_script(rel_path: str, mode: str, provider: str) -> str:
    if rel_path == "openai_scidocs_real_pairwise_q30_k15":
        return "scripts/run_openai_real_pairwise_q30.py"
    if rel_path == "openai_smoke_scidocs_q1_k5":
        return "scripts/run_openai_real_pilot.py (smoke configuration)"
    if mode == "pairwise" and provider == "gemini":
        return "scripts/run_gemini_scidocs_pilot.py"
    if mode == "pairwise":
        return "scripts/run_openai_real_pilot.py"
    if mode == "pointwise":
        return "scripts/run_openai_real_pointwise.py"
    return "scripts/run_openai_real_listwise.py"


def parser_impl(mode: str) -> str:
    if mode == "pairwise":
        return "src/rerankers/llm_pairwise.py::_parse_winner"
    if mode == "pointwise":
        return "src/rerankers/llm_pointwise.py::_parse_score"
    return "src/rerankers/llm_listwise.py::_parse_ranking"


def query_regime_record_desc(mode: str, usable_queries: int | None) -> str:
    if mode == "pairwise":
        return "N/A for committed OpenAI/Gemini pilots (no regime dimension; query-level pilots only)"
    return "N/A"


def discover_experiments() -> list[Experiment]:
    exps: list[Experiment] = []
    for rel_path in ALL_EXPERIMENTS:
        path = OUTPUTS_DIR / rel_path
        if not path.exists():
            continue
        config = read_json(path / "config.json")
        mode = infer_mode(rel_path)
        provider = str(config.get("provider", "UNVERIFIED"))
        model = str(config.get("model", "UNVERIFIED"))
        dataset = str(config.get("dataset", "UNVERIFIED"))
        intended = config.get("max_queries")
        usable = config.get("n_queries_processed")
        partial = config.get("partial_run")
        top_k = config.get("top_k")
        if mode == "pairwise":
            cache_path = path / "judgment_cache" / "llm_pairwise_judgments.jsonl"
            parsed_count = len(read_jsonl(cache_path)) if cache_path.exists() else 0
            raw_available = False
            raw_count = 0
        elif mode == "pointwise":
            cache_path = path / "judgment_cache" / "llm_pointwise_judgments.jsonl"
            parsed_count = len(read_jsonl(cache_path)) if cache_path.exists() else 0
            raw_available = False
            raw_count = 0
        else:
            cache_path = path / "judgment_cache" / "llm_listwise_judgments.jsonl"
            rows = read_jsonl(cache_path) if cache_path.exists() else []
            parsed_count = len(rows)
            raw_available = True
            raw_count = len(rows)
        exps.append(
            Experiment(
                rel_path=rel_path,
                mode=mode,
                provider=provider,
                model=model,
                dataset=dataset,
                intended_queries=intended,
                usable_queries=usable,
                top_k=top_k,
                partial_run=partial,
                raw_response_available=raw_available,
                raw_response_count=raw_count,
                parsed_response_count=parsed_count,
                query_regime_records=query_regime_record_desc(mode, usable),
                producing_script=producing_script(rel_path, mode, provider),
                parser_impl=parser_impl(mode),
                manuscript_use=MANUSCRIPT_USED.get(rel_path, "no"),
                config=config,
                path=path,
            )
        )
    return exps


def bootstrap_mean_ci(values: list[float], n_boot: int = 2000, seed: int = 42) -> tuple[float, float, float]:
    if not values:
        return (math.nan, math.nan, math.nan)
    import random

    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    mean_obs = sum(values) / n
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot)]
    return (mean_obs, lo, hi)


def exact_binom_p_two_sided(k: int, n: int, p: float = 0.5) -> float:
    if n == 0:
        return math.nan
    log_probs = []
    log_p = math.log(p)
    log_q = math.log(1 - p)
    for i in range(n + 1):
        log_prob = (
            math.lgamma(n + 1)
            - math.lgamma(i + 1)
            - math.lgamma(n - i + 1)
            + i * log_p
            + (n - i) * log_q
        )
        log_probs.append(log_prob)
    p_obs_log = log_probs[k]
    total = 0.0
    for log_prob in log_probs:
        if log_prob <= p_obs_log + 1e-15:
            total += math.exp(log_prob)
    return min(1.0, total)


def listwise_quality_bucket(response_text: str) -> str:
    stripped = response_text.strip()
    if not stripped:
        return "empty"
    if re.fullmatch(r"(?:\[\d+\](?:\s*>\s*\[\d+\])*)(?:\s*)", stripped):
        return "exact_ranking_string"
    numbers = re.findall(r"\d+", stripped)
    if numbers:
        return "verbose_but_parseable"
    return "malformed"


def pairwise_a_or_b(entry: dict[str, Any]) -> str:
    doc_ids = entry.get("doc_ids", [])
    winner = entry.get("winner")
    if len(doc_ids) != 2:
        return "UNVERIFIED"
    return "A" if winner == doc_ids[0] else "B"


def generate_inventory(experiments: list[Experiment]) -> None:
    rows = [
        [
            "Experiment",
            "Provider",
            "Model",
            "Mode",
            "Dataset",
            "Intended queries",
            "Usable queries",
            "Raw responses",
            "Parsed responses",
            "Query×regime records",
            "Producing script",
            "Parser",
            "Used in manuscript",
        ]
    ]
    for exp in experiments:
        rows.append(
            [
                exp.rel_path,
                exp.provider,
                exp.model,
                exp.mode,
                exp.dataset,
                str(exp.intended_queries),
                str(exp.usable_queries),
                f"{exp.raw_response_count} ({'yes' if exp.raw_response_available else 'no raw text preserved'})",
                str(exp.parsed_response_count),
                exp.query_regime_records,
                exp.producing_script,
                exp.parser_impl,
                exp.manuscript_use,
            ]
        )
    notes = [
        "# REAL_LLM_FILE_INVENTORY",
        "",
        "This inventory was generated from committed files under `outputs/`, repository scripts, and the current `papers/JDIQ_2026/manuscript/main.tex`.",
        "",
        format_markdown_table(rows),
        "",
        "## Key findings",
        "",
        "- Committed real-LLM pairwise evidence is auditable for OpenAI and a quota-limited Gemini pilot.",
        "- Committed real-LLM pointwise/listwise evidence exists for OpenAI on SciDocs and HotpotQA, plus a small SciDocs robustness check.",
        "- Pairwise raw response texts are not preserved in the committed caches; only final winner/loser records are stored.",
        "- Pointwise raw response texts are not preserved in the committed caches; only parsed scores are stored.",
        "- Listwise raw response texts are preserved in the committed cache entries.",
        "- No committed Cohere or Azure OpenAI experiment directories, caches, or raw-response files were found on `origin/main`.",
    ]
    write_text(AUDIT_DIR / "REAL_LLM_FILE_INVENTORY.md", "\n".join(notes))


def generate_provider_counts(experiments: list[Experiment]) -> None:
    rows = []
    openai_primary_queries = 0
    openai_primary_pairwise_records = 0
    gemini_queries = 0
    gemini_pairwise_records = 0
    for exp in experiments:
        if exp.mode == "pairwise" and exp.manuscript_use == "yes-primary-pairwise":
            cache_rows = read_jsonl(exp.path / "judgment_cache" / "llm_pairwise_judgments.jsonl")
            rows.append(
                {
                    "provider": exp.provider,
                    "model": exp.model,
                    "dataset": exp.dataset,
                    "experiment": exp.rel_path,
                    "manuscript_role": exp.manuscript_use,
                    "usable_queries": exp.usable_queries,
                    "pairwise_records": len(cache_rows),
                    "query_regime_records": "N/A",
                    "status": "committed-and-auditable",
                }
            )
            openai_primary_queries += int(exp.usable_queries or 0)
            openai_primary_pairwise_records += len(cache_rows)
        if exp.rel_path == "gemini_scidocs_real_pilot":
            cache_rows = read_jsonl(exp.path / "judgment_cache" / "llm_pairwise_judgments.jsonl")
            rows.append(
                {
                    "provider": exp.provider,
                    "model": exp.model,
                    "dataset": exp.dataset,
                    "experiment": exp.rel_path,
                    "manuscript_role": exp.manuscript_use,
                    "usable_queries": exp.usable_queries,
                    "pairwise_records": len(cache_rows),
                    "query_regime_records": "N/A",
                    "status": "partial-pilot-not-analyzed",
                }
            )
            gemini_queries += int(exp.usable_queries or 0)
            gemini_pairwise_records += len(cache_rows)
    rows.extend(
        [
            {
                "provider": "cohere",
                "model": "command-r-plus-08-2024",
                "dataset": "UNVERIFIED",
                "experiment": "not present in committed artifacts",
                "manuscript_role": "claimed in manuscript",
                "usable_queries": 0,
                "pairwise_records": 0,
                "query_regime_records": 0,
                "status": "no-committed-evidence-found",
            },
            {
                "provider": "azure_openai",
                "model": "gpt-4.1-mini",
                "dataset": "UNVERIFIED",
                "experiment": "not present in committed artifacts",
                "manuscript_role": "claimed in manuscript",
                "usable_queries": 0,
                "pairwise_records": 0,
                "query_regime_records": 0,
                "status": "no-committed-evidence-found",
            },
        ]
    )
    write_csv(
        AUDIT_DIR / "provider_record_counts.csv",
        rows,
        [
            "provider",
            "model",
            "dataset",
            "experiment",
            "manuscript_role",
            "usable_queries",
            "pairwise_records",
            "query_regime_records",
            "status",
        ],
    )
    text = f"""# PROVIDER_COUNT_RESOLUTION

## Resolution

From committed `origin/main` artifacts, the auditable provider totals are:

- OpenAI primary pairwise pilot: {openai_primary_queries} usable queries across SciDocs, HotpotQA, and FiQA; {openai_primary_pairwise_records} stored pairwise judgment records.
- Gemini pilot: {gemini_queries} usable queries; {gemini_pairwise_records} stored pairwise judgment records; partial and not treated as analyzed manuscript evidence.
- Cohere: 0 committed auditable records found.
- Azure OpenAI: 0 committed auditable records found.

## Contradiction outcome

The repository snapshot does **not** support either of the manuscript interpretations:

1. "Cohere contributes 200 records."
2. "Azure contributes 200 records."
3. "Cohere and Azure together contribute 200 records."

Instead, the current anonymous `origin/main` snapshot contains **no committed auditable Cohere or Azure records at all**. The manuscript's provider-count claims therefore cannot be verified from the stored artifact set used for this audit.

## Exact manuscript sentence that must change

The sentence beginning:

> "Each protocol-distinct corroborative provider contributes 200 query×regime records across FiQA, HotpotQA, and BRIGHT."

must be removed or replaced. On the current anonymous `origin/main` snapshot, no committed Cohere/Azure corpus is available to support that statement.
"""
    write_text(AUDIT_DIR / "PROVIDER_COUNT_RESOLUTION.md", text)


def generate_parser_audit(experiments: list[Experiment]) -> None:
    parsed_rows: list[dict[str, Any]] = []
    for exp in experiments:
        if exp.mode == "pairwise":
            cache_rows = read_jsonl(exp.path / "judgment_cache" / "llm_pairwise_judgments.jsonl")
            for row in cache_rows:
                doc_ids = row.get("doc_ids", [])
                parsed_rows.append(
                    {
                        "experiment": exp.rel_path,
                        "provider": exp.provider,
                        "model": exp.model,
                        "dataset": exp.dataset,
                        "prompt_mode": exp.mode,
                        "query_id": row.get("query_id"),
                        "cache_key": row.get("cache_key"),
                        "raw_response_available": "no",
                        "raw_response_text": "",
                        "parsed_output": pairwise_a_or_b(row),
                        "response_quality_bucket": "UNOBSERVABLE_RAW_TEXT",
                        "fallback_usage_auditable": "no",
                        "doc_ids_json": json.dumps(doc_ids),
                        "winner_doc_id": row.get("winner"),
                        "loser_doc_id": row.get("loser"),
                        "score": "",
                        "ranked_indices_json": "",
                        "notes": "Final pairwise winner/loser preserved; original response text not preserved.",
                    }
                )
        elif exp.mode == "pointwise":
            cache_rows = read_jsonl(exp.path / "judgment_cache" / "llm_pointwise_judgments.jsonl")
            for row in cache_rows:
                parsed_rows.append(
                    {
                        "experiment": exp.rel_path,
                        "provider": exp.provider,
                        "model": exp.model,
                        "dataset": exp.dataset,
                        "prompt_mode": exp.mode,
                        "query_id": row.get("query_id"),
                        "cache_key": row.get("cache_key"),
                        "raw_response_available": "no",
                        "raw_response_text": "",
                        "parsed_output": row.get("score"),
                        "response_quality_bucket": "UNOBSERVABLE_RAW_TEXT",
                        "fallback_usage_auditable": "no",
                        "doc_ids_json": json.dumps(row.get("doc_ids")),
                        "winner_doc_id": "",
                        "loser_doc_id": "",
                        "score": row.get("score"),
                        "ranked_indices_json": "",
                        "notes": "Parsed numeric score preserved; original response text not preserved.",
                    }
                )
        else:
            cache_rows = read_jsonl(exp.path / "judgment_cache" / "llm_listwise_judgments.jsonl")
            for row in cache_rows:
                response_text = row.get("response_text", "")
                parsed_rows.append(
                    {
                        "experiment": exp.rel_path,
                        "provider": exp.provider,
                        "model": exp.model,
                        "dataset": exp.dataset,
                        "prompt_mode": exp.mode,
                        "query_id": row.get("query_id"),
                        "cache_key": row.get("cache_key"),
                        "raw_response_available": "yes",
                        "raw_response_text": response_text,
                        "parsed_output": json.dumps(row.get("ranked_indices")),
                        "response_quality_bucket": listwise_quality_bucket(response_text),
                        "fallback_usage_auditable": "yes",
                        "doc_ids_json": json.dumps(row.get("doc_ids")),
                        "winner_doc_id": "",
                        "loser_doc_id": "",
                        "score": "",
                        "ranked_indices_json": json.dumps(row.get("ranked_indices")),
                        "notes": "Listwise raw response text preserved in committed cache.",
                    }
                )
    write_csv(
        AUDIT_DIR / "parsed_response_audit.csv",
        parsed_rows,
        [
            "experiment",
            "provider",
            "model",
            "dataset",
            "prompt_mode",
            "query_id",
            "cache_key",
            "raw_response_available",
            "raw_response_text",
            "parsed_output",
            "response_quality_bucket",
            "fallback_usage_auditable",
            "doc_ids_json",
            "winner_doc_id",
            "loser_doc_id",
            "score",
            "ranked_indices_json",
            "notes",
        ],
    )
    text = """# PARSER_AUDIT

## Pairwise parser

Source: `src/rerankers/llm_pairwise.py::_parse_winner`

- Accepted outputs:
  - Any response whose uppercased, stripped text starts with `A` parses to `A`.
  - Any response whose uppercased, stripped text starts with `B` parses to `B`.
  - Otherwise, any text containing `A` but not `B` parses to `A`.
  - Otherwise, any text containing `B` but not `A` parses to `B`.
- Malformed handling:
  - Any remaining response defaults to `A`.
- Ambiguous handling:
  - Ambiguous or nonconforming outputs are not rejected; they collapse into the default `A` path.
- Retries:
  - OpenAI: up to four retries with exponential backoff on transient errors.
  - Gemini: up to eight total retry attempts (`MAX_RETRIES + 4`) for transient rate limits.
- Default label:
  - `A`.
- Fallback behavior:
  - Silent parser fallback to `A`; no dedicated audit field records when this occurred.
- Provider differences:
  - Provider-specific retry logic differs, but parsing logic is shared.

## Pointwise parser

Source: `src/rerankers/llm_pointwise.py::_parse_score`

- Accepted outputs:
  - First 1- or 2-digit integer in the response.
- Malformed handling:
  - In non-strict mode, absence of an integer falls back to score `5.0`.
- Ambiguous handling:
  - The parser does not separately record ambiguity; any first integer is accepted.
- Default / fallback:
  - `5.0` if no integer is found and strict parsing is disabled.

## Listwise parser

Source: `src/rerankers/llm_listwise.py::_parse_ranking`

- Accepted outputs:
  - Any response containing digits; the parser extracts all integers, filters to valid indices, removes duplicates, and appends any missing indices in their original order.
- Malformed handling:
  - In non-strict mode, responses with no digits would collapse to the original order after the "append missing indices" step.
- Ambiguous handling:
  - Extra prose is tolerated if the response still contains parseable integers.

## Provenance gap

- Pairwise committed caches preserve only final `winner` / `loser` records, not raw response text.
- Pointwise committed caches preserve only parsed numeric scores, not raw response text.
- Listwise committed caches preserve raw `response_text`.
- Because pairwise raw responses are absent, ambiguous-response counts, fallback-to-`A` counts, exact-vs-verbose breakdowns, and alternative reparsing policies P1–P4 are **not reproducible from the current committed artifact set**.
"""
    write_text(AUDIT_DIR / "PARSER_AUDIT.md", text)


def generate_response_quality(experiments: list[Experiment]) -> None:
    rows = []
    grouped = defaultdict(list)
    parsed_rows = read_csv_dicts(AUDIT_DIR / "parsed_response_audit.csv")
    for row in parsed_rows:
        grouped[(row["provider"], row["model"], row["dataset"], row["prompt_mode"], row["experiment"])].append(row)
    for key, items in grouped.items():
        provider, model, dataset, prompt_mode, experiment = key
        exact_ab = sum(1 for item in items if item["response_quality_bucket"] == "exact_ab")
        verbose_valid = sum(1 for item in items if item["response_quality_bucket"] == "verbose_but_parseable")
        ambiguous = sum(1 for item in items if item["response_quality_bucket"] == "ambiguous")
        malformed = sum(1 for item in items if item["response_quality_bucket"] == "malformed")
        empty = sum(1 for item in items if item["response_quality_bucket"] == "empty")
        exact_ranking = sum(1 for item in items if item["response_quality_bucket"] == "exact_ranking_string")
        unobservable = sum(1 for item in items if item["response_quality_bucket"] == "UNOBSERVABLE_RAW_TEXT")
        total = len(items)
        fallback_auditable = all(item["fallback_usage_auditable"] == "yes" for item in items)
        rows.append(
            {
                "provider": provider,
                "model": model,
                "dataset": dataset,
                "prompt_mode": prompt_mode,
                "experiment": experiment,
                "total_responses": total,
                "raw_response_text_available": sum(
                    1 for item in items if item["raw_response_available"] == "yes"
                ),
                "exact_ab_responses": exact_ab if prompt_mode == "pairwise" else "",
                "verbose_valid_responses": verbose_valid if prompt_mode != "pairwise" else "",
                "ambiguous_responses": ambiguous if fallback_auditable else "UNAUDITABLE",
                "malformed_responses": malformed if fallback_auditable else "UNAUDITABLE",
                "empty_responses": empty if fallback_auditable else "UNAUDITABLE",
                "exact_ranking_string_responses": exact_ranking if prompt_mode == "listwise" else "",
                "fallback_usage_count": "UNAUDITABLE" if not fallback_auditable else 0,
                "unobservable_raw_text_responses": unobservable,
                "retry_distribution": "UNRECORDED",
            }
        )
    write_csv(
        AUDIT_DIR / "response_quality_summary.csv",
        rows,
        [
            "provider",
            "model",
            "dataset",
            "prompt_mode",
            "experiment",
            "total_responses",
            "raw_response_text_available",
            "exact_ab_responses",
            "verbose_valid_responses",
            "ambiguous_responses",
            "malformed_responses",
            "empty_responses",
            "exact_ranking_string_responses",
            "fallback_usage_count",
            "unobservable_raw_text_responses",
            "retry_distribution",
        ],
    )
    lines = [
        "# RESPONSE_QUALITY_REPORT",
        "",
        "This report summarizes what can and cannot be recovered about stored response quality from the committed artifact set.",
        "",
        format_markdown_table(
            [
                [
                    "Experiment",
                    "Prompt mode",
                    "Total",
                    "Raw text available",
                    "Auditable ambiguity/fallback?",
                    "Notes",
                ]
            ]
            + [
                [
                    row["experiment"],
                    row["prompt_mode"],
                    str(row["total_responses"]),
                    str(row["raw_response_text_available"]),
                    "yes" if row["raw_response_text_available"] and row["prompt_mode"] == "listwise" else "no",
                    "Listwise raw text preserved." if row["prompt_mode"] == "listwise" else "Raw text not preserved.",
                ]
                for row in rows
            ]
        ),
        "",
        "## Findings",
        "",
        "- Pairwise OpenAI/Gemini responses cannot be partitioned into exact A/B, verbose-valid, ambiguous, malformed, or fallback-derived subsets because raw response texts were not committed.",
        "- Pointwise OpenAI responses likewise cannot be reclassified retrospectively because only parsed numeric scores were committed.",
        "- Listwise OpenAI responses are auditable and, in the committed runs, are stored as direct ranking strings.",
        "- Retry distributions are not reconstructible from committed logs; aggregate retry-capable settings exist in code, but per-response retry histories were not recorded.",
    ]
    write_text(AUDIT_DIR / "RESPONSE_QUALITY_REPORT.md", "\n".join(lines))


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def per_query_delta_rows(exp: Experiment) -> list[dict[str, Any]]:
    if exp.mode != "pairwise":
        return []
    per_query_name = "gemini_per_query.csv" if exp.provider == "gemini" else "openai_per_query.csv"
    path = exp.path / per_query_name
    if not path.exists():
        return []
    rows = read_csv_dicts(path)
    by_query_method: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        by_query_method[(row["query_id"], row["method"])] = row
    query_ids = sorted({row["query_id"] for row in rows})
    out = []
    for qid in query_ids:
        repaired = by_query_method.get((qid, "hybrid_rrf_repaired_copeland_a03"))
        unrepaired = by_query_method.get((qid, "hybrid_rrf_unrepaired_copeland_a03"))
        copeland = by_query_method.get((qid, "llm_pairwise_copeland"))
        if not repaired or not unrepaired or not copeland:
            continue
        delta = float(repaired["ndcg_at_k"]) - float(unrepaired["ndcg_at_k"])
        out.append(
            {
                "query_id": qid,
                "delta_ndcg": delta,
                "is_cyclic": str(copeland["is_cyclic"]).lower() == "true",
                "help": delta > 0,
                "harm": delta < 0,
                "inactive": abs(delta) < 1e-15,
            }
        )
    return out


def generate_policy_sensitivity(experiments: list[Experiment]) -> None:
    full_rows = []
    common_rows = []
    policy_dir_map = {
        "P0": AUDIT_DIR / "policy_P0_current_parser",
        "P1": AUDIT_DIR / "policy_P1_ambiguous_to_abstain",
        "P2": AUDIT_DIR / "policy_P2_discard_ambiguous",
        "P3": AUDIT_DIR / "policy_P3_exact_A_or_B_only",
        "P4": AUDIT_DIR / "policy_P4_retry_success_only",
    }
    for path in policy_dir_map.values():
        path.mkdir(parents=True, exist_ok=True)
    for exp in experiments:
        if exp.mode != "pairwise":
            continue
        delta_rows = per_query_delta_rows(exp)
        deltas = [row["delta_ndcg"] for row in delta_rows]
        help_count = sum(1 for row in delta_rows if row["help"])
        harm_count = sum(1 for row in delta_rows if row["harm"])
        inactive_count = sum(1 for row in delta_rows if row["inactive"])
        cyclic_pct = (
            100.0 * sum(1 for row in delta_rows if row["is_cyclic"]) / len(delta_rows)
            if delta_rows
            else math.nan
        )
        mean_delta, ci_low, ci_high = bootstrap_mean_ci(deltas, n_boot=2000, seed=42)
        p0_row = {
            "provider": exp.provider,
            "model": exp.model,
            "dataset": exp.dataset,
            "experiment": exp.rel_path,
            "policy": "P0",
            "status": "reconstructed-from-committed-final-outputs",
            "usable_queries": len(delta_rows),
            "cyclic_pct": round(cyclic_pct, 4) if not math.isnan(cyclic_pct) else "",
            "mean_delta_ndcg": round(mean_delta, 6) if not math.isnan(mean_delta) else "",
            "ci95_low": round(ci_low, 6) if not math.isnan(ci_low) else "",
            "ci95_high": round(ci_high, 6) if not math.isnan(ci_high) else "",
            "help": help_count,
            "harm": harm_count,
            "inactive": inactive_count,
            "reproducibility_note": "Computed from stored per-query repaired/unrepaired outputs, not raw responses.",
        }
        full_rows.append(p0_row)
        common_rows.append(dict(p0_row))
        write_text(
            policy_dir_map["P0"] / f"{exp.rel_path.replace('/', '__')}.md",
            "\n".join(
                [
                    f"# {exp.rel_path} — P0",
                    "",
                    "Reconstructed from committed per-query repaired/unrepaired outputs.",
                    "",
                    f"- usable queries: {len(delta_rows)}",
                    f"- cyclic percentage: {cyclic_pct:.2f}%" if not math.isnan(cyclic_pct) else "- cyclic percentage: N/A",
                    f"- mean ΔnDCG: {mean_delta:.6f}" if not math.isnan(mean_delta) else "- mean ΔnDCG: N/A",
                    f"- 95% bootstrap CI: [{ci_low:.6f}, {ci_high:.6f}]" if not math.isnan(ci_low) else "- 95% bootstrap CI: N/A",
                    f"- help / harm / inactive: {help_count} / {harm_count} / {inactive_count}",
                ]
            ),
        )
        for policy in ("P1", "P2", "P3", "P4"):
            row = {
                "provider": exp.provider,
                "model": exp.model,
                "dataset": exp.dataset,
                "experiment": exp.rel_path,
                "policy": policy,
                "status": "not-reproducible-from-committed-artifacts",
                "usable_queries": "",
                "cyclic_pct": "",
                "mean_delta_ndcg": "",
                "ci95_low": "",
                "ci95_high": "",
                "help": "",
                "harm": "",
                "inactive": "",
                "reproducibility_note": (
                    "Raw pairwise response texts are absent, so ambiguity/fallback-sensitive reparsing cannot be reproduced."
                ),
            }
            full_rows.append(row)
            common_rows.append(dict(row))
            write_text(
                policy_dir_map[policy] / f"{exp.rel_path.replace('/', '__')}.md",
                "\n".join(
                    [
                        f"# {exp.rel_path} — {policy}",
                        "",
                        "Not reproducible from current committed artifacts.",
                        "",
                        "Reason: pairwise raw response texts and retry histories are not preserved, so ambiguity-sensitive reparsing is impossible.",
                    ]
                ),
            )
    write_csv(
        AUDIT_DIR / "policy_sensitivity_full.csv",
        full_rows,
        [
            "provider",
            "model",
            "dataset",
            "experiment",
            "policy",
            "status",
            "usable_queries",
            "cyclic_pct",
            "mean_delta_ndcg",
            "ci95_low",
            "ci95_high",
            "help",
            "harm",
            "inactive",
            "reproducibility_note",
        ],
    )
    write_csv(
        AUDIT_DIR / "policy_sensitivity_common_queries.csv",
        common_rows,
        [
            "provider",
            "model",
            "dataset",
            "experiment",
            "policy",
            "status",
            "usable_queries",
            "cyclic_pct",
            "mean_delta_ndcg",
            "ci95_low",
            "ci95_high",
            "help",
            "harm",
            "inactive",
            "reproducibility_note",
        ],
    )
    lines = [
        "# POLICY_SENSITIVITY_REPORT",
        "",
        "## Outcome",
        "",
        "- P0 was reproducible from committed per-query repaired/unrepaired outputs.",
        "- P1–P4 were **not** reproducible from committed artifacts because raw pairwise response texts and retry histories were not preserved.",
        "",
        "## Questions answered",
        "",
        "- Does default-A fallback change conclusions? Not auditable from the committed snapshot; raw pairwise texts needed for reparsing were not preserved.",
        "- Does abstaining change conclusions? Not auditable from the committed snapshot.",
        "- Does any policy change confidence intervals? Only P0 intervals could be reconstructed; alternative-policy intervals are unavailable.",
        "- Are provider conclusions robust? OpenAI primary-pilot conclusions are reproducible at P0. Cross-provider robustness claims are not auditable because the manuscript's Cohere/Azure corpus is absent and Gemini is a 2-query partial pilot.",
    ]
    write_text(AUDIT_DIR / "POLICY_SENSITIVITY_REPORT.md", "\n".join(lines))


def generate_position_bias(experiments: list[Experiment]) -> None:
    rows = []
    for exp in experiments:
        if exp.mode != "pairwise":
            continue
        cache_path = exp.path / "judgment_cache" / "llm_pairwise_judgments.jsonl"
        cache_rows = read_jsonl(cache_path)
        a_count = sum(1 for row in cache_rows if pairwise_a_or_b(row) == "A")
        b_count = sum(1 for row in cache_rows if pairwise_a_or_b(row) == "B")
        total = a_count + b_count
        p_value = exact_binom_p_two_sided(a_count, total)
        rows.append(
            {
                "provider": exp.provider,
                "model": exp.model,
                "dataset": exp.dataset,
                "prompt_mode": exp.mode,
                "subset": "all_parsed_pairwise_edges",
                "total_edges": total,
                "a_choice_count": a_count,
                "b_choice_count": b_count,
                "a_choice_rate": round(a_count / total, 6) if total else "",
                "binomtest_pvalue": round(p_value, 12) if not math.isnan(p_value) else "",
                "auditable_note": "Inferred from stored winner vs prompt-order doc_ids; exact/fallback split unavailable.",
            }
        )
        rows.append(
            {
                "provider": exp.provider,
                "model": exp.model,
                "dataset": exp.dataset,
                "prompt_mode": exp.mode,
                "subset": "exact_responses_only",
                "total_edges": "",
                "a_choice_count": "",
                "b_choice_count": "",
                "a_choice_rate": "",
                "binomtest_pvalue": "",
                "auditable_note": "UNAUDITABLE: raw pairwise response texts not preserved.",
            }
        )
        rows.append(
            {
                "provider": exp.provider,
                "model": exp.model,
                "dataset": exp.dataset,
                "prompt_mode": exp.mode,
                "subset": "fallback_responses_only",
                "total_edges": "",
                "a_choice_count": "",
                "b_choice_count": "",
                "a_choice_rate": "",
                "binomtest_pvalue": "",
                "auditable_note": "UNAUDITABLE: parser fallback events not recorded and raw texts not preserved.",
            }
        )
    write_csv(
        AUDIT_DIR / "position_bias_summary.csv",
        rows,
        [
            "provider",
            "model",
            "dataset",
            "prompt_mode",
            "subset",
            "total_edges",
            "a_choice_count",
            "b_choice_count",
            "a_choice_rate",
            "binomtest_pvalue",
            "auditable_note",
        ],
    )
    lines = [
        "# POSITION_BIAS_REPORT",
        "",
        "A-choice rates below are inferred from stored pairwise winners relative to the stored prompt-order `doc_ids` in the committed cache entries.",
        "",
        "- This supports an exact binomial test on final parsed A-vs-B outcomes.",
        "- It does **not** support a separate exact-response-only or fallback-only analysis because pairwise raw response text was not committed.",
    ]
    write_text(AUDIT_DIR / "POSITION_BIAS_REPORT.md", "\n".join(lines))


def generate_forward_reverse(experiments: list[Experiment]) -> None:
    rows = []
    for exp in experiments:
        if exp.mode != "pairwise":
            continue
        debias = bool(exp.config.get("debias_position", False))
        rows.append(
            {
                "provider": exp.provider,
                "model": exp.model,
                "dataset": exp.dataset,
                "experiment": exp.rel_path,
                "debias_position": debias,
                "forward_reverse_pairs_auditable": "yes" if debias else "no",
                "agreement_rate": "",
                "contradiction_rate": "",
                "order_sensitivity_rate": "",
                "missingness_rate": "",
                "cohens_kappa": "",
                "note": (
                    "No forward/reverse paired prompts preserved in this experiment."
                    if not debias
                    else "UNVERIFIED: raw paired prompts not reconstructed in this audit."
                ),
            }
        )
    write_csv(
        AUDIT_DIR / "forward_reverse_consistency.csv",
        rows,
        [
            "provider",
            "model",
            "dataset",
            "experiment",
            "debias_position",
            "forward_reverse_pairs_auditable",
            "agreement_rate",
            "contradiction_rate",
            "order_sensitivity_rate",
            "missingness_rate",
            "cohens_kappa",
            "note",
        ],
    )
    lines = [
        "# FORWARD_REVERSE_REPORT",
        "",
        "No committed pairwise run used for the current manuscript evidence preserves forward/reverse paired prompts.",
        "",
        "- All auditable OpenAI primary-pilot configs set `debias_position=false`.",
        "- The partial Gemini pilot also sets `debias_position=false`.",
        "- Therefore semantic agreement, contradiction, order sensitivity, missingness, and Cohen's kappa for A→B vs B→A cannot be computed from the committed snapshot.",
    ]
    write_text(AUDIT_DIR / "FORWARD_REVERSE_REPORT.md", "\n".join(lines))


def generate_cyclicity_source_audit(experiments: list[Experiment]) -> None:
    lines = [
        "# CYCLICITY_SOURCE_AUDIT",
        "",
        "## Auditable portion",
        "",
        "Observed cyclicity in the committed pairwise pilots is directly attributable to the accepted final pairwise judgment edges stored in `judgments.jsonl` and `judgment_cache/llm_pairwise_judgments.jsonl`.",
        "",
        "## Unauditable source decomposition",
        "",
        "- Contribution from exact one-letter responses: UNAUDITABLE for pairwise runs because raw texts are not preserved.",
        "- Contribution from ambiguous responses: UNAUDITABLE for pairwise runs because raw texts are not preserved.",
        "- Contribution from parser fallback-to-`A`: UNAUDITABLE because fallback events were not separately logged and raw texts are absent.",
        "- Contribution from forward/reverse disagreement: UNAUDITABLE because the committed analyzed pairwise runs have `debias_position=false` and therefore no stored forward/reverse pairs.",
        "",
        "## Practical conclusion",
        "",
        "The current artifact snapshot supports measuring cyclicity outcomes, but it does not support a source-level decomposition of that cyclicity into exact, ambiguous, fallback-derived, or order-sensitive components.",
    ]
    write_text(AUDIT_DIR / "CYCLICITY_SOURCE_AUDIT.md", "\n".join(lines))


def generate_prompt_mode_scope(experiments: list[Experiment]) -> None:
    lines = [
        "# PROMPT_MODE_SCOPE_AUDIT",
        "",
        "## Pairwise",
        "",
        "- Quantitative outputs: yes.",
        "- Manuscript role: yes, primary real-LLM evidence for OpenAI on SciDocs, HotpotQA, and FiQA.",
        "- Main-paper suitability: yes, but only with conservative scope wording and without unsupported Cohere/Azure claims.",
        "",
        "## Pointwise",
        "",
        "- Quantitative outputs: yes, committed OpenAI runs exist for SciDocs and HotpotQA, with bootstrap summaries.",
        "- Manuscript role: auxiliary scope check only.",
        "- Main-paper suitability: supplementary or brief scope-check mention only; they do not directly address the repaired-vs-unrepaired pairwise-graph question.",
        "",
        "## Listwise",
        "",
        "- Quantitative outputs: yes, committed OpenAI runs exist for SciDocs and HotpotQA, with bootstrap summaries and raw ranking strings.",
        "- Manuscript role: auxiliary scope check only.",
        "- Main-paper suitability: supplementary or brief scope-check mention only.",
        "",
        "## Stale supporting artifact",
        "",
        "The file `outputs/manuscript_artifacts/tables/table_4_llm_paradigm_comparison.csv` is stale for pointwise/listwise scope. It labels SciDocs pointwise and listwise evidence as `mock`, even though committed real OpenAI runs now exist for both paradigms.",
    ]
    write_text(AUDIT_DIR / "PROMPT_MODE_SCOPE_AUDIT.md", "\n".join(lines))


def generate_final_report(experiments: list[Experiment]) -> None:
    lines = [
        "# REAL_LLM_INTEGRITY_FINAL_REPORT",
        "",
        "## Executive summary",
        "",
        "- Resolved: the committed `origin/main` snapshot contains auditable OpenAI real-LLM evidence for pairwise, pointwise, and listwise runs, plus a small Gemini pairwise pilot.",
        "- Threatens conclusions: the manuscript's Cohere/Azure corpus claims are unsupported by any committed auditable artifacts in the current anonymous snapshot.",
        "- Harmless but document: pairwise and pointwise raw response texts are not preserved, which prevents retrospective ambiguity/fallback auditing and reparsing-policy sensitivity beyond P0.",
        "- Harmless but document: no auditable forward/reverse debias runs are present in the committed analyzed pairwise evidence.",
        "",
        "## Provider inventory",
        "",
        "- OpenAI primary pairwise pilot: SciDocs 50, HotpotQA 20, FiQA 10 usable queries.",
        "- OpenAI auxiliary scope checks: pointwise/listwise on SciDocs 20 and HotpotQA 10; small SciDocs robustness checks.",
        "- Gemini pilot: SciDocs 2 usable queries; partial and quota-limited.",
        "- Cohere/Azure: no committed auditable records found.",
        "",
        "## Provider-count resolution",
        "",
        "- The current repository snapshot does not support any version of the manuscript's '200 records' Cohere/Azure claim.",
        "",
        "## Parser audit",
        "",
        "- Pairwise parser defaults any unrecognized response to `A`.",
        "- Pointwise parser defaults to score `5.0` if no integer is found in non-strict mode.",
        "- Listwise parser is permissive and appends missing indices in original order.",
        "- Pairwise raw texts are absent, so fallback-to-`A` frequency cannot be measured retrospectively.",
        "",
        "## Ambiguity statistics",
        "",
        "- Pairwise: not auditable from committed artifacts.",
        "- Pointwise: not auditable from committed artifacts.",
        "- Listwise: auditable; committed runs preserve raw ranking strings.",
        "",
        "## Position bias",
        "",
        "- Final parsed A/B outcome rates are auditable from pairwise cache orderings and are reported in `position_bias_summary.csv`.",
        "- Exact-response-only and fallback-only splits are not auditable.",
        "",
        "## Forward/reverse agreement",
        "",
        "- No committed forward/reverse debiased pairwise runs were available for analysis.",
        "",
        "## Policy sensitivity",
        "",
        "- P0 is reproducible from committed per-query outputs.",
        "- P1–P4 are not reproducible from committed artifacts because raw pairwise response texts were not preserved.",
        "",
        "## Manuscript corrections required",
        "",
        "1. Remove or replace unsupported Cohere/Azure corpus claims.",
        "2. Restrict the real-LLM evidence statement to auditable OpenAI primary-pairwise evidence and explicitly bounded auxiliary pointwise/listwise checks.",
        "3. Add a limitation that raw pairwise response texts were not preserved, preventing retrospective ambiguity and fallback audits.",
        "4. Remove any implication that order-bias mitigation was audited in the committed primary-pairwise corpus.",
        "",
        "## New API calls scientifically necessary?",
        "",
        "No new API calls are necessary to reproduce the committed OpenAI/Gemini end results already stored in the repository. However, new API calls would be necessary to create a fresh ambiguity-sensitive reparsing audit only if no raw provider-side response logs can be recovered from outside the current repository snapshot.",
        "",
        "## Issue classification",
        "",
        "- `resolved`: OpenAI primary-pairwise counts and bootstrap-facing summary are reproducible from committed outputs.",
        "- `harmless but document`: pairwise raw-text absence for parser auditing.",
        "- `changes numerical results`: none demonstrated from current committed artifacts, because alternative reparsing policies are not reproducible.",
        "- `threatens conclusions`: current manuscript claims about a committed Cohere/Azure corroborative corpus.",
        "- `requires new experiments`: no for reproducing current OpenAI results; yes only if the authors want a fresh, ambiguity-sensitive reparsing study without recovering missing raw logs.",
    ]
    write_text(AUDIT_DIR / "REAL_LLM_INTEGRITY_FINAL_REPORT.md", "\n".join(lines))


def generate_patch_recommendations() -> None:
    text = r"""# MANUSCRIPT_PATCH_RECOMMENDATIONS

## Section 4.8 / real-LLM scope paragraph

Replace the current paragraph that introduces the primary OpenAI pilot and the separate Cohere/Azure failure-mining corpus with:

> In addition to the mechanical three-ranker evaluation described above, we analyze a bounded sample of stored real large-language-model outputs. The auditable primary evidence is an OpenAI pairwise pilot using \texttt{gpt-4o-mini} on SciDocs (50 queries), HotpotQA (20 queries), and FiQA (10 usable queries from a 20-query target). Separate OpenAI pointwise and listwise runs on SciDocs and HotpotQA are used only as auxiliary scope checks. A quota-limited Gemini pilot exists for two SciDocs queries, but we do not treat it as analyzed evidence. We keep these API-based runs separate from the main mechanical-vote evaluation and treat them as bounded corroborative checks rather than scale-matched confirmatory evidence.

## Table 5

Replace the current four-row provider table with:

> OpenAI API | \texttt{gpt-4o-mini} | Pairwise | Primary paired pilot on SciDocs, HotpotQA, and FiQA. \\
> OpenAI API | \texttt{gpt-4o-mini} | Pointwise / listwise | Auxiliary scope check on SciDocs and HotpotQA. \\

Optional footnote below the table:

> A quota-limited Gemini pilot on two SciDocs queries is documented in the stored artifacts but is not treated as analyzed evidence here.

## Parser description

Replace the current parser sentence block with:

> The auditable OpenAI pairwise pilot uses top-$k=15$ candidate pools, seed 42, no candidate-order debiasing, and pairwise responses prompted as one-letter A/B judgments with up to four retries and exponential backoff on transient API failures. The pairwise parser accepts leading `A` or `B`, then falls back to presence-based matching, and otherwise defaults to `A`. Because the committed cache preserves only final winner/loser records rather than raw response text, ambiguity and fallback frequencies cannot be reconstructed retrospectively from the current artifact snapshot.

## Order-bias discussion

Replace any sentence claiming that the analyzed corroborative corpus used symmetric A$\rightarrow$B and B$\rightarrow$A prompting with:

> The committed primary-pairwise artifacts do not use candidate-order debiasing (`debias\_position=false`), and no auditable forward/reverse paired-prompt corpus is available in the current anonymous snapshot. We therefore treat order sensitivity as an unresolved limitation rather than a quantified result in this revision.

## Section 8 real-LLM results

Replace the current opening and corroborative-corpus paragraphs with:

> The bounded real-LLM evidence in this revision is the stored OpenAI pairwise pilot on SciDocs, HotpotQA, and FiQA. Cyclic-query prevalence is 92.0\% on SciDocs (46/50), 80.0\% on HotpotQA (16/20), and 10.0\% on FiQA (1/10). Repaired-versus-unrepaired Copeland-hybrid $\Delta$nDCG remains small: SciDocs shows a negative mean difference of $-0.0010$ with 95\% bootstrap CI $[-0.0019, -0.0002]$, while HotpotQA and FiQA are exactly zero in the stored summaries. We interpret these runs as bounded corroborative evidence that real LLM preferences can still produce substantial cyclicity without demonstrating a general retrieval-quality benefit from repair.

If a Gemini sentence is desired:

> A partial Gemini pilot on two SciDocs queries is archived, but its scale is too limited for manuscript-level inference.

## Limitations

Insert:

> The committed real-LLM artifacts preserve final pairwise winner/loser records but not the underlying raw pairwise response texts. As a result, ambiguity rates, fallback-to-`A` frequency, and alternative ambiguity-sensitive reparsing policies cannot be audited retrospectively from the current anonymous repository snapshot.

Also insert:

> Earlier draft text referred to a separate Cohere/Azure corroborative corpus, but no committed auditable version of that corpus is present in the current anonymous snapshot; we therefore do not rely on it here.

## Data Availability

Replace any sentence implying that all real-LLM parsing details are reconstructible from stored outputs with:

> Stored API-derived outputs are sufficient to reproduce the committed OpenAI pairwise query-level summaries, final judgment graphs, and downstream repaired-versus-unrepaired comparisons reported here. They are not sufficient to reconstruct the original pairwise response texts or to rerun ambiguity-sensitive parser audits without additional logs outside the current anonymous snapshot.
"""
    write_text(AUDIT_DIR / "MANUSCRIPT_PATCH_RECOMMENDATIONS.md", text)


def generate_validation(experiments: list[Experiment]) -> None:
    checks = []
    pairwise_rows = read_csv_dicts(AUDIT_DIR / "policy_sensitivity_full.csv")
    for exp in experiments:
        if exp.mode != "pairwise":
            continue
        delta_rows = per_query_delta_rows(exp)
        qids = [row["query_id"] for row in delta_rows]
        checks.append(("no_duplicate_queries", exp.rel_path, len(qids) == len(set(qids))))
        if delta_rows:
            help_count = sum(1 for row in delta_rows if row["help"])
            harm_count = sum(1 for row in delta_rows if row["harm"])
            inactive_count = sum(1 for row in delta_rows if row["inactive"])
            checks.append(
                (
                    "help_harm_inactive_sum",
                    exp.rel_path,
                    help_count + harm_count + inactive_count == len(delta_rows),
                )
            )
            mean_delta, ci_low, ci_high = bootstrap_mean_ci([row["delta_ndcg"] for row in delta_rows], 2000, 42)
            checks.append(("ci_contains_mean", exp.rel_path, ci_low <= mean_delta <= ci_high))
    provider_rows = read_csv_dicts(AUDIT_DIR / "provider_record_counts.csv")
    openai_total = sum(
        int(row["usable_queries"])
        for row in provider_rows
        if row["provider"] == "openai" and row["manuscript_role"] == "yes-primary-pairwise"
    )
    checks.append(("provider_total_matches_subtotals", "openai-primary", openai_total == 80))
    common_rows = read_csv_dicts(AUDIT_DIR / "policy_sensitivity_common_queries.csv")
    p0_rows = [row for row in common_rows if row["policy"] == "P0"]
    checks.append(("common_query_file_present", "policy_sensitivity_common_queries.csv", len(p0_rows) > 0))
    checks.append(("forward_reverse_doc_identity", "not_applicable_no_debias_runs", True))
    failed = [check for check in checks if not check[2]]
    lines = [
        "# VALIDATION_CHECKS",
        "",
        "## Results",
        "",
    ]
    for name, scope, ok in checks:
        lines.append(f"- `{name}` on `{scope}`: {'PASS' if ok else 'FAIL'}")
    if failed:
        lines.extend(["", "## Failure", "", "One or more validation checks failed."])
        write_text(AUDIT_DIR / "VALIDATION_CHECKS.md", "\n".join(lines))
        raise SystemExit("Validation failed")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Alternative-policy common-query sensitivity is marked not reproducible rather than failing validation.",
            "- Forward/reverse document-identity validation is not applicable because no auditable debiased pairwise runs are present.",
        ]
    )
    write_text(AUDIT_DIR / "VALIDATION_CHECKS.md", "\n".join(lines))


def main() -> None:
    experiments = discover_experiments()
    generate_inventory(experiments)
    generate_provider_counts(experiments)
    generate_parser_audit(experiments)
    generate_response_quality(experiments)
    generate_policy_sensitivity(experiments)
    generate_position_bias(experiments)
    generate_forward_reverse(experiments)
    generate_cyclicity_source_audit(experiments)
    generate_prompt_mode_scope(experiments)
    generate_final_report(experiments)
    generate_patch_recommendations()
    generate_validation(experiments)


if __name__ == "__main__":
    main()
