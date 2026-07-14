#!/usr/bin/env python3
"""Light presentation polish: Data Availability env pointer; freeze contradictory claim language."""
from __future__ import annotations

from pathlib import Path

REPO = Path("/home/soroush/consistency-aware-llm-rankin")
MS = REPO / "papers/JDIQ_2026/manuscript/main.tex"
OUT = REPO / "reports/jdiq-overnight-cont-20260713-230229"
changes: list[str] = []

text = MS.read_text()

# Strengthen Data Availability with dependency pointer (no author URL).
old_da = (
    "\\textbf{Reproducibility.} Mechanical results in\n"
    "Sections~\\ref{sec:structural-results}--\\ref{sec:downstream-results} regenerate\n"
    "from stored intermediates with the seeds, solver settings, and eligibility rule\n"
    "in Section~\\ref{sec:experimental-setup}. Upstream retrieval and paid APIs need\n"
    "not be rerun. Stored LLM records support protocol-quality checks only."
)
new_da = (
    "\\textbf{Reproducibility.} Mechanical results in\n"
    "Sections~\\ref{sec:structural-results}--\\ref{sec:downstream-results} regenerate\n"
    "from stored intermediates with the seeds, solver settings, and eligibility rule\n"
    "in Section~\\ref{sec:experimental-setup}. Upstream retrieval and paid APIs need\n"
    "not be rerun. Stored LLM records support protocol-quality checks only. The review\n"
    "artifact includes a dependency list (\\texttt{requirements.txt}) together with\n"
    "the code snapshot used for mechanical regeneration."
)
if old_da in text:
    text = text.replace(old_da, new_da, 1)
    changes.append("data_availability_requirements_pointer")

# Soften any residual absolute overclaim if present
if "not yet performed" in text:
    changes.append("WARNING_residual_not_yet_performed")

MS.write_text(text)
(OUT / "logs" / "phase05_changes.txt").write_text("\n".join(changes) + "\n")
print("Phase 5 changes:", changes)
