# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.1] - 2026-05-10

### Added
- Core CLI package structure and `sgm` entry point.
- `sgm start` command for first-run configuration.
- Branded startup banner and help text.
- User configuration persistence at `~/.config/sgm/config.toml`.
- Functional implementation of core finance features:
  - Account management (`sgm acc`): add, list, rename, set-limit.
  - Transaction logging (`sgm exp`, `sgm inc`, `sgm tr`).
  - History and auditing (`sgm log`, `sgm status`).
  - Render snapshots (`sgm render`, `sgm restore`).
  - Record deletion (`sgm delete`).
  - Configuration management (`sgm config`).
- Basic development tooling (Makefile, Ruff, Pytest).
- Continuous Integration workflow.

### Fixed
- Fixed several inconsistencies in CLI command handling.
- Improved database migration logic for schema updates.
