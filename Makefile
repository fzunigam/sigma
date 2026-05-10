.PHONY: help install test lint smoke

help:
	@echo "install test lint smoke"

install:
	python3 -m pip install -e ".[dev]"

test:
	python3 -m pytest -q

lint:
	python3 -m ruff check .

smoke:
	python3 -m pytest tests/smoke -q
