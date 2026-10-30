#!/usr/bin/env python3
"""Build three editable tables and two vector figures from retained results."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'results/quality_gates'
OUT = ROOT / 'results/displays'
MODELS = ['qwen2.5-coder:1.5b', 'qwen2.5-coder:7b', 'qwen2.5-coder:14b']
SIZES = ['1.5B', '7B', '14B']
LABELS = ['Qwen '+s for s in SIZES]
COLORS = ['#6A9ABD', '#356A91', '#153D5B']
plt.rcParams.update({'axes.spines.top':False, 'axes.spines.right':False,
                     'axes.titlesize':'medium', 'axes.labelsize':'medium',
                     'legend.fontsize':'medium', 'xtick.labelsize':'medium',
                     'ytick.labelsize':'medium', 'pdf.fonttype':42, 'ps.fonttype':42})


def tabular(columns, header, rows, panel=None):
    lines=[r'\begin{tabular}{'+columns+'}', r'\toprule', header+r' \\', r'\midrule']
    if panel:
        lines.insert(1,r'\multicolumn{'+str(len(columns))+r'}{l}{\textbf{'+panel+r'}} \\')
    for row in rows:
        lines.append(row if isinstance(row,str) else ' & '.join(map(str,row))+r' \\')
    return '\n'.join(lines+[r'\bottomrule',r'\end{tabular}'])


def table(name, caption, content, note, aliases=()):
    labels=''.join(r'\label{tab:'+key+'}' for key in (name,*aliases))
    text=(r'\begin{table}[!htbp]'+'\n'+r'\caption{'+caption+'}'+labels+'\n'
          +r'\centering\setlength{\tabcolsep}{4pt}'+'\n'+content+'\n'
          +r'\par\smallskip\begin{minipage}{\linewidth}'+note+r'\end{minipage}'+'\n'+r'\end{table}'+'\n')
    (OUT/(name+'.tex')).write_text(text)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    summary=pd.read_csv(DATA/'historical_summary.csv')
    rows=[]
    for domain,n in [('ult',600),('similo',2412)]:
        rows.append(r'\multicolumn{4}{l}{'+('ULT' if domain=='ult' else 'Similo')+f': {n:,} calls per model'+r'} \\')
        for model,label in zip(MODELS,SIZES):
            r=summary[(summary.domain==domain)&(summary.model==model)&(summary.variant=='original')].iloc[0]
            rows.append([label,f'{100*r.schema_ok:.2f}',f'{100*r.correct:.2f}',f'[{100*r.correct_lo:.2f}, {100*r.correct_hi:.2f}]'])
    content=tabular('lrrl',r'Qwen & Schema (\%) & Correct (\%) & 95\% CI',rows,
                    panel='(a) Format acceptance and reference correctness')
    rows=[]
    for model,label in zip(MODELS,SIZES):
        r=summary[(summary.domain=='ult')&(summary.model==model)&(summary.variant=='original')].iloc[0]
        rows.append([label,f'{100*r.positive_execution:.2f}',f'{100*r.assertion_mean:.2f}',f'{int(r.mutants_killed)}/{int(r.mutants_evaluated)}',f'{100*r.conditional_mutation_rate:.2f}',f'{100*r.unconditional_mutation_rate:.2f}'])
    content+='\n'+r'\par\medskip\textbf{(b) Partial ULT utility and mutation yield}\par\smallskip'+'\n'
    content+=tabular('lrrrrr',r'Qwen & \shortstack{Positive\\(\%)} & \shortstack{Assertion\\(\%)} & \shortstack{Killed/\\evaluable} & \shortstack{Cond.\\(\%)} & \shortstack{Uncond.\\(\%)}',rows)
    table('primary','Original-input artifact quality in the historical cohort.',content,
          r'Correctness is strict suite success in ULT and exact target matching in Similo. Intervals resample 200 tasks or 47 applications. Positive denotes calls with a passing test; Assertion is mean per-call assertion success. Conditional mutation yield uses evaluable artifact--mutant pairs; unconditional yield uses 1,800 scheduled pairs per model. Panel (b) evaluates passing subsets, not complete-suite acceptance.',aliases=('mutation',))
    gates=pd.read_csv(DATA/'historical_gate_retention.csv')
    held=pd.read_csv(DATA/'historical_holdout.csv');rows=[]
    for domain,n in [('ult',200),('similo',804)]:
        rows.append(r'\multicolumn{6}{l}{'+('ULT' if domain=='ult' else 'Similo')+f': {n} cases'+r'} \\')
        for model,label in zip(MODELS,SIZES):
            r=gates[(gates.domain==domain)&(gates.model==model)].iloc[0]
            h=held[(held.domain==domain)&(held.model==model)].set_index('policy')
            rows.append([label,int(r.stable_original_cases),int(r.joint_cases),int(r.at_least_seven),
                         f"{int(h.loc['schema_only','held_out_pass'])}/{int(h.loc['schema_only','selected_cases'])}",
                         f"{int(h.loc['joint','held_out_pass'])}/{int(h.loc['joint','selected_cases'])}"])
    content=tabular('lrrrrr',r'Qwen & \shortstack{Original\\3/3} & \shortstack{All\\9/9} & \shortstack{At least\\7/9} & \shortstack{Held-out\\schema} & \shortstack{Held-out\\joint}',rows)
    table('joint','Case retention and held-out success under explicit historical policies.',content,
          r'The first three outcome columns count accepted cases. The last two give held-out passing cases divided by selected cases. Held-out selection uses the first two repetitions of each variant; evaluation uses the third repetition. All 9/9 is the strict gate; 7/9 is a relaxed policy. Original 3/3 concerns repeated original inputs. Each applicable artifact and fault-detection predicate must pass. The held-out analysis evaluates recorded cases, not transfer to new tasks.',aliases=('holdout',))
    matched=pd.read_csv(DATA/'matched_summary.csv');stable=pd.read_csv(DATA/'matched_stability.csv');rows=[]
    for domain in ['ult','similo']:
        rows.append(r'\multicolumn{5}{l}{'+('ULT' if domain=='ult' else 'Similo')+r': 100 cases, 300 calls per configuration} \\')
        for model,label in zip(MODELS+['deepseek-coder:6.7b'],LABELS+['DeepSeek 6.7B']):
            r=matched[(matched.domain==domain)&(matched.model==model)].iloc[0]
            s=stable[(stable.domain==domain)&(stable.model==model)].iloc[0]
            rows.append([label,f'{100*r.schema_ok:.2f}',f'{100*r.correct:.2f}',f'[{100*r.correct_lo:.2f}, {100*r.correct_hi:.2f}]',int(s.stable_pass)])
    content=tabular('lrrlr',r'Model & \shortstack{Schema\\(\%)} & \shortstack{Correct\\(\%)} & 95\% CI & \shortstack{Stable\\3/3}',rows)
    table('family','Case-matched original-prompt comparison across two model families.',content,
          r'Stable 3/3 counts cases correct in every original repetition. Intervals resample ULT tasks or Similo applications. All scheduled requests remain in the denominators, including backend failures. These observations do not estimate the nine-condition gate or isolate architecture from runtime and decoding differences.')
    drops=pd.read_csv(DATA/'historical_paired_drops.csv')
    fig,axs=plt.subplots(1,2,figsize=(5.15,2.9),sharey=True,layout='constrained')
    for ax,domain,title in zip(axs,['ult','similo'],['(a) Unit tests','(b) Localization']):
        for vi,(variant,color,marker,label) in enumerate([('paraphrase',COLORS[1],'o','Reformulation'),('noise',COLORS[2],'s','Context / warning')]):
            g=drops[(drops.domain==domain)&(drops.variant==variant)].set_index('model').loc[MODELS];y=np.arange(3)+(vi-.5)*.15
            ax.errorbar(g['drop']*100,y,xerr=np.vstack([(g['drop']-g.lo)*100,(g.hi-g['drop'])*100]),fmt=marker,ms=4,capsize=3,color=color,label=label)
        ax.axvline(0,color='0.5',ls=':',lw=1);ax.set_yticks(range(3),LABELS)
        ax.set_xlabel('Correctness loss (pp)');ax.set_title(title);ax.grid(axis='x',color='#dddddd')
    axs[0].invert_yaxis();handles,labels=axs[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=2,frameon=False)
    fig.savefig(OUT/'paired_drops.pdf');fig.savefig(OUT/'Fig1.eps');plt.close(fig)
    d=pd.read_csv(DATA/'historical_case_decisions.csv')
    fig,axs=plt.subplots(1,2,figsize=(5.15,3.15),layout='constrained')
    for ax,domain,title in zip(axs,['ult','similo'],['(a) Unit tests','(b) Localization']):
        for model,label,color,style in zip(MODELS,LABELS,COLORS,['-','--',':']):
            g=d[(d.domain==domain)&(d.model==model)]
            costs=np.sort(g.loc[g.fault_all_nine==1,'mean_generation_ms'].to_numpy())/1000
            xs=np.r_[0,costs,20];ys=np.r_[0,np.arange(1,len(costs)+1)/len(g)*100,len(costs)/len(g)*100]
            ax.step(xs,ys,where='post',color=color,ls=style,lw=1.5,label=label)
        ax.set_xlim(0,20);ax.set_xlabel('Budget (s/call)');ax.set_ylabel('Cases accepted (%)');ax.set_title(title);ax.grid(color='#dddddd')
    handles,labels=axs[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=3,frameon=False)
    fig.savefig(OUT/'cost_gate.pdf');fig.savefig(OUT/'Fig2.eps');plt.close(fig)


if __name__=='__main__':main()
