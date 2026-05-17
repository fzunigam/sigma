# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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