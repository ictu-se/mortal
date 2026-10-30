#!/usr/bin/env python3
"""Reference-filtered evaluation for the three retained ULT wrapper operators.

The operators preserve the historical mutant contents. They are syntax-checked,
not equivalence-filtered, and their detection yield is not a real-defect recall.
Execution uses POSIX interval timers and requires macOS or Linux.
"""
from __future__ import annotations
import ast
import contextlib
import io
import json
import signal
from typing import Any

MAX_MUTANTS_PER_TASK = 3
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

    return viable

