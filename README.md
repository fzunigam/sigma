# Sigma (`sgm`)

Sigma is a CLI-first personal finance tracker focused on fast transaction logging and auditable render snapshots.

## Project Status
- Core v0.1.0 foundations are implemented (domain model, SQLite repositories, CLI workflows, and test suites).
- The project is ready for iterative feature work on top of the current local-first baseline.

## v1 Scope
- Local CLI usage only.
- SQLite persistence (default: `~/.local/share/sgm/sigma.db`).
- Debit/Credit account tracking.
- Income/Expense movement logging (CLP integer pesos).
- Manual render workflow with immutable render history.

## Development
### Install
```bash
python3.12 -m venv .venv
source .venv/bin/activate
python3.12 -m pip install -e ".[dev]"
```

### Run
```bash
sgm --help
sgm --db ./sigma.db account create a1 "Checking" debit 120000
sgm --db ./sigma.db movement add m1 a1 "Salary" 100000 income
sgm --db ./sigma.db render run s1
```

### Test
```bash
python3.12 -m pytest -q
```

### Lint
```bash
python3.12 -m ruff check .
```

## Testing approach
- **Unit tests** (`tests/unit`): domain invariants, rendering use case, and small infrastructure helpers.
- **Integration tests** (`tests/integration`): SQLite schema + repository roundtrips against a real DB file.
- **Smoke tests** (`tests/smoke`): end-to-end CLI command flows with Typer `CliRunner` and isolated DB paths.
- Keep tests deterministic (fixed timestamps where needed, no network calls, no shared state).

## Versioning and changelog process
- Sigma follows **Semantic Versioning**.
- `CHANGELOG.md` follows **Keep a Changelog** with entries under `[Unreleased]` in these sections: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
- For each release, move relevant `[Unreleased]` entries into a versioned section (`## [x.y.z] - YYYY-MM-DD`) and reset `[Unreleased]`.
- Keep runtime version metadata aligned by bumping both `pyproject.toml` and `src/sgm/__init__.py`.

### Release checklist (concise)
1. Set the same release version in `pyproject.toml` and `src/sgm/__init__.py`.
2. Move completed `[Unreleased]` entries into `## [x.y.z] - YYYY-MM-DD` and reset `[Unreleased]` to an empty scaffold.
3. Run checks:
   - `python3.12 -m pytest -q`
   - `python3.12 -m ruff check .`
   - `PYTHONPATH=src python3.12 -m typer sgm.cli run --help` (or `sgm --help` if installed)

## Documentation
- Design: `docs/plans/2026-05-05-sigma-cli-finance-tracker-design.md`
- Architecture: `docs/architecture.md`
- Decision log: `docs/decisions/`
- Conventions: `docs/conventions/`
- Changelog: `CHANGELOG.md`
