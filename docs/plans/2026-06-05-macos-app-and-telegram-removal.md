# macOS Desktop App and Telegram Removal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the Telegram Bot integration completely to declutter the codebase, and introduce a native macOS desktop window container (`pywebview`) for the Next.js web application via a new `sgm app` CLI command.

**Architecture:** 
1. **Telegram Cleanup**: Delete all telegram bot code, tests, docker files, CI configurations, and docs. Simplify the interactive configuration wizard in the CLI to only ask for default accounts.
2. **Desktop App**: Add `pywebview` as an optional dependency `[desktop]`. In `sgm/cli.py`, implement a new `sgm app` command that launches the FastAPI server on a background thread and opens a native macOS WKWebView window pointing to it.

**Tech Stack:** Python 3.12, FastAPI, Next.js, Uvicorn, Typer, `pywebview`.

---

### Task 1: Remove Telegram Bot Code & Build Configuration

**Files:**
- Remove: `src/sgm/telegram_bot.py`
- Remove: `tests/smoke/test_telegram_bot.py`
- Remove: `docs/telegram-deployment.md`
- Remove: `Dockerfile`
- Remove: `docker-compose.yml`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Modify: `Makefile`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

**Step 1: Verify all current tests pass**

Run: `python3.12 -m pytest`
Expected: 82 passed.

**Step 2: Delete files and modify pyproject.toml, Makefile, and CI workflow**

*   Delete: `src/sgm/telegram_bot.py`
*   Delete: `tests/smoke/test_telegram_bot.py`
*   Delete: `docs/telegram-deployment.md`
*   Delete: `Dockerfile`
*   Delete: `docker-compose.yml`
*   Modify `pyproject.toml` to remove the `telegram` entry under `[project.optional-dependencies]`.
*   Modify `Makefile` (line 13) to remove `telegram` from the installation command.
*   Modify `.github/workflows/ci.yml` (line 16) to change installation command to `python -m pip install -e ".[dev]"`.
*   Modify `AGENTS.md` (line 18) and `CLAUDE.md` (line 18) to change installation command recommendation to `python3.12 -m pip install -e ".[dev]"`.

**Step 3: Run pytest to verify no broken dependencies**

Run: `python3.12 -m pytest`
Expected: 77 passed (5 tests from `test_telegram_bot.py` deleted).

**Step 4: Commit**

```bash
git rm src/sgm/telegram_bot.py tests/smoke/test_telegram_bot.py docs/telegram-deployment.md Dockerfile docker-compose.yml
git add pyproject.toml .github/workflows/ci.yml Makefile AGENTS.md CLAUDE.md
git commit -m "cleanup: remove telegram bot implementation and dev configuration"
```

---

### Task 2: Remove Telegram Configuration and Commands from CLI

**Files:**
- Modify: `src/sgm/cli.py`
- Modify: `tests/smoke/test_cli_config.py`

**Step 1: Modify the config smoke tests to remove Telegram helper tests**

Modify `tests/smoke/test_cli_config.py` to remove `test_config_helper_functions` (lines 55-66) since the helpers `mask_token` and `format_allowed_users` will be deleted from CLI.

**Step 2: Run test to verify it fails**

Run: `python3.12 -m pytest tests/smoke/test_cli_config.py`
Expected: FAIL (if helpers are still imported/tested but missing, or check if it fails/passes).

**Step 3: Modify `src/sgm/cli.py` to remove `bot_app`, config options, and helpers**

*   Remove helper functions: `mask_token()` and `format_allowed_users()`.
*   Remove `bot_app` definition:
    ```python
    bot_app = typer.Typer(
        help="Telegram Bot configuration and control",
        no_args_is_help=True,
    )
    app.add_typer(bot_app, name="bot")
    ```
*   Remove `@bot_app.command("setup")` and `@bot_app.command("run")` subcommands entirely.
*   Modify `config` wizard menu in `cli.py` (lines 420-435 and 524-640) to remove options `2` (Telegram Bot Token) and `3` (Telegram Allowed Users) entirely. Ensure choice indices are updated so that the menu only lists options for default income and default expense accounts.

**Step 4: Run tests to verify they pass**

Run: `python3.12 -m pytest`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sgm/cli.py tests/smoke/test_cli_config.py
git commit -m "cleanup: remove telegram config helpers and command group from cli"
```

---

### Task 3: Clean up Documentation and Readmes

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/cli-usage.md`

**Step 1: Modify README.md**
Remove the "Telegram Bot" section and the command table entries. Change installation recommendation from `sigma-finance[telegram]` to `sigma-finance[desktop]`.

**Step 2: Modify docs/architecture.md**
Update line 28 (which mentions "No Telegram implementation yet") to completely remove it or describe it as deprecated/removed in favor of the desktop app.

**Step 3: Modify docs/cli-usage.md**
Remove "Telegram Bot Integration" command guides.

**Step 4: Update CHANGELOG.md**
Add an entry under `[Unreleased]` under `Removed` noting:
"Removed the Telegram Bot integration completely to keep the CLI and backend clean and focused."

**Step 5: Run tests and commit**

Run: `python3.12 -m pytest`
Expected: PASS

```bash
git add README.md CHANGELOG.md docs/architecture.md docs/cli-usage.md
git commit -m "docs: remove telegram bot mentions and add changelog entry"
```

---

### Task 4: Add `pywebview` Optional Dependency and Desktop App CLI Command

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/sgm/cli.py`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Create: `tests/smoke/test_app_cli.py`

**Step 1: Write a failing test for the `app` CLI command registration**

Create `tests/smoke/test_app_cli.py`:
```python
from typer.testing import CliRunner
from sgm.cli import app

def test_app_command_registered():
    result = CliRunner().invoke(app, ["app", "--help"])
    assert result.exit_code == 0
    assert "Launch the Sigma desktop app in a native window" in result.stdout
```

**Step 2: Run the test to verify it fails**

Run: `python3.12 -m pytest tests/smoke/test_app_cli.py`
Expected: FAIL (unrecognized command "app")

**Step 3: Add `desktop` extra to `pyproject.toml` and implement `app` command in `src/sgm/cli.py`**

*   Add to `pyproject.toml`:
    ```toml
    [project.optional-dependencies]
    dev = [ ... ]
    desktop = [
      "pywebview>=5.1",
    ]
    ```
*   Implement `app` command in `src/sgm/cli.py`:
    ```python
    @app.command("app")
    def app_cmd(
        ctx: typer.Context,
        host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address"),
        port: int = typer.Option(8000, "--port", "-p", help="Bind port number"),
    ) -> None:
        """Launch the Sigma desktop app in a native window."""
        if not is_configured():
            typer.echo("Error: Sigma configuration file not found.", err=True)
            typer.echo("Please run 'sgm start' to initialize configuration.", err=True)
            raise typer.Exit(1)

        init_db()

        # Check for pywebview dependency dynamically
        try:
            import webview
        except ImportError:
            typer.echo("Error: 'pywebview' library is not installed.", err=True)
            typer.echo("Please install desktop support by running:", err=True)
            typer.echo("  pip install \"sigma-finance[desktop]\"", err=True)
            raise typer.Exit(1)

        import uvicorn
        import threading

        # Start the FastAPI server on a background thread
        from sgm.interface.web.server import app as web_app
        from sgm.infrastructure.database import get_db_path
        web_app.state.db_path = get_db_path()

        def start_server():
            # Run server silently to avoid console spam in windowed mode
            uvicorn.run(web_app, host=host, port=port, log_level="warning")

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

        # Open pywebview pointing to the local FastAPI port
        typer.echo(f"Starting native desktop application window at http://{host}:{port}")
        webview.create_window(
            title="Sigma Personal Finance",
            url=f"http://{host}:{port}",
            width=1280,
            height=800,
            resizable=True,
            min_size=(800, 600),
        )
        webview.start()
    ```

*   Add `desktop` to CI/commands in `AGENTS.md` and `CLAUDE.md`:
    `- Install dev setup: python3.12 -m pip install -e ".[dev,desktop]"`

**Step 4: Run the test to verify it passes**

Run: `python3.12 -m pytest tests/smoke/test_app_cli.py`
Expected: PASS

**Step 5: Run full test suite**

Run: `python3.12 -m pytest`
Expected: All tests pass (including `test_app_cli.py`).

**Step 6: Commit**

```bash
git add pyproject.toml src/sgm/cli.py tests/smoke/test_app_cli.py AGENTS.md CLAUDE.md
git commit -m "feat: add desktop app command using pywebview"
```
