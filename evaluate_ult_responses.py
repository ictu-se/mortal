#!/usr/bin/env python3
"""Replay the historical process-isolated ULT reference oracle on saved responses.

Kept separate from statistical analysis so spawned Python workers import the
same lightweight oracle module used by the historical acquisition runner.
"""
import argparse
import hashlib
import json
from pathlib import Path
import run_ollama_ult_lite_experiment as ult

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--datasets', type=Path, default=ROOT / 'reproduction_datasets')
    parser.add_argument('--directory', type=Path, default=ROOT / 'results/family_extension')
    args = parser.parse_args()
    ult.DATA = args.datasets
    tasks = {str(t['task_id']): t for t in ult.load_tasks(200)}
    design = json.loads((args.directory / 'design.json').read_text())
    output = args.directory / 'reference_evaluations.jsonl'
    saved = {}
    if output.exists():
        for line in output.read_text().splitlines():
            r = json.loads(line)
            saved[(r['case_id'], r['variant'], r['repeat'])] = r
    records = [json.loads(line) for line in (args.directory / 'responses.jsonl').read_text().splitlines()]
    with output.open('a') as handle:
        for r in records:
            if r['domain'] != 'ult' or r['variant'] not in design['variants']:
                continue
            key = (r['case_id'], r['variant'], r['repeat'])
            response = r['result'].get('response', '')
            digest = hashlib.sha256(response.encode()).hexdigest()
            if key in saved:
                assert saved[key]['response_sha256'] == digest
                continue
            result = ult.evaluate_response(tasks[r['case_id']], response)
            result.update(case_id=r['case_id'], variant=r['variant'], repeat=r['repeat'],
                          response_sha256=digest, reference_protocol='historical_spawn_1p5s')
            handle.write(json.dumps(result) + '\n'); handle.flush()
            saved[key] = result
    print('Reference oracle cache:', len(saved), 'ULT calls')


if __name__ == '__main__':
    main()
