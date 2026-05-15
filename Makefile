.PHONY: test validate simulate-normal simulate-fall

PYTHON ?= python

test:
	$(PYTHON) -m pytest tests

validate:
	$(PYTHON) scripts/validate_configs.py

simulate-normal:
	$(PYTHON) scripts/simulate_events.py normal_activity

simulate-fall:
	$(PYTHON) scripts/simulate_events.py fall_suspected
