#!/usr/bin/env python
"""
Run publication-style vote comparison: three vote constructions × SciDocs + HotpotQA.

Vote variants (per dataset, shared ``query_ids.txt`` and score files):
  - ``ms2``: ``build_votes_file`` with ``--min-support 2``
  - ``ms1``: ``--min-support 1``
  - ``ms1_drop_mutual``: ``ms1`` votes then ``postprocess_votes_drop_mutual_pairs``

Then ``run_real_experiment`` with a short hybrid-only method list.

Example::
    python scripts/run_publication_vote_suite.py --root outputs/pub_vote_cmp_v2
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"
METHODS = [
    "hybrid_rrf_prior_only",
    "hybrid_rrf_unrepaired_copeland_a03",
    "hybrid_rrf_repaired_copeland_a03",
    "hybrid_rrf_unrepaired_balance_a03",
    "hybrid_rrf_repaired_balance_a03",
]


def _run(cmd: list[str]) -> None:
    print(">>", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, cwd=_REPO)
    if r.returncode != 0:
        sys.exit(r.returncode)


def _write_query_ids_from_processed(dataset: str, path: Path, n: int) -> int:
    if dataset == "scidocs":
        qpath = _REPO / "data/processed/beir/scidocs/queries.jsonl"
    elif dataset == "hotpotqa":
        qpath = _REPO / "data/processed/hotpotqa/queries.jsonl"
    else:
        raise ValueError(dataset)
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
    return len(ids)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path("outputs/pub_vote_cmp_v2"))
    p.add_argument("--scidocs-queries", type=int, default=120)
    p.add_argument("--hotpot-queries", type=int, default=70)
    p.add_argument("--scidocs-top-n", type=int, default=50)
    p.add_argument("--hotpot-top-n", type=int, default=35)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    py = sys.executable

    for dataset, nq, topn, topk in (
        ("scidocs", args.scidocs_queries, args.scidocs_top_n, 20),
        ("hotpotqa", args.hotpot_queries, args.hotpot_top_n, 10),
    ):
        base = args.root / dataset
        base.mkdir(parents=True, exist_ok=True)
        qfile = base / "query_ids.txt"
        n_written = _write_query_ids_from_processed(dataset, qfile, nq)
        print(f"[suite] {dataset}: wrote {n_written} query ids → {qfile}")

        for ranker in ("bm25", "tfidf", "minilm"):
            outp = base / f"scores_{ranker}.jsonl"
            _run(
                [
                    py,
                    str(_SCRIPTS / "generate_score_file.py"),
                    "--dataset",
                    dataset,
                    "--ranker",
                    ranker,
                    "--max-queries",
                    str(n_written),
                    "--top-n",
                    str(topn),
                    "--seed",
                    str(args.seed),
                    "--query-id-file",
                    str(qfile),
                    "--output",
                    str(outp),
                ]
            )

        s_bm = base / "scores_bm25.jsonl"
        s_tf = base / "scores_tfidf.jsonl"
        s_mn = base / "scores_minilm.jsonl"
        v_ms2 = base / "votes_ms2.jsonl"
        v_ms1 = base / "votes_ms1.jsonl"
        v_dm = base / "votes_ms1_drop_mutual.jsonl"

        common_vote = [
            py,
            str(_SCRIPTS / "build_votes_file.py"),
            "--dataset",
            dataset,
            "--score-files",
            str(s_bm),
            str(s_tf),
            str(s_mn),
            "--top-k",
            str(topk),
            "--vote-weight-scheme",
            "margin",
            "--min-vote-margin",
            "0.05",
            "--abstain-missing",
            "--query-id-file",
            str(qfile),
        ]

        _run(
            common_vote
            + [
                "--min-support",
                "2",
                "--min-aggregate-margin",
                "0.1",
                "--output",
                str(v_ms2),
            ]
        )
        _run(
            common_vote
            + [
                "--min-support",
                "1",
                "--min-aggregate-margin",
                "0.0",
                "--output",
                str(v_ms1),
            ]
        )
        _run(
            [
                py,
                str(_SCRIPTS / "postprocess_votes_drop_mutual_pairs.py"),
                "--input",
                str(v_ms1),
                "--output",
                str(v_dm),
            ]
        )

        for variant, vpath in (
            ("ms2", v_ms2),
            ("ms1", v_ms1),
            ("ms1_drop_mutual", v_dm),
        ):
            outd = base / variant
            _run(
                [
                    py,
                    str(_SCRIPTS / "run_real_experiment.py"),
                    "--dataset",
                    dataset,
                    "--preference-source",
                    "votes_file",
                    "--pairwise-file",
                    str(vpath),
                    "--query-id-file",
                    str(qfile),
                    "--score-prior-files",
                    str(s_bm),
                    str(s_tf),
                    str(s_mn),
                    "--max-queries",
                    str(n_written),
                    "--top-k",
                    str(topk),
                    "--include-hybrid-ablation",
                    "--methods",
                    *METHODS,
                    "--save-timings",
                    "--no-plots",
                    "--overwrite-existing",
                    "--output-dir",
                    str(outd),
                    "--seed",
                    str(args.seed),
                ]
            )

    print("[suite] done.")


if __name__ == "__main__":
    main()
