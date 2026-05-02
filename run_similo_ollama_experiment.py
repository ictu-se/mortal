#!/usr/bin/env python3
"""Run local Ollama models on the SimiloLLM web-element localization task."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import subprocess
import time
import urllib.error
import urllib.request
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
BASE = ROOT
DATA = BASE / "reproduction_datasets" / "SimiloLLM"
OUT = ROOT / "pilot_outputs" / "similo_ollama"
RAW = OUT / "similo_ollama_raw.csv"
DRY_RUN = OUT / "similo_dry_run_cases.csv"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_BIN = shutil.which("ollama") or "ollama"

MODELS = ["qwen2.5-coder:1.5b", "qwen2.5-coder:7b", "qwen2.5-coder:14b"]
VARIANTS = ["original", "paraphrase", "noise"]
FIELDNAMES = [
    "model",
    "case_id",
    "app",
    "app_name",
    "variant",
    "repeat",
    "temperature",
    "top_k",
    "oracle_in_top_k",
    "oracle_rank",
    "candidate_count",
    "client_elapsed_ms",
    "prompt_eval_count",
    "eval_count",
    "eval_tokens_per_second",
    "json_ok",
    "schema_ok",
    "candidate_index_valid",
    "selected_candidate_index",
    "selected_xpath",
    "selected_idxpath",
    "exact_match",
    "valid_but_wrong",
    "parse_error",
    "raw_response",
]


def norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def tokens(value: str | None) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", norm(value)))


def split_paths(value: str | None) -> list[str]:
    return [part.strip() for part in (value or "").split(" || ") if part.strip()]


def read_semicolon_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", errors="ignore", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def load_data() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    old = read_semicolon_csv(DATA / "old.txt")
    new = read_semicolon_csv(DATA / "new.txt")
    oracles = read_semicolon_csv(DATA / "oracles.txt")
    return old, new, oracles


def path_matches(element: dict[str, str], xpath: str) -> bool:
    wanted = xpath.strip()
    return wanted in split_paths(element.get("xpath")) or wanted in split_paths(element.get("idxpath"))


def element_signature(element: dict[str, str]) -> str:
    fields = ["tag", "class", "name", "id", "href", "alt", "visible_text", "neighbor_text", "is_button"]
    return " ".join(norm(element.get(field)) for field in fields if element.get(field))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def xpath_tail_similarity(a: str, b: str) -> float:
    a_parts = [part for part in a.split("/") if part]
    b_parts = [part for part in b.split("/") if part]
    if not a_parts or not b_parts:
        return 0.0
    matches = 0
    for left, right in zip(reversed(a_parts), reversed(b_parts)):
        if left == right:
            matches += 1
        else:
            break
    return matches / max(len(a_parts), len(b_parts))


def similarity(old_target: dict[str, str], candidate: dict[str, str]) -> float:
    old_sig = element_signature(old_target)
    cand_sig = element_signature(candidate)
    score = 0.0
    score += 3.0 * jaccard(tokens(old_sig), tokens(cand_sig))
    for field, weight in [
        ("id", 2.5),
        ("name", 2.0),
        ("visible_text", 2.0),
        ("href", 1.5),
        ("class", 1.0),
        ("alt", 1.0),
    ]:
        left = norm(old_target.get(field))
        right = norm(candidate.get(field))
        if left and right:
            if left == right:
                score += weight
            elif left in right or right in left:
                score += weight * 0.5
    if norm(old_target.get("tag")) and norm(old_target.get("tag")) == norm(candidate.get("tag")):
        score += 0.75
    if norm(old_target.get("is_button")) == norm(candidate.get("is_button")):
        score += 0.25
    score += xpath_tail_similarity(old_target.get("xpath", ""), candidate.get("xpath", ""))
    return score


def brief_element(element: dict[str, str], index: int | None = None) -> dict[str, Any]:
    fields = {
        "tag": element.get("tag", ""),
        "class": element.get("class", ""),
        "name": element.get("name", ""),
        "id": element.get("id", ""),
        "href": element.get("href", ""),
        "alt": element.get("alt", ""),
        "is_button": element.get("is_button", ""),
        "visible_text": element.get("visible_text", ""),
        "neighbor_text": element.get("neighbor_text", ""),
        "xpath": element.get("xpath", ""),
        "idxpath": element.get("idxpath", ""),
    }
    if index is not None:
        fields = {"candidate_index": index, **fields}
    return fields


def candidate_line(candidate: dict[str, str], index: int) -> str:
    xpath_tail = "/".join([part for part in candidate.get("xpath", "").split("/") if part][-4:])
    parts = [
        f"[{index}]",
        f"tag={candidate.get('tag', '')[:35]!r}",
        f"id={candidate.get('id', '')[:45]!r}",
        f"name={candidate.get('name', '')[:45]!r}",
        f"class={candidate.get('class', '')[:55]!r}",
        f"text={candidate.get('visible_text', '')[:85]!r}",
        f"near={candidate.get('neighbor_text', '')[:85]!r}",
        f"href={candidate.get('href', '')[:65]!r}",
        f"button={candidate.get('is_button', '')!r}",
        f"path_tail={xpath_tail[:80]!r}",
    ]
    return " | ".join(parts)


def build_cases(top_k: int, limit: int | None = None) -> list[dict[str, Any]]:
    old, new, oracles = load_data()
    old_by_app: dict[str, list[dict[str, str]]] = defaultdict(list)
    new_by_app: dict[str, list[dict[str, str]]] = defaultdict(list)
    for element in old:
        old_by_app[element["app"]].append(element)
    for element in new:
        new_by_app[element["app"]].append(element)

    cases = []
    for case_id, oracle in enumerate(oracles):
        app = oracle["app"]
        old_target = next((element for element in old_by_app[app] if path_matches(element, oracle["fromxpath"])), None)
        if old_target is None:
            continue
        scored = []
        for candidate in new_by_app[app]:
            scored.append((similarity(old_target, candidate), candidate))
        scored.sort(key=lambda item: item[0], reverse=True)
        candidates = [candidate for _, candidate in scored[:top_k]]
        oracle_rank = ""
        for rank, (_, candidate) in enumerate(scored, start=1):
            if path_matches(candidate, oracle["toxpath"]):
                oracle_rank = rank
                break
        oracle_in_top_k = bool(oracle_rank and int(oracle_rank) <= top_k)
        cases.append(
            {
                "case_id": str(case_id),
                "app": app,
                "app_name": oracle.get("name", ""),
                "fromxpath": oracle["fromxpath"],
                "toxpath": oracle["toxpath"],
                "old_target": old_target,
                "candidates": candidates,
                "oracle_in_top_k": oracle_in_top_k,
                "oracle_rank": oracle_rank,
                "candidate_count": len(candidates),
            }
        )
    if limit is not None:
        return cases[:limit]
    return cases


def build_prompt(case: dict[str, Any], variant: str) -> str:
    old_target = json.dumps(brief_element(case["old_target"]), ensure_ascii=False)
    candidates = "\n".join(candidate_line(candidate, index) for index, candidate in enumerate(case["candidates"]))
    variant_text = {
        "original": "Choose the candidate in the new UI that corresponds to the old target element.",
        "paraphrase": "Identify which new-page element is the migrated counterpart of the old-page target. Preserve the same user-facing intent, not just the same DOM path.",
        "noise": "Some candidates are distractors with similar text, classes, or nearby labels. Ignore unrelated neighbors and select the true migrated counterpart.",
    }[variant]
    return f"""You are evaluating web UI element localization after a website version change.

Task: {variant_text}

Return only valid JSON with this exact schema:
{{"candidate_index": 0, "confidence": 0.0, "rationale": "short reason"}}

Rules:
- candidate_index must be one integer from 0 to {max(0, len(case['candidates']) - 1)}
- return at most 20 words in rationale
- choose exactly one candidate
- do not copy a candidate object
- do not use keys such as text, tag, xpath, selected, answer, or data
- do not return markdown or explanations outside JSON
- base the choice on visible text, id/name/class, href, role/button status, neighbor text, and path similarity

Application: {case['app_name']} (app id {case['app']})

Old target element:
{old_target}

New UI candidates:
{candidates}
"""


def ensure_ollama_available() -> None:
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2).read()
        return
    except Exception:
        subprocess.Popen(
            [OLLAMA_BIN, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(5)
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5).read()
    except Exception as exc:
        raise SystemExit(f"Ollama server is not reachable: {exc}") from exc


def installed_models() -> set[str]:
    try:
        raw = subprocess.check_output([OLLAMA_BIN, "list"], text=True)
    except Exception:
        return set()
    models = set()
    for line in raw.splitlines()[1:]:
        parts = line.split()
        if parts:
            models.add(parts[0])
    return models


def ensure_models(models: list[str]) -> None:
    have = installed_models()
    for model in models:
        if model in have:
            continue
        subprocess.run([OLLAMA_BIN, "pull", model], check=True)


def call_ollama(model: str, prompt: str, temperature: float, timeout: float) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "top_p": 1.0,
            "num_ctx": 8192,
            "num_predict": 96,
        },
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ollama_error:{exc}") from exc
    result = json.loads(raw)
    result["client_elapsed_ms"] = (time.perf_counter() - start) * 1000
    return result


def parse_prediction(raw_response: str, candidate_count: int) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        return {
            "json_ok": 0,
            "schema_ok": 0,
            "candidate_index_valid": 0,
            "selected_candidate_index": "",
            "parse_error": f"json_error:{exc.msg}",
        }
    index = parsed.get("candidate_index") if isinstance(parsed, dict) else None
    if index is None and isinstance(parsed, dict):
        for fallback_key in ["index", "candidate", "selected_candidate", "answer"]:
            if fallback_key in parsed:
                index = parsed[fallback_key]
                break
    if isinstance(index, str) and index.strip().isdigit():
        index = int(index.strip())
    schema_ok = isinstance(parsed, dict) and isinstance(index, int)
    valid = schema_ok and 0 <= index < candidate_count
    return {
        "json_ok": 1,
        "schema_ok": int(schema_ok),
        "candidate_index_valid": int(valid),
        "selected_candidate_index": index if schema_ok else "",
        "parse_error": "" if schema_ok else "schema_error:candidate_index_not_int",
    }


def evaluate(case: dict[str, Any], raw_response: str) -> dict[str, Any]:
    parsed = parse_prediction(raw_response, len(case["candidates"]))
    selected_xpath = ""
    selected_idxpath = ""
    exact_match = 0
    valid_but_wrong = 0
    if not parsed["candidate_index_valid"]:
        try:
            parsed_object = json.loads(raw_response)
        except json.JSONDecodeError:
            parsed_object = None
        if isinstance(parsed_object, dict):
            output_paths = split_paths(parsed_object.get("xpath")) + split_paths(parsed_object.get("idxpath"))
            for index, candidate in enumerate(case["candidates"]):
                candidate_paths = split_paths(candidate.get("xpath")) + split_paths(candidate.get("idxpath"))
                if output_paths and any(path in candidate_paths for path in output_paths):
                    parsed["selected_candidate_index"] = index
                    selected_xpath = candidate.get("xpath", "")
                    selected_idxpath = candidate.get("idxpath", "")
                    exact_match = int(path_matches(candidate, case["toxpath"]))
                    valid_but_wrong = int(not exact_match)
                    return {
                        **parsed,
                        "selected_xpath": selected_xpath,
                        "selected_idxpath": selected_idxpath,
                        "exact_match": exact_match,
                        "valid_but_wrong": valid_but_wrong,
                    }
    if parsed["candidate_index_valid"]:
        selected = case["candidates"][int(parsed["selected_candidate_index"])]
        selected_xpath = selected.get("xpath", "")
        selected_idxpath = selected.get("idxpath", "")
        exact_match = int(path_matches(selected, case["toxpath"]))
        valid_but_wrong = int(not exact_match)
    return {
        **parsed,
        "selected_xpath": selected_xpath,
        "selected_idxpath": selected_idxpath,
        "exact_match": exact_match,
        "valid_but_wrong": valid_but_wrong,
    }


def existing_keys(path: Path) -> set[tuple[str, str, str, str]]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            (row["model"], row["case_id"], row["variant"], row["repeat"])
            for row in csv.DictReader(handle)
        }


def append_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()


def write_dry_run(cases: list[dict[str, Any]]) -> None:
    rows = []
    for case in cases:
        rows.append(
            {
                "case_id": case["case_id"],
                "app": case["app"],
                "app_name": case["app_name"],
                "fromxpath": case["fromxpath"],
                "toxpath": case["toxpath"],
                "candidate_count": case["candidate_count"],
                "oracle_in_top_k": int(case["oracle_in_top_k"]),
                "oracle_rank": case["oracle_rank"],
                "prompt_chars_original": len(build_prompt(case, "original")),
            }
        )
    DRY_RUN.parent.mkdir(parents=True, exist_ok=True)
    with DRY_RUN.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run(args: argparse.Namespace) -> None:
    models = args.models.split(",") if args.models else MODELS
    variants = args.variants.split(",") if args.variants else VARIANTS
    limit = args.limit if args.limit > 0 else None
    cases = build_cases(args.top_k, limit)
    write_dry_run(cases)
    topk_recall = sum(case["oracle_in_top_k"] for case in cases) / len(cases) if cases else 0.0
    print(f"Loaded {len(cases)} SimiloLLM cases; top-{args.top_k} oracle recall={topk_recall:.4f}")
    print(f"Wrote {DRY_RUN}")
    if args.dry_run:
        return

    ensure_ollama_available()
    if args.pull:
        ensure_models(models)

    done = existing_keys(RAW)
    planned = len(cases) * len(models) * len(variants) * args.repeats
    print(f"Planned calls: {planned}; already completed: {len(done)}")

    for model in models:
        for case in cases:
            for variant in variants:
                prompt = build_prompt(case, variant)
                for repeat in range(args.repeats):
                    key = (model, case["case_id"], variant, str(repeat))
                    if key in done:
                        continue
                    try:
                        response = call_ollama(model, prompt, args.temperature, args.timeout)
                        raw_response = response.get("response", "")
                        eval_row = evaluate(case, raw_response)
                        row = {
                            "model": model,
                            "case_id": case["case_id"],
                            "app": case["app"],
                            "app_name": case["app_name"],
                            "variant": variant,
                            "repeat": repeat,
                            "temperature": args.temperature,
                            "top_k": args.top_k,
                            "oracle_in_top_k": int(case["oracle_in_top_k"]),
                            "oracle_rank": case["oracle_rank"],
                            "candidate_count": case["candidate_count"],
                            "client_elapsed_ms": round(response.get("client_elapsed_ms", 0.0), 2),
                            "prompt_eval_count": response.get("prompt_eval_count", ""),
                            "eval_count": response.get("eval_count", ""),
                            "eval_tokens_per_second": round(
                                float(response.get("eval_count", 0) or 0)
                                / max(float(response.get("eval_duration", 0) or 0) / 1_000_000_000, 1e-9),
                                2,
                            ),
                            **eval_row,
                            "raw_response": raw_response,
                        }
                    except Exception as exc:
                        row = {
                            "model": model,
                            "case_id": case["case_id"],
                            "app": case["app"],
                            "app_name": case["app_name"],
                            "variant": variant,
                            "repeat": repeat,
                            "temperature": args.temperature,
                            "top_k": args.top_k,
                            "oracle_in_top_k": int(case["oracle_in_top_k"]),
                            "oracle_rank": case["oracle_rank"],
                            "candidate_count": case["candidate_count"],
                            "client_elapsed_ms": "",
                            "prompt_eval_count": "",
                            "eval_count": "",
                            "eval_tokens_per_second": "",
                            "json_ok": 0,
                            "schema_ok": 0,
                            "candidate_index_valid": 0,
                            "selected_candidate_index": "",
                            "selected_xpath": "",
                            "selected_idxpath": "",
                            "exact_match": 0,
                            "valid_but_wrong": 0,
                            "parse_error": str(exc),
                            "raw_response": "",
                        }
                    append_row(RAW, row)
                    done.add(key)
                    if len(done) % args.progress_every == 0:
                        print(f"Completed {len(done)}/{planned} calls")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="0 means all cases")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--variants", default=",".join(VARIANTS))
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pull", action="store_true")
    parser.add_argument("--progress-every", type=int, default=25)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
