#!/usr/bin/env python3
"""Build a compact cross-domain evidence report from generated CSV tables."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PILOT = ROOT / "pilot_outputs"
ULT = PILOT / "ollama_ult_lite"
SIMILO = PILOT / "similo_ollama"
REPORT = PILOT / "CROSS_DOMAIN_EVIDENCE_FOR_Q1_VI.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"Missing required input: {path}")
    return list(csv.DictReader(path.open(encoding="utf-8")))


def main() -> None:
    ult_summary = read_csv(ULT / "ollama_ult_lite_extended_metrics.csv")
    ult_mutation = read_csv(ULT / "ollama_ult_lite_mutation_detection_summary.csv")
    similo_summary = read_csv(SIMILO / "similo_ollama_summary.csv")

    lines = [
        "# Cross-Domain Evidence Summary",
        "",
        "This report is generated from the artifact CSV files. It summarizes the two",
        "main empirical domains used by MORTAL: ULT Lite unit test generation and",
        "SimiloLLM web element localization.",
        "",
        "## Domain 1: ULT Lite Unit Test Generation",
        "",
        "| Model | Variant | Calls | Schema | Assertion success | Strict suite | Positive execution |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in ult_summary:
        lines.append(
            f"| {row['model']} | {row['variant']} | {row['calls']} | {row['schema_validity']} | "
            f"{row['assertion_success']} | {row['full_pass_call_rate']} | {row['positive_execution_rate']} |"
        )

    lines.extend(
        [
            "",
            "### ULT Lite Mutation Detection",
            "",
            "| Model | Variant | Evaluations | Failure detection | Unique mutant detection | Ref-usable rate |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in ult_mutation:
        lines.append(
            f"| {row['model']} | {row['variant']} | {row['mutation_evaluations']} | "
            f"{row['failure_detection_rate']} | {row['unique_mutant_detection_rate']} | {row['ref_usable_rate']} |"
        )

    lines.extend(
        [
            "",
            "## Domain 2: SimiloLLM Web Element Localization",
            "",
            "| Model | Variant | Calls | Index valid | Top-k recall | Accuracy | Valid but wrong |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in similo_summary:
        lines.append(
            f"| {row['model']} | {row['variant']} | {row['calls']} | {row['candidate_index_validity']} | "
            f"{row['top_k_recall_ceiling']} | {row['accuracy']} | {row['valid_but_wrong_rate']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- ULT Lite stresses executable and fault-detection oracles.",
            "- SimiloLLM stresses valid structured decisions and exact target matching.",
            "- The two domains show why schema validity, semantic correctness, robustness, stability, and cost should be reported separately.",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
