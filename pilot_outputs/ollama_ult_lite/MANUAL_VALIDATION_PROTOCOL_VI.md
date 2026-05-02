# Quy trinh manual validation cho ULT Lite

File can annotate: `manual_validation_sample_ult_lite.csv`.

Muc tieu: kiem tra xem auto-oracle va failure taxonomy co dang tin khong, va tao bang manual taxonomy cho manuscript.

## Mau duoc lay

| Sample type | Target count | Y nghia |
|---|---:|---|
| format_schema_failure | 40 | Loi JSON/schema |
| syntax_failure | 40 | Assertion/code khong parse/compile |
| semantic_execution_failure | 80 | Assertion chay duoc nhung sai oracle |
| missing_target_call | toi da 20 | Test khong goi ham can test |
| full_pass | 40 | Mau doi chung pass day du |
| mutation_killed | 50 | Generated tests kill synthetic mutant |

## Label nen dung

| Label | Mo ta |
|---|---|
| correct_failure | Auto oracle dung, day la failure that |
| false_positive | Auto oracle bao fail nhung manual thay chap nhan duoc |
| weak_test | Test pass/fail nhung qua yeu, khong kiem tra hanh vi quan trong |
| wrong_oracle | Assertion ky vong sai voi dac ta/reference |
| non_executable | Output khong the chay hop le |
| format_error | Output sai JSON/schema |
| hallucinated_entity | Goi bien/ham/entity khong ton tai |
| mutation_valid_kill | Mutant kill hop ly |
| mutation_questionable | Mutant/test kill khong co y nghia ro |

## Cach bao cao

- Can it nhat 2 annotators neu co the.
- Bao cao agreement: percent agreement hoac Cohen's kappa.
- Dua 3-5 vi du failure representative vao paper.
- Neu chi co 1 annotator, dua vao threats to validity.