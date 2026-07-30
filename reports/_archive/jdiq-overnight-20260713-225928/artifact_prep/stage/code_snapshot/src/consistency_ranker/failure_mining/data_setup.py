"""Dataset and vote-file preparation for failure mining."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from consistency_ranker.data.dataset_registry import DATASET_NAMES, get_config, processed_queries_jsonl
from consistency_ranker.data.unified_loader import load_dataset_splits

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS = REPO_ROOT / "scripts"

VOTE_REGIMES = ("ms1", "ms2", "ms1_drop_mutual")
DEFAULT_RANKERS = ("bm25", "tfidf", "minilm")


def ensure_dataset_prepared(dataset: str, *, max_queries: int, force: bool = False) -> None:
    """Download (if needed) and prepare a dataset."""
    cfg = get_config(dataset)
    queries_path = cfg.processed_path / "queries.jsonl"
    if queries_path.exists() and not force:
        return

    raw_ok = (
        (cfg.raw_path / "queries.jsonl").exists()
        and (cfg.raw_path / "documents.jsonl").exists()
        and (cfg.raw_path / "qrels.jsonl").exists()
    )
    if not raw_ok:
        subprocess.run(
            [sys.executable, str(SCRIPTS / "download_datasets.py"), "--dataset", dataset],
            cwd=REPO_ROOT,
            check=True,
        )
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "prepare_datasets.py"),
            "--dataset",
            dataset,
            "--max-queries",
            str(max(max_queries, 200)),
        ],
        cwd=REPO_ROOT,
        check=True,
    )


def write_query_ids(dataset: str, path: Path, n: int) -> list[str]:
    qpath = processed_queries_jsonl(dataset)
    ids: list[str] = []
    with qpath.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            ids.append(str(row["query_id"]))
            if len(ids) >= n:
                break
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(ids) + "\n", encoding="utf-8")
    return ids


def ensure_score_files(
    dataset: str,
    work_dir: Path,
    *,
    query_ids: list[str],
    top_n: int,
    seed: int = 42,
) -> list[Path]:
    """Generate BM25/TF-IDF/MiniLM score files if missing."""
    qfile = work_dir / "query_ids.txt"
    if not qfile.exists():
        write_query_ids(dataset, qfile, len(query_ids))

    score_paths: list[Path] = []
    for ranker in DEFAULT_RANKERS:
        outp = work_dir / f"scores_{ranker}.jsonl"
        score_paths.append(outp)
        if outp.exists():
            continue
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_score_file.py"),
                "--dataset",
                dataset,
                "--ranker",
                ranker,
                "--max-queries",
                str(len(query_ids)),
                "--top-n",
                str(top_n),
                "--seed",
                str(seed),
                "--query-id-file",
                str(qfile),
                "--output",
                str(outp),
            ],
            cwd=REPO_ROOT,
            check=True,
        )
    return score_paths


def ensure_vote_file(
    dataset: str,
    work_dir: Path,
    regime: str,
    score_files: list[Path],
    *,
    top_k: int,
    query_id_file: Path,
) -> Path:
    """Build or reuse vote JSONL for a regime."""
    out = work_dir / f"votes_{regime}.jsonl"
    if out.exists():
        return out

    min_support = 2 if regime == "ms2" else 1
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "build_votes_file.py"),
            "--dataset",
            dataset,
            "--score-files",
            *[str(p) for p in score_files],
            "--top-k",
            str(top_k),
            "--vote-weight-scheme",
            "margin",
            "--min-vote-margin",
            "0.05",
            "--abstain-missing",
            "--min-support",
            str(min_support),
            "--query-id-file",
            str(query_id_file),
            "--output",
            str(out.with_suffix(".raw.jsonl") if regime == "ms1_drop_mutual" else out),
        ],
        cwd=REPO_ROOT,
        check=True,
    )

    if regime == "ms1_drop_mutual":
        raw = out.with_suffix(".raw.jsonl")
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "postprocess_votes_drop_mutual_pairs.py"),
                "--input",
                str(raw),
                "--output",
                str(out),
            ],
            cwd=REPO_ROOT,
            check=True,
        )
    return out


def load_documents_map(dataset: str) -> dict[str, dict[str, str]]:
    """Load doc_id -> {title, text_snippet} for forensic records."""
    _, documents, _ = load_dataset_splits(dataset)
    out: dict[str, dict[str, str]] = {}
    for doc in documents:
        text = doc.text or ""
        snippet = text[:500] + ("…" if len(text) > 500 else "")
        out[doc.doc_id] = {"title": doc.title or "", "text_snippet": snippet}
    return out


def supported_datasets() -> tuple[str, ...]:
    return tuple(sorted(DATASET_NAMES))
