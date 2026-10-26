"""Freeze query identities before grades/pools; never compute retrieval utility."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import importlib.util
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa

from .common import (
    DATASETS,
    DEVELOPMENT_COUNTS,
    EVALUATION_COUNTS,
    GATE_THRESHOLDS,
    MODEL_ID,
    MODEL_REVISION,
    SEED,
    WORKTREE,
    atomic,
    canonical,
    digest,
    filehash,
    now,
    requests_for,
    source_hashes,
)

REVISIONS = {
    "BeIR/fiqa": "979c07a7cb5ccc6ca009792241fa1250b98055dd",
    "BeIR/fiqa-qrels": "252958f2d646e22cab6d0c72dd3f0d5de6d0655a",
    "BeIR/scidocs": "acebceec772628c6679d76d6cff30ad517d17f4e",
    "BeIR/scidocs-qrels": "735ea1048e37b1ebce14c6dc3d33a5edaf66d3dc",
    "xlangai/BRIGHT": "3066d29c9651a576c8aba4832d249807b181ecae",
}


def arrow(path, columns=None):
    with pa.memory_map(str(path), "r") as stream:
        table = pa.ipc.open_stream(stream).read_all()
        if columns is not None:
            table = table.select(columns)
        return table.to_pylist()


def unique_file(root, pattern):
    paths = sorted(root.glob(pattern))
    if len(paths) != 1:
        raise ValueError(f"Expected one pinned source: {root}/{pattern}; got {len(paths)}")
    return paths[0]


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def semantic_controls():
    # These transparently synthetic canaries are instrument checks, not benchmark results.
    facts = [
        ("What is the capital of France?", "Paris is the capital of France."),
        ("What is the chemical formula of water?", "Water has the chemical formula H2O."),
        ("How many days are in a week?", "A week contains seven days."),
        ("What organ pumps blood?", "The heart pumps blood around the body."),
        ("What gas do plants absorb for photosynthesis?", "Plants absorb carbon dioxide."),
        ("How many sides does a triangle have?", "A triangle has three sides."),
        ("Which planet is known as the red planet?", "Mars is known as the red planet."),
        (
            "At what temperature does pure water freeze in Celsius?",
            "Water freezes at zero degrees Celsius.",
        ),
        ("What is two plus two?", "Two plus two equals four."),
        ("Who wrote Hamlet?", "William Shakespeare wrote Hamlet."),
        ("What force pulls objects toward Earth?", "Gravity pulls objects toward Earth."),
        (
            "Which animal is known for black and white stripes?",
            "Zebras have black and white stripes.",
        ),
    ]
    rows = []
    for index, (query, answer) in enumerate(facts):
        irrelevant = facts[(index + 5) % len(facts)][1]
        rows.append(
            {
                "uid": f"control:{index:02d}",
                "dataset": "synthetic_control_only",
                "query_id": str(index),
                "query": query,
                "pools": {"natural": ["relevant", "unrelated"]},
                "documents": {"relevant": answer, "unrelated": irrelevant},
                "control_winner": "relevant",
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--analysis-python", type=Path, required=True)
    args = parser.parse_args()
    base, run = args.workspace.resolve(), args.run.resolve()
    if run.exists():
        raise FileExistsError("Preparation never replaces an existing run")
    run.mkdir(parents=True, mode=0o700)
    for name in ("inputs", "provenance", "private", "checkpoints", "logs", "results"):
        (run / name).mkdir(mode=0o700)
    if shutil.disk_usage(run).free < 25 * 1024**3:
        raise RuntimeError("Need at least 25 GiB free before preparation")

    typed, untyped, exclusion_sources = set(), set(), []
    exclusion = base / "runs/prospective_20261025T162122Z/provenance/EXCLUDED_QUERY_IDS.json"
    prior = json.loads(exclusion.read_text())
    typed.update(tuple(x) for x in prior["dataset_query"])
    untyped.update(prior["untyped_query_ids"])
    exclusion_sources.append({"path": str(exclusion), "sha256": filehash(exclusion)})
    # Read identities only; no historical metric values are used for selection.
    metric_source = base / "runs/offline_repair_20261025T050245Z/reports/EXPERIMENT_METRICS.csv"
    with metric_source.open() as stream:
        for row in csv.DictReader(stream):
            typed.add((row["dataset"], str(row["query_id"])))
    exclusion_sources.append(
        {
            "path": str(metric_source),
            "sha256": filehash(metric_source),
            "projection": ["dataset", "query_id"],
        }
    )
    for name in ("prospective_20261025T162122Z", "candidate_intervention_20261025T184050Z"):
        path = base / "runs" / name / "inputs/FROZEN_QUERY_IDS.json"
        for row in json.loads(path.read_text())["queries"]:
            typed.add((row["dataset"], str(row["query_id"])))
        exclusion_sources.append({"path": str(path), "sha256": filehash(path)})
    atomic(
        run / "provenance/EXCLUSIONS.json",
        {"typed": sorted(typed), "untyped": sorted(untyped), "sources": exclusion_sources},
    )

    definitions, receipts, selection = {}, {}, []
    used_texts = set()
    for name, n_dev, n_eval in zip(DATASETS, DEVELOPMENT_COUNTS, EVALUATION_COUNTS, strict=True):
        dataset, _, domain = name.partition(":")
        if dataset != "bright":
            root = base / "repo/data/raw/beir" / dataset
            revision = REVISIONS["BeIR/" + dataset]
            qpath = unique_file(root, f"BeIR___{dataset}/queries/0.0.0/{revision}/*.arrow")
            dpath = unique_file(root, f"BeIR___{dataset}/corpus/0.0.0/{revision}/*.arrow")
            qrevision = REVISIONS["BeIR/" + dataset + "-qrels"]
            lpath = unique_file(
                root, f"BeIR___{dataset}-qrels/default/0.0.0/{qrevision}/*test.arrow"
            )
            eligible_ids = {str(r["query-id"]) for r in arrow(lpath, ["query-id"])}
            queries = [
                {"query_id": str(r["_id"]), "query": r["text"]}
                for r in arrow(qpath, ["_id", "text"])
                if str(r["_id"]) in eligible_ids
            ]
        else:
            root = base / "repo/data/raw/bright/xlangai___bright"
            revision = REVISIONS["xlangai/BRIGHT"]
            qpath = unique_file(root, f"examples/0.0.0/{revision}/bright-{domain}.arrow")
            dpath = unique_file(root, f"documents/0.0.0/{revision}/bright-{domain}.arrow")
            lpath = qpath
            # Eligibility requires nonempty gold IDs but does not inspect IDs/grades yet.
            with pa.memory_map(str(qpath), "r") as stream:
                table = pa.ipc.open_stream(stream).read_all()
                import pyarrow.compute as pc

                mask = pc.greater(pc.list_value_length(table["gold_ids"]), 0)
                projected = table.select(["id", "query"]).filter(mask).to_pylist()
            queries = [
                {"query_id": domain + ":" + str(r["id"]), "query": r["query"]} for r in projected
            ]
        candidates = []
        for q in queries:
            text_hash = digest(" ".join(q["query"].lower().split()))
            if not q["query"].strip() or (dataset, q["query_id"]) in typed:
                continue
            if q["query_id"] in untyped or text_hash in used_texts:
                continue
            candidates.append({**q, "query_text_hash": text_hash})
        candidates.sort(key=lambda q: digest([SEED, name, q["query_id"]]))
        chosen = []
        for q in candidates:
            if q["query_text_hash"] in used_texts:
                continue
            chosen.append(q)
            used_texts.add(q["query_text_hash"])
            if len(chosen) == n_dev + n_eval:
                break
        if len(chosen) != n_dev + n_eval:
            raise RuntimeError(f"Insufficient unused eligible queries in {name}: {len(chosen)}")
        for index, q in enumerate(chosen):
            selection.append(
                {
                    **q,
                    "dataset": dataset,
                    "domain": domain or None,
                    "stratum": name,
                    "uid": dataset + ":" + q["query_id"],
                    "phase": "development" if index < n_dev else "evaluation",
                    "selection_index": index if index < n_dev else index - n_dev,
                }
            )
        definitions[name] = (qpath, dpath, lpath)
        receipts[name] = {
            "eligible_after_history": len(candidates),
            "development": n_dev,
            "evaluation": n_eval,
        }
    roster = [{k: v for k, v in r.items() if k != "query"} for r in selection]
    atomic(
        run / "inputs/FROZEN_QUERY_IDS.json",
        {
            "frozen_utc": now(),
            "seed": SEED,
            "queries": roster,
            "grade_values_opened": False,
            "retrieval_utility_computed": False,
        },
    )
    (run / "inputs/FROZEN_QUERY_IDS.json").chmod(0o400)

    # Only now load grades and create both prespecified candidate conditions.
    sys.path.insert(0, str(WORKTREE / "src"))
    spec = importlib.util.spec_from_file_location(
        "existing_bm25", WORKTREE / "scripts/generate_score_file.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    labels, rows, sources = {}, [], []
    for name, (qpath, dpath, lpath) in definitions.items():
        dataset, _, domain = name.partition(":")
        if dataset != "bright":
            docs = [
                SimpleNamespace(doc_id=str(r["_id"]), text=r["text"], title=r["title"])
                for r in arrow(dpath, ["_id", "text", "title"])
            ]
            qrels = {}
            for r in arrow(lpath):
                qrels.setdefault(str(r["query-id"]), {})[str(r["corpus-id"])] = int(r["score"])
            exclusions = {}
        else:
            docs = [
                SimpleNamespace(doc_id=str(r["id"]), text=r["content"], title="")
                for r in arrow(dpath, ["id", "content"])
            ]
            projected = arrow(qpath, ["id", "gold_ids", "excluded_ids"])
            qrels = {
                domain + ":" + str(r["id"]): {str(d): 1 for d in r["gold_ids"]} for r in projected
            }
            exclusions = {
                domain + ":" + str(r["id"]): set(map(str, r["excluded_ids"])) for r in projected
            }
        by_id = {d.doc_id: d for d in docs}
        if len(by_id) != len(docs):
            raise RuntimeError("Duplicate document identity")
        index = module.BM25Ranker(docs, k1=1.5, b=0.75)
        for query in (q for q in selection if q["stratum"] == name):
            qid, uid = query["query_id"], query["uid"]
            excluded = exclusions.get(qid, set())
            retrieved = index.top_docs(query["query"], min(len(docs), 12 + len(excluded)))
            natural = [(d, s) for d, s in retrieved if d not in excluded][:12]
            if len(natural) != 12:
                raise RuntimeError("Cannot freeze twelve eligible natural candidates")
            gold = qrels[qid]
            if not any(g > 0 for g in gold.values()):
                raise RuntimeError("Selected query has no official positive qrel")
            if any(d not in by_id for d, grade in gold.items() if grade > 0):
                raise RuntimeError("Official positive document missing from corpus; no resampling")
            ordinary = [d for d, _ in natural]
            enriched = ordinary[:10]
            positives = sorted(
                (d for d, g in gold.items() if g > 0 and d not in excluded and d not in enriched),
                key=lambda d: digest([SEED, uid, "enriched", d]),
            )
            enriched.extend(positives[:2])
            enriched.extend(d for d in ordinary if d not in enriched)
            enriched = enriched[:12]
            if not any(gold.get(d, 0) > 0 for d in enriched):
                raise RuntimeError("No eligible positive for enriched pool; no resampling")
            union = sorted(set(ordinary) | set(enriched))
            row = {
                **query,
                "pools": {"natural": ordinary, "enriched": enriched},
                "documents": {d: module._document_text(by_id[d]) for d in union},
                "bm25_scores": dict(natural),
                "corpus_size": len(docs),
                "official_excluded_count": len(excluded),
            }
            row["input_sha256"] = digest(row)
            labels[uid] = gold
            rows.append(row)
        sources.extend(
            {"stratum": name, "path": str(p), "sha256": filehash(p), "role": role}
            for p, role in ((qpath, "queries"), (dpath, "corpus"), (lpath, "qrels"))
        )
        del docs, by_id, index
    rows.sort(key=lambda r: (r["selection_index"], DATASETS.index(r["stratum"])))
    for phase in ("development", "evaluation"):
        path = run / "inputs" / (phase + ".jsonl")
        path.write_text("".join(canonical(r) + "\n" for r in rows if r["phase"] == phase))
        path.chmod(0o400)
    atomic(run / "inputs/QRELS_EVALUATION_ONLY.json", labels)
    (run / "inputs/QRELS_EVALUATION_ONLY.json").chmod(0o400)
    atomic(run / "inputs/SEMANTIC_CONTROLS.json", semantic_controls())
    (run / "inputs/SEMANTIC_CONTROLS.json").chmod(0o400)

    model_path = args.model_path.resolve()
    if model_path.name != MODEL_REVISION:
        raise RuntimeError("Model snapshot directory does not match immutable revision")
    metadata = fetch_json(
        f"https://huggingface.co/api/models/{MODEL_ID}/revision/{MODEL_REVISION}?blobs=true"
    )
    if (
        metadata["sha"] != MODEL_REVISION
        or metadata.get("cardData", {}).get("license") != "apache-2.0"
    ):
        raise RuntimeError("Model metadata/license verification failed")
    if metadata.get("gated") or metadata.get("private"):
        raise RuntimeError("Expected public, non-gated checkpoint")
    atomic(run / "provenance/MODEL_PUBLIC_METADATA.json", metadata)
    with urllib.request.urlopen(
        f"https://huggingface.co/{MODEL_ID}/raw/{MODEL_REVISION}/LICENSE", timeout=30
    ) as response:
        license_text = response.read().decode()
    if "Apache License" not in license_text or "Version 2.0" not in license_text:
        raise RuntimeError("Unexpected model license text")
    (run / "provenance/MODEL_LICENSE.txt").write_text(license_text)
    model_hashes = {p.name: filehash(p) for p in sorted(model_path.iterdir()) if p.is_file()}
    expected = json.loads((model_path / "model.safetensors.index.json").read_text())["weight_map"]
    if not set(expected.values()) <= set(model_hashes):
        raise RuntimeError("Incomplete model weights")
    lfs_checked = []
    for sibling in metadata["siblings"]:
        name, lfs = sibling["rfilename"], sibling.get("lfs", {})
        if name in model_hashes and lfs.get("sha256"):
            if model_hashes[name] != lfs["sha256"]:
                raise RuntimeError("Local model does not match official LFS identity: " + name)
            lfs_checked.append(name)
    if not set(expected.values()) <= set(lfs_checked):
        raise RuntimeError("Not all model weight hashes verified against official LFS")
    atomic(
        run / "provenance/MODEL_FILES.json",
        {
            "id": MODEL_ID,
            "revision": MODEL_REVISION,
            "path": str(model_path),
            "sha256": model_hashes,
            "official_lfs_checked": lfs_checked,
            "license": "Apache-2.0",
            "weight_bytes": sum((model_path / x).stat().st_size for x in set(expected.values())),
        },
    )
    for dataset, revision in REVISIONS.items():
        meta = fetch_json(f"https://huggingface.co/api/datasets/{dataset}/revision/{revision}")
        if meta["sha"] != revision:
            raise RuntimeError("Dataset revision mismatch")
        atomic(run / "provenance" / (dataset.replace("/", "_") + ".json"), meta)

    planned = sum(len(requests_for(r)) for r in rows if r["phase"] == "evaluation")
    inputs = {p.name: filehash(p) for p in sorted((run / "inputs").iterdir())}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKTREE, text=True).strip()
    manifest = {
        "schema": "jdsa-prospective-v1",
        "created_utc": now(),
        "seed": SEED,
        "base_commit": "2c69f331fa4add10ce577c17516afb997b630dfe",
        "preparation_commit": commit,
        "code_sha256": source_hashes(),
        "reused_core_sha256": {
            name: filehash(WORKTREE / name)
            for name in (
                "scripts/generate_score_file.py",
                "src/consistency_ranker/baseline_ranking.py",
                "src/consistency_ranker/greedy_fas.py",
                "src/consistency_ranker/mwfas_solver.py",
                "src/consistency_ranker/evaluation.py",
                "src/consistency_ranker/statistical_inference.py",
            )
        },
        "input_sha256": inputs,
        "source_files": sources,
        "selection": receipts,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_identity_sha256": filehash(run / "provenance/MODEL_FILES.json"),
        "gate_thresholds": GATE_THRESHOLDS,
        "evaluation_queries": 390,
        "development_queries": 12,
        "development_responses": 240,
        "main_responses": planned,
        "max_attempts": planned + 240 + 16,
        "max_active_wall_s": 43200,
        "analysis_reserve_s": 3600,
        "max_new_disk_bytes": 30 * 1024**3,
        "model_path": str(model_path),
        "analysis_python": str(args.analysis_python.resolve()),
        "prepare_packages": {
            p: importlib.metadata.version(p) for p in ["pyarrow", "numpy", "networkx"]
        },
        "retrieval_utility_computed": False,
    }
    atomic(run / "RUN_MANIFEST.json", manifest)
    (run / "RUN_MANIFEST.json").chmod(0o400)
    atomic(
        run / "provenance/PREPARATION_COMPLETE.json",
        {
            "utc": now(),
            "manifest_sha256": filehash(run / "RUN_MANIFEST.json"),
            "query_ids_frozen_before_grades": True,
            "utility_computed": False,
            "planned_main_responses": planned,
        },
    )
    print(
        json.dumps(
            {
                "run": str(run),
                "evaluation_queries": 390,
                "development_queries": 12,
                "main_responses": planned,
                "weights_lfs_verified": len(lfs_checked),
            }
        )
    )


if __name__ == "__main__":
    main()
