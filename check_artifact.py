#!/usr/bin/env python3
"""Lightweight structural checks for the MORTAL artifact."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent

REQUIRED_FILES = [
    "README.md",
    "requirements.txt",
    "run_ollama_ult_lite_experiment.py",
    "run_similo_ollama_experiment.py",
    "analyze_ollama_ult_lite_metrics.py",
    "analyze_ollama_mutation_detection.py",
    "analyze_q1_readiness_stats.py",
    "analyze_similo_ollama_results.py",
    "build_cross_domain_evidence.py",
    "pilot_outputs/ollama_ult_lite/ollama_ult_lite_raw.csv",
    "pilot_outputs/ollama_ult_lite/ollama_ult_lite_extended_metrics.csv",
    "pilot_outputs/ollama_ult_lite/ollama_ult_lite_mutation_detection_summary.csv",
    "pilot_outputs/similo_ollama/similo_ollama_raw.csv",
    "pilot_outputs/similo_ollama/similo_ollama_summary.csv",
]


def require(path: str) -> Path:
    file_path = ROOT / path
    if not file_path.exists():
        raise SystemExit(f"Missing required file: {path}")
    return file_path


def count_rows(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> None:
    for path in REQUIRED_FILES:
        require(path)

    ult_rows = count_rows(ROOT / "pilot_outputs/ollama_ult_lite/ollama_ult_lite_raw.csv")
    similo_rows = count_rows(ROOT / "pilot_outputs/similo_ollama/similo_ollama_raw.csv")
    if ult_rows != 5400:
        raise SystemExit(f"Unexpected ULT raw row count: {ult_rows} (expected 5400)")
    if similo_rows != 21708:
        raise SystemExit(f"Unexpected Similo raw row count: {similo_rows} (expected 21708)")

    print("Artifact check passed.")
    print(f"ULT Lite raw rows: {ult_rows}")
    print(f"SimiloLLM raw rows: {similo_rows}")


if __name__ == "__main__":
    main()

