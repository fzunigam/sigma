# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.2] - 2026-05-10

### Added
- Expanded Python compatibility to support versions 3.10 and 3.11 (previously 3.12+).
- Added `tomli` as a dependency for Python < 3.11.

### Fixed
- Fixed test suite leaks where local user configuration could interfere with smoke tests.
- Improved Makefile flexibility by using generic `python3` commands.

## [0.1.1] - 2026-05-10
