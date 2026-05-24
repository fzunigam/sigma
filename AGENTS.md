# Sigma

Sigma is a CLI-first personal finance tracker focused on fast transaction logging and auditable render snapshots.

## Stack
- Python 3.12
- SQLite
- Typer + Rich

## Guidance
- Architecture overview: `docs/architecture.md`
- Coding conventions: `docs/conventions/`
- Decision log: `docs/decisions/`
- Implementation plans: `docs/plans/`

## Commands
- Install dev setup: `python3.12 -m pip install -e ".[dev,telegram]"`
- Run tests: `python3.12 -m pytest -q`
- Run lint: `python3.12 -m ruff check .`
- Convenience commands: `make install`, `make test`, `make lint`, `make smoke`

## Changelog
Keep `CHANGELOG.md` up to date. Add entries under `[Unreleased]` for every meaningful change using: Added, Changed, Deprecated, Removed, Fixed, Security.
