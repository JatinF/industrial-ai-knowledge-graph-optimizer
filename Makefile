PYTHON ?= python

.PHONY: seed demo test benchmark

seed:
	$(PYTHON) scripts/seed_graph.py

demo:
	$(PYTHON) scripts/run_demo.py

test:
	$(PYTHON) -m pytest

benchmark:
	$(PYTHON) scripts/benchmark.py
