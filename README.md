# Sigma (`sgm`)

Sigma is a CLI-first personal finance tracker focused on fast logging and auditable render snapshots.

## Project Status
- Design approved.
- Implementation planning is the next phase.

## v1 Scope
- Local CLI usage only.
- SQLite persistence (default: `~/.local/share/sgm/sigma.db`).
- Debit/Credit account tracking.
- Income/Expense movement logging (CLP integer pesos).
- Manual render workflow with immutable render history.

## Documentation
- Design: `docs/plans/2026-05-05-sigma-cli-finance-tracker-design.md`
- Architecture: `docs/architecture.md`
- Decision log: `docs/decisions/`
- Conventions: `docs/conventions/`
- Changelog: `CHANGELOG.md`

## Versioning
This project follows Semantic Versioning and Keep a Changelog.
The initial release line starts at `0.1.0`.
