# Ollama ULT_Lite Local Experiment

Model: `qwen2.5-coder:14b`

Dataset: `UnLeakedTestBench/datasets/ULT_Lite.jsonl`

Scope:

- seed tasks: 200
- variants per task: 3
- repeats per condition: 3
- total calls: 5400
- temperature: 0.1

## Aggregate Results

| model | variant | calls | json_validity | schema_validity | avg_generated_tests | syntax_rate | execution_pass_rate | target_function_call_rate | failure_rate | avg_latency_ms | avg_prompt_tokens | avg_output_tokens | avg_tokens_per_second |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen2.5-coder:1.5b | noise | 600 | 0.9733 | 0.855 | 2.73 | 0.8329 | 0.104 | 0.8547 | 0.9833 | 3147.47 | 526.04 | 126.64 | 171.79 |
| qwen2.5-coder:1.5b | original | 600 | 0.9683 | 0.9083 | 2.9 | 0.8828 | 0.1039 | 0.908 | 0.9817 | 3661.11 | 501.9 | 123.45 | 171.61 |
| qwen2.5-coder:1.5b | paraphrase | 600 | 0.9833 | 0.5533 | 1.83 | 0.5404 | 0.0633 | 0.553 | 0.9883 | 3181.81 | 531.68 | 134.7 | 173.18 |
| qwen2.5-coder:14b | noise | 600 | 1.0 | 1.0 | 5.0 | 0.9953 | 0.275 | 0.9997 | 0.9483 | 10732.89 | 541.76 | 203.01 | 31.64 |
| qwen2.5-coder:14b | original | 600 | 1.0 | 1.0 | 5.0 | 0.9953 | 0.285 | 0.9997 | 0.9433 | 11124.47 | 518.76 | 202.49 | 31.75 |
| qwen2.5-coder:14b | paraphrase | 600 | 1.0 | 1.0 | 5.0 | 0.995 | 0.2657 | 1.0 | 0.9483 | 10764.36 | 541.76 | 205.4 | 31.67 |
| qwen2.5-coder:7b | noise | 600 | 0.9983 | 0.9983 | 4.61 | 0.9894 | 0.2269 | 0.9971 | 0.9717 | 4261.71 | 540.81 | 176.21 | 86.06 |
| qwen2.5-coder:7b | original | 600 | 1.0 | 1.0 | 4.43 | 0.9918 | 0.2267 | 0.9971 | 0.9717 | 4308.33 | 518.76 | 173.26 | 85.68 |
| qwen2.5-coder:7b | paraphrase | 600 | 0.995 | 0.995 | 4.76 | 0.9889 | 0.2251 | 0.9946 | 0.9717 | 4427.34 | 540.02 | 186.87 | 85.7 |

## Interpretation

- `json_validity` and `schema_validity` measure whether the model obeyed the required structured-output contract.
- `syntax_rate` measures whether generated assertion strings parse as Python.
- `execution_pass_rate` measures whether generated assertions execute against the provided reference implementation.
- `failure_rate` counts calls with schema failure or at least one generated assertion failing at execution time.
- `avg_latency_ms`, token counts, and token/s support the cost-effectiveness table in the IMRAD draft.

This is now a full local ULT Lite run for three Ollama models: 1.5B, 7B, and 14B. The expanded manuscript metrics are in `OLLAMA_ULT_LITE_EXTENDED_METRICS_VI.md`, including validity, correctness, robustness, stability, failure taxonomy proxy, and cost-efficiency tables.
