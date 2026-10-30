# Evidence manifest

The current release retains 27,108 historical responses, 600 wrapper mutants,
14,874 historical mutation evaluations, 600 primary second-family request records,
and 49 exploratory probe responses. The extension oracle cache covers the 600
primary responses, with 300 process-isolated ULT reference evaluations.

`SHA256SUMS` covers frozen observations, design/provenance records, and retained
oracle evaluations. `check_artifact.py` checks design coverage, uniqueness,
response hashes, and logical nesting of the acceptance predicates. Statistical
outputs can be regenerated with `make analyze`; empirical displays with
`make displays`.

## Included paths

- `.gitignore`
- `CITATION.cff`
- `LICENSE`
- `Makefile`
- `README.md`
- `analyze_quality_gates.py`
- `build_empirical_displays.py`
- `check_artifact.py`
- `evaluate_ult_responses.py`
- `mutants.py`
- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_mutation_detection_raw.csv`
- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_raw.csv`
- `pilot_outputs/ollama_ult_lite/ollama_ult_lite_synthetic_mutants.csv`
- `pilot_outputs/similo_ollama/similo_ollama_raw.csv`
- `requirements.txt`
- `results/displays/Fig1.eps`
- `results/displays/Fig2.eps`
- `results/displays/cost_gate.pdf`
- `results/displays/paired_drops.pdf`
- `results/family_extension/design.json`
- `results/family_extension/design_amendment.json`
- `results/family_extension/design_initial.json`
- `results/family_extension/environment.json`
- `results/family_extension/evaluated.jsonl`
- `results/family_extension/execution_sessions.jsonl`
- `results/family_extension/reference_evaluations.jsonl`
- `results/family_extension/responses.jsonl`
- `results/quality_gates/extension_evaluated.csv`
- `results/quality_gates/extension_generation_diagnostics.csv`
- `results/quality_gates/historical_additional_insights.csv`
- `results/quality_gates/historical_case_decisions.csv`
- `results/quality_gates/historical_cost_gate.csv`
- `results/quality_gates/historical_gate_retention.csv`
- `results/quality_gates/historical_holdout.csv`
- `results/quality_gates/historical_paired_drops.csv`
- `results/quality_gates/historical_stability.csv`
- `results/quality_gates/historical_summary.csv`
- `results/quality_gates/matched_family_differences.csv`
- `results/quality_gates/matched_stability.csv`
- `results/quality_gates/matched_summary.csv`
- `run_family_extension.py`
- `run_ollama_ult_lite_experiment.py`
- `run_similo_ollama_experiment.py`

Manuscripts, journal templates, reviewer correspondence, local audit notes, runtime caches, and third-party benchmark downloads are excluded.
