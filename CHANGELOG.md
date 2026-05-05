# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- _No changes yet._

### Changed
- _No changes yet._

### Deprecated
- _No changes yet._

### Removed
- _No changes yet._

### Fixed
- _No changes yet._

### Security
- _No changes yet._

## [0.1.0] - 2026-05-05

### Added
- Bootstrapped the Python package (`pyproject.toml`, `src` layout, CLI entrypoint `sgm`) with dev tooling (`pytest`, `ruff`).
- Implemented core domain models and invariants for accounts, movements, CLP amounts, and domain-specific validation errors.
- Added render application workflow that computes income/expense/net snapshots and tracks processed movement IDs.
- Added SQLite schema initialization plus repositories for accounts, movements, transfers, and render history.
- Added simplified daily commands: `income`, `expense`, `pending`, `render`, and `balances`.
- Added first-run setup with `sgm start` and persisted user config at `~/.config/sgm/config.toml`.
- Added default database resolution at `~/.local/share/sgm/sigma.db`.
- Added CI workflow, pull request template, Makefile shortcuts, and tag-based PyPI publishing workflow.
- Added automated test suites split into unit, integration, and smoke coverage for domain logic, repositories, and CLI workflows.
- Added repository conventions documentation for Python coding and testing practices (`docs/conventions/python.md`, `docs/conventions/testing.md`).

### Changed
- Expanded contributor-facing docs with simplified CLI quickstart, make-based dev commands, and release automation guidance.
- Updated agent guidance to include current project-specific test and lint command usage.
