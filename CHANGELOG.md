# Changelog

Cambios que se notan al usar Sigma. Formato:
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.1.0] - 2026-07-26

### Added
- **Editar movimientos.** Cada fila de la lista tiene un lápiz: se puede corregir el monto, la
  descripción, el tipo, la cuenta y la fecha sin borrar y volver a escribir. Los saldos se ajustan
  solos. Eliminar vive ahora dentro de esa misma ventana.
- **Buscador en Movimientos.** Escribe una palabra y Sigma busca en todo el historial, no solo en
  el mes que estás viendo. Encuentra por descripción o por nombre de cuenta, sin distinguir
  mayúsculas ni tildes: *cafe* encuentra *Café*.
- **Los traspasos aceptan una descripción.** Aparecen como "Transferencia: pago tarjeta" en vez de
  solo "Transferencia", así se distingue pagar la tarjeta de sacar efectivo.

### Changed
- El campo de monto separa los miles mientras escribes: `1.250.000` en vez de `1250000`.
- La lista de movimientos ya no esconde sus acciones hasta pasar el cursor.

## [1.0.0] - 2026-07-24

Reformulación completa: Sigma deja de ser una herramienta de terminal con una interfaz encima y
pasa a ser una aplicación de escritorio simple, en español.

### Added
- **El archivo de datos lo eliges tú.** Al abrir Sigma por primera vez decides dónde vive tu base
  de datos. Guardándola en Google Drive o Dropbox queda respaldada sola. Se puede cambiar de
  archivo desde Ajustes, con una lista de recientes.
- **Respaldos automáticos.** Sigma guarda una copia con la fecha en `.sigma-backups/`: una vez al
  día al abrir la aplicación, y siempre que cambies de base o restaures. Se conservan las últimas
  10 y se restauran desde Ajustes.
- **Migración desde la versión anterior.** Si tenías Sigma instalado, la pantalla de bienvenida
  ofrece traer tus cuentas y movimientos al archivo nuevo. El original no se toca.
- **Aviso de archivo abierto en otro equipo**, para evitar que la sincronización pierda cambios.
- **Las conciliaciones recuerdan qué movimientos cerraron.** Antes solo se guardaba el total.
- Diálogos nativos de macOS para elegir archivos, en vez de la subida de archivos del navegador.
- Tema claro, además del oscuro.

### Changed
- **Todo en español y sin jerga.** "Verification Node" es ahora *Conciliar*, "Chronological
  Activity" es *Últimos movimientos*, "Add Ledger" es *Agregar cuenta*.
- **El ciclo `render` pasa a llamarse conciliación**, que es lo que hace. La mecánica es la misma:
  los movimientos nacen pendientes y se cierran en grupo.
- **Registrar un movimiento está siempre a la vista** en Resumen y necesita solo monto y
  descripción.
- Movimientos muestra un mes a la vez, con sus totales, en vez de un formulario de filtros.
- Eliminar una cuenta ya no reasigna sus movimientos a una cuenta ficticia `deleted`: la cuenta
  se marca como eliminada y su historial se conserva legible.
- Interfaz reconstruida con Vite en vez de Next.js, y repartida en componentes y vistas en lugar
  de un único archivo de 1.777 líneas.
- El paquete de Python pasa de `sgm` a `sigma`.

### Removed
- **La interfaz de línea de comandos completa** (21 comandos) y su publicación en PyPI.
- El symlink automático a `/usr/local/bin/sgm`.
- El comando `update` y el aviso de nueva versión.
- Los respaldos manuales en ZIP con CSVs, reemplazados por el archivo elegible y los respaldos
  automáticos.
- El botón de "resetear la base de datos", innecesario ahora que se puede crear un archivo nuevo.

### Fixed
- Un cierre forzado de la aplicación ya no deja un aviso permanente de "abierto en otro equipo":
  los bloqueos de procesos que ya no existen se detectan como obsoletos.
- El diálogo para elegir archivos funciona de forma confiable: se usa el diálogo nativo del
  sistema en lugar de `<input type="file">`, que fallaba dentro de WKWebView.
- El bundle de macOS ya no incluye numpy, IPython, Jupyter ni jedi, que entraban por recoger el
  entorno de desarrollo completo.

## [0.4.0] - 2026-06-05

### Added
- Native macOS desktop app support (Pattern 1: GUI-First, CLI Bundled Inside): Added packaging support using `Sigma.spec` to compile both the GUI `Sigma` app and the CLI `sgm` command line executable into a single `dist/Sigma.app` bundle.
- Automatic Path Registration: On launch, the `Sigma` desktop app automatically checks and registers a symbolic link to the CLI tool at `/usr/local/bin/sgm` (or `~/.local/bin/sgm` as fallback) to allow immediate command-line usage without manual setup.
- Added `pyinstaller` to developer dependencies and created build targets for the macOS app bundle.
- Standalone Backup & Restore operations: Expose API endpoints for exporting and importing data backups, along with a full UI panel in the Settings menu for non-coding users to download backups and upload zip restores.
- Danger-Zone Database Resetting: Added capability to reset the database and configuration directly from the UI settings pane with double-check confirmation typing checks.
- First-Run Onboarding Welcome Wizard: Added a sleek configuration screen that detects new database installations and guides the user to customize their cash account or upload a backup zip immediately.
- Sidebar Version & Update Notification: Expose app versions and fetch latest releases from GitHub directly in the sidebar with tailored update instructions.

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