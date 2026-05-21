# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.0] - 2026-05-21

### Added
- Telegram Bot Integration: Easily control SGM from Telegram.
- New `sgm bot setup` command to configure Telegram bot token and allowed user IDs.
- New `sgm bot run` command to start the Telegram bot daemon.
- Secure command authorization filtering to restrict bot control to specified Telegram users.
- Support for CLI commands mapped directly to Telegram messages (e.g. `exp`, `inc`, `tr`, `status`, `log`, `render`, `acc`).
- Added SQLite WAL (Write-Ahead Logging) mode activation when launching the bot for safe concurrent CLI and bot write access.
- Containerized bot deployment option using `Dockerfile` and `docker-compose.yml`.
- Expanded documentation with `docs/plans/telegram-deployment.md`.
- Automated smoke tests in `tests/smoke/test_telegram_bot.py`.

## [0.1.5] - 2026-05-17

### Added
- Data Export: New `sgm export` command to bundle all database tables into a timestamped ZIP file containing CSVs.
- Data Import: Integrated import option in `sgm start` setup wizard, allowing restoration from ZIP or folder.
- Robust data validation and schema checking for imported CSV files.
- Automated smoke tests for export and import functionalities.

## [0.1.4] - 2026-05-17

### Added
- Optional `[date]` argument (YYYY-MM-DD) for `exp`, `inc`, and `tr` commands.
- Smart ambiguity resolution for optional account ID and date in `exp`/`inc` commands.
- Automatic database migration of existing ISO timestamps to date-only format.

### Changed
- Transactions now store only the date (`YYYY-MM-DD`) instead of full date-time strings for cleaner logs and history.

## [0.1.3] - 2026-05-17

### Added
- Added `acc delete` command to remove accounts while preserving their transaction history in a hidden ghost account.
- Implemented protection for the reserved `deleted` account ID across all commands.
- Major README overhaul with improved structure, badges, and detailed usage documentation.
- Added comprehensive smoke tests for account deletion.

## [0.1.2] - 2026-05-10

### Added
- Expanded Python compatibility to support versions 3.10 and 3.11 (previously 3.12+).
- Added `tomli` as a dependency for Python < 3.11.

### Fixed
- Fixed test suite leaks where local user configuration could interfere with smoke tests.
- Improved Makefile flexibility by using generic `python3` commands.

## [0.1.1] - 2026-05-10

### Added
- First functional version
- Added all basic commands 