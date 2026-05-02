# Thong ke, Oracle Ablation va Cost Cho ULT Lite

Bao cao nay bo sung cac bang can thiet de dua study tu pilot sang dang gan voi chuan Q1/STVR hon.

## 1. 95% Bootstrap Confidence Intervals

Bootstrap 2,000 vong tren tung condition model x variant. Bang day nen dua vao appendix; manuscript chinh chi can trich cac metric quan trong.

### Full-pass CI

| Model | Variant | n | Estimate | 95% CI |
|---|---|---:|---:|---:|
| qwen2.5-coder:1.5b | noise | 600 | 0.0167 | [0.0067, 0.0283] |
| qwen2.5-coder:1.5b | original | 600 | 0.0183 | [0.0083, 0.03] |
| qwen2.5-coder:1.5b | paraphrase | 600 | 0.0117 | [0.0033, 0.02] |
| qwen2.5-coder:14b | noise | 600 | 0.0517 | [0.035, 0.07] |
| qwen2.5-coder:14b | original | 600 | 0.0567 | [0.04, 0.075] |
| qwen2.5-coder:14b | paraphrase | 600 | 0.0517 | [0.035, 0.07] |
| qwen2.5-coder:7b | noise | 600 | 0.0283 | [0.0167, 0.0433] |
| qwen2.5-coder:7b | original | 600 | 0.0283 | [0.015, 0.0433] |
| qwen2.5-coder:7b | paraphrase | 600 | 0.0283 | [0.0167, 0.0417] |

### Assertion-success CI

| Model | Variant | n | Estimate | 95% CI |
|---|---|---:|---:|---:|
| qwen2.5-coder:1.5b | noise | 600 | 0.104 | [0.088, 0.1212] |
| qwen2.5-coder:1.5b | original | 600 | 0.1039 | [0.0863, 0.1228] |
| qwen2.5-coder:1.5b | paraphrase | 600 | 0.0633 | [0.0499, 0.0776] |
| qwen2.5-coder:14b | noise | 600 | 0.275 | [0.2517, 0.2983] |
| qwen2.5-coder:14b | original | 600 | 0.285 | [0.262, 0.3093] |
| qwen2.5-coder:14b | paraphrase | 600 | 0.2657 | [0.242, 0.2907] |
| qwen2.5-coder:7b | noise | 600 | 0.2269 | [0.2061, 0.2496] |
| qwen2.5-coder:7b | original | 600 | 0.2267 | [0.2061, 0.2496] |
| qwen2.5-coder:7b | paraphrase | 600 | 0.2251 | [0.2037, 0.247] |

## 2. Oracle Ablation

Bang nay tra loi cau hoi: neu chi dung schema-only thi bo sot bao nhieu failure so voi them syntax/execution oracle.

| Model | Variant | Oracle | Failures | Rate | Increment |
|---|---|---|---:|---:|---:|
| qwen2.5-coder:1.5b | noise | schema_only | 87 | 0.145 | 87 |
| qwen2.5-coder:1.5b | noise | schema_plus_syntax | 104 | 0.1733 | 17 |
| qwen2.5-coder:1.5b | noise | schema_syntax_execution | 590 | 0.9833 | 486 |
| qwen2.5-coder:1.5b | original | schema_only | 55 | 0.0917 | 55 |
| qwen2.5-coder:1.5b | original | schema_plus_syntax | 77 | 0.1283 | 22 |
| qwen2.5-coder:1.5b | original | schema_syntax_execution | 589 | 0.9817 | 512 |
| qwen2.5-coder:1.5b | paraphrase | schema_only | 268 | 0.4467 | 268 |
| qwen2.5-coder:1.5b | paraphrase | schema_plus_syntax | 281 | 0.4683 | 13 |
| qwen2.5-coder:1.5b | paraphrase | schema_syntax_execution | 593 | 0.9883 | 312 |
| qwen2.5-coder:14b | noise | schema_only | 0 | 0.0 | 0 |
| qwen2.5-coder:14b | noise | schema_plus_syntax | 11 | 0.0183 | 11 |
| qwen2.5-coder:14b | noise | schema_syntax_execution | 569 | 0.9483 | 558 |
| qwen2.5-coder:14b | original | schema_only | 0 | 0.0 | 0 |
| qwen2.5-coder:14b | original | schema_plus_syntax | 12 | 0.02 | 12 |
| qwen2.5-coder:14b | original | schema_syntax_execution | 566 | 0.9433 | 554 |
| qwen2.5-coder:14b | paraphrase | schema_only | 0 | 0.0 | 0 |
| qwen2.5-coder:14b | paraphrase | schema_plus_syntax | 14 | 0.0233 | 14 |
| qwen2.5-coder:14b | paraphrase | schema_syntax_execution | 569 | 0.9483 | 555 |
| qwen2.5-coder:7b | noise | schema_only | 1 | 0.0017 | 1 |
| qwen2.5-coder:7b | noise | schema_plus_syntax | 13 | 0.0217 | 12 |
| qwen2.5-coder:7b | noise | schema_syntax_execution | 583 | 0.9717 | 570 |
| qwen2.5-coder:7b | original | schema_only | 0 | 0.0 | 0 |
| qwen2.5-coder:7b | original | schema_plus_syntax | 12 | 0.02 | 12 |
| qwen2.5-coder:7b | original | schema_syntax_execution | 583 | 0.9717 | 571 |
| qwen2.5-coder:7b | paraphrase | schema_only | 3 | 0.005 | 3 |
| qwen2.5-coder:7b | paraphrase | schema_plus_syntax | 15 | 0.025 | 12 |
| qwen2.5-coder:7b | paraphrase | schema_syntax_execution | 583 | 0.9717 | 568 |

## 3. Cost-Effectiveness

| Model | Variant | Median ms/call | Full passes | ms/full-pass | Oracle failures | ms/oracle failure | Mutation kills | ms/killed mutation eval |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| qwen2.5-coder:1.5b | noise | 2092.3 | 10 | 188847.95 | 590 | 3200.81 | 312 | 6052.82 |
| qwen2.5-coder:1.5b | original | 2149.24 | 11 | 199697.03 | 589 | 3729.49 | 285 | 7707.6 |
| qwen2.5-coder:1.5b | paraphrase | 2209.36 | 7 | 272726.35 | 593 | 3219.37 | 206 | 9267.4 |
| qwen2.5-coder:14b | noise | 8837.08 | 31 | 207733.39 | 569 | 11317.64 | 855 | 7531.85 |
| qwen2.5-coder:14b | original | 9577.29 | 34 | 196314.16 | 566 | 11792.72 | 895 | 7457.74 |
| qwen2.5-coder:14b | paraphrase | 8782.05 | 31 | 208342.49 | 569 | 11350.82 | 822 | 7857.2 |
| qwen2.5-coder:7b | noise | 3667.7 | 17 | 150413.41 | 583 | 4385.98 | 735 | 3478.95 |
| qwen2.5-coder:7b | original | 3718.26 | 17 | 152058.55 | 583 | 4433.95 | 706 | 3661.47 |
| qwen2.5-coder:7b | paraphrase | 3868.35 | 17 | 156258.94 | 583 | 4556.44 | 737 | 3604.34 |

## 4. Model Comparison Tren Original Variant

| A | B | Metric | Mean A | Mean B | Delta | A12 | Holm p |
|---|---|---|---:|---:|---:|---:|---:|
| qwen2.5-coder:14b | qwen2.5-coder:7b | assertion_success | 0.285 | 0.2267 | 0.0583 | 0.5598 | 1.0 |
| qwen2.5-coder:14b | qwen2.5-coder:7b | full_pass | 0.0567 | 0.0283 | 0.0283 | 0.5142 | 0.119883 |
| qwen2.5-coder:14b | qwen2.5-coder:7b | latency_ms | 11124.4691 | 4308.3255 | 6816.1436 | 0.9246 | 1.0 |
| qwen2.5-coder:7b | qwen2.5-coder:1.5b | assertion_success | 0.2267 | 0.1039 | 0.1228 | 0.6442 | 1.0 |
| qwen2.5-coder:7b | qwen2.5-coder:1.5b | full_pass | 0.0283 | 0.0183 | 0.01 | 0.505 | 1.0 |
| qwen2.5-coder:7b | qwen2.5-coder:1.5b | latency_ms | 4308.3255 | 3661.1123 | 647.2133 | 0.7701 | 1.0 |
| qwen2.5-coder:14b | qwen2.5-coder:1.5b | assertion_success | 0.285 | 0.1039 | 0.1811 | 0.7071 | 1.0 |
| qwen2.5-coder:14b | qwen2.5-coder:1.5b | full_pass | 0.0567 | 0.0183 | 0.0383 | 0.5192 | 0.00427 |
| qwen2.5-coder:14b | qwen2.5-coder:1.5b | latency_ms | 11124.4691 | 3661.1123 | 7463.3569 | 0.9522 | 1.0 |

## 5. Dien giai de dua vao bai

- Schema/parse gan dat tran voi 7B va 14B, nen schema-only khong du de danh gia reliability.
- Execution oracle la phan dong gop lon nhat trong failure detection, vi da so loi la assertion/semantic failure chu khong phai format failure.
- 14B co assertion-success va mutation detection tot nhat, nhung chi phi latency/full-pass cao; nen trinh bay nhu trade-off reliability-cost.
- CI cho full-pass van hep do n=600 moi condition, nhung full-pass tuyet doi thap; day la finding quan trong: output hop le khong dong nghia output dung.
- Phan statistical nay moi ap dung cho ULT Lite; de nop Q1 van can them domain thu hai hoac giai thich ro scope reproducible local study.

## Generated Files

- `ollama_ult_lite_statistical_ci.csv`
- `ollama_ult_lite_oracle_ablation.csv`
- `ollama_ult_lite_cost_effectiveness.csv`
- `ollama_ult_lite_model_comparison.csv`