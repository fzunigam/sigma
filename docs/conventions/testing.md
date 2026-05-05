# Testing Conventions

## Test suite structure
- `tests/unit`: fast, isolated tests for domain logic and application helpers.
- `tests/integration`: SQLite schema/repository roundtrips using real DB files.
- `tests/smoke`: CLI command behavior through Typer `CliRunner`.

## Naming and organization
- Name files `test_*.py` and test functions `test_<behavior>()`.
- Group tests by layer and module path (for example `tests/unit/domain/test_movements.py`).

## Fixtures and isolation
- Use built-in pytest fixtures (`tmp_path`, `monkeypatch`) for filesystem/env isolation.
- Integration and smoke tests must use per-test SQLite files under `tmp_path`.
- Prefer local helpers inside a test module (for example `_invoke`) before introducing shared fixtures.

## Assertions and behavior
- Assert both success paths and invariant/error paths.
- For CLI tests, assert exit code and key output signals (table content, summary lines, error text).
- Keep tests deterministic: use fixed timestamps when checking rendered metadata.

## Commands
- Run all tests: `python3.12 -m pytest -q`
- Run lint checks: `python3.12 -m ruff check .`
