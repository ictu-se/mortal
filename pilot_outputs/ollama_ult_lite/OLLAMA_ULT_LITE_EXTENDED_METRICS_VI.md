# Tong hop metric mo rong cho Ollama ULT Lite

Du lieu: 200 task ULT Lite x 3 bien the (original/paraphrase/noise) x 3 lan lap x 3 model = 5,400 luot goi.

Luu y ve fault detection: ULT Lite hien tai khong co seeded mutants/buggy implementations trong pipeline nay. Vi vay cac metric fault detection ben duoi la proxy dua tren oracle violation va failure type cua generated tests; de do dung failure detection rate that su can them buoc mutation testing hoac buggy-program injection.

## Bang metric chinh

| Model | Variant | Schema | Parse | Compile | Assertion success | Full-pass | pass@3 proxy | Oracle violation | Avg latency ms | P95 latency ms | ms/full-pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen2.5-coder:1.5b | noise | 0.8550 | 0.8550 | 0.8329 | 0.1040 | 0.0167 | 0.0250 | 0.9833 | 3147.47 | 7840.25 | 188847.95 |
| qwen2.5-coder:1.5b | original | 0.9083 | 0.9083 | 0.8828 | 0.1039 | 0.0183 | 0.0250 | 0.9817 | 3661.11 | 7215.15 | 199697.03 |
| qwen2.5-coder:1.5b | paraphrase | 0.5533 | 0.5533 | 0.5404 | 0.0633 | 0.0117 | 0.0150 | 0.9883 | 3181.81 | 7958.36 | 272726.35 |
| qwen2.5-coder:14b | noise | 1.0000 | 1.0000 | 0.9953 | 0.2750 | 0.0517 | 0.0650 | 0.9483 | 10732.89 | 22495.2 | 207733.39 |
| qwen2.5-coder:14b | original | 1.0000 | 1.0000 | 0.9953 | 0.2850 | 0.0567 | 0.0700 | 0.9433 | 11124.47 | 22040.75 | 196314.16 |
| qwen2.5-coder:14b | paraphrase | 1.0000 | 1.0000 | 0.9950 | 0.2657 | 0.0517 | 0.0600 | 0.9483 | 10764.36 | 20826.88 | 208342.49 |
| qwen2.5-coder:7b | noise | 0.9983 | 0.9983 | 0.9894 | 0.2269 | 0.0283 | 0.0450 | 0.9717 | 4261.71 | 8231.76 | 150413.41 |
| qwen2.5-coder:7b | original | 1.0000 | 1.0000 | 0.9918 | 0.2267 | 0.0283 | 0.0350 | 0.9717 | 4308.33 | 8572.63 | 152058.55 |
| qwen2.5-coder:7b | paraphrase | 0.9950 | 0.9950 | 0.9889 | 0.2251 | 0.0283 | 0.0350 | 0.9717 | 4427.34 | 8373.46 | 156258.94 |

## Robustness

| Model | Perturbation | Assertion drop | Full-pass drop | Consistency | Metamorphic violation proxy | Same-repeat agreement |
|---|---|---:|---:|---:|---:|---:|
| qwen2.5-coder:1.5b | paraphrase | 0.0406 | 0.0067 |  |  |  |
| qwen2.5-coder:1.5b | noise | -0.0000 | 0.0017 |  |  |  |
| qwen2.5-coder:14b | paraphrase | 0.0193 | 0.0050 |  |  |  |
| qwen2.5-coder:14b | noise | 0.0100 | 0.0050 |  |  |  |
| qwen2.5-coder:7b | paraphrase | 0.0016 | 0.0000 |  |  |  |
| qwen2.5-coder:7b | noise | -0.0002 | 0.0000 |  |  |  |
| qwen2.5-coder:1.5b | cross_variant |  |  | 0.9103 | 0.2250 | 0.9850 |
| qwen2.5-coder:14b | cross_variant |  |  | 0.8990 | 0.1350 | 0.9717 |
| qwen2.5-coder:7b | cross_variant |  |  | 0.8969 | 0.1800 | 0.9783 |

## Reliability / Stability

| Model | Stable pass | Flaky | Stable fail | Flaky rate |
|---|---:|---:|---:|---:|
| qwen2.5-coder:1.5b | 7 | 6 | 587 | 0.0100 |
| qwen2.5-coder:14b | 25 | 14 | 561 | 0.0233 |
| qwen2.5-coder:7b | 11 | 12 | 577 | 0.0200 |

## Failure taxonomy proxy

| Model | Variant | Failure type | Count | Rate |
|---|---|---|---:|---:|
| qwen2.5-coder:1.5b | noise | AssertionError | 390 | 0.6500 |
| qwen2.5-coder:1.5b | noise | IndexError | 15 | 0.0250 |
| qwen2.5-coder:1.5b | noise | KeyError | 1 | 0.0017 |
| qwen2.5-coder:1.5b | noise | NameError | 55 | 0.0917 |
| qwen2.5-coder:1.5b | noise | TypeError | 21 | 0.0350 |
| qwen2.5-coder:1.5b | noise | ValueError | 4 | 0.0067 |
| qwen2.5-coder:1.5b | noise | invalid_json | 16 | 0.0267 |
| qwen2.5-coder:1.5b | noise | schema_no_tests | 71 | 0.1183 |
| qwen2.5-coder:1.5b | noise | syntax_error | 17 | 0.0283 |
| qwen2.5-coder:1.5b | original | AssertionError | 394 | 0.6567 |
| qwen2.5-coder:1.5b | original | IndexError | 14 | 0.0233 |
| qwen2.5-coder:1.5b | original | KeyError | 2 | 0.0033 |
| qwen2.5-coder:1.5b | original | NameError | 62 | 0.1033 |
| qwen2.5-coder:1.5b | original | TypeError | 24 | 0.0400 |
| qwen2.5-coder:1.5b | original | ValueError | 16 | 0.0267 |
| qwen2.5-coder:1.5b | original | invalid_json | 19 | 0.0317 |
| qwen2.5-coder:1.5b | original | schema_no_tests | 36 | 0.0600 |
| qwen2.5-coder:1.5b | original | syntax_error | 22 | 0.0367 |
| qwen2.5-coder:1.5b | paraphrase | AssertionError | 246 | 0.4100 |
| qwen2.5-coder:1.5b | paraphrase | IndexError | 9 | 0.0150 |
| qwen2.5-coder:1.5b | paraphrase | KeyError | 4 | 0.0067 |
| qwen2.5-coder:1.5b | paraphrase | NameError | 42 | 0.0700 |
| qwen2.5-coder:1.5b | paraphrase | TypeError | 10 | 0.0167 |
| qwen2.5-coder:1.5b | paraphrase | ValueError | 1 | 0.0017 |
| qwen2.5-coder:1.5b | paraphrase | invalid_json | 10 | 0.0167 |
| qwen2.5-coder:1.5b | paraphrase | schema_no_tests | 258 | 0.4300 |
| qwen2.5-coder:1.5b | paraphrase | syntax_error | 13 | 0.0217 |
| qwen2.5-coder:14b | noise | AssertionError | 460 | 0.7667 |
| qwen2.5-coder:14b | noise | IndexError | 10 | 0.0167 |
| qwen2.5-coder:14b | noise | KeyError | 3 | 0.0050 |
| qwen2.5-coder:14b | noise | NameError | 74 | 0.1233 |
| qwen2.5-coder:14b | noise | TypeError | 10 | 0.0167 |
| qwen2.5-coder:14b | noise | missing_target_call | 1 | 0.0017 |
| qwen2.5-coder:14b | noise | syntax_error | 11 | 0.0183 |
| qwen2.5-coder:14b | original | AssertionError | 458 | 0.7633 |
| qwen2.5-coder:14b | original | IndexError | 5 | 0.0083 |
| qwen2.5-coder:14b | original | KeyError | 3 | 0.0050 |
| qwen2.5-coder:14b | original | NameError | 74 | 0.1233 |
| qwen2.5-coder:14b | original | TypeError | 10 | 0.0167 |
| qwen2.5-coder:14b | original | ValueError | 3 | 0.0050 |
| qwen2.5-coder:14b | original | missing_target_call | 1 | 0.0017 |
| qwen2.5-coder:14b | original | syntax_error | 12 | 0.0200 |
| qwen2.5-coder:14b | paraphrase | AssertionError | 464 | 0.7733 |
| qwen2.5-coder:14b | paraphrase | IndexError | 7 | 0.0117 |
| qwen2.5-coder:14b | paraphrase | KeyError | 6 | 0.0100 |
| qwen2.5-coder:14b | paraphrase | NameError | 72 | 0.1200 |
| qwen2.5-coder:14b | paraphrase | TypeError | 6 | 0.0100 |
| qwen2.5-coder:14b | paraphrase | syntax_error | 14 | 0.0233 |
| qwen2.5-coder:7b | noise | AssertionError | 465 | 0.7750 |
| qwen2.5-coder:7b | noise | IndexError | 15 | 0.0250 |
| qwen2.5-coder:7b | noise | KeyError | 2 | 0.0033 |
| qwen2.5-coder:7b | noise | NameError | 71 | 0.1183 |
| qwen2.5-coder:7b | noise | TypeError | 11 | 0.0183 |
| qwen2.5-coder:7b | noise | ValueError | 6 | 0.0100 |
| qwen2.5-coder:7b | noise | invalid_json | 1 | 0.0017 |
| qwen2.5-coder:7b | noise | syntax_error | 12 | 0.0200 |
| qwen2.5-coder:7b | original | AssertionError | 462 | 0.7700 |
| qwen2.5-coder:7b | original | IndexError | 13 | 0.0217 |
| qwen2.5-coder:7b | original | NameError | 71 | 0.1183 |
| qwen2.5-coder:7b | original | TypeError | 13 | 0.0217 |
| qwen2.5-coder:7b | original | ValueError | 9 | 0.0150 |
| qwen2.5-coder:7b | original | missing_target_call | 3 | 0.0050 |
| qwen2.5-coder:7b | original | syntax_error | 12 | 0.0200 |
| qwen2.5-coder:7b | paraphrase | AssertionError | 466 | 0.7767 |
| qwen2.5-coder:7b | paraphrase | IndexError | 17 | 0.0283 |
| qwen2.5-coder:7b | paraphrase | NameError | 70 | 0.1167 |
| qwen2.5-coder:7b | paraphrase | TypeError | 9 | 0.0150 |
| qwen2.5-coder:7b | paraphrase | ValueError | 6 | 0.0100 |
| qwen2.5-coder:7b | paraphrase | invalid_json | 3 | 0.0050 |
| qwen2.5-coder:7b | paraphrase | syntax_error | 12 | 0.0200 |

## Dien giai nhanh

- Validity: 7B va 14B gan nhu dat tran ve JSON/schema; 1.5B yeu hon ro, dac biet voi paraphrase.
- Correctness: 14B co assertion-success cao nhat, nhung full-pass van thap; day la bang chung rang format dung khong dong nghia voi oracle dung.
- Robustness: drop giua original va paraphrase/noise can duoc bao cao rieng, vi mot so model co schema on dinh nhung semantic consistency kem.
- Reliability: flakiness nen bao cao theo task-variant, khong chi theo call trung binh.
- Cost: 14B tang chat luong nhung latency/tokens per successful full-pass tang manh; day la trade-off chinh cho bai bao.
- Fault detection: can bo sung mutation/bug injection neu muon dung thuat ngu failure detection rate theo nghia nghiem ngat.
