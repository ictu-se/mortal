#!/usr/bin/env python3
"""Verify retained evidence, design coverage, and oracle-cache provenance."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def rows(path):
    with (ROOT / path).open(newline='') as handle:
        return list(csv.DictReader(handle))


def check():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-only', action='store_true')
    args = parser.parse_args()
    for path, expected, case in [
        ('pilot_outputs/ollama_ult_lite/ollama_ult_lite_raw.csv', 5400, 'task_id'),
        ('pilot_outputs/similo_ollama/similo_ollama_raw.csv', 21708, 'case_id')]:
        data = rows(path)
        assert len(data) == expected, (path, len(data))
        keys = [(r['model'], r[case], r['variant'], r['repeat']) for r in data]
        assert len(keys) == len(set(keys)), 'Duplicate observation'
        assert set(Counter((r['model'], r[case]) for r in data).values()) == {9}
        assert {r['repeat'] for r in data} == {'0', '1', '2'}
        assert {r['variant'] for r in data} == {'original', 'paraphrase', 'noise'}
    mutants = rows('pilot_outputs/ollama_ult_lite/ollama_ult_lite_synthetic_mutants.csv')
    assert len(mutants) == 600 and len({r['mutant_id'] for r in mutants}) == 600
    mutation = rows('pilot_outputs/ollama_ult_lite/ollama_ult_lite_mutation_detection_raw.csv')
    assert len(mutation) == 14874
    assert {r['mutant_id'] for r in mutation} <= {r['mutant_id'] for r in mutants}
    assert {r['killed'] for r in mutation} <= {'0', '1'}
    if not args.historical_only:
        directory = ROOT / 'results/family_extension'
        design = json.loads((directory / 'design.json').read_text())
        raw = [json.loads(line) for line in (directory / 'responses.jsonl').read_text().splitlines()]
        def key(record):
            return tuple(record[k] for k in ['domain', 'case_id', 'variant', 'repeat'])
        assert len(raw) == len({key(r) for r in raw}), 'Duplicate acquired response'
        expected = {(domain, case, variant, repeat)
                    for domain, field in [('ult', 'ult_ids'), ('similo', 'similo_ids')]
                    for case in design[field] for variant in design['variants'] for repeat in range(3)}
        primary = {key(r): r for r in raw if r['variant'] in design['variants']}
        assert set(primary) == expected and len(primary) == design['planned_calls'] == 600
        amendment = json.loads((directory / 'design_amendment.json').read_text())
        assert len(raw) - len(primary) == amendment['exploratory_probes_retained'] == 49
        evaluated = [json.loads(line) for line in (directory / 'evaluated.jsonl').read_text().splitlines()]
        assert len(evaluated) == len(expected) and {key(r) for r in evaluated} == expected
        for record in evaluated:
            response = primary[key(record)]['result'].get('response', '')
            assert record['response_sha256'] == hashlib.sha256(response.encode()).hexdigest()
            assert record['fault_pass'] <= record['artifact_pass'] <= record['correct']
            assert record['mutants_killed'] <= record['mutants_evaluated']
        print('Verified 600 primary and 49 exploratory second-family responses; cache hashes agree.')
    manifest = ROOT / 'SHA256SUMS'
    if manifest.exists():
        for line in manifest.read_text().splitlines():
            digest, path = line.split('  ', 1)
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    print('Verified 27,108 historical calls, 600 mutants, and 14,874 mutation evaluations.')


if __name__ == '__main__':
    check()
