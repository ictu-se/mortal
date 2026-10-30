#!/usr/bin/env python3
"""Acquire a case-matched second-family replication.

The historical prompt builders are reused verbatim. Raw responses are append-only;
analysis is a separate step so inference timing excludes oracle execution.
"""
import argparse
import concurrent.futures
import hashlib
import json
import platform
import random
import subprocess
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import run_ollama_ult_lite_experiment as ult
import run_similo_ollama_experiment as sim


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def acquire(job, model, endpoint):
    domain, item, variant, repeat = job
    prompt = (ult.build_prompt if domain == "ult" else sim.build_prompt)(item, variant)
    options = {"temperature": 0.1, "top_p": 1.0,
               "num_ctx": 4096 if domain == "ult" else 8192,
               "seed": 20261029 + repeat}
    if domain == "similo":
        options["num_predict"] = 96
    payload = {"model": model, "prompt": prompt, "stream": False,
               "format": "json", "options": options}
    start = time.perf_counter()
    try:
        request = urllib.request.Request(endpoint + "/api/generate",
                    data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=240) as response:
            result = json.load(response)
    except Exception as exc:
        result = {"error": type(exc).__name__ + ": " + str(exc), "response": ""}
    return {"domain": domain, "case_id": str(item["task_id"] if domain == "ult" else item["case_id"]),
            "model": model, "variant": variant, "repeat": repeat,
            "options": options, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "client_elapsed_ms": 1000 * (time.perf_counter() - start), "result": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results/family_extension")
    parser.add_argument("--model", default="deepseek-coder:6.7b")
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--variants", default="original")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    ult.DATA = args.datasets
    sim.DATA = args.datasets / "SimiloLLM"
    tasks = ult.load_tasks(200)
    cases = sim.build_cases(50)
    rng = random.Random(20261029)
    tasks = sorted(rng.sample(tasks, args.sample_size), key=lambda x: str(x["task_id"]))
    # Cover applications before drawing another case from the same application.
    groups = defaultdict(list)
    for case in cases:
        groups[case["app"]].append(case)
    for key in sorted(groups):
        rng.shuffle(groups[key])
    selected = []
    while len(selected) < args.sample_size:
        for key in sorted(groups):
            if groups[key] and len(selected) < args.sample_size:
                selected.append(groups[key].pop())
    manifest = {"seed": 20261029, "model": args.model, "sample_size_per_domain": args.sample_size,
                "ult_ids": [str(t["task_id"]) for t in tasks],
                "similo_ids": [str(c["case_id"]) for c in selected],
                "similo_applications": len({c["app"] for c in selected}),
                "variants": args.variants.split(','), "repeats": 3,
                "workers": args.workers, "planned_calls": args.sample_size * 6 * len(args.variants.split(',')),
                "dataset_sha256": {str(p.relative_to(args.datasets)): sha(p) for p in
                    [args.datasets / "UnLeakedTestBench/datasets/ULT_Lite.jsonl",
                     *[args.datasets / "SimiloLLM" / f for f in ["old.txt", "new.txt", "oracles.txt"]]]}}
    manifest_path = args.output / "design.json"
    if manifest_path.exists():
        old_manifest = json.loads(manifest_path.read_text())
        assert {k: v for k, v in old_manifest.items() if k != 'workers'} == {
            k: v for k, v in manifest.items() if k != 'workers'}, "Design changed; use a new output directory"
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        meta = {"platform": platform.platform(), "python": platform.python_version()}
        for path in ["version", "tags"]:
            with urllib.request.urlopen(args.endpoint + "/api/" + path) as r:
                meta[path] = json.load(r)
        meta["hardware"] = (subprocess.check_output(["system_profiler", "SPHardwareDataType"], text=True)
                            if platform.system() == 'Darwin' else platform.processor())
        # Keep only the selected model metadata, and omit host identifiers.
        meta["tags"]["models"] = [m for m in meta["tags"]["models"] if m["name"] == args.model]
        meta["hardware"] = "\n".join(l for l in meta["hardware"].splitlines()
                                    if not any(x in l for x in ["Serial", "UUID", "UDID"]))
        (args.output / "environment.json").write_text(json.dumps(meta, indent=2) + "\n")
    raw = args.output / "responses.jsonl"
    done = set()
    if raw.exists():
        for line in raw.read_text().splitlines():
            r = json.loads(line)
            if r['variant'] in manifest['variants']:
                done.add((r["domain"], r["case_id"], r["variant"], r["repeat"]))
    jobs = []
    for domain, items in [("ult", tasks), ("similo", selected)]:
        for item in items:
            for variant in manifest["variants"]:
                for repeat in range(3):
                    key = (domain, str(item["task_id"] if domain == "ult" else item["case_id"]), variant, repeat)
                    if key not in done:
                        jobs.append((domain, item, variant, repeat))
    random.Random(20261029).shuffle(jobs)
    # Batch context sizes to avoid unloading/reloading the same model between domains.
    jobs.sort(key=lambda job: (job[0], str(job[1].get('task_id', job[1].get('case_id'))),
                               job[2], job[3]))
    with (args.output / 'execution_sessions.jsonl').open('a') as session:
        with urllib.request.urlopen(args.endpoint + '/api/tags') as response:
            selected_model = next(m for m in json.load(response)['models'] if m['name'] == args.model)
        recorded_environment = json.loads((args.output / 'environment.json').read_text())
        assert selected_model['digest'] == recorded_environment['tags']['models'][0]['digest'], 'Model digest changed; use a new output directory'
        session.write(json.dumps({'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                  'workers': args.workers, 'retained': len(done), 'pending': len(jobs),
                                  'model_digest': selected_model['digest']}) + '\n')
    print(f"Planned {manifest['planned_calls']} calls; {len(done)} retained; {len(jobs)} pending", flush=True)
    with raw.open("a") as out, concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(acquire, job, args.model, args.endpoint) for job in jobs]
        for n, future in enumerate(concurrent.futures.as_completed(futures), len(done) + 1):
            row = future.result()
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            if n % 20 == 0 or row["result"].get("error"):
                print(f"{n}/{manifest['planned_calls']} {row['domain']} {row['case_id']} "
                      f"{row['client_elapsed_ms']:.0f}ms error={row['result'].get('error', '')}", flush=True)


if __name__ == "__main__":
    main()
