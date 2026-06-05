# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Native macOS desktop app support: Added a new `sgm app` command to launch the web dashboard inside a native Cocoa WKWebView window wrapper using `pywebview` (compatible with macOS Monterey and newer). Added the `[desktop]` packaging extra.

### Removed
- Removed the Telegram bot integration (`sgm bot setup`, `sgm bot run`) and its associated code, configurations, docker files, tests, and deployment guides to simplify the codebase and project structure.

## [0.3.5] - 2026-05-30

### Added
- Web design guidelines: Added [design-guidelines.md](file:///Users/fzunigam/dev/personal/sigma/docs/conventions/design-guidelines.md) in the conventions directory and updated [AGENTS.md](file:///Users/fzunigam/dev/personal/sigma/AGENTS.md) to ensure all future web interface additions or changes adhere to these brand and tech guidelines.
- Web Dashboard "Marked" column: Added a column to the Chronological Activity table indicating if the transaction is marked for the next render cycle, placed directly after the Account column.
- Backend API transaction status: Included the `marked` status attribute in the `/api/v1/transactions` API response for movements and transfers.
- Movements Log Page: Added a "Movements" page to the web interface allowing filtering and auditing of all financial transactions (expenses, incomes, and transfers) by year and month. The page defaults to displaying the previous month's movements.
- Backend date-based filtering: Extended the GET `/api/v1/transactions` endpoint and database `get_recent_logs` method to optionally filter transactions by year and month using a `year_month` string parameter (formatted as `YYYY-MM`).

## [0.3.4] - 2026-05-24

### Added
- Auto-compile Frontend: The `sgm web` command now dynamically locates the `web/` source directory (including parent folders) and automatically builds the frontend dashboard, copying compiled assets to the active server directory on clean package installations.
- CI Workflow Integration: Added automatic Next.js frontend compilation to the Publish to PyPI release workflow, ensuring Python wheels are pre-packaged with frontend static files.
- Makefile compilation: Added conditional frontend compilation to `make install` if `npm` is present.

## [0.3.3] - 2026-05-24 [YANKED]

### Added
- Auto-compile Frontend: The `sgm web` command now automatically compiles the frontend static dashboard (using `npm install` and `npm run build`) if the static assets are missing, ensuring a seamless startup experience.

### Changed
- Package Data: Configured setuptools packaging in `pyproject.toml` to include compiled static web dashboard assets under `src/sgm/interface/web/static` in package distributions.

## [0.3.2] - 2026-05-24

### Changed
- Modified the `sgm restore` command to delete the sqlite database (`sigma.db`) and the config file (`config.toml`) instead of just emptying the tables, resetting Sigma to its first-run state.

### Fixed
- Fixed GitHub Action CI test failure by adding `httpx` to dev dependencies and ensuring `telegram` optional dependencies are installed during the CI test run.

## [0.3.1] - 2026-05-24

### Added
- Credit Card Transfer Validation: Transfers from credit card accounts are now blocked in both the CLI and web interface.
- Credit Card Balance Validation: Transfers to credit card accounts that would result in a negative balance (overpaying the card) are now blocked in both the CLI and web interface.

### Fixed
- Fixed a validation message in the React frontend where source and destination accounts being identical reported that they "must be identical".
- Fixed a TypeScript deprecation error in `web/tsconfig.json` by updating the deprecated `moduleResolution=node` setting to `bundler`.

## [0.3.0] - 2026-05-24

### Added
- Local Web Dashboard: Added the `sgm web` command to spin up a local FastAPI server serving a statically exported Next.js client on localhost.
- Designed a minimalist, responsive web dashboard utilizing Tailwind CSS v4 and an OKLCH color palette.
- Light/Dark theme toggle integration directly accessible on the sidebar.
- Form logging actions (Expense, Income, Transfer) with input validations, double-check deletion confirmations, and live toast alerts (complying with Vercel Web Interface Guidelines).
- SPA catch-all static router supporting Next.js client-side subroute page refreshes without 404 errors.
- Added comprehensive integration and smoke test suites for API endpoints and CLI commands.

### Changed
- Added `fastapi` and `uvicorn` as core Python dependencies to support the local web application.


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