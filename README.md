# Sigma (`sgm`)

Sigma is a CLI-first personal finance tracker focused on fast transaction logging and auditable render snapshots.

## Quickstart
```bash
pip install sigma-finance
sgm start
```

## Setup and persistence
- First-run setup: `sgm start` (writes `~/.config/sgm/config.toml`)

## Development
```bash
python3.12 -m venv .venv
source .venv/bin/activate
make install
make lint
make test
```

## Testing approach
- **Smoke tests** (`tests/smoke`): end-to-end CLI flows with Typer `CliRunner`.

## Versioning and changelog process
- Sigma follows **Semantic Versioning**.
- `CHANGELOG.md` follows **Keep a Changelog**.
- Keep `pyproject.toml` and `src/sgm/__init__.py` versions in sync.

## Documentation
- Architecture: `docs/architecture.md`
- Decision log: `docs/decisions/`
- Conventions: `docs/conventions/`
