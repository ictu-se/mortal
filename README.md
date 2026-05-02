# MORTAL Artifact

This repository contains the reproduction package for **MORTAL: Multi-Oracle
Robustness Testing as a Quality Gate for LLM-Generated Software Artifacts**.

MORTAL evaluates LLM-generated software artifacts with layered oracles:
format validity, syntax/execution checks, semantic correctness, robustness under
input perturbation, repeated-run stability, mutation-based fault detection, and
cost-effectiveness.

## Contents

```text
.
├── run_ollama_ult_lite_experiment.py       # ULT Lite local Ollama runner
├── run_similo_ollama_experiment.py         # SimiloLLM local Ollama runner
├── analyze_ollama_ult_lite_metrics.py      # ULT validity/correctness/stability metrics
├── analyze_ollama_mutation_detection.py    # ULT mutation-based fault detection
├── analyze_q1_readiness_stats.py           # ULT CIs, ablation, cost, comparisons
├── analyze_similo_ollama_results.py        # SimiloLLM aggregate metrics
├── build_cross_domain_evidence.py          # Cross-domain summary report
├── prepare_manual_validation_sample.py     # Manual-audit sample for ULT outputs
├── check_artifact.py                       # Lightweight structural smoke test
├── MANIFEST.md                             # Expected files and row counts
├── pilot_outputs/                          # Frozen raw outputs and generated tables
├── manuscript_tables/                      # Tables copied into the manuscript
├── manuscript_figures/                     # Figures copied into the manuscript
└── reproduction_datasets/                  # Place external datasets here
```

## Quick Start

Create a Python environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the structural check:

```bash
python3 check_artifact.py
```

Rebuild aggregate tables from the frozen raw outputs:

```bash
make analyze
```

The mutation detector requires the ULT Lite dataset because it re-executes
generated tests against reference implementations and synthetic mutants:

```bash
python3 analyze_ollama_mutation_detection.py
```

## External Datasets

The artifact does not vendor third-party benchmark datasets by default. Place
them under `reproduction_datasets/` using the following layout:

```text
reproduction_datasets/
├── UnLeakedTestBench/
│   └── datasets/
│       └── ULT_Lite.jsonl
└── SimiloLLM/
    ├── old.txt
    ├── new.txt
    └── oracles.txt
```

The raw model outputs and aggregate tables used by the manuscript are already
included under `pilot_outputs/`, so most analysis tables can be regenerated
without rerunning local LLM inference.

## Reproducing Local LLM Calls

Install Ollama and pull the models:

```bash
ollama pull qwen2.5-coder:1.5b
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:14b
```

Run ULT Lite:

```bash
python3 run_ollama_ult_lite_experiment.py \
  --models qwen2.5-coder:1.5b,qwen2.5-coder:7b,qwen2.5-coder:14b \
  --repeats 3 \
  --limit 200
```

Run SimiloLLM:

```bash
python3 run_similo_ollama_experiment.py \
  --models qwen2.5-coder:1.5b,qwen2.5-coder:7b,qwen2.5-coder:14b \
  --variants original,paraphrase,noise \
  --repeats 3 \
  --top-k 50 \
  --pull
```

Both runners are resume-safe: completed rows in the raw CSV files are skipped.

## Expected Scale

| Domain | Cases | Variants | Models | Repeats | Calls |
|---|---:|---:|---:|---:|---:|
| ULT Lite | 200 | 3 | 3 | 3 | 5,400 |
| SimiloLLM | 804 | 3 | 3 | 3 | 21,708 |
| Total | - | - | - | - | 27,108 |

## Main Outputs

ULT Lite outputs:

- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_raw.csv`
- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_extended_metrics.csv`
- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_oracle_ablation.csv`
- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_mutation_detection_summary.csv`
- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_statistical_ci.csv`

SimiloLLM outputs:

- `pilot_outputs/similo_ollama/similo_ollama_raw.csv`
- `pilot_outputs/similo_ollama/similo_ollama_summary.csv`
- `pilot_outputs/similo_ollama/similo_ollama_robustness.csv`
- `pilot_outputs/similo_ollama/similo_ollama_flakiness.csv`
- `pilot_outputs/similo_ollama/similo_ollama_statistical_ci.csv`

## Notes for Reviewers

- The included raw outputs make aggregate-table reproduction possible without
  rerunning Ollama.
- Full LLM reruns require local hardware, installed Ollama models, and the
  external datasets listed above.
- Timing metrics are hardware-dependent; correctness, validity, and stability
  metrics should be reproduced from the raw output tables.
- The reported setup used local open-weight models to avoid sending source code,
  DOMs, prompts, and generated artifacts to remote APIs.
