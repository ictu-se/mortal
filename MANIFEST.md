# Artifact Manifest

This file records the expected contents and reproducibility scope of the
MORTAL artifact package.

## Reproducibility Scope

The package supports two reproduction modes:

1. **Table reproduction from frozen raw outputs.** This mode does not require
   Ollama or external datasets and rebuilds the aggregate CSV/Markdown outputs
   from `pilot_outputs/`.
2. **Full local inference reproduction.** This mode requires Ollama, the three
   Qwen2.5-Coder models listed in `README.md`, and the external benchmark
   files placed under `reproduction_datasets/`.

## Frozen Raw Outputs

| File | Expected data rows | Description |
|---|---:|---|
| `pilot_outputs/ollama_ult_lite/ollama_ult_lite_raw.csv` | 5,400 | ULT Lite local Ollama calls |
| `pilot_outputs/similo_ollama/similo_ollama_raw.csv` | 21,708 | SimiloLLM local Ollama calls |

## Regenerated Aggregate Outputs

The following command rebuilds the main analysis outputs from the frozen raw
CSV files:

```bash
make analyze
```

The generated files include:

- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_extended_metrics.csv`
- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_statistical_ci.csv`
- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_oracle_ablation.csv`
- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_cost_effectiveness.csv`
- `pilot_outputs/similo_ollama/similo_ollama_summary.csv`
- `pilot_outputs/similo_ollama/similo_ollama_robustness.csv`
- `pilot_outputs/similo_ollama/similo_ollama_flakiness.csv`
- `pilot_outputs/similo_ollama/similo_ollama_statistical_ci.csv`
- `pilot_outputs/CROSS_DOMAIN_EVIDENCE_FOR_Q1_VI.md`

## Smoke Test

Run:

```bash
make check
```

The check verifies required files and expected raw-output row counts.

