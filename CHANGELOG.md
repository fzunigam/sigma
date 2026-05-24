# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- Improved visual consistency, contrast, and layout of the SwiftUI macOS application (`/macos`) to adhere strictly to the monochrome design language.
- Replaced standard native `Picker` controls in the transaction entry popup with custom-styled dropdown `Menu` selectors and custom segment button toggles, eliminating native blue tinting issues.

### Fixed
- Fixed contrast issues where table headers, row items, and text fields in `AccountsView` and `RenderView` rendered low-contrast or invisible (white text on white background) under macOS Dark Mode.
- Applied `.preferredColorScheme(.light)` globally to ensure system-drawn controls, date pickers, and popovers are consistently legible and stark black-on-white.

## [0.2.1] - 2026-05-24

### Added
- Database refactoring to support multi-device sync: migrated movements, transfers, and render history tables from auto-incrementing integer IDs to UUIDv4 strings.
- Added sync metadata columns (`updated_at` and `deleted_at`) to accounts, movements, transfers, and render history schemas.
- Implemented soft deletes (tombstones) across the application to track offline deletions.
- Added automatic SQLite schema migrations to upgrade existing databases to the new UUID/sync-aware schema on startup.
- Support for prefix-matching resolution in the CLI delete command, allowing users to copy/paste visual short ID prefixes (e.g. `m-3f2504e0`) for deletion.
- Added backward-compatible CSV/ZIP data import capability to automatically map legacy integer IDs to UUIDs and default sync metadata columns.

### Changed
- Improved the `sgm config` command with an interactive terminal menu using arrow-key navigation and Escape-to-cancel support.
- Integrated Telegram Bot Token and Allowed User IDs setup directly into the main config menu.
- Enhanced configuration UI visuals with cyan styling matching the Sigma brand theme.

### Fixed
- Fixed Docker build failure where setuptools `egg_info` failed during dependency caching step because the `src` directory did not exist yet in the build context.
- Fixed a bug where terminal arrow-key escape sequences were incorrectly processed as standalone Escape/exit events due to Python's buffered standard input stream reading. Bypassed buffering using raw OS descriptor reads.

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