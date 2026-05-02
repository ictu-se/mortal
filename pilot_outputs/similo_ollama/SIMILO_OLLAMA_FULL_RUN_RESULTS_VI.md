# Ket qua full-run SimiloLLM bang Ollama

Raw rows hien co: 21708. Full plan target neu day du: 804 cases x 3 variants x 3 models x 3 repeats = 21,708 calls.

## Main Summary

| Model | Variant | Calls | JSON | Schema | Index valid | Top-k recall | Accuracy | Valid-wrong | Median ms | ms/correct |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen2.5-coder:1.5b | noise | 2412 | 0.978 | 0.978 | 0.978 | 0.9863 | 0.2927 | 0.6853 | 1063.4 | 4700.68 |
| qwen2.5-coder:1.5b | original | 2412 | 0.9871 | 0.9871 | 0.9871 | 0.9863 | 0.3176 | 0.6696 | 930.82 | 4156.62 |
| qwen2.5-coder:1.5b | paraphrase | 2412 | 0.9892 | 0.9892 | 0.9892 | 0.9863 | 0.3429 | 0.6464 | 893.7 | 3792.12 |
| qwen2.5-coder:14b | noise | 2412 | 1.0 | 1.0 | 1.0 | 0.9863 | 0.9013 | 0.0987 | 1511.24 | 7333.18 |
| qwen2.5-coder:14b | original | 2412 | 1.0 | 1.0 | 1.0 | 0.9863 | 0.8972 | 0.1028 | 1481.69 | 7323.53 |
| qwen2.5-coder:14b | paraphrase | 2412 | 1.0 | 1.0 | 1.0 | 0.9863 | 0.8814 | 0.1186 | 1508.45 | 7497.56 |
| qwen2.5-coder:7b | noise | 2412 | 1.0 | 1.0 | 1.0 | 0.9863 | 0.6439 | 0.3561 | 916.6 | 5063.48 |
| qwen2.5-coder:7b | original | 2412 | 1.0 | 1.0 | 1.0 | 0.9863 | 0.7102 | 0.2898 | 897.5 | 4570.85 |
| qwen2.5-coder:7b | paraphrase | 2412 | 1.0 | 1.0 | 1.0 | 0.9863 | 0.6625 | 0.3375 | 880.23 | 4864.0 |

## Accuracy CI

| Model | Variant | n | Accuracy | 95% CI |
|---|---|---:|---:|---:|
| qwen2.5-coder:1.5b | noise | 2412 | 0.2927 | [0.2753, 0.3109] |
| qwen2.5-coder:1.5b | original | 2412 | 0.3176 | [0.2989, 0.3362] |
| qwen2.5-coder:1.5b | paraphrase | 2412 | 0.3429 | [0.3238, 0.3619] |
| qwen2.5-coder:14b | noise | 2412 | 0.9013 | [0.8889, 0.9133] |
| qwen2.5-coder:14b | original | 2412 | 0.8972 | [0.8851, 0.9092] |
| qwen2.5-coder:14b | paraphrase | 2412 | 0.8814 | [0.8677, 0.8939] |
| qwen2.5-coder:7b | noise | 2412 | 0.6439 | [0.6252, 0.6625] |
| qwen2.5-coder:7b | original | 2412 | 0.7102 | [0.6928, 0.728] |
| qwen2.5-coder:7b | paraphrase | 2412 | 0.6625 | [0.6434, 0.6824] |

## Robustness

| Model | Perturbation | Original | Perturbed | Drop | Consistency | Metamorphic violation proxy |
|---|---|---:|---:|---:|---:|---:|
| qwen2.5-coder:1.5b | paraphrase | 0.3176 | 0.3429 | -0.0253 |  |  |
| qwen2.5-coder:1.5b | noise | 0.3176 | 0.2927 | 0.0249 |  |  |
| qwen2.5-coder:1.5b | cross_variant |  |  |  | 0.8126 | 0.1642 |
| qwen2.5-coder:14b | paraphrase | 0.8972 | 0.8814 | 0.0158 |  |  |
| qwen2.5-coder:14b | noise | 0.8972 | 0.9013 | -0.0041 |  |  |
| qwen2.5-coder:14b | cross_variant |  |  |  | 0.9606 | 0.0373 |
| qwen2.5-coder:7b | paraphrase | 0.7102 | 0.6625 | 0.0477 |  |  |
| qwen2.5-coder:7b | noise | 0.7102 | 0.6439 | 0.0663 |  |  |
| qwen2.5-coder:7b | cross_variant |  |  |  | 0.8657 | 0.1244 |

## Flakiness

| Model | Stable pass | Flaky | Stable fail |
|---|---:|---:|---:|
| qwen2.5-coder:1.5b | 577 | 371 | 1464 |
| qwen2.5-coder:14b | 2143 | 24 | 245 |
| qwen2.5-coder:7b | 1567 | 112 | 733 |

## Interpretation

- Day la domain thu hai chay cung protocol voi ULT Lite: structured output, oracle ro, perturbation, repeat va cost.
- `top_k_recall_ceiling` can duoc bao cao rieng vi LLM chi co the dung neu deterministic prefilter dua oracle vao candidate set.
- `valid_but_wrong_rate` la loi semantic chinh cua domain nay: model tra JSON hop le va index hop le nhung chon sai element.
- Neu raw rows chua dat 21,708 thi day la partial/resumable run; tiep tuc chay script se skip rows da co.