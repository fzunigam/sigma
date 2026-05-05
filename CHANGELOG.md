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
- Implemented Typer CLI command groups for `account`, `movement`, `transfer`, `render`, and `report`, including a global `--db` override.
- Added default configuration for local data storage at `~/.local/share/sgm/sigma.db`.
- Added automated test suites split into unit, integration, and smoke coverage for domain logic, repositories, and CLI workflows.
- Added repository conventions documentation for Python coding and testing practices (`docs/conventions/python.md`, `docs/conventions/testing.md`).

### Changed
- Expanded contributor-facing docs with concrete development commands, testing approach, and versioning/changelog workflow guidance.
- Updated agent guidance to include current project-specific test and lint command usage.
