# Sigma (`sgm`)

Sigma is a CLI-first personal finance tracker focused on fast transaction logging and auditable render snapshots.

## Quickstart
```bash
pip install sgm
sgm start
sgm income cash 100000 "Salary"
sgm expense cash 12000 "Groceries"
sgm pending
sgm render
sgm balances
```

## Daily command UX
- `sgm income <account> <amount> "<description>"`
- `sgm expense <account> <amount> "<description>"`
- `sgm pending`
- `sgm render [snapshot_id]`
- `sgm balances`

## Setup and persistence
- First-run setup: `sgm start` (writes `~/.config/sgm/config.toml`)
- Default database path: `~/.local/share/sgm/sigma.db`

## Development
```bash
python3.12 -m venv .venv
source .venv/bin/activate
make install
make lint
make test
make smoke
```

## Testing approach
- **Unit tests** (`tests/unit`): domain invariants and helpers.
- **Integration tests** (`tests/integration`): SQLite schema and repository roundtrips.
- **Smoke tests** (`tests/smoke`): end-to-end CLI flows with Typer `CliRunner`.

## Release automation
- CI runs lint + tests on pushes and pull requests.
- Tagged pushes (`v*`) build and publish to PyPI through Trusted Publishing.

## Versioning and changelog process
- Sigma follows **Semantic Versioning**.
- `CHANGELOG.md` follows **Keep a Changelog** with entries under `[Unreleased]`.
- Keep `pyproject.toml` and `src/sgm/__init__.py` versions in sync.

## Documentation
- Design: `docs/plans/2026-05-05-sigma-cli-finance-tracker-design.md`
- Architecture: `docs/architecture.md`
- Decision log: `docs/decisions/`
- Conventions: `docs/conventions/`
- CLI usage: `docs/cli-usage.md`
