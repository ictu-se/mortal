#!/usr/bin/env python3
"""Aggregate SimiloLLM Ollama results into manuscript-ready tables."""

from __future__ import annotations

import csv
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "pilot_outputs" / "similo_ollama"
RAW = OUT / "similo_ollama_raw.csv"
SUMMARY = OUT / "similo_ollama_summary.csv"
ROBUSTNESS = OUT / "similo_ollama_robustness.csv"
FLAKINESS = OUT / "similo_ollama_flakiness.csv"
COST = OUT / "similo_ollama_cost_effectiveness.csv"
CI = OUT / "similo_ollama_statistical_ci.csv"
COMPARISON = OUT / "similo_ollama_model_comparison.csv"
REPORT = OUT / "SIMILO_OLLAMA_FULL_RUN_RESULTS_VI.md"
CROSS_DOMAIN = ROOT / "pilot_outputs" / "CROSS_DOMAIN_EVIDENCE_FOR_Q1_VI.md"

BOOTSTRAP_ROUNDS = 2000
RANDOM_SEED = 20260430


def f(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "") or 0)
    except ValueError:
        return 0.0


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def q(sorted_values: list[float], value: float) -> float:
    if not sorted_values:
        return 0.0
    pos = (len(sorted_values) - 1) * value
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[lo]
    weight = pos - lo
    return sorted_values[lo] * (1 - weight) + sorted_values[hi] * weight


def bootstrap_ci(values: list[float]) -> tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(RANDOM_SEED + len(values) + int(sum(values) * 10000))
    n = len(values)
    samples = []
    for _ in range(BOOTSTRAP_ROUNDS):
        samples.append(mean([values[rng.randrange(n)] for _ in range(n)]))
    samples.sort()
    return mean(values), q(samples, 0.025), q(samples, 0.975)


def z_test(success_a: int, total_a: int, success_b: int, total_b: int) -> float:
    if total_a == 0 or total_b == 0:
        return 1.0
    pooled = (success_a + success_b) / (total_a + total_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / total_a + 1 / total_b))
    if se == 0:
        return 1.0
    z = ((success_a / total_a) - (success_b / total_b)) / se
    return math.erfc(abs(z) / math.sqrt(2))


def holm(p_values: list[float]) -> list[float]:
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [1.0] * len(p_values)
    running = 0.0
    m = len(p_values)
    for rank, (idx, p_value) in enumerate(indexed):
        value = min(1.0, (m - rank) * p_value)
        running = max(running, value)
        adjusted[idx] = running
    return adjusted


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def r4(value: float) -> float:
    return round(value, 4)


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"Missing raw file: {RAW}")
    rows = list(csv.DictReader(RAW.open(encoding="utf-8")))
    by_condition: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    by_case_variant: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    by_case_model: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_condition[(row["model"], row["variant"])].append(row)
        by_case_variant[(row["model"], row["case_id"], row["variant"])].append(row)
        by_case_model[(row["model"], row["case_id"])].append(row)

    summary_rows = []
    for (model, variant), group in sorted(by_condition.items()):
        calls = len(group)
        correct = sum(int(f(row, "exact_match")) for row in group)
        failures = calls - correct
        total_latency = sum(f(row, "client_elapsed_ms") for row in group)
        total_tokens = sum(f(row, "prompt_eval_count") + f(row, "eval_count") for row in group)
        summary_rows.append(
            {
                "model": model,
                "variant": variant,
                "calls": calls,
                "json_validity": r4(mean([f(row, "json_ok") for row in group])),
                "schema_validity": r4(mean([f(row, "schema_ok") for row in group])),
                "candidate_index_validity": r4(mean([f(row, "candidate_index_valid") for row in group])),
                "top_k_recall_ceiling": r4(mean([f(row, "oracle_in_top_k") for row in group])),
                "accuracy": r4(correct / calls if calls else 0.0),
                "valid_but_wrong_rate": r4(mean([f(row, "valid_but_wrong") for row in group])),
                "failure_rate": r4(failures / calls if calls else 0.0),
                "median_latency_ms": round(median([f(row, "client_elapsed_ms") for row in group]), 2),
                "avg_latency_ms": round(mean([f(row, "client_elapsed_ms") for row in group]), 2),
                "avg_tokens": round(total_tokens / calls, 2) if calls else 0,
                "ms_per_correct": round(total_latency / correct, 2) if correct else "",
                "tokens_per_correct": round(total_tokens / correct, 2) if correct else "",
            }
        )
    write_csv(SUMMARY, list(summary_rows[0].keys()), summary_rows)

    robustness_rows = []
    for model in sorted({row["model"] for row in rows}):
        original = by_condition.get((model, "original"), [])
        original_accuracy = mean([f(row, "exact_match") for row in original])
        for variant in ["paraphrase", "noise"]:
            group = by_condition.get((model, variant), [])
            if not group:
                continue
            accuracy = mean([f(row, "exact_match") for row in group])
            robustness_rows.append(
                {
                    "model": model,
                    "perturbation": variant,
                    "original_accuracy": r4(original_accuracy),
                    "perturbed_accuracy": r4(accuracy),
                    "accuracy_drop": r4(original_accuracy - accuracy),
                }
            )
        consistency = []
        violations = []
        for (m, case_id), case_group in by_case_model.items():
            if m != model:
                continue
            variant_means = []
            for variant in ["original", "paraphrase", "noise"]:
                vals = [f(row, "exact_match") for row in by_case_variant.get((m, case_id, variant), [])]
                if vals:
                    variant_means.append(mean(vals))
            if len(variant_means) == 3:
                spread = max(variant_means) - min(variant_means)
                consistency.append(1.0 - spread)
                violations.append(1.0 if spread > 0.34 else 0.0)
        robustness_rows.append(
            {
                "model": model,
                "perturbation": "cross_variant",
                "original_accuracy": "",
                "perturbed_accuracy": "",
                "accuracy_drop": "",
                "consistency_rate": r4(mean(consistency)),
                "metamorphic_violation_rate_proxy": r4(mean(violations)),
            }
        )
    write_csv(
        ROBUSTNESS,
        [
            "model",
            "perturbation",
            "original_accuracy",
            "perturbed_accuracy",
            "accuracy_drop",
            "consistency_rate",
            "metamorphic_violation_rate_proxy",
        ],
        robustness_rows,
    )

    flakiness_rows = []
    for (model, case_id, variant), group in sorted(by_case_variant.items()):
        passes = sum(int(f(row, "exact_match")) for row in group)
        if passes == len(group):
            status = "stable_pass"
        elif passes == 0:
            status = "stable_fail"
        else:
            status = "flaky"
        flakiness_rows.append(
            {
                "model": model,
                "case_id": case_id,
                "variant": variant,
                "runs": len(group),
                "correct": passes,
                "incorrect": len(group) - passes,
                "status": status,
            }
        )
    write_csv(FLAKINESS, list(flakiness_rows[0].keys()), flakiness_rows)

    cost_rows = []
    for row in summary_rows:
        cost_rows.append(
            {
                "model": row["model"],
                "variant": row["variant"],
                "calls": row["calls"],
                "median_latency_ms": row["median_latency_ms"],
                "avg_latency_ms": row["avg_latency_ms"],
                "avg_tokens": row["avg_tokens"],
                "accuracy": row["accuracy"],
                "ms_per_correct": row["ms_per_correct"],
                "tokens_per_correct": row["tokens_per_correct"],
            }
        )
    write_csv(COST, list(cost_rows[0].keys()), cost_rows)

    ci_rows = []
    for (model, variant), group in sorted(by_condition.items()):
        metrics = {
            "json_validity": [f(row, "json_ok") for row in group],
            "schema_validity": [f(row, "schema_ok") for row in group],
            "candidate_index_validity": [f(row, "candidate_index_valid") for row in group],
            "top_k_recall_ceiling": [f(row, "oracle_in_top_k") for row in group],
            "accuracy": [f(row, "exact_match") for row in group],
            "valid_but_wrong_rate": [f(row, "valid_but_wrong") for row in group],
        }
        for metric, values in metrics.items():
            estimate, low, high = bootstrap_ci(values)
            ci_rows.append(
                {
                    "model": model,
                    "variant": variant,
                    "metric": metric,
                    "n": len(values),
                    "estimate": r4(estimate),
                    "ci95_low": r4(low),
                    "ci95_high": r4(high),
                }
            )
    write_csv(CI, list(ci_rows[0].keys()), ci_rows)

    original_groups = {model: by_condition[(model, "original")] for model, variant in by_condition if variant == "original"}
    pairs = [
        ("qwen2.5-coder:14b", "qwen2.5-coder:7b"),
        ("qwen2.5-coder:7b", "qwen2.5-coder:1.5b"),
        ("qwen2.5-coder:14b", "qwen2.5-coder:1.5b"),
    ]
    temp = []
    p_values = []
    for a, b in pairs:
        if a not in original_groups or b not in original_groups:
            continue
        ga = original_groups[a]
        gb = original_groups[b]
        sa = sum(int(f(row, "exact_match")) for row in ga)
        sb = sum(int(f(row, "exact_match")) for row in gb)
        p = z_test(sa, len(ga), sb, len(gb))
        p_values.append(p)
        temp.append(
            {
                "model_a": a,
                "model_b": b,
                "variant": "original",
                "metric": "accuracy",
                "mean_a": r4(sa / len(ga) if ga else 0.0),
                "mean_b": r4(sb / len(gb) if gb else 0.0),
                "delta_a_minus_b": r4((sa / len(ga) if ga else 0.0) - (sb / len(gb) if gb else 0.0)),
                "p_value": round(p, 6),
            }
        )
    adjusted = holm(p_values)
    for row, p_adj in zip(temp, adjusted):
        row["holm_p"] = round(p_adj, 6)
    if temp:
        write_csv(COMPARISON, list(temp[0].keys()), temp)

    status_counts = defaultdict(lambda: defaultdict(int))
    for row in flakiness_rows:
        status_counts[row["model"]][row["status"]] += 1

    report = [
        "# Ket qua full-run SimiloLLM bang Ollama",
        "",
        f"Raw rows hien co: {len(rows)}. Full plan target neu day du: 804 cases x 3 variants x 3 models x 3 repeats = 21,708 calls.",
        "",
        "## Main Summary",
        "",
        "| Model | Variant | Calls | JSON | Schema | Index valid | Top-k recall | Accuracy | Valid-wrong | Median ms | ms/correct |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        report.append(
            f"| {row['model']} | {row['variant']} | {row['calls']} | {row['json_validity']} | {row['schema_validity']} | {row['candidate_index_validity']} | {row['top_k_recall_ceiling']} | {row['accuracy']} | {row['valid_but_wrong_rate']} | {row['median_latency_ms']} | {row['ms_per_correct']} |"
        )

    report.extend(
        [
            "",
            "## Accuracy CI",
            "",
            "| Model | Variant | n | Accuracy | 95% CI |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in ci_rows:
        if row["metric"] == "accuracy":
            report.append(
                f"| {row['model']} | {row['variant']} | {row['n']} | {row['estimate']} | [{row['ci95_low']}, {row['ci95_high']}] |"
            )

    report.extend(
        [
            "",
            "## Robustness",
            "",
            "| Model | Perturbation | Original | Perturbed | Drop | Consistency | Metamorphic violation proxy |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in robustness_rows:
        report.append(
            f"| {row['model']} | {row['perturbation']} | {row.get('original_accuracy', '')} | {row.get('perturbed_accuracy', '')} | {row.get('accuracy_drop', '')} | {row.get('consistency_rate', '')} | {row.get('metamorphic_violation_rate_proxy', '')} |"
        )

    report.extend(
        [
            "",
            "## Flakiness",
            "",
            "| Model | Stable pass | Flaky | Stable fail |",
            "|---|---:|---:|---:|",
        ]
    )
    for model, counts in sorted(status_counts.items()):
        report.append(
            f"| {model} | {counts['stable_pass']} | {counts['flaky']} | {counts['stable_fail']} |"
        )

    report.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Day la domain thu hai chay cung protocol voi ULT Lite: structured output, oracle ro, perturbation, repeat va cost.",
            "- `top_k_recall_ceiling` can duoc bao cao rieng vi LLM chi co the dung neu deterministic prefilter dua oracle vao candidate set.",
            "- `valid_but_wrong_rate` la loi semantic chinh cua domain nay: model tra JSON hop le va index hop le nhung chon sai element.",
            "- Neu raw rows chua dat 21,708 thi day la partial/resumable run; tiep tuc chay script se skip rows da co.",
        ]
    )
    REPORT.write_text("\n".join(report), encoding="utf-8")

    cross_domain = [
        "# Cross-Domain Evidence Cho Huong Bai Q1",
        "",
        "File nay da duoc cap nhat de xem SimiloLLM la domain thuc nghiem thu hai khi `similo_ollama_raw.csv` co du lieu tu local Ollama.",
        "",
        "## Domain 1: Unit Test Generation / ULT Lite",
        "",
        "- 200 ULT Lite tasks x 3 variants x 3 repeats x 3 models = 5,400 calls.",
        "- Co validity, correctness, robustness, flakiness, cost va mutation-based fault detection.",
        "",
        "## Domain 2: Web Element Localization / SimiloLLM",
        "",
        f"- Current raw rows: {len(rows)}.",
        "- Full target: 804 cases x 3 variants x 3 repeats x 3 models = 21,708 calls.",
        "- Oracle: exact match voi migrated target XPath trong `oracles.txt`.",
        "",
        "### SimiloLLM current summary",
        "",
        "| Model | Variant | Calls | Accuracy | Top-k recall | Index valid | Median ms |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        cross_domain.append(
            f"| {row['model']} | {row['variant']} | {row['calls']} | {row['accuracy']} | {row['top_k_recall_ceiling']} | {row['candidate_index_validity']} | {row['median_latency_ms']} |"
        )
    cross_domain.extend(
        [
            "",
            "## Readiness judgement",
            "",
            "- Khi SimiloLLM dat full target, bai se co 2 main domains chay cung protocol.",
            "- Neu run chua full target, bao cao nay la interim evidence va can tiep tuc resume.",
        ]
    )
    CROSS_DOMAIN.write_text("\n".join(cross_domain), encoding="utf-8")

    print(f"Wrote {SUMMARY}")
    print(f"Wrote {ROBUSTNESS}")
    print(f"Wrote {FLAKINESS}")
    print(f"Wrote {COST}")
    print(f"Wrote {CI}")
    if temp:
        print(f"Wrote {COMPARISON}")
    print(f"Wrote {REPORT}")
    print(f"Wrote {CROSS_DOMAIN}")


if __name__ == "__main__":
    main()
