#!/usr/bin/env python3
"""Reproduce joined quality gates, clustered intervals, and cross-family results."""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import run_ollama_ult_lite_experiment as ult
import run_similo_ollama_experiment as sim
import mutants as mut

ROOT = Path(__file__).resolve().parent
VARIANTS = ['original', 'paraphrase', 'noise']


def cluster_ci(frame, column, cluster, rounds=4000):
    groups = frame.groupby(cluster)[column].agg(['sum', 'count'])
    if cluster.startswith('app') and all(str(x).isdecimal() for x in groups.index):
        groups = groups.sort_index(key=lambda values: values.astype(int))
    rng = np.random.default_rng(20261029)
    idx = rng.integers(0, len(groups), (rounds, len(groups)))
    vals = groups['sum'].to_numpy()[idx].sum(axis=1) / groups['count'].to_numpy()[idx].sum(axis=1)
    return [float(frame[column].mean()), *np.quantile(vals, [.025, .975]).tolist()]


def historical():
    all_rows = []
    for domain, prefix in [('ult', 'ollama_ult_lite'), ('similo', 'similo_ollama')]:
        d = pd.read_csv(ROOT / 'pilot_outputs' / prefix / (prefix + '_raw.csv'), keep_default_na=False,
                        dtype={'app': str, 'case_id': str, 'task_id': str})
        d['domain'] = domain
        d['cohort'] = 'historical'
        if domain == 'ult':
            d['case_id'] = d['task_id'].astype(str)
            d['app'] = d['case_id']
            d['correct'] = ((d.schema_ok == 1) & (d.exec_pass_rate == 1)).astype(int)
            d['artifact_pass'] = ((d.correct == 1) & (d.syntax_rate == 1)
                                  & (d.target_function_call_rate == 1)).astype(int)
            d['syntax_pass'] = ((d.schema_ok == 1) & (d.syntax_rate == 1)).astype(int)
            d['positive_execution'] = (d.exec_pass_rate > 0).astype(int)
            d['assertion_mean'] = d.exec_pass_rate
            m = pd.read_csv(ROOT / 'pilot_outputs/ollama_ult_lite/ollama_ult_lite_mutation_detection_raw.csv')
            m['case_id'] = m.task_id.astype(str)
            grouped = m.groupby(['model', 'case_id', 'variant', 'repeat']).killed.agg(['sum', 'count']).reset_index()
            grouped = grouped.rename(columns={'sum': 'mutants_killed', 'count': 'mutants_evaluated'})
            d = d.merge(grouped, on=['model', 'case_id', 'variant', 'repeat'], how='left')
            d[['mutants_killed', 'mutants_evaluated']] = d[['mutants_killed', 'mutants_evaluated']].fillna(0)
            d['fault_pass'] = ((d.artifact_pass == 1) & (d.mutants_killed > 0)).astype(int)
        else:
            d['case_id'] = d.case_id.astype(str)
            d['correct'] = d.exact_match
            d['syntax_pass'] = d.candidate_index_valid
            d['artifact_pass'] = ((d.schema_ok == 1) & (d.candidate_index_valid == 1) & (d.correct == 1)).astype(int)
            d['fault_pass'] = d.artifact_pass
            d['mutants_killed'] = 0
            d['mutants_evaluated'] = 0
        all_rows.append(d)
    return pd.concat(all_rows, ignore_index=True)


def extension(args):
    source = ROOT / 'results/family_extension/responses.jsonl'
    if not source.exists():
        return pd.DataFrame()
    design = json.loads((ROOT / 'results/family_extension/design.json').read_text())
    cache_path = ROOT / 'results/family_extension/evaluated.jsonl'
    cached = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            r = json.loads(line)
            if r['variant'] in design['variants']:
                cached[(r['domain'], r['case_id'], r['variant'], r['repeat'])] = r
    records = [json.loads(line) for line in source.read_text().splitlines()
               if json.loads(line)['variant'] in design['variants']]
    if all((r['domain'],r['case_id'],r['variant'],r['repeat']) in cached for r in records):
        for r in records:
            key=(r['domain'],r['case_id'],r['variant'],r['repeat'])
            assert cached[key]['response_sha256'] == hashlib.sha256(r['result'].get('response','').encode()).hexdigest()
        return pd.DataFrame(list(cached.values()))
    ult.DATA = args.datasets
    sim.DATA = args.datasets / 'SimiloLLM'
    tasks = {str(t['task_id']): t for t in ult.load_tasks(200)}
    cases = {str(c['case_id']): c for c in sim.build_cases(50)}
    subprocess.run([sys.executable, str(ROOT / 'evaluate_ult_responses.py'),
                    '--datasets', str(args.datasets)], check=True)
    reference = {}
    for line in (ROOT / 'results/family_extension/reference_evaluations.jsonl').read_text().splitlines():
        r = json.loads(line)
        reference[(r['case_id'], r['variant'], r['repeat'])] = r
    with cache_path.open('a') as out:
        for record in records:
            key = (record['domain'], record['case_id'], record['variant'], record['repeat'])
            if key in cached:
                assert cached[key]['response_sha256'] == hashlib.sha256(record['result'].get('response', '').encode()).hexdigest()
                continue
            response = record['result'].get('response', '')
            row = {k: record[k] for k in ['domain', 'case_id', 'model', 'variant', 'repeat', 'client_elapsed_ms']}
            row['response_sha256'] = hashlib.sha256(response.encode()).hexdigest()
            row.update(cohort='extension', error=record['result'].get('error', ''),
                       prompt_eval_count=record['result'].get('prompt_eval_count', 0),
                       eval_count=record['result'].get('eval_count', 0))
            if record['domain'] == 'ult':
                task = tasks[record['case_id']]
                json_ok, schema_ok, tests, error = ult.parse_tests(response)
                syntax_ok, n = ult.check_test_syntax(tests)
                execution = reference[(record['case_id'], record['variant'], record['repeat'])]
                assert execution['response_sha256'] == row['response_sha256']
                passed = execution['exec_passed_tests']
                target_calls = sum(f"{task['func_name']}(" in t for t in tests)
                correct = int(schema_ok and n > 0 and passed == n)
                artifact_pass = int(correct and syntax_ok == n and target_calls == n)
                filtered = mut.parse_generated_tests(response)
                passing = mut.passing_assertions(task['code'], filtered)
                mutants = mut.generate_synthetic_mutants(task) if filtered else []
                killed = 0
                for mutant in mutants:
                    if passing:
                        p, t, _ = mut.run_assertions(mutant['mutant_code'], passing)
                        killed += int(p < t)
                row.update(app=row['case_id'], json_ok=int(json_ok), schema_ok=int(schema_ok),
                           correct=correct, artifact_pass=artifact_pass,
                           syntax_pass=int(schema_ok and syntax_ok == n),
                           positive_execution=int(passed > 0), assertion_mean=passed / n if n else 0,
                           generated_tests=n, mutants_killed=killed, mutants_evaluated=len(mutants),
                           fault_pass=int(artifact_pass and killed > 0), parse_error=error,
                           reference_protocol=execution['reference_protocol'], exec_error=execution['exec_error'])
            else:
                case = cases[record['case_id']]
                result = sim.evaluate(case, response)
                artifact_pass = int(result['schema_ok'] and result['candidate_index_valid'] and result['exact_match'])
                row.update(result)
                row.update(app=case['app'], correct=result['exact_match'], artifact_pass=artifact_pass,
                           syntax_pass=result['candidate_index_valid'], fault_pass=artifact_pass,
                           oracle_in_top_k=int(case['oracle_in_top_k']), mutants_killed=0, mutants_evaluated=0)
            out.write(json.dumps(row) + '\n'); out.flush()
            cached[key] = row
    return pd.DataFrame(list(cached.values()))


def summarize(data, out, cohort_name):
    rows, gates, stability, paired, decisions, budgets = [], [], [], [], [], []
    for (domain, model), group in data.groupby(['domain', 'model']):
        cluster = 'case_id' if domain == 'ult' else 'app'
        for variant, cond in group.groupby('variant'):
            row = dict(domain=domain, model=model, variant=variant, calls=len(cond), cases=cond.case_id.nunique())
            for metric in ['schema_ok', 'syntax_pass', 'correct', 'artifact_pass', 'fault_pass']:
                row[metric], row[metric + '_lo'], row[metric + '_hi'] = cluster_ci(cond, metric, cluster)
            row['positive_execution'] = cond.positive_execution.mean() if domain == 'ult' else None
            row['assertion_mean'] = cond.assertion_mean.mean() if domain == 'ult' else None
            row['total_latency_ms'] = cond.client_elapsed_ms.sum()
            row['median_latency_ms'] = cond.client_elapsed_ms.median()
            row['ms_per_correct'] = row['total_latency_ms'] / cond.correct.sum() if cond.correct.sum() else None
            row['ms_per_pass'] = row['total_latency_ms'] / cond.artifact_pass.sum() if cond.artifact_pass.sum() else None
            row['mutants_evaluated'] = cond.mutants_evaluated.sum()
            row['mutants_killed'] = cond.mutants_killed.sum()
            row['conditional_mutation_rate'] = row['mutants_killed']/row['mutants_evaluated'] if row['mutants_evaluated'] else None
            row['unconditional_mutation_rate'] = row['mutants_killed']/(3 * len(cond)) if domain == 'ult' else None
            rows.append(row)
            sums = cond.groupby('case_id').correct.agg(['sum', 'count'])
            stability.append(dict(domain=domain, model=model, variant=variant, cases=len(sums),
                                  stable_pass=int((sums['sum'] == sums['count']).sum()),
                                  stable_fail=int((sums['sum'] == 0).sum()),
                                  mixed=int(((sums['sum'] > 0) & (sums['sum'] < sums['count'])).sum())))
        if set(group.variant) != set(VARIANTS):
            continue  # Original-only extension does not estimate the nine-condition gate.
        original = group[group.variant == 'original']
        original_cases = original.groupby('case_id').artifact_pass.min()
        joint_cases = group.groupby('case_id').artifact_pass.agg(['sum', 'count'])
        fault_cases = group.groupby('case_id').fault_pass.min()
        gates.append(dict(domain=domain, model=model, cases=group.case_id.nunique(), original_calls=len(original),
                          schema_calls=int(original.schema_ok.sum()), syntax_calls=int(original.syntax_pass.sum()),
                          correct_calls=int(original.correct.sum()), artifact_calls=int(original.artifact_pass.sum()),
                          fault_calls=int(original.fault_pass.sum()),
                          stable_original_cases=int(original_cases.sum()),
                          joint_cases=int(((joint_cases['sum'] == 9) & (joint_cases['count'] == 9)).sum()),
                          joint_fault_cases=int(fault_cases.sum()),
                          at_least_seven=int((joint_cases['sum'] >= 7).sum()),
                          at_least_one=int((joint_cases['sum'] >= 1).sum())))
        for case_id, observations in group.groupby('case_id'):
            complete = len(observations) == 9 and observations.variant.nunique() == 3
            correct_nine = complete and observations.artifact_pass.min() == 1
            fault_nine = correct_nine and observations.fault_pass.min() == 1
            mean_cost = observations.client_elapsed_ms.mean()
            decision = dict(domain=domain, model=model, case_id=case_id,
                            observations=len(observations), complete=int(complete),
                            artifact_passes=int(observations.artifact_pass.sum()),
                            correct_all_nine=int(correct_nine), fault_all_nine=int(fault_nine),
                            total_generation_ms=observations.client_elapsed_ms.sum(),
                            mean_generation_ms=mean_cost)
            decisions.append(decision)
            for budget in [1000, 2000, 5000, 10000, 20000]:
                budgets.append(dict(domain=domain, model=model, case_id=case_id, budget_ms=budget,
                                    accepted=int(fault_nine and mean_cost <= budget)))
        wide = group.pivot(index=['case_id', 'app', 'repeat'], columns='variant', values='correct').reset_index()
        for variant in ['paraphrase', 'noise']:
            if variant not in wide or 'original' not in wide:
                continue
            wide['drop'] = wide.original - wide[variant]
            point, lo, hi = cluster_ci(wide, 'drop', cluster)
            paired.append(dict(domain=domain, model=model, variant=variant, drop=point, lo=lo, hi=hi))
    for filename, items in [('summary',rows),('gate_retention',gates),('stability',stability),
                            ('paired_drops',paired),('case_decisions',decisions)]:
        if items:
            pd.DataFrame(items).to_csv(out / (cohort_name + '_' + filename + '.csv'), index=False)
    if budgets:
        pd.DataFrame(budgets).groupby(['domain','model','budget_ms']).accepted.agg(['sum','count']).reset_index().to_csv(
            out / (cohort_name + '_cost_gate.csv'),index=False)


def held_out_replay(data, out):
    rows = []
    for (domain, model), observations in data.groupby(['domain', 'model']):
        training = observations[observations['repeat'] < 2].groupby('case_id').agg(
            schema_only=('schema_ok', 'min'), joint=('fault_pass', 'min'))
        held_out = observations[observations['repeat'] == 2].groupby('case_id').fault_pass.min()
        assert set(training.index) == set(held_out.index)
        for policy in ['schema_only', 'joint']:
            selected = training[policy] == 1
            count = int(selected.sum())
            success = int(held_out[selected].sum())
            rows.append(dict(domain=domain, model=model, policy=policy, cases=len(training),
                             selected_cases=count, held_out_pass=success, held_out_fail=count-success,
                             selection_fraction=count/len(training),
                             conditional_success=success/count if count else None))
    pd.DataFrame(rows).to_csv(out / 'historical_holdout.csv', index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--datasets', type=Path, default=ROOT / 'reproduction_datasets')
    parser.add_argument('--historical-only', action='store_true')
    args = parser.parse_args()
    out = ROOT / 'results/quality_gates'
    out.mkdir(parents=True, exist_ok=True)
    data = historical()
    assert len(data) == 27108
    assert not data.duplicated(['domain','model','case_id','variant','repeat']).any()
    assert set(data.variant) == set(VARIANTS) and set(data['repeat']) == {0, 1, 2}
    assert set(data.groupby(['domain', 'model', 'case_id']).size()) == {9}
    summarize(data, out, 'historical')
    held_out_replay(data, out)
    if not args.historical_only:
        new = extension(args)
        if len(new):
            design = json.loads((ROOT/'results/family_extension/design.json').read_text())
            if len(new) != design['planned_calls']:
                print('Cached',len(new),'of',design['planned_calls'],'extension evaluations; final comparison withheld.')
                return
            expected = {(domain, case, variant, repeat)
                        for domain, key in [('ult', 'ult_ids'), ('similo', 'similo_ids')]
                        for case in design[key] for variant in design['variants'] for repeat in range(3)}
            actual = set(new[['domain', 'case_id', 'variant', 'repeat']].itertuples(index=False, name=None))
            assert actual == expected and len(actual) == len(new)
            subset = data[((data.domain == 'ult') & data.case_id.isin(design['ult_ids'])) |
                          ((data.domain == 'similo') & data.case_id.isin(design['similo_ids']))]
            subset = subset[subset.variant.isin(design['variants'])]
            combined = pd.concat([subset, new], ignore_index=True)
            summarize(combined, out, 'matched')
            comparisons = []
            for model, comparator in subset.groupby('model'):
                paired = new.merge(comparator, on=['domain', 'case_id', 'variant', 'repeat'],
                                   suffixes=('_extension', '_historical'), validate='one_to_one')
                assert len(paired) == 600
                assert (paired.app_extension == paired.app_historical).all()
                for domain, observations in paired.groupby('domain'):
                    observations = observations.copy()
                    observations['difference'] = observations.correct_extension - observations.correct_historical
                    estimate, lower, upper = cluster_ci(observations, 'difference',
                                                        'case_id' if domain == 'ult' else 'app_extension')
                    comparisons.append(dict(domain=domain, extension_model=design['model'], comparator=model,
                                            calls=len(observations), difference=estimate, lo=lower, hi=upper))
            pd.DataFrame(comparisons).to_csv(out / 'matched_family_differences.csv', index=False)
            raw = [json.loads(line) for line in (ROOT / 'results/family_extension/responses.jsonl').read_text().splitlines()]
            indexed = {(r.domain, r.case_id, r.variant, r.repeat): r
                       for r in new.itertuples(index=False)}
            diagnostics = []
            for domain in ['ult', 'similo']:
                records = [r for r in raw if r['domain'] == domain and r['variant'] in design['variants']]
                limited = [r for r in records if r['result'].get('done_reason') == 'length']
                invalid = sum(indexed[(r['domain'], r['case_id'], r['variant'], r['repeat'])].json_ok == 0
                              for r in limited)
                diagnostics.append(dict(domain=domain, calls=len(records), length_limited=len(limited),
                                        length_limited_invalid_json=invalid,
                                        backend_errors=sum(bool(r['result'].get('error')) for r in records),
                                        max_prompt_tokens=max(r['result'].get('prompt_eval_count', 0) for r in records),
                                        max_output_tokens=max(r['result'].get('eval_count', 0) for r in records)))
            pd.DataFrame(diagnostics).to_csv(out / 'extension_generation_diagnostics.csv', index=False)
            new.to_csv(out/'extension_evaluated.csv',index=False)
            print('Extension rows evaluated:',len(new),'planned:',design['planned_calls'])
    print(pd.read_csv(out/'historical_gate_retention.csv').to_string(index=False))


if __name__ == '__main__':
    main()
