# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Core CLI package structure and `sgm` entry point.
- `sgm start` command for first-run configuration.
- Branded startup banner and help text.
- User configuration persistence at `~/.config/sgm/config.toml`.
- Basic development tooling (Makefile, Ruff, Pytest).
- Continuous Integration workflow.

### Removed
- All previous development features (income, expense, pending, render, balances, accounts, transfers) as part of a project reset.
