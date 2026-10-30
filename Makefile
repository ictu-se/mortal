PYTHON ?= python3
DATASETS ?= reproduction_datasets

.PHONY: install check analyze historical displays acquire
install:
	$(PYTHON) -m pip install -r requirements.txt
check:
	$(PYTHON) check_artifact.py
analyze:
	$(PYTHON) analyze_quality_gates.py --datasets "$(DATASETS)"
historical:
	$(PYTHON) analyze_quality_gates.py --historical-only
displays:
	$(PYTHON) build_empirical_displays.py
acquire:
	$(PYTHON) run_family_extension.py --datasets "$(DATASETS)" --variants original --workers 1
