#!/usr/bin/env python3
"""Run local Ollama models on the ULT Lite unit-test-generation task.

The script is resume-safe: existing model/task/variant/repeat rows in the raw
CSV are skipped. Place the ULT Lite dataset at
`reproduction_datasets/UnLeakedTestBench/datasets/ULT_Lite.jsonl`.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import multiprocessing as mp
import statistics
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
DATA = BASE / "reproduction_datasets"
OUT = BASE / "pilot_outputs" / "ollama_ult_lite"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


VARIANT_SUFFIXES = {
    "original": "",
    "paraphrase": (
        "\nRewrite the tests for the same intent even if the wording is different. "
        "Do not change the function under test."
    ),
    "noise": (
        "\nIgnore this irrelevant context: the project also contains logging, UI, "
        "and database utilities. Only test the given function."
    ),
}


def load_tasks(limit: int) -> list[dict[str, Any]]:
    path = DATA / "UnLeakedTestBench" / "datasets" / "ULT_Lite.jsonl"
    with path.open(encoding="utf-8") as f:
        return json.load(f)[:limit]


def build_prompt(task: dict[str, Any], variant: str) -> str:
    suffix = VARIANT_SUFFIXES[variant]
    return f"""Generate Python unit test assertions for the function below.

Return only valid JSON with this exact schema:
{{"tests": ["assert ...", "assert ..."]}}

Rules:
- produce 3 to 5 Python assert statements
- each assert must call function `{task["func_name"]}`
- do not use pytest, unittest, imports, markdown, or explanations
- keep the assertions executable with the provided function

Function description:
{task["prompt"]}

Function code:
```python
{task["code"]}
```
{suffix}
"""


def call_ollama(model: str, prompt: str, temperature: float, request_timeout: float) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "top_p": 1.0,
            "num_ctx": 4096,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=request_timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Ollama server is not reachable at {OLLAMA_URL}: {exc}") from exc
    elapsed_ms = (time.perf_counter() - start) * 1000
    result = json.loads(raw)
    result["client_elapsed_ms"] = elapsed_ms
    return result


def parse_tests(raw_response: str) -> tuple[bool, bool, list[str], str]:
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        return False, False, [], f"json_error:{exc.msg}"

    tests = parsed.get("tests") if isinstance(parsed, dict) else None
    if not isinstance(tests, list):
        return True, False, [], "schema_error:tests_not_list"

    clean_tests = [x.strip() for x in tests if isinstance(x, str) and x.strip()][:5]
    if not clean_tests:
        return True, False, [], "schema_error:no_tests"
    return True, True, clean_tests, ""


def check_test_syntax(tests: list[str]) -> tuple[int, int]:
    ok = 0
    for test in tests:
        try:
            ast.parse(test)
            ok += 1
        except SyntaxError:
            pass
    return ok, len(tests)


def execute_tests(code: str, tests: list[str]) -> tuple[int, int, str]:
    passed = 0
    first_error = ""
    for test in tests:
        queue: mp.Queue[str] = mp.Queue()
        process = mp.Process(target=execute_one_test, args=(code, test, queue))
        process.start()
        process.join(1.5)
        if process.is_alive():
            process.terminate()
            process.join()
            result = "timeout"
        else:
            result = queue.get() if not queue.empty() else "no_result"
        if result == "pass":
            passed += 1
        elif not first_error:
            first_error = result
    return passed, len(tests), first_error


def execute_one_test(code: str, test: str, queue: mp.Queue[str]) -> None:
    namespace: dict[str, Any] = {}
    try:
        exec(code, namespace)
        exec(test, namespace)
        queue.put("pass")
    except Exception as exc:
        queue.put(type(exc).__name__)


def evaluate_response(task: dict[str, Any], raw_response: str) -> dict[str, Any]:
    json_ok, schema_ok, tests, parse_error = parse_tests(raw_response)
    syntax_ok, syntax_total = check_test_syntax(tests)
    exec_passed, exec_total, exec_error = execute_tests(task["code"], tests)
    func_name = task["func_name"]
    calls_target = sum(1 for test in tests if f"{func_name}(" in test)
    return {
        "json_ok": int(json_ok),
        "schema_ok": int(schema_ok),
        "generated_tests": len(tests),
        "syntax_ok_tests": syntax_ok,
        "syntax_total_tests": syntax_total,
        "syntax_rate": syntax_ok / syntax_total if syntax_total else 0.0,
        "exec_passed_tests": exec_passed,
        "exec_total_tests": exec_total,
        "exec_pass_rate": exec_passed / exec_total if exec_total else 0.0,
        "target_function_call_rate": calls_target / len(tests) if tests else 0.0,
        "parse_error": parse_error,
        "exec_error": exec_error,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_existing_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def as_float(row: dict[str, Any], key: str) -> float:
        value = row.get(key, 0)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["model"], row["variant"])].append(row)

    summary = []
    for (model, variant), group in sorted(grouped.items()):
        calls = len(group)
        failures = sum(
            1
            for row in group
            if as_float(row, "exec_pass_rate") < 1.0 or as_float(row, "schema_ok") == 0
        )
        summary.append(
            {
                "model": model,
                "variant": variant,
                "calls": calls,
                "json_validity": round(statistics.mean(as_float(row, "json_ok") for row in group), 4),
                "schema_validity": round(statistics.mean(as_float(row, "schema_ok") for row in group), 4),
                "avg_generated_tests": round(statistics.mean(as_float(row, "generated_tests") for row in group), 2),
                "syntax_rate": round(statistics.mean(as_float(row, "syntax_rate") for row in group), 4),
                "execution_pass_rate": round(statistics.mean(as_float(row, "exec_pass_rate") for row in group), 4),
                "target_function_call_rate": round(
                    statistics.mean(as_float(row, "target_function_call_rate") for row in group), 4
                ),
                "failure_rate": round(failures / calls if calls else 0.0, 4),
                "avg_latency_ms": round(statistics.mean(as_float(row, "client_elapsed_ms") for row in group), 2),
                "avg_prompt_tokens": round(statistics.mean(as_float(row, "prompt_eval_count") for row in group), 2),
                "avg_output_tokens": round(statistics.mean(as_float(row, "eval_count") for row in group), 2),
                "avg_tokens_per_second": round(
                    statistics.mean(as_float(row, "eval_tokens_per_second") for row in group), 2
                ),
            }
        )
    return summary


def markdown_table(rows: list[dict[str, Any]]) -> str:
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5-coder:1.5b")
    parser.add_argument(
        "--models",
        default="",
        help="Comma-separated model list. Overrides --model when provided.",
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--request-timeout", type=float, default=30.0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    tasks = load_tasks(args.limit)
    raw_path = OUT / "ollama_ult_lite_raw.csv"
    rows: list[dict[str, Any]] = read_existing_rows(raw_path) if args.resume else []
    models = [m.strip() for m in args.models.split(",") if m.strip()] or [args.model]
    done = {
        (row.get("model", ""), str(row["task_id"]), row["variant"], str(row["repeat"]))
        for row in rows
    }
    if rows:
        print(f"Resuming with {len(rows)} existing rows.", flush=True)

    for model in models:
        for task in tasks:
            for variant in VARIANT_SUFFIXES:
                for repeat in range(args.repeats):
                    key = (model, str(task["task_id"]), variant, str(repeat))
                    if key in done:
                        continue
                    prompt = build_prompt(task, variant)
                    call_start = time.perf_counter()
                    try:
                        result = call_ollama(model, prompt, args.temperature, args.request_timeout)
                    except Exception as exc:
                        result = {
                            "response": "",
                            "client_elapsed_ms": (time.perf_counter() - call_start) * 1000,
                            "prompt_eval_count": 0,
                            "eval_count": 0,
                            "eval_duration": 0,
                            "error": f"{type(exc).__name__}:{exc}",
                        }
                    response = result.get("response", "")
                    eval_row = evaluate_response(task, response)
                    eval_tokens = result.get("eval_count", 0) or 0
                    eval_duration_ns = result.get("eval_duration", 0) or 0
                    eval_tps = eval_tokens / (eval_duration_ns / 1_000_000_000) if eval_duration_ns else 0.0
                    rows.append(
                        {
                            "model": model,
                            "task_id": task["task_id"],
                            "func_name": task["func_name"],
                            "variant": variant,
                            "repeat": repeat,
                            "temperature": args.temperature,
                            "client_elapsed_ms": round(result["client_elapsed_ms"], 2),
                            "prompt_eval_count": result.get("prompt_eval_count", 0),
                            "eval_count": eval_tokens,
                            "eval_tokens_per_second": round(eval_tps, 2),
                            **eval_row,
                            "raw_response": response.replace("\n", "\\n"),
                        }
                    )
                    done.add(key)
                    if len(rows) % args.checkpoint_every == 0:
                        summary = aggregate(rows)
                        write_csv(OUT / "ollama_ult_lite_raw.csv", rows)
                        write_csv(OUT / "ollama_ult_lite_summary.csv", summary)
                    print(
                        f"{model} task={task['task_id']} variant={variant} repeat={repeat} "
                        f"schema={eval_row['schema_ok']} exec={eval_row['exec_pass_rate']:.2f} "
                        f"latency={result['client_elapsed_ms']:.0f}ms",
                        flush=True,
                    )

    summary = aggregate(rows)
    write_csv(OUT / "ollama_ult_lite_raw.csv", rows)
    write_csv(OUT / "ollama_ult_lite_summary.csv", summary)

    report = f"""# Ollama ULT_Lite Local Experiment

Models: `{", ".join(models)}`

Dataset: `UnLeakedTestBench/datasets/ULT_Lite.jsonl`

Scope:

- seed tasks: {args.limit}
- variants per task: {len(VARIANT_SUFFIXES)}
- repeats per condition: {args.repeats}
- total calls: {len(rows)}
- temperature: {args.temperature}

## Aggregate Results

{markdown_table(summary)}

## Interpretation

- `json_validity` and `schema_validity` measure whether the model obeyed the required structured-output contract.
- `syntax_rate` measures whether generated assertion strings parse as Python.
- `execution_pass_rate` measures whether generated assertions execute against the provided reference implementation.
- `failure_rate` counts calls with schema failure or at least one generated assertion failing at execution time.
- `avg_latency_ms`, token counts, and token/s support the cost-effectiveness table in the IMRAD draft.

This is a small local pilot, not a final full run. It is suitable for filling the first local-data table and deciding whether to scale to 14B/32B models.
"""
    (OUT / "OLLAMA_ULT_LITE_RESULTS.md").write_text(report, encoding="utf-8")
    print(f"Wrote {OUT / 'OLLAMA_ULT_LITE_RESULTS.md'}")


if __name__ == "__main__":
    main()
