"""Detached gate and strictly conditional main collection; no provider APIs."""

from __future__ import annotations

import argparse
import collections
import fcntl
import importlib.metadata
import json
import os
import random
import resource
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from .common import (
    MODEL_ID,
    MODEL_REVISION,
    PROMPTS,
    SEED,
    SYSTEM,
    WORKTREE,
    atomic,
    canonical,
    database,
    digest,
    filehash,
    now,
    paired_disposition,
    parse,
    request_id,
    requests_for,
    response_rows,
    source_hashes,
)
from .gate import gate_report


def compute_pids():
    if os.environ.get("SLURM_JOB_ID"):
        # Slurm isolates the allocated MIG instance. A global nvidia-smi process
        # list includes other legitimate instances and is not a conflict test.
        visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
        if visible.lower() in {"", "-1", "none", "nodevfiles"} or "," in visible:
            raise RuntimeError("Slurm must expose exactly one allocated CUDA device")
        return set()
    result = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
        text=True,
        capture_output=True,
        check=True,
        timeout=15,
    )
    return {int(line.strip()) for line in result.stdout.splitlines() if line.strip().isdigit()}


def host_available_bytes():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("Cannot verify host memory")


def control_requests(row):
    pair = sorted(row["documents"])
    return [
        {
            "uid": row["uid"],
            "pair": pair,
            "orientation": orientation,
            "variant": "primary",
            "repeat": 0,
            "id": request_id(row["uid"], pair, orientation),
        }
        for orientation in (0, 1)
    ]


class Worker:
    def __init__(self, run, resume=False):
        self.run = run.resolve()
        self.manifest = json.loads((self.run / "RUN_MANIFEST.json").read_text())
        self.manifest_hash = filehash(self.run / "RUN_MANIFEST.json")
        if self.manifest["code_sha256"] != source_hashes():
            raise RuntimeError("Frozen code or protocol identity changed")
        for name, expected in self.manifest["reused_core_sha256"].items():
            if filehash(WORKTREE / name) != expected:
                raise RuntimeError("Reused ranking/evaluation implementation changed: " + name)
        for name, expected in self.manifest["input_sha256"].items():
            if filehash(self.run / "inputs" / name) != expected:
                raise RuntimeError("Frozen input identity changed: " + name)
        if (
            filehash(self.run / "provenance/MODEL_FILES.json")
            != self.manifest["model_identity_sha256"]
        ):
            raise RuntimeError("Model file identity manifest changed")
        identity = json.loads((self.run / "provenance/MODEL_FILES.json").read_text())
        self.model_path = Path(self.manifest["model_path"])
        for name, expected in identity["sha256"].items():
            if filehash(self.model_path / name) != expected:
                raise RuntimeError("Frozen model/tokenizer/config bytes changed: " + name)
        self.locks = []
        for path in (
            self.run / "campaign.lock",
            Path("/tmp") / f"caar-prospective-gpu0-{os.getuid()}.lock",
        ):
            stream = path.open("a")
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.locks.append(stream)
        if compute_pids() - {os.getpid()}:
            raise RuntimeError("Unrelated GPU process present; refusing to allocate")
        if host_available_bytes() < 24 * 1024**3:
            raise RuntimeError("Less than 24 GiB available host memory")
        if shutil.disk_usage(self.run).free < 25 * 1024**3:
            raise RuntimeError("Less than 25 GiB available disk")
        self.connection = database(self.run / "private/responses.sqlite3")
        old_attempts = self.connection.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        if old_attempts and not resume:
            raise RuntimeError("Existing inference attempts require explicit --resume")
        for session_id, started, charged, closed in self.connection.execute(
            "SELECT * FROM sessions"
        ).fetchall():
            if not closed:
                conservative = max(
                    charged,
                    (datetime.now(timezone.utc) - datetime.fromisoformat(started)).total_seconds(),
                )
                self.connection.execute(
                    "UPDATE sessions SET charged_s=?,closed=1 WHERE id=?",
                    (conservative, session_id),
                )
        self.connection.execute(
            "UPDATE attempts SET disposition='interrupted_inflight' WHERE disposition='started'"
        )
        self.prior_s = self.connection.execute(
            "SELECT COALESCE(SUM(charged_s),0) FROM sessions"
        ).fetchone()[0]
        self.session = digest([now(), os.getpid()])
        self.started = time.monotonic()
        self.connection.execute("INSERT INTO sessions VALUES(?,?,?,0)", (self.session, now(), 0.0))
        self.connection.commit()
        existing = response_rows(self.connection)
        self.counters = collections.Counter(r["phase"] for r in existing)
        self.statuses = collections.Counter(
            r["status"] for r in existing if r["phase"] == "evaluation"
        )
        self.completed_queries = len(list((self.run / "results").glob("*.json")))
        self.phase, self.uid = "loading_model", None
        self.runtime = {}
        self.check_budget()
        self.heartbeat()

    def charged_s(self):
        return self.prior_s + time.monotonic() - self.started

    def check_budget(self, reserve=0):
        if self.charged_s() + reserve >= self.manifest["max_active_wall_s"]:
            raise RuntimeError("Cumulative active wall budget exhausted")
        if (
            self.connection.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
            >= self.manifest["max_attempts"]
        ):
            raise RuntimeError("Cumulative inference-attempt budget exhausted")
        if shutil.disk_usage(self.run).free < 2 * 1024**3:
            raise RuntimeError("Less than 2 GiB disk remains")

    def heartbeat(self, state="RUNNING_HEALTHY"):
        elapsed = time.monotonic() - self.started
        self.connection.execute(
            "UPDATE sessions SET charged_s=? WHERE id=?", (elapsed, self.session)
        )
        self.connection.commit()
        progress = {
            "state": state,
            "phase": self.phase,
            "utc": now(),
            "pid": os.getpid(),
            "host": os.uname().nodename,
            "uid": self.uid,
            "manifest_sha256": self.manifest_hash,
            "model": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "qrels_loaded_by_collector": False,
            "responses": dict(self.counters),
            "evaluation_dispositions": dict(self.statuses),
            "completed_queries": self.completed_queries,
            "total_queries": 390,
            "charged_wall_s": self.charged_s(),
            "runtime": self.runtime,
        }
        atomic(self.run / "PROGRESS.json", progress)

    def load_model(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch.set_num_threads(2)
        random.seed(SEED)
        np.random.seed(SEED)
        torch.manual_seed(SEED)
        torch.cuda.manual_seed_all(SEED)
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cuda.matmul.allow_tf32 = False
        if torch.cuda.device_count() != 1:
            raise RuntimeError("Exactly one visible CUDA device is required")
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, local_files_only=True, trust_remote_code=False
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            dtype=torch.bfloat16,
            device_map={"": "cuda:0"},
            attn_implementation="sdpa",
            local_files_only=True,
            trust_remote_code=False,
        )
        self.model.eval()
        if next(self.model.parameters()).device.type != "cuda":
            raise RuntimeError("Model was not allocated on CUDA")
        self.runtime = {
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_cpus_per_task": os.environ.get("SLURM_CPUS_PER_TASK"),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "packages": {
                p: importlib.metadata.version(p)
                for p in ("torch", "transformers", "accelerate", "numpy", "huggingface-hub")
            },
            "cuda_version": torch.version.cuda,
            "gpu_name": torch.cuda.get_device_name(0),
            "gpu_total_bytes": torch.cuda.get_device_properties(0).total_memory,
            "gpu_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "gpu_peak_reserved_bytes": torch.cuda.max_memory_reserved(),
            "peak_host_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "tokenizer_class": type(self.tokenizer).__name__,
            "chat_template_sha256": digest(self.tokenizer.chat_template),
            "generation_defaults": self.model.generation_config.to_dict(),
            "effective_parameters": {
                "do_sample": False,
                "max_new_tokens": 4,
                "batch_size": 1,
                "dtype": "bfloat16",
                "query_tokens": 128,
                "document_tokens": 256,
                "input_cap": 1024,
                "seed": SEED,
                "deterministic_algorithms": True,
            },
        }
        atomic(self.run / "provenance/RUNTIME.json", self.runtime)
        self.heartbeat()
        print(
            canonical(
                {
                    "event": "model_loaded",
                    "gpu": self.runtime["gpu_name"],
                    "allocated_bytes": torch.cuda.memory_allocated(),
                }
            ),
            flush=True,
        )

    def collect_one(self, row, request, phase):
        if self.connection.execute(
            "SELECT 1 FROM responses WHERE id=?", (request["id"],)
        ).fetchone():
            return
        self.check_budget(
            reserve=self.manifest["analysis_reserve_s"] if phase == "evaluation" else 0
        )
        tokenizer, torch = self.tokenizer, self.torch
        query_tokens = tokenizer.encode(row["query"], add_special_tokens=False)[:128]
        query = tokenizer.decode(query_tokens, skip_special_tokens=True)
        first, second = request["pair"] if request["orientation"] == 0 else request["pair"][::-1]
        document_tokens = {
            d: tokenizer.encode(row["documents"][d], add_special_tokens=False)[:256]
            for d in (first, second)
        }
        documents = {
            d: tokenizer.decode(ids, skip_special_tokens=True) for d, ids in document_tokens.items()
        }
        prompt = PROMPTS[request["variant"]].format(
            query=query, a=documents[first], b=documents[second]
        )
        rendered = tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
        encoded = tokenizer(rendered, return_tensors="pt", add_special_tokens=False).to("cuda:0")
        n_input = encoded["input_ids"].shape[1]
        if n_input > 1024:
            raise RuntimeError("Frozen input cap exceeded")
        seed = int(digest([SEED, request["id"]])[:8], 16)
        # Greedy decoding is independent of seed; record it for every fresh forward pass.
        torch.manual_seed(seed)
        self.connection.execute(
            "INSERT INTO attempts(id,phase,started,disposition) VALUES(?,?,?,'started')",
            (request["id"], phase, now()),
        )
        attempt = self.connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.connection.commit()
        start = time.perf_counter()
        with torch.inference_mode():
            output = self.model.generate(
                **encoded,
                do_sample=False,
                max_new_tokens=4,
                use_cache=True,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=self.model.generation_config.eos_token_id,
            )
        torch.cuda.synchronize()
        latency = time.perf_counter() - start
        token_ids = output[0, n_input:].tolist()
        eos = self.model.generation_config.eos_token_id
        eos_ids = {eos} if isinstance(eos, int) else set(eos or [])
        capped = len(token_ids) >= 4 and token_ids[-1] not in eos_ids
        raw = tokenizer.decode(token_ids, skip_special_tokens=True)
        status, label = parse(raw, capped=capped)
        winner = (first if label == "A" else second) if label else None
        record = {
            **request,
            "phase": phase,
            "attempt": attempt,
            "raw": raw,
            "status": status,
            "label": label,
            "winner": winner,
            "utc": now(),
            "seed": seed,
            "input_token_ids": encoded["input_ids"][0].tolist(),
            "input_token_sha256": digest(encoded["input_ids"][0].tolist()),
            "output_token_ids": token_ids,
            "raw_sha256": digest(raw),
            "retained_query_tokens": len(query_tokens),
            "retained_document_tokens": {d: len(tokens) for d, tokens in document_tokens.items()},
            "input_tokens": n_input,
            "output_tokens": len(token_ids),
            "capped": capped,
            "latency_s": latency,
            "model_revision": MODEL_REVISION,
        }
        self.connection.execute(
            "INSERT INTO responses VALUES(?,?,?,?)",
            (request["id"], phase, row["uid"], canonical(record)),
        )
        self.connection.execute(
            "UPDATE attempts SET disposition='recorded' WHERE attempt=?", (attempt,)
        )
        self.connection.commit()
        self.counters[phase] += 1
        if phase == "evaluation":
            self.statuses[status] += 1
        self.runtime["gpu_peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
        self.runtime["gpu_peak_reserved_bytes"] = torch.cuda.max_memory_reserved()
        self.heartbeat()
        if sum(self.counters.values()) % 24 == 0:
            print(
                canonical(
                    {
                        "event": "progress",
                        "phase": phase,
                        "responses": dict(self.counters),
                        "completed_queries": self.completed_queries,
                    }
                ),
                flush=True,
            )
        if phase == "evaluation" and self.counters[phase] >= 100:
            invalid = sum(n for name, n in self.statuses.items() if name.startswith("invalid"))
            if (
                invalid / self.counters[phase] > 0.05
                or self.statuses["abstention"] / self.counters[phase] > 0.20
            ):
                raise RuntimeError("Label-blind main validity/abstention stopping boundary reached")

    def validate(self):
        self.phase = "instrument_validation"
        rows = [json.loads(line) for line in (self.run / "inputs/development.jsonl").open()]
        for row in rows:
            self.uid = row["uid"]
            for request in requests_for(row, development=True):
                self.collect_one(row, request, "development")
        for row in json.loads((self.run / "inputs/SEMANTIC_CONTROLS.json").read_text()):
            for request in control_requests(row):
                self.collect_one(row, request, "development")
        # Natural forward passes (repeats included) only. No evaluation labels opened.
        sys.path.insert(0, str(WORKTREE / "src"))
        report = gate_report(
            response_rows(self.connection, "development"),
            self.manifest,
            self.runtime,
            self.charged_s(),
        )
        report.update(
            {
                "utc": now(),
                "manifest_sha256": self.manifest_hash,
                "code_sha256": source_hashes(),
                "gate_identity": digest(report),
            }
        )
        atomic(self.run / "INSTRUMENT_VALIDATION.json", report)
        print(
            canonical(
                {
                    "event": "validation_gate",
                    "pass": report["gate_pass"],
                    "failed_checks": report["failed_checks"],
                }
            ),
            flush=True,
        )
        return report

    def main_collection(self, report):
        if not report["gate_pass"] or report["manifest_sha256"] != self.manifest_hash:
            raise RuntimeError("Main collection requires passed identity-bound gate")
        if report["code_sha256"] != source_hashes():
            raise RuntimeError("Code changed after gate")
        for name, expected in self.manifest["reused_core_sha256"].items():
            if filehash(WORKTREE / name) != expected:
                raise RuntimeError("Reused implementation changed after gate: " + name)
        launch_path = self.run / "MAIN_LAUNCH.json"
        if not launch_path.exists():
            estimate = report["estimated_remaining_wall_s_with_1_5x_allowance"]
            atomic(
                launch_path,
                {
                    "utc": now(),
                    "pid": os.getpid(),
                    "host": os.uname().nodename,
                    "instrument_validation_sha256": filehash(
                        self.run / "INSTRUMENT_VALIDATION.json"
                    ),
                    "manifest_sha256": self.manifest_hash,
                    "expected_remaining_wall_s": estimate,
                    "expected_completion_utc": (
                        datetime.now(timezone.utc) + timedelta(seconds=estimate)
                    ).isoformat(),
                },
            )
        self.phase = "main_collecting"
        self.heartbeat()
        for line in (self.run / "inputs/evaluation.jsonl").open():
            row = json.loads(line)
            self.uid = row["uid"]
            if compute_pids() - {os.getpid()}:
                raise RuntimeError("Unrelated GPU activity detected; stopping own campaign")
            for request in requests_for(row):
                self.collect_one(row, request, "evaluation")
            current = response_rows(self.connection, "evaluation", row["uid"])
            pairs = collections.defaultdict(list)
            for record in current:
                pairs[tuple(record["pair"])].append(record)
            if len(pairs) >= 30:
                corroborated = sum(
                    paired_disposition(records)[0] == "corroborated" for records in pairs.values()
                )
                if corroborated / len(pairs) < 0.60:
                    raise RuntimeError("Label-blind main corroboration stopping boundary reached")
            self.check_budget()
            path = self.run / "results" / (digest(row["uid"]) + ".json")
            if not path.exists():
                self.phase = "query_evaluation"
                self.heartbeat()
                subprocess.run(
                    [
                        self.manifest["analysis_python"],
                        "-m",
                        "experiments.jdsa_prospective_v1.analyze",
                        "--run",
                        str(self.run),
                        "--uid",
                        row["uid"],
                    ],
                    cwd=WORKTREE,
                    check=True,
                    timeout=100,
                    stdout=subprocess.DEVNULL,
                )
                self.completed_queries += 1
            self.phase = "main_collecting"
            self.heartbeat()
            disk_bytes = sum(p.stat().st_size for p in self.run.rglob("*") if p.is_file())
            if disk_bytes > self.manifest["max_new_disk_bytes"]:
                raise RuntimeError("New-run disk budget exhausted")
        self.phase = "final_analysis"
        self.heartbeat()
        subprocess.run(
            [
                self.manifest["analysis_python"],
                "-m",
                "experiments.jdsa_prospective_v1.analyze",
                "--run",
                str(self.run),
                "--summarize",
            ],
            cwd=WORKTREE,
            check=True,
            timeout=1200,
            stdout=subprocess.DEVNULL,
        )
        self.phase = "complete"
        self.heartbeat("COMPLETED_SUCCESS")

    def close(self):
        self.connection.execute(
            "UPDATE sessions SET charged_s=?,closed=1 WHERE id=?",
            (time.monotonic() - self.started, self.session),
        )
        self.connection.commit()
        self.connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--validation-only", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    worker = None

    def terminate(_signum, _frame):
        raise RuntimeError("Own campaign received a stop/timeout signal")

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    try:
        worker = Worker(args.run, resume=args.resume)
        worker.load_model()
        path = args.run / "INSTRUMENT_VALIDATION.json"
        report = json.loads(path.read_text()) if path.exists() else worker.validate()
        if not report["gate_pass"]:
            worker.phase = "instrument_gate_failed_no_main_launch"
            worker.heartbeat("FAILED")
            return 2
        if args.validation_only:
            worker.phase = "instrument_gate_passed_validation_only"
            worker.heartbeat("COMPLETED_SUCCESS")
            return 0
        worker.main_collection(report)
        return 0
    except Exception as error:
        atomic(
            args.run / "FAILURE.json",
            {"utc": now(), "type": type(error).__name__, "reason": str(error), "pid": os.getpid()},
        )
        if worker is not None:
            worker.heartbeat("FAILED")
        print(
            canonical({"event": "failed", "type": type(error).__name__, "reason": str(error)}),
            flush=True,
        )
        return 1
    finally:
        if worker is not None:
            worker.close()


if __name__ == "__main__":
    raise SystemExit(main())
