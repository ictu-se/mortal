#!/usr/bin/env python3
"""Prepare a stratified manual-validation sample for ULT Lite outputs."""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "pilot_outputs" / "ollama_ult_lite"
RAW = OUT / "ollama_ult_lite_raw.csv"
MUTATION_RAW = OUT / "ollama_ult_lite_mutation_detection_raw.csv"
SAMPLE = OUT / "manual_validation_sample_ult_lite.csv"
PROTOCOL = OUT / "MANUAL_VALIDATION_PROTOCOL_VI.md"

RANDOM_SEED = 20260430


def f(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "") or 0)
    except ValueError:
        return 0.0


def full_pass(row: dict[str, str]) -> bool:
    return f(row, "schema_ok") == 1.0 and f(row, "exec_pass_rate") == 1.0


def failure_type(row: dict[str, str]) -> str:
    parse_error = (row.get("parse_error") or "").strip()
    exec_error = (row.get("exec_error") or "").strip()
    if f(row, "json_ok") == 0:
        return "invalid_json"
    if f(row, "schema_ok") == 0:
        if "no_tests" in parse_error:
            return "schema_no_tests"
        return "schema_error"
    if f(row, "syntax_rate") < 1.0:
        return "syntax_error"
    if f(row, "target_function_call_rate") < 1.0:
        return "missing_target_call"
    if f(row, "exec_pass_rate") < 1.0:
        return exec_error or "assertion_failure"
    return "none"


def clean_response(text: str, limit: int = 1200) -> str:
    text = (text or "").replace("\r", "")
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def pick(rows: list[dict[str, Any]], n: int, rng: random.Random) -> list[dict[str, Any]]:
    if len(rows) <= n:
        return list(rows)
    return rng.sample(rows, n)


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    raw_rows = list(csv.DictReader(RAW.open(encoding="utf-8")))
    mut_rows = list(csv.DictReader(MUTATION_RAW.open(encoding="utf-8")))

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        row = dict(row)
        row["_failure_type"] = failure_type(row)
        if full_pass(row):
            buckets["full_pass"].append(row)
        elif row["_failure_type"] in {"invalid_json", "schema_no_tests", "schema_error"}:
            buckets["format_schema_failure"].append(row)
        elif row["_failure_type"] == "syntax_error":
            buckets["syntax_failure"].append(row)
        elif row["_failure_type"] == "missing_target_call":
            buckets["missing_target_call"].append(row)
        elif row["_failure_type"] != "none":
            buckets["semantic_execution_failure"].append(row)

    sample_rows: list[dict[str, Any]] = []
    allocation = {
        "format_schema_failure": 40,
        "syntax_failure": 40,
        "semantic_execution_failure": 80,
        "missing_target_call": 20,
        "full_pass": 40,
    }
    for bucket, count in allocation.items():
        for row in pick(buckets[bucket], count, rng):
            sample_rows.append(
                {
                    "sample_type": bucket,
                    "model": row["model"],
                    "task_id": row["task_id"],
                    "func_name": row["func_name"],
                    "variant": row["variant"],
                    "repeat": row["repeat"],
                    "auto_failure_type": row["_failure_type"],
                    "exec_pass_rate": row["exec_pass_rate"],
                    "target_function_call_rate": row["target_function_call_rate"],
                    "raw_response_excerpt": clean_response(row.get("raw_response", "")),
                    "annotator_label": "",
                    "annotator_confidence_1_5": "",
                    "notes": "",
                }
            )

    killed = [row for row in mut_rows if row.get("killed") == "1"]
    for row in pick(killed, 50, rng):
        sample_rows.append(
            {
                "sample_type": "mutation_killed",
                "model": row["model"],
                "task_id": row["task_id"],
                "func_name": "",
                "variant": row["variant"],
                "repeat": row["repeat"],
                "auto_failure_type": row["mutation_type"],
                "exec_pass_rate": row["ref_pass_rate"],
                "target_function_call_rate": "",
                "raw_response_excerpt": f"mutant_id={row['mutant_id']}; killed_tests={row['killed_tests']}; first_error={row['mutant_first_error']}",
                "annotator_label": "",
                "annotator_confidence_1_5": "",
                "notes": "",
            }
        )

    fieldnames = [
        "sample_type",
        "model",
        "task_id",
        "func_name",
        "variant",
        "repeat",
        "auto_failure_type",
        "exec_pass_rate",
        "target_function_call_rate",
        "raw_response_excerpt",
        "annotator_label",
        "annotator_confidence_1_5",
        "notes",
    ]
    with SAMPLE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_rows)

    protocol = [
        "# Quy trinh manual validation cho ULT Lite",
        "",
        f"File can annotate: `{SAMPLE.name}`.",
        "",
        "Muc tieu: kiem tra xem auto-oracle va failure taxonomy co dang tin khong, va tao bang manual taxonomy cho manuscript.",
        "",
        "## Mau duoc lay",
        "",
        "| Sample type | Target count | Y nghia |",
        "|---|---:|---|",
        "| format_schema_failure | 40 | Loi JSON/schema |",
        "| syntax_failure | 40 | Assertion/code khong parse/compile |",
        "| semantic_execution_failure | 80 | Assertion chay duoc nhung sai oracle |",
        "| missing_target_call | toi da 20 | Test khong goi ham can test |",
        "| full_pass | 40 | Mau doi chung pass day du |",
        "| mutation_killed | 50 | Generated tests kill synthetic mutant |",
        "",
        "## Label nen dung",
        "",
        "| Label | Mo ta |",
        "|---|---|",
        "| correct_failure | Auto oracle dung, day la failure that |",
        "| false_positive | Auto oracle bao fail nhung manual thay chap nhan duoc |",
        "| weak_test | Test pass/fail nhung qua yeu, khong kiem tra hanh vi quan trong |",
        "| wrong_oracle | Assertion ky vong sai voi dac ta/reference |",
        "| non_executable | Output khong the chay hop le |",
        "| format_error | Output sai JSON/schema |",
        "| hallucinated_entity | Goi bien/ham/entity khong ton tai |",
        "| mutation_valid_kill | Mutant kill hop ly |",
        "| mutation_questionable | Mutant/test kill khong co y nghia ro |",
        "",
        "## Cach bao cao",
        "",
        "- Can it nhat 2 annotators neu co the.",
        "- Bao cao agreement: percent agreement hoac Cohen's kappa.",
        "- Dua 3-5 vi du failure representative vao paper.",
        "- Neu chi co 1 annotator, dua vao threats to validity.",
    ]
    PROTOCOL.write_text("\n".join(protocol), encoding="utf-8")

    print(f"Wrote {SAMPLE} ({len(sample_rows)} rows)")
    print(f"Wrote {PROTOCOL}")


if __name__ == "__main__":
    main()
