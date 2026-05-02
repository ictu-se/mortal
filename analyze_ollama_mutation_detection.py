#!/usr/bin/env python3
"""Mutation-based fault detection analysis for Ollama ULT Lite outputs."""

from __future__ import annotations

import ast
import contextlib
import copy
import csv
import io
import json
import multiprocessing as mp
import signal
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "reproduction_datasets" / "UnLeakedTestBench" / "datasets" / "ULT_Lite.jsonl"
OUT = ROOT / "pilot_outputs" / "ollama_ult_lite"
RAW = OUT / "ollama_ult_lite_raw.csv"
MUTANTS = OUT / "ollama_ult_lite_synthetic_mutants.csv"
DETECTION_RAW = OUT / "ollama_ult_lite_mutation_detection_raw.csv"
DETECTION_SUMMARY = OUT / "ollama_ult_lite_mutation_detection_summary.csv"
REPORT = OUT / "OLLAMA_ULT_LITE_MUTATION_DETECTION_VI.md"


MAX_MUTANTS_PER_TASK = 3
MAX_CANDIDATES_PER_TASK = 80
TIMEOUT_SECONDS = 0.5


class AssertionTimeout(Exception):
    pass


def timeout_handler(signum: int, frame: Any) -> None:
    raise AssertionTimeout()


def run_assertions(code: str, tests: list[str], timeout: float = TIMEOUT_SECONDS) -> tuple[int, int, str]:
    if not tests:
        return 0, 0, ""
    results = [run_one_assertion_fast(code, test, timeout) for test in tests]
    passed = sum(1 for result in results if result == "pass")
    first_error = next((result for result in results if result != "pass"), "")
    return passed, len(tests), first_error


def run_assertion_batch(code: str, tests: list[str], queue: mp.Queue[list[str]]) -> None:
    results = []
    for test in tests:
        results.append(run_one_assertion_in_process(code, test))
    queue.put(results)


def run_one_assertion_in_process(code: str, test: str) -> str:
    namespace: dict[str, Any] = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            exec(code, namespace)
            exec(test, namespace)
        return "pass"
    except Exception as exc:
        return type(exc).__name__


def passing_assertions(code: str, tests: list[str], timeout: float = TIMEOUT_SECONDS) -> list[str]:
    if not tests:
        return []
    results = [run_one_assertion_fast(code, test, timeout) for test in tests]
    return [test for test, result in zip(tests, results) if result == "pass"]


def run_one_assertion_fast(code: str, test: str, timeout: float = TIMEOUT_SECONDS) -> str:
    namespace: dict[str, Any] = {}
    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            exec(code, namespace)
            exec(test, namespace)
        return "pass"
    except AssertionTimeout:
        return "timeout"
    except Exception as exc:
        return type(exc).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def run_assertions_slow(code: str, tests: list[str], timeout: float = TIMEOUT_SECONDS) -> tuple[int, int, str]:
    passed = 0
    first_error = ""
    for test in tests:
        queue: mp.Queue[str] = mp.Queue()
        process = mp.Process(target=run_one_assertion, args=(code, test, queue))
        process.start()
        process.join(timeout)
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


def run_one_assertion(code: str, test: str, queue: mp.Queue[str]) -> None:
    namespace: dict[str, Any] = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            exec(code, namespace)
            exec(test, namespace)
        queue.put("pass")
    except Exception as exc:
        queue.put(type(exc).__name__)


def parse_generated_tests(raw_response: str) -> list[str]:
    def normalize_structural_newlines(text: str) -> str:
        chars: list[str] = []
        in_string = False
        escaped = False
        i = 0
        while i < len(text):
            ch = text[i]
            if escaped:
                chars.append(ch)
                escaped = False
                i += 1
                continue
            if ch == "\\":
                if not in_string and i + 1 < len(text) and text[i + 1] == "n":
                    chars.append("\n")
                    i += 2
                    continue
                chars.append(ch)
                escaped = True
                i += 1
                continue
            if ch == '"':
                in_string = not in_string
            chars.append(ch)
            i += 1
        return "".join(chars)

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        try:
            parsed = json.loads(normalize_structural_newlines(raw_response))
        except json.JSONDecodeError:
            return []
    tests = parsed.get("tests") if isinstance(parsed, dict) else None
    if not isinstance(tests, list):
        return []
    clean = []
    for item in tests:
        if not isinstance(item, str):
            continue
        item = item.strip()
        if not item:
            continue
        try:
            ast.parse(item)
        except SyntaxError:
            continue
        clean.append(item)
    return clean[:5]


def op_name(node: ast.AST) -> str:
    return type(node).__name__


def candidate_count(tree: ast.AST) -> int:
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and node.ops:
            count += 1
        elif isinstance(node, ast.BoolOp):
            count += 1
        elif isinstance(node, ast.BinOp):
            count += 1
        elif isinstance(node, ast.Constant) and isinstance(node.value, (bool, int, float)):
            count += 1
    return count


def mutate_operator(node: ast.AST) -> tuple[ast.AST | None, str]:
    if isinstance(node, ast.Compare) and node.ops:
        original = node.ops[0]
        replacements = {
            ast.Eq: ast.NotEq(),
            ast.NotEq: ast.Eq(),
            ast.Lt: ast.LtE(),
            ast.LtE: ast.Lt(),
            ast.Gt: ast.GtE(),
            ast.GtE: ast.Gt(),
            ast.In: ast.NotIn(),
            ast.NotIn: ast.In(),
            ast.Is: ast.IsNot(),
            ast.IsNot: ast.Is(),
        }
        for klass, replacement in replacements.items():
            if isinstance(original, klass):
                new_node = copy.deepcopy(node)
                new_node.ops[0] = replacement
                return new_node, f"compare_{op_name(original)}_to_{op_name(replacement)}"
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            new_node = copy.deepcopy(node)
            new_node.op = ast.Or()
            return new_node, "bool_And_to_Or"
        if isinstance(node.op, ast.Or):
            new_node = copy.deepcopy(node)
            new_node.op = ast.And()
            return new_node, "bool_Or_to_And"
    if isinstance(node, ast.BinOp):
        replacements = {
            ast.Add: ast.Sub(),
            ast.Sub: ast.Add(),
            ast.Mult: ast.FloorDiv(),
            ast.FloorDiv: ast.Mult(),
            ast.Div: ast.Mult(),
            ast.Mod: ast.Add(),
        }
        for klass, replacement in replacements.items():
            if isinstance(node.op, klass):
                new_node = copy.deepcopy(node)
                new_node.op = replacement
                return new_node, f"binop_{op_name(node.op)}_to_{op_name(replacement)}"
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return ast.Constant(value=not node.value), f"const_bool_{node.value}_flip"
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            return ast.Constant(value=node.value + 1), "const_int_plus_one"
        if isinstance(node.value, float):
            return ast.Constant(value=node.value + 1.0), "const_float_plus_one"
    return None, ""


class NthMutator(ast.NodeTransformer):
    def __init__(self, target_index: int) -> None:
        self.target_index = target_index
        self.current_index = -1
        self.mutation_type = ""
        self.changed = False

    def maybe_mutate(self, node: ast.AST) -> ast.AST:
        replacement, mutation_type = mutate_operator(node)
        if replacement is None:
            return node
        self.current_index += 1
        if self.current_index == self.target_index and not self.changed:
            self.changed = True
            self.mutation_type = mutation_type
            return ast.copy_location(replacement, node)
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        return self.maybe_mutate(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        self.generic_visit(node)
        return self.maybe_mutate(node)

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        return self.maybe_mutate(node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        return self.maybe_mutate(node)


def make_mutant(code: str, index: int) -> tuple[str, str] | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    mutator = NthMutator(index)
    mutated = mutator.visit(copy.deepcopy(tree))
    if not mutator.changed:
        return None
    ast.fix_missing_locations(mutated)
    try:
        return ast.unparse(mutated), mutator.mutation_type
    except Exception:
        return None


def generate_synthetic_mutants(task: dict[str, Any]) -> list[dict[str, str]]:
    try:
        tree = ast.parse(task["code"])
    except SyntaxError:
        return []

    viable = []
    seen_codes = set()

    wrapper_templates = [
        (
            "return_value_corruption",
            """
{code}

__ult_original_{func_name} = {func_name}
def {func_name}(*args, **kwargs):
    result = __ult_original_{func_name}(*args, **kwargs)
    if isinstance(result, bool):
        return not result
    if isinstance(result, int) and not isinstance(result, bool):
        return result + 1
    if isinstance(result, float):
        return result + 1.0
    if isinstance(result, str):
        return result + "__mutated__"
    if isinstance(result, list):
        return result[:-1] if result else ["__mutated__"]
    if isinstance(result, tuple):
        return result[:-1] if result else ("__mutated__",)
    if isinstance(result, dict):
        mutated = dict(result)
        mutated["__mutated__"] = True
        return mutated
    if result is None:
        return "__mutated__"
    return None
""",
        ),
        (
            "return_none",
            """
{code}

__ult_original_{func_name} = {func_name}
def {func_name}(*args, **kwargs):
    __ult_original_{func_name}(*args, **kwargs)
    return None
""",
        ),
        (
            "first_argument_perturbation",
            """
{code}

__ult_original_{func_name} = {func_name}
def {func_name}(*args, **kwargs):
    args = list(args)
    if args:
        first = args[0]
        if isinstance(first, bool):
            args[0] = not first
        elif isinstance(first, int) and not isinstance(first, bool):
            args[0] = first + 1
        elif isinstance(first, float):
            args[0] = first + 1.0
        elif isinstance(first, str):
            args[0] = first + "__mutated__"
    return __ult_original_{func_name}(*args, **kwargs)
""",
        ),
    ]
    for mutation_type, template in wrapper_templates:
        mutant_code = template.format(code=task["code"], func_name=task["func_name"]).strip() + "\n"
        try:
            compile(mutant_code, "<mutant>", "exec")
        except SyntaxError:
            continue
        viable.append(
            {
                "task_id": str(task["task_id"]),
                "func_name": task["func_name"],
                "mutant_id": f"{task['task_id']}_m{len(viable)}",
                "mutation_type": mutation_type,
                "oracle_killed_tests": "",
                "oracle_total_tests": "",
                "oracle_first_error": "not_filtered_by_official_oracle",
                "mutant_code": mutant_code,
            }
        )
        if len(viable) >= MAX_MUTANTS_PER_TASK:
            return viable

    total_candidates = min(candidate_count(tree), MAX_CANDIDATES_PER_TASK)
    for index in range(total_candidates):
        made = make_mutant(task["code"], index)
        if made is None:
            continue
        mutant_code, mutation_type = made
        if mutant_code in seen_codes or mutant_code == task["code"]:
            continue
        seen_codes.add(mutant_code)
        viable.append(
            {
                "task_id": str(task["task_id"]),
                "func_name": task["func_name"],
                "mutant_id": f"{task['task_id']}_m{len(viable)}",
                "mutation_type": mutation_type,
                "oracle_killed_tests": "",
                "oracle_total_tests": "",
                "oracle_first_error": "not_filtered_by_official_oracle",
                "mutant_code": mutant_code,
            }
        )
        if len(viable) >= MAX_MUTANTS_PER_TASK:
            break
    return viable


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    tasks = json.load(DATA.open(encoding="utf-8"))
    task_by_id = {str(task["task_id"]): task for task in tasks}
    raw_rows = list(csv.DictReader(RAW.open(encoding="utf-8")))

    mutants: list[dict[str, str]] = []
    for task in tasks:
        mutants.extend(generate_synthetic_mutants(task))

    write_csv(
        MUTANTS,
        [
            "task_id",
            "func_name",
            "mutant_id",
            "mutation_type",
            "oracle_killed_tests",
            "oracle_total_tests",
            "oracle_first_error",
            "mutant_code",
        ],
        mutants,
    )

    mutants_by_task: dict[str, list[dict[str, str]]] = defaultdict(list)
    for mutant in mutants:
        mutants_by_task[mutant["task_id"]].append(mutant)

    detection_rows: list[dict[str, Any]] = []
    for row in raw_rows:
        task_id = row["task_id"]
        task = task_by_id.get(task_id)
        if task is None:
            continue
        tests = parse_generated_tests(row.get("raw_response", ""))
        if not tests:
            continue
        ref_passing_tests = passing_assertions(task["code"], tests)
        ref_passed = len(ref_passing_tests)
        ref_total = len(tests)
        for mutant in mutants_by_task.get(task_id, []):
            if not ref_passing_tests:
                killed = 0
                killed_tests = 0
                total_ref_passing = 0
                first_error = "no_ref_passing_generated_tests"
            else:
                mut_passed, mut_total, first_error = run_assertions(mutant["mutant_code"], ref_passing_tests)
                killed_tests = mut_total - mut_passed
                killed = 1 if killed_tests > 0 else 0
                total_ref_passing = len(ref_passing_tests)
            detection_rows.append(
                {
                    "model": row["model"],
                    "task_id": task_id,
                    "variant": row["variant"],
                    "repeat": row["repeat"],
                    "mutant_id": mutant["mutant_id"],
                    "mutation_type": mutant["mutation_type"],
                    "generated_tests": len(tests),
                    "ref_passing_tests": total_ref_passing,
                    "ref_pass_rate": ref_passed / ref_total if ref_total else 0.0,
                    "killed": killed,
                    "killed_tests": killed_tests,
                    "mutant_total_tests": total_ref_passing,
                    "mutant_first_error": first_error,
                }
            )

    write_csv(
        DETECTION_RAW,
        [
            "model",
            "task_id",
            "variant",
            "repeat",
            "mutant_id",
            "mutation_type",
            "generated_tests",
            "ref_passing_tests",
            "ref_pass_rate",
            "killed",
            "killed_tests",
            "mutant_total_tests",
            "mutant_first_error",
        ],
        detection_rows,
    )

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in detection_rows:
        grouped[(row["model"], row["variant"])].append(row)

    summary_rows = []
    for (model, variant), group in sorted(grouped.items()):
        killed = sum(int(row["killed"]) for row in group)
        mutants_seen = len(group)
        ref_usable = sum(1 for row in group if int(row["ref_passing_tests"]) > 0)
        unique_mutants = {(row["task_id"], row["mutant_id"]) for row in group}
        unique_killed = {(row["task_id"], row["mutant_id"]) for row in group if int(row["killed"]) == 1}
        total_generated = sum(int(row["generated_tests"]) for row in group)
        summary_rows.append(
            {
                "model": model,
                "variant": variant,
                "mutation_evaluations": mutants_seen,
                "unique_viable_mutants": len(unique_mutants),
                "killed_evaluations": killed,
                "failure_detection_rate": round(killed / mutants_seen if mutants_seen else 0.0, 4),
                "unique_mutant_detection_rate": round(len(unique_killed) / len(unique_mutants) if unique_mutants else 0.0, 4),
                "ref_usable_rate": round(ref_usable / mutants_seen if mutants_seen else 0.0, 4),
                "avg_ref_pass_rate": round(statistics.mean(float(row["ref_pass_rate"]) for row in group), 4),
                "avg_generated_tests": round(total_generated / mutants_seen if mutants_seen else 0.0, 2),
            }
        )

    write_csv(
        DETECTION_SUMMARY,
        [
            "model",
            "variant",
            "mutation_evaluations",
            "unique_viable_mutants",
            "killed_evaluations",
            "failure_detection_rate",
            "unique_mutant_detection_rate",
            "ref_usable_rate",
            "avg_ref_pass_rate",
            "avg_generated_tests",
        ],
        summary_rows,
    )

    mutation_type_counts = Counter(mutant["mutation_type"] for mutant in mutants)
    report = [
        "# Phan tich fault detection bang mutation testing cho Ollama ULT Lite",
        "",
        f"So synthetic mutants duoc tao: {len(mutants)} tren {len(tasks)} tasks.",
        f"Gioi han: toi da {MAX_MUTANTS_PER_TASK} mutants/task; mutant khong loc bang `test_list` chuan vi nhieu reference task trong ULT Lite khong pass day du official tests.",
        "",
        "## Mutation operators",
        "",
        "| Mutation type | Count |",
        "|---|---:|",
    ]
    for mutation_type, count in sorted(mutation_type_counts.items()):
        report.append(f"| {mutation_type} | {count} |")

    report.extend(
        [
            "",
            "## Failure detection summary",
            "",
            "| Model | Variant | Eval mutants | Unique mutants | Killed evals | Failure detection rate | Unique mutant detection | Ref-usable rate | Avg ref pass |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary_rows:
        report.append(
            f"| {row['model']} | {row['variant']} | {row['mutation_evaluations']} | {row['unique_viable_mutants']} | {row['killed_evaluations']} | {row['failure_detection_rate']} | {row['unique_mutant_detection_rate']} | {row['ref_usable_rate']} | {row['avg_ref_pass_rate']} |"
        )

    report.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `failure_detection_rate`: ty le evaluation ma generated tests pass tren reference va kill duoc mutant.",
            "- `unique_mutant_detection_rate`: ty le mutant rieng biet duoc kill boi it nhat mot generated-test set trong cung model/variant.",
            "- `ref_usable_rate`: ty le evaluation co it nhat mot generated assertion pass tren reference; neu thap thi model tao oracle sai, khong nen tinh la fault detector tot.",
            "- Day la mutation-based fault detection that su hon proxy oracle-violation: generated tests phai pass tren implementation goc roi moi duoc tinh neu kill mutant.",
            "- Mutants la synthetic faults, khong thay the defect benchmark thuc te. Nen bao cao la mutation score/fault-detection proxy.",
            "",
        ]
    )
    REPORT.write_text("\n".join(report), encoding="utf-8")

    print(f"Wrote {MUTANTS}")
    print(f"Wrote {DETECTION_RAW}")
    print(f"Wrote {DETECTION_SUMMARY}")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
