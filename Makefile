PYTHON ?= python3

.PHONY: check analyze ult similo cross

check:
	$(PYTHON) check_artifact.py

analyze:
	$(PYTHON) analyze_ollama_ult_lite_metrics.py
	$(PYTHON) analyze_q1_readiness_stats.py
	$(PYTHON) analyze_similo_ollama_results.py
	$(PYTHON) build_cross_domain_evidence.py

ult:
	$(PYTHON) run_ollama_ult_lite_experiment.py --limit 200 --repeats 3

similo:
	$(PYTHON) run_similo_ollama_experiment.py --top-k 50 --repeats 3 --pull

cross:
	$(PYTHON) build_cross_domain_evidence.py
