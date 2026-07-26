"""Live judge adapter: Action → MultiProviderJudge with cell lock + shared cache."""

from __future__ import annotations

import csv
import json
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from consistency_ranker.multi_provider_eval.providers import MultiProviderJudge
from consistency_ranker.multi_provider_eval.spending import SpendingCeiling
from consistency_ranker.multifactor_acquisition.pricing import estimate_usd
from consistency_ranker.reliability_repair.pair_evidence import (
    NormalizedEvidence,
    canonical_pair_id,
    normalize_judgment_record,
)


@dataclass
class AccountingCounters:
    """Separated skip / failure / success accounting."""

    http_ok: int = 0
    transport_failures: int = 0
    auth_failures: int = 0
    rate_limits: int = 0
    parse_failures: int = 0
    content_filter_refusals: int = 0
    missing_doc_text_skips: int = 0
    unavailable_pair_skips: int = 0
    completed_judgments: int = 0
    incomplete_policy_requests: int = 0


@dataclass
class CircuitState:
    consecutive_auth_failures: int = 0
    recent_attempts: deque = field(default_factory=lambda: deque(maxlen=50))
    # Only HTTP-OK responses that returned model content intended for parsing.
    recent_http_ok_malformed: deque = field(default_factory=lambda: deque(maxlen=50))
    broken: bool = False
    reason: str | None = None
    accounting: AccountingCounters = field(default_factory=AccountingCounters)


@dataclass
class CellLock:
    provider: str
    model: str
    prompt_version: str
    orientation: Literal["ab", "ba"]
    query_id: str
    query_text: str
    doc_texts: dict[str, str]
    max_unique_calls: int = 20
    effective_depth: int | None = None


class LiveCellJudge:
    """Shared judgment cache for one factor cell; remaps actions to the cell lock.

    Unique external judgments are capped at ``max_unique_calls``. Cache hits across
    policies do not re-bill. Wrong-orientation reverse cells are separate LiveCellJudge
    instances (never reuse ab as ba).
    """

    def __init__(
        self,
        *,
        cell: CellLock,
        mp_judge: MultiProviderJudge,
        cost_ledger_path: Path,
        raw_path: Path,
        parsed_path: Path,
        failures_path: Path,
        circuit: CircuitState,
        provider_spend: dict[str, float],
        provider_spend_cap: float,
        global_spend_cap: float,
        global_spend: list[float],
        consumers_log_path: Path,
        skips_path: Path | None = None,
    ) -> None:
        self.cell = cell
        self.mp = mp_judge
        self.cost_ledger_path = cost_ledger_path
        self.raw_path = raw_path
        self.parsed_path = parsed_path
        self.failures_path = failures_path
        self.skips_path = skips_path or (failures_path.parent / "SKIPS.jsonl")
        self.circuit = circuit
        self.provider_spend = provider_spend
        self.provider_spend_cap = provider_spend_cap
        self.global_spend_cap = global_spend_cap
        self.global_spend = global_spend  # mutable singleton list [usd]
        self.consumers_log_path = consumers_log_path
        self._cache: dict[str, NormalizedEvidence] = {}
        self._lock = threading.Lock()
        self.n_unique_calls = 0
        self.n_cache_hits = 0
        self.n_requests = 0
        self.stopped_reason: str | None = None
        self.policy_consumers: dict[str, set[str]] = {}

    def preload_parsed(self, parsed_path: Path) -> int:
        """Load valid prior judgments for this cell by deterministic identity."""
        if not parsed_path.exists():
            return 0
        n = 0
        prefix = (
            f"|{self.cell.provider}|{self.cell.model}|"
            f"{self.cell.prompt_version}|{self.cell.orientation}"
        )
        with parsed_path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                identity = str(row.get("identity") or "")
                if not identity.endswith(prefix):
                    continue
                if self.cell.query_id not in identity:
                    continue
                if row.get("valid") is False:
                    continue
                # Require a usable signed preference or explicit valid flag.
                if int(row.get("z") or 0) == 0 and not row.get("valid", False):
                    continue
                ev = normalize_judgment_record(row)
                ev.displayed_orientation = self.cell.orientation
                ev.provider = self.cell.provider
                ev.model = self.cell.model
                ev.prompt_version = self.cell.prompt_version
                self._cache[identity] = ev
                n += 1
        return n

    def available(self, action) -> bool:
        if getattr(action, "action_type", None) == "NO_ACTION":
            return True
        if self.circuit.broken or self.stopped_reason:
            return False
        if self.n_unique_calls >= self.cell.max_unique_calls:
            # still available if already cached for this remapped signature
            key = self._identity(action)
            return key in self._cache
        return True

    def _identity(self, action) -> str:
        doc_i = str(action.doc_i)
        doc_j = str(action.doc_j)
        pair = canonical_pair_id(self.cell.query_id, doc_i, doc_j)
        return (
            f"{pair}|{self.cell.provider}|{self.cell.model}|"
            f"{self.cell.prompt_version}|{self.cell.orientation}"
        )

    def judge(self, action, *, consumer: str = "unknown") -> NormalizedEvidence | None:
        if getattr(action, "action_type", None) == "NO_ACTION":
            return None
        self.n_requests += 1
        key = self._identity(action)
        with self._lock:
            if key in self._cache:
                self.n_cache_hits += 1
                self.policy_consumers.setdefault(key, set()).add(consumer)
                self._append_jsonl(
                    self.consumers_log_path,
                    {
                        "identity": key,
                        "consumer": consumer,
                        "from_cache": True,
                        "ts": _utc(),
                    },
                )
                return self._cache[key]

            if self.circuit.broken:
                self.circuit.accounting.incomplete_policy_requests += 1
                return None
            if self.n_unique_calls >= self.cell.max_unique_calls:
                self.stopped_reason = self.stopped_reason or "cell_unique_call_ceiling"
                self.circuit.accounting.incomplete_policy_requests += 1
                return None
            if self.provider_spend.get(self.cell.provider, 0.0) >= self.provider_spend_cap:
                self.stopped_reason = "provider_usd_ceiling"
                self.circuit.broken = True
                self.circuit.reason = "provider_usd_ceiling"
                return None
            if self.global_spend[0] >= self.global_spend_cap:
                self.stopped_reason = "global_usd_ceiling"
                return None

            doc_a = str(action.doc_i)
            doc_b = str(action.doc_j)
            ta = self.cell.doc_texts.get(doc_a, "")
            tb = self.cell.doc_texts.get(doc_b, "")
            if not ta or not tb:
                self.circuit.accounting.missing_doc_text_skips += 1
                self._skip(
                    {
                        "reason": "missing_doc_text",
                        "category": "data_availability_skip",
                        "doc_a": doc_a,
                        "doc_b": doc_b,
                        "provider": self.cell.provider,
                        "ts": _utc(),
                    }
                )
                return None

            t0 = time.perf_counter()
            try:
                rec = self.mp.compare(
                    provider=self.cell.provider,
                    model=self.cell.model,
                    query_id=self.cell.query_id,
                    query_text=self.cell.query_text,
                    doc_a_id=doc_a,
                    doc_a_text=ta,
                    doc_b_id=doc_b,
                    doc_b_text=tb,
                    orientation=self.cell.orientation,
                    prompt_version=self.cell.prompt_version,
                    temperature=0.0,
                    seed=0,
                    repeat_index=0,
                )
            except Exception as exc:  # noqa: BLE001 — classify + circuit
                self._handle_exception(exc)
                return None

            latency = time.perf_counter() - t0
            payload = rec.to_dict() if hasattr(rec, "to_dict") else dict(rec.__dict__)
            from_cache = bool(payload.get("from_cache"))
            valid = bool(payload.get("valid"))
            pt = int(payload.get("prompt_tokens") or 0)
            ct = int(payload.get("completion_tokens") or 0)
            usd = 0.0 if from_cache else estimate_usd(self.cell.provider, pt, ct)
            choice = str(payload.get("parsed_choice") or "")

            self._append_jsonl(
                self.raw_path,
                {
                    **payload,
                    "latency_seconds": latency,
                    "estimated_cost_usd": usd,
                    "cell_identity": key,
                    "consumer": consumer,
                },
            )

            if not from_cache:
                self.n_unique_calls += 1
                self.global_spend[0] += usd
                self.provider_spend[self.cell.provider] = (
                    self.provider_spend.get(self.cell.provider, 0.0) + usd
                )
                # Transport succeeded if we have raw content or a classified parse.
                self.circuit.recent_attempts.append(True)
                self.circuit.accounting.http_ok += 1
                self.circuit.consecutive_auth_failures = 0
                raw = payload.get("raw_response")
                if raw and not valid:
                    if choice == "REFUSAL":
                        self.circuit.accounting.content_filter_refusals += 1
                    else:
                        self.circuit.accounting.parse_failures += 1
                    # Denominator: only model content intended for parsing.
                    self.circuit.recent_http_ok_malformed.append(1)
                elif raw:
                    self.circuit.accounting.completed_judgments += 1
                    self.circuit.recent_http_ok_malformed.append(0)
                self._append_csv_ledger(
                    {
                        "ts": _utc(),
                        "provider": self.cell.provider,
                        "model": self.cell.model,
                        "prompt_version": self.cell.prompt_version,
                        "orientation": self.cell.orientation,
                        "query_id": self.cell.query_id,
                        "identity": key,
                        "prompt_tokens": pt,
                        "completion_tokens": ct,
                        "estimated_usd": usd,
                        "provider_spend": self.provider_spend.get(self.cell.provider, 0.0),
                        "global_spend": self.global_spend[0],
                        "from_cache": False,
                        "valid": valid,
                    }
                )
                self._check_circuits()
            else:
                self.n_cache_hits += 1

            ev = normalize_judgment_record(payload)
            # Force displayed orientation metadata to the cell lock.
            ev.displayed_orientation = self.cell.orientation
            ev.provider = self.cell.provider
            ev.model = self.cell.model
            ev.prompt_version = self.cell.prompt_version
            self._cache[key] = ev
            self.policy_consumers.setdefault(key, set()).add(consumer)
            self._append_jsonl(
                self.parsed_path,
                {
                    **ev.to_dict(),
                    "identity": key,
                    "consumers": sorted(self.policy_consumers[key]),
                    "from_cache": from_cache,
                    "estimated_cost_usd": usd,
                    "parser_version": (payload.get("extra") or {}).get("parser_version"),
                    "output_format_category": (payload.get("extra") or {}).get(
                        "output_format_category"
                    ),
                },
            )
            self._append_jsonl(
                self.consumers_log_path,
                {
                    "identity": key,
                    "consumer": consumer,
                    "from_cache": from_cache,
                    "ts": _utc(),
                },
            )
            return ev

    def _handle_exception(self, exc: Exception) -> None:
        msg = str(exc)
        lower = msg.lower()
        auth = any(
            x in lower
            for x in ("auth", "unauthorized", "401", "403", "permission", "credential")
        )
        deploy = any(x in lower for x in ("deployment", "404", "not found", "model_not"))
        rate = "429" in lower or "rate limit" in lower
        self.circuit.recent_attempts.append(False)
        self.circuit.accounting.transport_failures += 1
        if auth or deploy:
            self.circuit.consecutive_auth_failures += 1
            self.circuit.accounting.auth_failures += 1
        if rate:
            self.circuit.accounting.rate_limits += 1
        self._fail(
            {
                "reason": "exception",
                "category": "api_transport_failure",
                "auth_like": auth or deploy,
                "error_type": type(exc).__name__,
                "error": msg[:500],
                "provider": self.cell.provider,
                "ts": _utc(),
            }
        )
        self._check_circuits()

    def _check_circuits(self) -> None:
        if self.circuit.consecutive_auth_failures >= 5:
            self.circuit.broken = True
            self.circuit.reason = "consecutive_auth_failures"
            return
        attempts = list(self.circuit.recent_attempts)
        if len(attempts) >= 20:
            err_rate = 1.0 - (sum(1 for a in attempts if a) / len(attempts))
            if err_rate > 0.20:
                self.circuit.broken = True
                self.circuit.reason = f"error_rate={err_rate:.2f}"
                return
        mal = list(self.circuit.recent_http_ok_malformed)
        # Denominator is only parseable HTTP-OK model outputs — never skips.
        if len(mal) >= 20 and (sum(mal) / len(mal)) > 0.20:
            self.circuit.broken = True
            self.circuit.reason = "malformed_output_rate"
            return
        provider = getattr(getattr(self, "cell", None), "provider", None)
        if provider is not None:
            if self.provider_spend.get(provider, 0.0) >= self.provider_spend_cap:
                self.circuit.broken = True
                self.circuit.reason = "provider_usd_ceiling"

    def _fail(self, row: dict[str, Any]) -> None:
        self._append_jsonl(self.failures_path, row)

    def _skip(self, row: dict[str, Any]) -> None:
        self._append_jsonl(self.skips_path, row)
        # Retain legacy FAILURES mirror tagged as skip for audit continuity.
        self._append_jsonl(
            self.failures_path,
            {**row, "legacy_mirror": True, "is_skip": True},
        )

    @staticmethod
    def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            fh.flush()

    def _append_csv_ledger(self, row: dict[str, Any]) -> None:
        path = self.cost_ledger_path
        path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not path.exists()
        with path.open("a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(row.keys()))
            if write_header:
                w.writeheader()
            w.writerow(row)
            fh.flush()


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_mp_judge(
    store_path: Path,
    *,
    max_calls_global: int,
    max_calls_per_provider: dict[str, int],
    max_usd_global: float,
    dry_run: bool = False,
) -> tuple[MultiProviderJudge, SpendingCeiling]:
    from consistency_ranker.multi_provider_eval.cache import ProvenanceJudgmentStore

    ceiling = SpendingCeiling(
        max_new_calls_global=max_calls_global,
        max_new_calls_per_provider=max_calls_per_provider,
        max_prompt_tokens_global=None,
        max_estimated_usd_global=max_usd_global,
    )
    store = ProvenanceJudgmentStore(store_path)
    return (
        MultiProviderJudge(
            store, ceiling, dry_run=dry_run, code_version="multifactor_acquisition_v1"
        ),
        ceiling,
    )
