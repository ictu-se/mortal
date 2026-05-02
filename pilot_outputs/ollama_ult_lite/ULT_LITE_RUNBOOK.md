# ULT Lite Analysis Runbook

This report documents the ULT Lite analysis path for the MORTAL artifact.

## Directory Layout

- `run_ollama_ult_lite_experiment.py`: runs local Ollama models on ULT Lite.
- `analyze_ollama_ult_lite_metrics.py`: aggregates validity, correctness, robustness, reliability, cost and failure taxonomy.
- `analyze_ollama_mutation_detection.py`: generates synthetic mutants and evaluates generated tests against them.
- `analyze_q1_readiness_stats.py`: computes bootstrap confidence intervals, oracle ablation, cost-effectiveness and model comparisons.
- `pilot_outputs/ollama_ult_lite/`: raw outputs and generated tables.

## Reproduction Commands

Run from the artifact root:

```bash
python3 analyze_ollama_ult_lite_metrics.py
python3 analyze_ollama_mutation_detection.py
python3 analyze_q1_readiness_stats.py
```

To reproduce raw LLM calls, ensure Ollama is running and the required models are installed, then run:

```bash
python3 run_ollama_ult_lite_experiment.py
```

## Frozen Configuration

- Dataset: ULT Lite, 200 tasks.
- Variants: original, paraphrase, noise.
- Repeats: 3.
- Models in current raw output: `qwen2.5-coder:1.5b`, `qwen2.5-coder:7b`, `qwen2.5-coder:14b`.
- Raw calls: 5,400.

## Main Expected Outputs

- `ollama_ult_lite_raw.csv`: raw model responses and evaluator fields.
- `OLLAMA_ULT_LITE_EXTENDED_METRICS_VI.md`: main metric summary.
- `OLLAMA_ULT_LITE_MUTATION_DETECTION_VI.md`: mutation-based fault detection summary.
- `Q1_READY_STATISTICS_AND_ABLATION_VI.md`: CI, ablation, cost and model comparison tables.

## Limitation

The full artifact includes ULT Lite and SimiloLLM. This runbook only covers ULT Lite-specific analysis.