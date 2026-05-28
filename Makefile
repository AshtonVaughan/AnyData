.PHONY: install dev test probe demo gui lint clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

dev-gui:
	pip install -e ".[dev,gui]"

test:
	pytest tests/

probe:
	python -m scripts.probe_provider

demo:
	@echo "Phase 2 (arithmetic pack) not yet built."
	@false

gui:
	@echo "Phase 4 (PySide6 control panel) not yet built."
	@false

lint:
	ruff check factory/ tests/ scripts/

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache build dist *.egg-info
