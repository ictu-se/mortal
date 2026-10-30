#!/usr/bin/env python3
"""Generate empirical figures and LaTeX table fragments from quality-gate analyses."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'results/quality_gates'
OUT = ROOT / 'results/displays'
OUT.mkdir(parents=True, exist_ok=True)
MODELS = ['qwen2.5-coder:1.5b', 'qwen2.5-coder:7b', 'qwen2.5-coder:14b']
LABELS = ['Qwen 1.5B','Qwen 7B','Qwen 14B']
COLORS = ['#4477AA','#228833','#CC6677']
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,
                     'pdf.fonttype':42, 'ps.fonttype':42})


def table(name, caption, columns, header, rows, note=''):
    text = '\\begin{table}[t]\n\\caption{'+caption+'}\\label{tab:'+name+'}\n\\centering\\small\n'
    text += '\\setlength{\\tabcolsep}{4pt}\n\\begin{tabular}{'+columns+'}\n\\toprule\n'
    text += header + r' \\' + '\n\\midrule\n'
    text += '\n'.join(' & '.join(map(str,row))+r' \\' for row in rows)
    text += '\n\\bottomrule\n\\end{tabular}\n'
    if note: text += '\\par\\smallskip\\begin{minipage}{\\linewidth}\\footnotesize '+note+'\\end{minipage}\n'
    text += '\\end{table}\n'
    (OUT/(name+'.tex')).write_text(text)


def main():
    summary = pd.read_csv(DATA/'historical_summary.csv')
    gates = pd.read_csv(DATA/'historical_gate_retention.csv')
    rows=[]
    for domain in ['ult','similo']:
        for model,label in zip(MODELS,LABELS):
            r=summary[(summary.domain==domain)&(summary.model==model)&(summary.variant=='original')].iloc[0]
            rows.append(['ULT' if domain=='ult' else 'Similo',label,int(r.calls),f'{100*r.schema_ok:.2f}',
                         f'{100*r.correct:.2f}',f'[{100*r.correct_lo:.2f}, {100*r.correct_hi:.2f}]'])
    table('primary','Original-input validity and reference correctness in the historical cohort. Rates are percentages.',
          'llrrrr',r'Domain & Model & Calls & Schema & Correct & 95\% CI',rows,
          r'ULT correctness is strict suite success; Similo correctness is exact target matching. Intervals resample 200 ULT tasks or 47 Similo applications and retain all repetitions within a cluster.')
    rows=[]
    for model,label in zip(MODELS,LABELS):
        r=summary[(summary.domain=='ult')&(summary.model==model)&(summary.variant=='original')].iloc[0]
        rows.append([label,f'{100*r.positive_execution:.2f}',f'{100*r.assertion_mean:.2f}',
                     f'{int(r.mutants_killed)}/{int(r.mutants_evaluated)}',f'{100*r.conditional_mutation_rate:.2f}',
                     f'{100*r.unconditional_mutation_rate:.2f}'])
    table('mutation','Partial execution and synthetic-mutant yield on original ULT inputs.',
          'lrrrrr',r'Model & Positive & Assertion & Killed/evaluated & Cond. & Uncond.',rows,
          r'Positive and Assertion are percentages of calls with a passing test and mean per-call assertion success. Conditional yield uses evaluable artifacts; unconditional yield uses 1,800 scheduled artifact--mutant pairs per model. These are diagnostic yields from passing subsets, not acceptance rates for complete suites.')
    rows=[]
    for domain in ['ult','similo']:
        for model,label in zip(MODELS,LABELS):
            r=gates[(gates.domain==domain)&(gates.model==model)].iloc[0]
            rows.append(['ULT' if domain=='ult' else 'Similo',label,int(r.cases),int(r.stable_original_cases),
                         int(r.joint_cases),int(r.at_least_seven)])
    table('joint','Case-level acceptance after joining repeated and perturbed observations.',
          'llrrrr',r'Domain & Model & Cases & Original 3/3 & All 9/9 & At least 7/9',rows,
          r'Original 3/3 requires three acceptable original artifacts. All 9/9 requires acceptable artifacts in every variant and repetition. In ULT, adding the requirement that each accepted artifact kill a mutant leaves these counts unchanged. The 7/9 column is a relaxed policy, not the strict gate.')
    held_out = pd.read_csv(DATA / 'historical_holdout.csv')
    rows = []
    for domain in ['ult', 'similo']:
        for model, label in zip(MODELS, LABELS):
            h = held_out[(held_out.domain == domain) & (held_out.model == model)].set_index('policy')
            rows.append(['ULT' if domain == 'ult' else 'Similo', label,
                         f"{int(h.loc['schema_only','held_out_pass'])}/{int(h.loc['schema_only','selected_cases'])}",
                         f"{int(h.loc['joint','held_out_pass'])}/{int(h.loc['joint','selected_cases'])}"])
    table('holdout', 'Selected cases passing all three held-out conditions in the historical cohort.',
          'llrr', r'Domain & Model & Schema-only selection & Joint selection', rows,
          r'Each entry is held-out passing cases divided by selected cases. Selection uses only the first two repetitions across all three variants (six observations); evaluation uses the third repetition in each variant (three observations). The held-out outcome requires all three artifacts to satisfy the applicable correctness and fault-detection predicates. This post hoc replay tests selection on recorded cases, not generalization to new tasks.')
    if (DATA / 'matched_summary.csv').exists():
        matched = pd.read_csv(DATA / 'matched_summary.csv')
        stable = pd.read_csv(DATA / 'matched_stability.csv')
        rows = []
        boundary = False
        for domain in ['ult', 'similo']:
            for model, label in zip(MODELS + ['deepseek-coder:6.7b'], LABELS + ['DeepSeek 6.7B']):
                r = matched[(matched.domain == domain) & (matched.model == model)].iloc[0]
                s = stable[(stable.domain == domain) & (stable.model == model)].iloc[0]
                ci = f'[{100*r.correct_lo:.2f}, {100*r.correct_hi:.2f}]'
                if r.correct in (0.0, 1.0):
                    ci = r'\textemdash'
                    boundary = True
                rows.append(['ULT' if domain == 'ult' else 'Similo', label,
                             f'{100*r.schema_ok:.2f}', f'{100*r.correct:.2f}',
                             ci, int(s.stable_pass)])
        table('family', 'Original-prompt comparison on the same 100 cases per domain. Rates are percentages.',
              'llrrlr', r'Domain & Model & Schema & Correct & 95\% CI & Stable 3/3', rows,
              r'Each row contains 300 calls. Stable 3/3 counts cases correct in all three repetitions, out of 100. Confidence intervals resample ULT tasks or Similo applications. This comparison covers original prompts only; it does not estimate the nine-condition gate or isolate architecture from runtime and decoding differences.'
              + (r' An em dash denotes a sample with no outcome variation, for which the bootstrap interval is uninformative.' if boundary else ''))
    drops=pd.read_csv(DATA/'historical_paired_drops.csv')
    fig,axs=plt.subplots(1,2,figsize=(6.8,3.2),layout='constrained')
    for ax,domain,title in zip(axs,['ult','similo'],['(a) ULT: strict suite success','(b) Similo: exact target match']):
        for vi,(variant,color,marker,label) in enumerate([('paraphrase','#4477AA','o','Reformulation'),('noise','#CC6677','s','Context / warning')]):
            g=drops[(drops.domain==domain)&(drops.variant==variant)].set_index('model').loc[MODELS]
            y=np.arange(3)+(vi-.5)*.15
            ax.errorbar(g['drop']*100,y,xerr=np.vstack([(g['drop']-g.lo)*100,(g.hi-g['drop'])*100]),
                        fmt=marker,ms=4,capsize=3,color=color,label=label)
        ax.axvline(0,color='0.5',ls=':',lw=1);ax.set_yticks(range(3),LABELS);ax.invert_yaxis()
        ax.set_xlabel('Original minus probe (pp)');ax.set_title(title,fontsize=11)
        ax.grid(axis='x',alpha=.15)
    handles, labels = axs[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='outside lower center', ncol=2, fontsize=10, frameon=False)
    fig.savefig(OUT/'paired_drops.pdf');plt.close(fig)
    d=pd.read_csv(DATA/'historical_case_decisions.csv')
    fig,axs=plt.subplots(1,2,figsize=(6.8,3.2),layout='constrained')
    for ax,domain,title in zip(axs,['ult','similo'],['(a) ULT Lite','(b) SimiloLLM']):
        for model,label,color in zip(MODELS,LABELS,COLORS):
            g=d[(d.domain==domain)&(d.model==model)]
            costs=np.sort(g.loc[g.fault_all_nine==1,'mean_generation_ms'].to_numpy())/1000
            xs=np.r_[0,costs,20];ys=np.r_[0,np.arange(1,len(costs)+1)/len(g)*100,len(costs)/len(g)*100]
            ax.step(xs,ys,where='post',color=color,label=label)
        ax.set_xlim(0,20);ax.set_xlabel('Mean generation budget (s/call)')
        ax.set_ylabel('Cases accepted (%)');ax.set_title(title,fontsize=11);ax.grid(alpha=.15)
    handles, labels = axs[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc='outside lower center', ncol=3, fontsize=10, frameon=False)
    fig.savefig(OUT/'cost_gate.pdf');plt.close(fig)


if __name__=='__main__': main()
