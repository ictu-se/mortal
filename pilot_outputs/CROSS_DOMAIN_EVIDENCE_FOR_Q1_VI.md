# Cross-Domain Evidence Summary

This report is generated from the artifact CSV files. It summarizes the two
main empirical domains used by MORTAL: ULT Lite unit test generation and
SimiloLLM web element localization.

## Domain 1: ULT Lite Unit Test Generation

| Model | Variant | Calls | Schema | Assertion success | Strict suite | Positive execution |
|---|---|---:|---:|---:|---:|---:|
| qwen2.5-coder:1.5b | noise | 600 | 0.8550 | 0.1040 | 0.0167 | 0.2317 |
| qwen2.5-coder:1.5b | original | 600 | 0.9083 | 0.1039 | 0.0183 | 0.2133 |
| qwen2.5-coder:1.5b | paraphrase | 600 | 0.5533 | 0.0633 | 0.0117 | 0.1450 |
| qwen2.5-coder:14b | noise | 600 | 1.0000 | 0.2750 | 0.0517 | 0.6133 |
| qwen2.5-coder:14b | original | 600 | 1.0000 | 0.2850 | 0.0567 | 0.6450 |
| qwen2.5-coder:14b | paraphrase | 600 | 1.0000 | 0.2657 | 0.0517 | 0.5917 |
| qwen2.5-coder:7b | noise | 600 | 0.9983 | 0.2269 | 0.0283 | 0.5300 |
| qwen2.5-coder:7b | original | 600 | 1.0000 | 0.2267 | 0.0283 | 0.5200 |
| qwen2.5-coder:7b | paraphrase | 600 | 0.9950 | 0.2251 | 0.0283 | 0.5383 |

### ULT Lite Mutation Detection

| Model | Variant | Evaluations | Failure detection | Unique mutant detection | Ref-usable rate |
|---|---|---:|---:|---:|---:|
| qwen2.5-coder:1.5b | noise | 1506 | 0.2072 | 0.2656 | 0.2809 |
| qwen2.5-coder:1.5b | original | 1599 | 0.1782 | 0.2366 | 0.2383 |
| qwen2.5-coder:1.5b | paraphrase | 981 | 0.21 | 0.2603 | 0.2661 |
| qwen2.5-coder:14b | noise | 1800 | 0.475 | 0.5183 | 0.6133 |
| qwen2.5-coder:14b | original | 1800 | 0.4972 | 0.5483 | 0.645 |
| qwen2.5-coder:14b | paraphrase | 1800 | 0.4567 | 0.5167 | 0.5917 |
| qwen2.5-coder:7b | noise | 1797 | 0.409 | 0.4633 | 0.5309 |
| qwen2.5-coder:7b | original | 1800 | 0.3922 | 0.4467 | 0.52 |
| qwen2.5-coder:7b | paraphrase | 1791 | 0.4115 | 0.4733 | 0.541 |

## Domain 2: SimiloLLM Web Element Localization

| Model | Variant | Calls | Index valid | Top-k recall | Accuracy | Valid but wrong |
|---|---|---:|---:|---:|---:|---:|
| qwen2.5-coder:1.5b | noise | 2412 | 0.978 | 0.9863 | 0.2927 | 0.6853 |
| qwen2.5-coder:1.5b | original | 2412 | 0.9871 | 0.9863 | 0.3176 | 0.6696 |
| qwen2.5-coder:1.5b | paraphrase | 2412 | 0.9892 | 0.9863 | 0.3429 | 0.6464 |
| qwen2.5-coder:14b | noise | 2412 | 1.0 | 0.9863 | 0.9013 | 0.0987 |
| qwen2.5-coder:14b | original | 2412 | 1.0 | 0.9863 | 0.8972 | 0.1028 |
| qwen2.5-coder:14b | paraphrase | 2412 | 1.0 | 0.9863 | 0.8814 | 0.1186 |
| qwen2.5-coder:7b | noise | 2412 | 1.0 | 0.9863 | 0.6439 | 0.3561 |
| qwen2.5-coder:7b | original | 2412 | 1.0 | 0.9863 | 0.7102 | 0.2898 |
| qwen2.5-coder:7b | paraphrase | 2412 | 1.0 | 0.9863 | 0.6625 | 0.3375 |

## Interpretation

- ULT Lite stresses executable and fault-detection oracles.
- SimiloLLM stresses valid structured decisions and exact target matching.
- The two domains show why schema validity, semantic correctness, robustness, stability, and cost should be reported separately.