#!/usr/bin/env python3
"""Aggregate ULT Lite Ollama raw results into manuscript-ready metrics."""

from __future__ import annotations

import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path


BASE = Path(__file__).resolve().parent / "pilot_outputs" / "ollama_ult_lite"
RAW = BASE / "ollama_ult_lite_raw.csv"
SUMMARY = BASE / "ollama_ult_lite_extended_metrics.csv"
ROBUSTNESS = BASE / "ollama_ult_lite_robustness.csv"
FLAKINESS = BASE / "ollama_ult_lite_flakiness.csv"
FAILURES = BASE / "ollama_ult_lite_failure_taxonomy.csv"
REPORT = BASE / "OLLAMA_ULT_LITE_EXTENDED_METRICS_VI.md"


def f(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "") or 0)
    except ValueError:
        return 0.0


def full_pass(row: dict[str, str]) -> bool:
    return f(row, "schema_ok") == 1.0 and f(row, "exec_pass_rate") == 1.0


def parse_success(row: dict[str, str]) -> bool:
    return f(row, "json_ok") == 1.0 and not (row.get("parse_error") or "").strip()


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


def stdev(values: list[float]) -> float:
    return statistics.pstdev(values) if len(values) > 1 else 0.0


def pct(value: float) -> str:
    return f"{value:.4f}"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = list(csv.DictReader(RAW.open()))
    for row in rows:
        row["_full_pass"] = "1" if full_pass(row) else "0"
        row["_failure_type"] = failure_type(row)

    by_model_variant: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    by_model: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_model_task_variant: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    by_model_task_repeat: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    by_model_task: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        by_model_variant[(row["model"], row["variant"])].append(row)
        by_model[row["model"]].append(row)
        by_model_task_variant[(row["model"], row["task_id"], row["variant"])].append(row)
        by_model_task_repeat[(row["model"], row["task_id"], row["repeat"])].append(row)
        by_model_task[(row["model"], row["task_id"])].append(row)

    summary_rows: list[dict[str, object]] = []
    for (model, variant), group in sorted(by_model_variant.items()):
        calls = len(group)
        full_passes = sum(full_pass(row) for row in group)
        any_positive = sum(f(row, "exec_pass_rate") > 0 for row in group)
        detected_failures = sum(row["_failure_type"] != "none" for row in group)
        total_latency = sum(f(row, "client_elapsed_ms") for row in group)
        total_tokens = sum(f(row, "prompt_eval_count") + f(row, "eval_count") for row in group)
        pass_at_3_groups = [
            any(full_pass(row) for row in task_group)
            for key, task_group in by_model_task_variant.items()
            if key[0] == model and key[2] == variant
        ]
        summary_rows.append(
            {
                "model": model,
                "variant": variant,
                "calls": calls,
                "json_validity": pct(mean([f(row, "json_ok") for row in group])),
                "schema_validity": pct(mean([f(row, "schema_ok") for row in group])),
                "parse_success": pct(mean([1.0 if parse_success(row) else 0.0 for row in group])),
                "compile_success": pct(mean([f(row, "syntax_rate") for row in group])),
                "executable_rate": pct(mean([1.0 if f(row, "exec_total_tests") > 0 else 0.0 for row in group])),
                "assertion_success": pct(mean([f(row, "exec_pass_rate") for row in group])),
                "full_pass_call_rate": pct(full_passes / calls if calls else 0.0),
                "pass_at_3_proxy": pct(mean([1.0 if ok else 0.0 for ok in pass_at_3_groups])),
                "positive_execution_rate": pct(any_positive / calls if calls else 0.0),
                "target_call_rate": pct(mean([f(row, "target_function_call_rate") for row in group])),
                "oracle_violation_rate": pct(detected_failures / calls if calls else 0.0),
                "avg_latency_ms": round(mean([f(row, "client_elapsed_ms") for row in group]), 2),
                "p95_latency_ms": round(sorted([f(row, "client_elapsed_ms") for row in group])[int(0.95 * calls) - 1], 2),
                "avg_tokens": round(mean([f(row, "prompt_eval_count") + f(row, "eval_count") for row in group]), 2),
                "avg_tokens_per_second": round(mean([f(row, "eval_tokens_per_second") for row in group]), 2),
                "ms_per_full_pass": round(total_latency / full_passes, 2) if full_passes else "",
                "tokens_per_full_pass": round(total_tokens / full_passes, 2) if full_passes else "",
                "ms_per_detected_failure": round(total_latency / detected_failures, 2) if detected_failures else "",
            }
        )

    write_csv(
        SUMMARY,
        [
            "model",
            "variant",
            "calls",
            "json_validity",
            "schema_validity",
            "parse_success",
            "compile_success",
            "executable_rate",
            "assertion_success",
            "full_pass_call_rate",
            "pass_at_3_proxy",
            "positive_execution_rate",
            "target_call_rate",
            "oracle_violation_rate",
            "avg_latency_ms",
            "p95_latency_ms",
            "avg_tokens",
            "avg_tokens_per_second",
            "ms_per_full_pass",
            "tokens_per_full_pass",
            "ms_per_detected_failure",
        ],
        summary_rows,
    )

    robustness_rows: list[dict[str, object]] = []
    for model, group in sorted(by_model.items()):
        variant_groups = defaultdict(list)
        for row in group:
            variant_groups[row["variant"]].append(row)
        original_exec = mean([f(row, "exec_pass_rate") for row in variant_groups["original"]])
        original_full = mean([1.0 if full_pass(row) else 0.0 for row in variant_groups["original"]])
        for variant in ["paraphrase", "noise"]:
            vgroup = variant_groups[variant]
            exec_rate = mean([f(row, "exec_pass_rate") for row in vgroup])
            full_rate = mean([1.0 if full_pass(row) else 0.0 for row in vgroup])
            robustness_rows.append(
                {
                    "model": model,
                    "perturbation": variant,
                    "original_assertion_success": pct(original_exec),
                    "perturbed_assertion_success": pct(exec_rate),
                    "assertion_success_drop": pct(original_exec - exec_rate),
                    "original_full_pass_rate": pct(original_full),
                    "perturbed_full_pass_rate": pct(full_rate),
                    "full_pass_drop": pct(original_full - full_rate),
                }
            )

    for model in sorted(by_model):
        task_consistency = []
        repeat_consistency = []
        metamorphic_violations = []
        for (m, task_id), task_group in by_model_task.items():
            if m != model:
                continue
            by_variant = defaultdict(list)
            for row in task_group:
                by_variant[row["variant"]].append(f(row, "exec_pass_rate"))
            if all(v in by_variant for v in ["original", "paraphrase", "noise"]):
                means = [mean(by_variant[v]) for v in ["original", "paraphrase", "noise"]]
                task_consistency.append(1.0 - (max(means) - min(means)))
                metamorphic_violations.append(1.0 if max(means) - min(means) > 0.2 else 0.0)
        for (m, task_id, repeat), repeat_group in by_model_task_repeat.items():
            if m != model or len(repeat_group) < 3:
                continue
            statuses = [full_pass(row) for row in repeat_group]
            repeat_consistency.append(1.0 if all(status == statuses[0] for status in statuses) else 0.0)
        robustness_rows.append(
            {
                "model": model,
                "perturbation": "cross_variant",
                "original_assertion_success": "",
                "perturbed_assertion_success": "",
                "assertion_success_drop": "",
                "original_full_pass_rate": "",
                "perturbed_full_pass_rate": "",
                "full_pass_drop": "",
                "consistency_rate": pct(mean(task_consistency)),
                "metamorphic_violation_rate_proxy": pct(mean(metamorphic_violations)),
                "same_repeat_agreement_rate": pct(mean(repeat_consistency)),
            }
        )

    write_csv(
        ROBUSTNESS,
        [
            "model",
            "perturbation",
            "original_assertion_success",
            "perturbed_assertion_success",
            "assertion_success_drop",
            "original_full_pass_rate",
            "perturbed_full_pass_rate",
            "full_pass_drop",
            "consistency_rate",
            "metamorphic_violation_rate_proxy",
            "same_repeat_agreement_rate",
        ],
        robustness_rows,
    )

    flakiness_rows: list[dict[str, object]] = []
    for (model, task_id, variant), group in sorted(by_model_task_variant.items()):
        passes = sum(full_pass(row) for row in group)
        if passes == len(group):
            status = "stable_pass"
        elif passes == 0:
            status = "stable_fail"
        else:
            status = "flaky"
        flakiness_rows.append(
            {
                "model": model,
                "task_id": task_id,
                "variant": variant,
                "runs": len(group),
                "passes": passes,
                "failures": len(group) - passes,
                "exec_pass_rate_mean": pct(mean([f(row, "exec_pass_rate") for row in group])),
                "exec_pass_rate_std": pct(stdev([f(row, "exec_pass_rate") for row in group])),
                "status": status,
            }
        )
    write_csv(
        FLAKINESS,
        [
            "model",
            "task_id",
            "variant",
            "runs",
            "passes",
            "failures",
            "exec_pass_rate_mean",
            "exec_pass_rate_std",
            "status",
        ],
        flakiness_rows,
    )

    failure_rows: list[dict[str, object]] = []
    for (model, variant), group in sorted(by_model_variant.items()):
        counts = Counter(row["_failure_type"] for row in group)
        for ftype, count in sorted(counts.items()):
            if ftype == "none":
                continue
            failure_rows.append(
                {
                    "model": model,
                    "variant": variant,
                    "failure_type": ftype,
                    "count": count,
                    "rate": pct(count / len(group)),
                }
            )
    write_csv(FAILURES, ["model", "variant", "failure_type", "count", "rate"], failure_rows)

    status_counts = Counter(row["status"] for row in flakiness_rows)
    model_status = defaultdict(Counter)
    for row in flakiness_rows:
        model_status[row["model"]][row["status"]] += 1

    report = [
        "# Tong hop metric mo rong cho Ollama ULT Lite",
        "",
        "Du lieu: 200 task ULT Lite x 3 bien the (original/paraphrase/noise) x 3 lan lap x 3 model = 5,400 luot goi.",
        "",
        "Luu y ve fault detection: ULT Lite hien tai khong co seeded mutants/buggy implementations trong pipeline nay. Vi vay cac metric fault detection ben duoi la proxy dua tren oracle violation va failure type cua generated tests; de do dung failure detection rate that su can them buoc mutation testing hoac buggy-program injection.",
        "",
        "## Bang metric chinh",
        "",
        "| Model | Variant | Schema | Parse | Compile | Assertion success | Full-pass | pass@3 proxy | Oracle violation | Avg latency ms | P95 latency ms | ms/full-pass |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        report.append(
            f"| {row['model']} | {row['variant']} | {row['schema_validity']} | {row['parse_success']} | {row['compile_success']} | {row['assertion_success']} | {row['full_pass_call_rate']} | {row['pass_at_3_proxy']} | {row['oracle_violation_rate']} | {row['avg_latency_ms']} | {row['p95_latency_ms']} | {row['ms_per_full_pass']} |"
        )

    report.extend(
        [
            "",
            "## Robustness",
            "",
            "| Model | Perturbation | Assertion drop | Full-pass drop | Consistency | Metamorphic violation proxy | Same-repeat agreement |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in robustness_rows:
        report.append(
            f"| {row['model']} | {row['perturbation']} | {row.get('assertion_success_drop', '')} | {row.get('full_pass_drop', '')} | {row.get('consistency_rate', '')} | {row.get('metamorphic_violation_rate_proxy', '')} | {row.get('same_repeat_agreement_rate', '')} |"
        )

    report.extend(
        [
            "",
            "## Reliability / Stability",
            "",
            "| Model | Stable pass | Flaky | Stable fail | Flaky rate |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for model in sorted(model_status):
        total = sum(model_status[model].values())
        report.append(
            f"| {model} | {model_status[model]['stable_pass']} | {model_status[model]['flaky']} | {model_status[model]['stable_fail']} | {model_status[model]['flaky'] / total:.4f} |"
        )

    report.extend(
        [
            "",
            "## Failure taxonomy proxy",
            "",
            "| Model | Variant | Failure type | Count | Rate |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in failure_rows:
        report.append(f"| {row['model']} | {row['variant']} | {row['failure_type']} | {row['count']} | {row['rate']} |")

    report.extend(
        [
            "",
            "## Dien giai nhanh",
            "",
            "- Validity: 7B va 14B gan nhu dat tran ve JSON/schema; 1.5B yeu hon ro, dac biet voi paraphrase.",
            "- Correctness: 14B co assertion-success cao nhat, nhung full-pass van thap; day la bang chung rang format dung khong dong nghia voi oracle dung.",
            "- Robustness: drop giua original va paraphrase/noise can duoc bao cao rieng, vi mot so model co schema on dinh nhung semantic consistency kem.",
            "- Reliability: flakiness nen bao cao theo task-variant, khong chi theo call trung binh.",
            "- Cost: 14B tang chat luong nhung latency/tokens per successful full-pass tang manh; day la trade-off chinh cho bai bao.",
            "- Fault detection: can bo sung mutation/bug injection neu muon dung thuat ngu failure detection rate theo nghia nghiem ngat.",
            "",
        ]
    )

    REPORT.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {SUMMARY}")
    print(f"Wrote {ROBUSTNESS}")
    print(f"Wrote {FLAKINESS}")
    print(f"Wrote {FAILURES}")
    print(f"Wrote {REPORT}")
    print(f"status_counts={dict(status_counts)}")


if __name__ == "__main__":
    main()
