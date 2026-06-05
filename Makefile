.PHONY: help install test lint smoke

help:
	@echo "install test lint smoke"

install:
	@if command -v npm >/dev/null 2>&1; then \
		echo "Found npm, compiling web dashboard..."; \
		(cd web && npm install && npm run build); \
	else \
		echo "Warning: npm not found. Skipping web dashboard compilation."; \
	fi
	python3 -m pip install -e ".[dev,desktop]"

test:
	python3 -m pytest -q

lint:
	python3 -m ruff check .

smoke:
	python3 -m pytest tests/smoke -q
