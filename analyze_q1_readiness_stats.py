#!/usr/bin/env python3
"""Q1-readiness statistics and ablation tables for the Ollama ULT Lite study."""

from __future__ import annotations

import csv
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "pilot_outputs" / "ollama_ult_lite"
RAW = OUT / "ollama_ult_lite_raw.csv"
MUTATION_SUMMARY = OUT / "ollama_ult_lite_mutation_detection_summary.csv"

STAT_CI = OUT / "ollama_ult_lite_statistical_ci.csv"
ABLATION = OUT / "ollama_ult_lite_oracle_ablation.csv"
COST = OUT / "ollama_ult_lite_cost_effectiveness.csv"
MODEL_COMPARISON = OUT / "ollama_ult_lite_model_comparison.csv"
REPORT = OUT / "Q1_READY_STATISTICS_AND_ABLATION_VI.md"
ULT_RUNBOOK = OUT / "ULT_LITE_RUNBOOK.md"

BOOTSTRAP_ROUNDS = 2000
RANDOM_SEED = 20260430


def f(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "") or 0)
    except ValueError:
        return 0.0


def full_pass(row: dict[str, str]) -> int:
    return int(f(row, "schema_ok") == 1.0 and f(row, "exec_pass_rate") == 1.0)


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


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    position = (len(sorted_values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def bootstrap_ci(values: list[float], rounds: int = BOOTSTRAP_ROUNDS) -> tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(RANDOM_SEED + len(values) + int(sum(values) * 10000))
    n = len(values)
    observed = mean(values)
    samples = []
    for _ in range(rounds):
        samples.append(mean([values[rng.randrange(n)] for _ in range(n)]))
    samples.sort()
    return observed, quantile(samples, 0.025), quantile(samples, 0.975)


def proportion_z_test(success_a: int, total_a: int, success_b: int, total_b: int) -> float:
    if total_a == 0 or total_b == 0:
        return 1.0
    pooled = (success_a + success_b) / (total_a + total_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / total_a + 1 / total_b))
    if se == 0:
        return 1.0
    z = ((success_a / total_a) - (success_b / total_b)) / se
    return math.erfc(abs(z) / math.sqrt(2))


def vargha_delaney_a12(values_a: list[float], values_b: list[float]) -> float:
    if not values_a or not values_b:
        return 0.5
    wins = 0.0
    for a in values_a:
        for b in values_b:
            if a > b:
                wins += 1
            elif a == b:
                wins += 0.5
    return wins / (len(values_a) * len(values_b))


def holm_adjust(p_values: list[float]) -> list[float]:
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
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def round4(value: float) -> float:
    return round(value, 4)


def main() -> None:
    rows = list(csv.DictReader(RAW.open(encoding="utf-8")))
    mutation_rows = list(csv.DictReader(MUTATION_SUMMARY.open(encoding="utf-8")))
    for row in rows:
        row["_failure_type"] = failure_type(row)
        row["_full_pass"] = str(full_pass(row))

    by_condition: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    by_model_original: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_condition[(row["model"], row["variant"])].append(row)
        if row["variant"] == "original":
            by_model_original[row["model"]].append(row)

    ci_rows: list[dict[str, Any]] = []
    metric_extractors = {
        "schema_validity": lambda r: f(r, "schema_ok"),
        "parse_success": lambda r: 1.0 if f(r, "json_ok") == 1.0 and not (r.get("parse_error") or "").strip() else 0.0,
        "compile_success": lambda r: f(r, "syntax_rate"),
        "assertion_success": lambda r: f(r, "exec_pass_rate"),
        "full_pass": lambda r: float(full_pass(r)),
        "oracle_violation": lambda r: 1.0 if r["_failure_type"] != "none" else 0.0,
    }
    for (model, variant), group in sorted(by_condition.items()):
        for metric, extractor in metric_extractors.items():
            values = [extractor(row) for row in group]
            observed, low, high = bootstrap_ci(values)
            ci_rows.append(
                {
                    "model": model,
                    "variant": variant,
                    "metric": metric,
                    "n": len(values),
                    "estimate": round4(observed),
                    "ci95_low": round4(low),
                    "ci95_high": round4(high),
                }
            )

    write_csv(STAT_CI, ["model", "variant", "metric", "n", "estimate", "ci95_low", "ci95_high"], ci_rows)

    ablation_rows: list[dict[str, Any]] = []
    oracle_order = [
        ("schema_only", {"invalid_json", "schema_no_tests", "schema_error"}),
        ("schema_plus_syntax", {"invalid_json", "schema_no_tests", "schema_error", "syntax_error"}),
        (
            "schema_syntax_execution",
            {
                "invalid_json",
                "schema_no_tests",
                "schema_error",
                "syntax_error",
                "missing_target_call",
                "AssertionError",
                "assertion_failure",
                "NameError",
                "TypeError",
                "ValueError",
                "IndexError",
                "KeyError",
            },
        ),
    ]
    for (model, variant), group in sorted(by_condition.items()):
        previous = 0
        for oracle_name, detectable in oracle_order:
            detected = sum(1 for row in group if row["_failure_type"] in detectable)
            ablation_rows.append(
                {
                    "model": model,
                    "variant": variant,
                    "oracle_setting": oracle_name,
                    "calls": len(group),
                    "failures_detected": detected,
                    "failure_rate": round4(detected / len(group) if group else 0.0),
                    "incremental_failures": detected - previous,
                    "incremental_rate": round4((detected - previous) / len(group) if group else 0.0),
                }
            )
            previous = detected

    write_csv(
        ABLATION,
        [
            "model",
            "variant",
            "oracle_setting",
            "calls",
            "failures_detected",
            "failure_rate",
            "incremental_failures",
            "incremental_rate",
        ],
        ablation_rows,
    )

    mutation_by_condition = {(r["model"], r["variant"]): r for r in mutation_rows}
    cost_rows: list[dict[str, Any]] = []
    for (model, variant), group in sorted(by_condition.items()):
        total_latency = sum(f(row, "client_elapsed_ms") for row in group)
        total_tokens = sum(f(row, "prompt_eval_count") + f(row, "eval_count") for row in group)
        full_passes = sum(full_pass(row) for row in group)
        oracle_failures = sum(1 for row in group if row["_failure_type"] != "none")
        mut = mutation_by_condition.get((model, variant), {})
        killed = int(float(mut.get("killed_evaluations", 0) or 0))
        cost_rows.append(
            {
                "model": model,
                "variant": variant,
                "calls": len(group),
                "total_latency_ms": round(total_latency, 2),
                "median_latency_ms": round(median([f(row, "client_elapsed_ms") for row in group]), 2),
                "total_tokens": int(total_tokens),
                "avg_tokens": round(total_tokens / len(group), 2) if group else 0,
                "full_passes": full_passes,
                "oracle_failures": oracle_failures,
                "mutation_killed_evaluations": killed,
                "ms_per_full_pass": round(total_latency / full_passes, 2) if full_passes else "",
                "tokens_per_full_pass": round(total_tokens / full_passes, 2) if full_passes else "",
                "ms_per_oracle_failure": round(total_latency / oracle_failures, 2) if oracle_failures else "",
                "tokens_per_oracle_failure": round(total_tokens / oracle_failures, 2) if oracle_failures else "",
                "ms_per_killed_mutation_eval": round(total_latency / killed, 2) if killed else "",
                "tokens_per_killed_mutation_eval": round(total_tokens / killed, 2) if killed else "",
            }
        )

    write_csv(
        COST,
        [
            "model",
            "variant",
            "calls",
            "total_latency_ms",
            "median_latency_ms",
            "total_tokens",
            "avg_tokens",
            "full_passes",
            "oracle_failures",
            "mutation_killed_evaluations",
            "ms_per_full_pass",
            "tokens_per_full_pass",
            "ms_per_oracle_failure",
            "tokens_per_oracle_failure",
            "ms_per_killed_mutation_eval",
            "tokens_per_killed_mutation_eval",
        ],
        cost_rows,
    )

    comparison_pairs = [
        ("qwen2.5-coder:14b", "qwen2.5-coder:7b"),
        ("qwen2.5-coder:7b", "qwen2.5-coder:1.5b"),
        ("qwen2.5-coder:14b", "qwen2.5-coder:1.5b"),
    ]
    comparison_rows: list[dict[str, Any]] = []
    p_values = []
    temp_rows = []
    for model_a, model_b in comparison_pairs:
        group_a = by_model_original.get(model_a, [])
        group_b = by_model_original.get(model_b, [])
        for metric, extractor in {
            "assertion_success": lambda r: f(r, "exec_pass_rate"),
            "full_pass": lambda r: float(full_pass(r)),
            "latency_ms": lambda r: f(r, "client_elapsed_ms"),
        }.items():
            values_a = [extractor(row) for row in group_a]
            values_b = [extractor(row) for row in group_b]
            if metric == "full_pass":
                p_value = proportion_z_test(int(sum(values_a)), len(values_a), int(sum(values_b)), len(values_b))
            else:
                # Normal approximation on proportions is only used for binary full-pass;
                # for continuous values we report A12 and leave p-values descriptive.
                p_value = 1.0
            p_values.append(p_value)
            temp_rows.append(
                {
                    "model_a": model_a,
                    "model_b": model_b,
                    "variant": "original",
                    "metric": metric,
                    "mean_a": round4(mean(values_a)),
                    "mean_b": round4(mean(values_b)),
                    "delta_a_minus_b": round4(mean(values_a) - mean(values_b)),
                    "a12_a_greater_b": round4(vargha_delaney_a12(values_a, values_b)),
                    "p_value": round(p_value, 6),
                }
            )
    adjusted = holm_adjust(p_values)
    for row, p_adj in zip(temp_rows, adjusted):
        row["holm_p"] = round(p_adj, 6)
        comparison_rows.append(row)

    write_csv(
        MODEL_COMPARISON,
        [
            "model_a",
            "model_b",
            "variant",
            "metric",
            "mean_a",
            "mean_b",
            "delta_a_minus_b",
            "a12_a_greater_b",
            "p_value",
            "holm_p",
        ],
        comparison_rows,
    )

    def rows_for_metric(metric: str) -> list[dict[str, Any]]:
        return [row for row in ci_rows if row["metric"] == metric]

    report = [
        "# Thong ke, Oracle Ablation va Cost Cho ULT Lite",
        "",
        "Bao cao nay bo sung cac bang can thiet de dua study tu pilot sang dang gan voi chuan Q1/STVR hon.",
        "",
        "## 1. 95% Bootstrap Confidence Intervals",
        "",
        "Bootstrap 2,000 vong tren tung condition model x variant. Bang day nen dua vao appendix; manuscript chinh chi can trich cac metric quan trong.",
        "",
        "### Full-pass CI",
        "",
        "| Model | Variant | n | Estimate | 95% CI |",
        "|---|---|---:|---:|---:|",
    ]
    for row in rows_for_metric("full_pass"):
        report.append(
            f"| {row['model']} | {row['variant']} | {row['n']} | {row['estimate']} | [{row['ci95_low']}, {row['ci95_high']}] |"
        )
    report.extend(
        [
            "",
            "### Assertion-success CI",
            "",
            "| Model | Variant | n | Estimate | 95% CI |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in rows_for_metric("assertion_success"):
        report.append(
            f"| {row['model']} | {row['variant']} | {row['n']} | {row['estimate']} | [{row['ci95_low']}, {row['ci95_high']}] |"
        )

    report.extend(
        [
            "",
            "## 2. Oracle Ablation",
            "",
            "Bang nay tra loi cau hoi: neu chi dung schema-only thi bo sot bao nhieu failure so voi them syntax/execution oracle.",
            "",
            "| Model | Variant | Oracle | Failures | Rate | Increment |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in ablation_rows:
        report.append(
            f"| {row['model']} | {row['variant']} | {row['oracle_setting']} | {row['failures_detected']} | {row['failure_rate']} | {row['incremental_failures']} |"
        )

    report.extend(
        [
            "",
            "## 3. Cost-Effectiveness",
            "",
            "| Model | Variant | Median ms/call | Full passes | ms/full-pass | Oracle failures | ms/oracle failure | Mutation kills | ms/killed mutation eval |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in cost_rows:
        report.append(
            f"| {row['model']} | {row['variant']} | {row['median_latency_ms']} | {row['full_passes']} | {row['ms_per_full_pass']} | {row['oracle_failures']} | {row['ms_per_oracle_failure']} | {row['mutation_killed_evaluations']} | {row['ms_per_killed_mutation_eval']} |"
        )

    report.extend(
        [
            "",
            "## 4. Model Comparison Tren Original Variant",
            "",
            "| A | B | Metric | Mean A | Mean B | Delta | A12 | Holm p |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in comparison_rows:
        report.append(
            f"| {row['model_a']} | {row['model_b']} | {row['metric']} | {row['mean_a']} | {row['mean_b']} | {row['delta_a_minus_b']} | {row['a12_a_greater_b']} | {row['holm_p']} |"
        )

    report.extend(
        [
            "",
            "## 5. Dien giai de dua vao bai",
            "",
            "- Schema/parse gan dat tran voi 7B va 14B, nen schema-only khong du de danh gia reliability.",
            "- Execution oracle la phan dong gop lon nhat trong failure detection, vi da so loi la assertion/semantic failure chu khong phai format failure.",
            "- 14B co assertion-success va mutation detection tot nhat, nhung chi phi latency/full-pass cao; nen trinh bay nhu trade-off reliability-cost.",
            "- CI cho full-pass van hep do n=600 moi condition, nhung full-pass tuyet doi thap; day la finding quan trong: output hop le khong dong nghia output dung.",
            "- Phan statistical nay moi ap dung cho ULT Lite; de nop Q1 van can them domain thu hai hoac giai thich ro scope reproducible local study.",
            "",
            "## Generated Files",
            "",
            f"- `{STAT_CI.name}`",
            f"- `{ABLATION.name}`",
            f"- `{COST.name}`",
            f"- `{MODEL_COMPARISON.name}`",
        ]
    )
    REPORT.write_text("\n".join(report), encoding="utf-8")

    artifact = [
        "# ULT Lite Analysis Runbook",
        "",
        "This report documents the ULT Lite analysis path for the MORTAL artifact.",
        "",
        "## Directory Layout",
        "",
        "- `run_ollama_ult_lite_experiment.py`: runs local Ollama models on ULT Lite.",
        "- `analyze_ollama_ult_lite_metrics.py`: aggregates validity, correctness, robustness, reliability, cost and failure taxonomy.",
        "- `analyze_ollama_mutation_detection.py`: generates synthetic mutants and evaluates generated tests against them.",
        "- `analyze_q1_readiness_stats.py`: computes bootstrap confidence intervals, oracle ablation, cost-effectiveness and model comparisons.",
        "- `pilot_outputs/ollama_ult_lite/`: raw outputs and generated tables.",
        "",
        "## Reproduction Commands",
        "",
        "Run from the artifact root:",
        "",
        "```bash",
        "python3 analyze_ollama_ult_lite_metrics.py",
        "python3 analyze_ollama_mutation_detection.py",
        "python3 analyze_q1_readiness_stats.py",
        "```",
        "",
        "To reproduce raw LLM calls, ensure Ollama is running and the required models are installed, then run:",
        "",
        "```bash",
        "python3 run_ollama_ult_lite_experiment.py",
        "```",
        "",
        "## Frozen Configuration",
        "",
        "- Dataset: ULT Lite, 200 tasks.",
        "- Variants: original, paraphrase, noise.",
        "- Repeats: 3.",
        "- Models in current raw output: `qwen2.5-coder:1.5b`, `qwen2.5-coder:7b`, `qwen2.5-coder:14b`.",
        "- Raw calls: 5,400.",
        "",
        "## Main Expected Outputs",
        "",
        "- `ollama_ult_lite_raw.csv`: raw model responses and evaluator fields.",
        "- `OLLAMA_ULT_LITE_EXTENDED_METRICS_VI.md`: main metric summary.",
        "- `OLLAMA_ULT_LITE_MUTATION_DETECTION_VI.md`: mutation-based fault detection summary.",
        "- `Q1_READY_STATISTICS_AND_ABLATION_VI.md`: CI, ablation, cost and model comparison tables.",
        "",
        "## Limitation",
        "",
        "The full artifact includes ULT Lite and SimiloLLM. This runbook only covers ULT Lite-specific analysis.",
    ]
    ULT_RUNBOOK.write_text("\n".join(artifact), encoding="utf-8")

    print(f"Wrote {STAT_CI}")
    print(f"Wrote {ABLATION}")
    print(f"Wrote {COST}")
    print(f"Wrote {MODEL_COMPARISON}")
    print(f"Wrote {REPORT}")
    print(f"Wrote {ULT_RUNBOOK}")


if __name__ == "__main__":
    main()
