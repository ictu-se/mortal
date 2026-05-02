# Phan tich fault detection bang mutation testing cho Ollama ULT Lite

So synthetic mutants duoc tao: 600 tren 200 tasks.
Gioi han: toi da 3 mutants/task; mutant khong loc bang `test_list` chuan vi nhieu reference task trong ULT Lite khong pass day du official tests.

## Mutation operators

| Mutation type | Count |
|---|---:|
| first_argument_perturbation | 200 |
| return_none | 200 |
| return_value_corruption | 200 |

## Failure detection summary

| Model | Variant | Eval mutants | Unique mutants | Killed evals | Failure detection rate | Unique mutant detection | Ref-usable rate | Avg ref pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| qwen2.5-coder:1.5b | noise | 1506 | 546 | 312 | 0.2072 | 0.2656 | 0.2809 | 0.1284 |
| qwen2.5-coder:1.5b | original | 1599 | 558 | 285 | 0.1782 | 0.2366 | 0.2383 | 0.1191 |
| qwen2.5-coder:1.5b | paraphrase | 981 | 411 | 206 | 0.21 | 0.2603 | 0.2661 | 0.1194 |
| qwen2.5-coder:14b | noise | 1800 | 600 | 855 | 0.475 | 0.5183 | 0.6133 | 0.2778 |
| qwen2.5-coder:14b | original | 1800 | 600 | 895 | 0.4972 | 0.5483 | 0.645 | 0.2868 |
| qwen2.5-coder:14b | paraphrase | 1800 | 600 | 822 | 0.4567 | 0.5167 | 0.5917 | 0.2678 |
| qwen2.5-coder:7b | noise | 1797 | 600 | 735 | 0.409 | 0.4633 | 0.5309 | 0.2295 |
| qwen2.5-coder:7b | original | 1800 | 600 | 706 | 0.3922 | 0.4467 | 0.52 | 0.23 |
| qwen2.5-coder:7b | paraphrase | 1791 | 600 | 737 | 0.4115 | 0.4733 | 0.541 | 0.2278 |

## Interpretation

- `failure_detection_rate`: ty le evaluation ma generated tests pass tren reference va kill duoc mutant.
- `unique_mutant_detection_rate`: ty le mutant rieng biet duoc kill boi it nhat mot generated-test set trong cung model/variant.
- `ref_usable_rate`: ty le evaluation co it nhat mot generated assertion pass tren reference; neu thap thi model tao oracle sai, khong nen tinh la fault detector tot.
- Day la mutation-based fault detection that su hon proxy oracle-violation: generated tests phai pass tren implementation goc roi moi duoc tinh neu kill mutant.
- Mutants la synthetic faults, khong thay the defect benchmark thuc te. Nen bao cao la mutation score/fault-detection proxy.
