# Reset Restore Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Modify the `sgm restore` command to delete the database file (`sigma.db`) and user configuration file (`config.toml`), resetting Sigma to its first-run state so that `sgm start` can be executed again.

**Architecture:** We will import `get_db_path` from `sgm.infrastructure.database` and `config_path` from `sgm.infrastructure.user_config` in `sgm/cli.py`, delete these files in the `restore` command if they exist, and print a clear reset message.

**Tech Stack:** Python 3.12, Typer

---

### Task 1: Update Tests for New Restore Behavior (TDD)

**Files:**
- Modify: [test_cli_restore.py](file:///Users/fzunigam/dev/personal/sigma/tests/smoke/test_cli_restore.py)

**Step 1: Write the failing tests**

Update `test_cli_restore.py` to expect the deletion of both `sigma.db` and `config.toml`, and verify that `sgm start` can be run successfully again after a restore.

```python
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from sgm.cli import app

runner = CliRunner()


def test_restore_cancels_if_not_confirmed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    
    # Init DB and insert something
    result_start = runner.invoke(app, ["start"], input="n\nwallet\nCash\ndebit\n0\n")
    assert result_start.exit_code == 0

    # Answer 'no' or something other than 'RESTORE'
    result = runner.invoke(app, ["restore"], input="no\n")
    
    assert result.exit_code == 0
    assert "Restore cancelled" in result.output
    
    # Check that data still exists
    db_path = tmp_path / ".local" / "share" / "sgm" / "sigma.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM accounts")
        count = cursor.fetchone()[0]
        assert count == 1


def test_restore_deletes_all_data(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    
    # Init DB and insert something
    result_start = runner.invoke(app, ["start"], input="n\nwallet\nCash\ndebit\n0\n")
    assert result_start.exit_code == 0
    
    db_path = tmp_path / ".local" / "share" / "sgm" / "sigma.db"
    config_file = tmp_path / ".config" / "sgm" / "config.toml"
    
    assert db_path.exists()
    assert config_file.exists()

    # Confirm restore
    result = runner.invoke(app, ["restore"], input="RESTORE\n")
    
    assert result.exit_code == 0
    assert "Sigma has been reset. All database files and configurations have been deleted." in result.output
    
    # Check that both database and config files were deleted
    assert not db_path.exists()
    assert not config_file.exists()

    # Verify that sgm start can be run again successfully after restore
    result_start_again = runner.invoke(app, ["start"], input="n\nwallet2\nCash 2\ndebit\n0\n")
    assert result_start_again.exit_code == 0
    assert "Account 'Cash 2' created successfully!" in result_start_again.output
    
    assert db_path.exists()
    assert config_file.exists()
```

**Step 2: Run test to verify it fails**

Run: `python3.12 -m pytest tests/smoke/test_cli_restore.py -v`
Expected: FAIL, because the files are not deleted and `sgm start` fails with "Sigma is already configured."

**Step 3: Commit the test changes**

```bash
git add tests/smoke/test_cli_restore.py
git commit -m "test: update restore command tests to assert config and database deletion"
```

---

### Task 2: Implement Config & Database Deletion in Restore Command

**Files:**
- Modify: [cli.py](file:///Users/fzunigam/dev/personal/sigma/src/sgm/cli.py)

**Step 1: Modify the imports and restore command**

Update imports to include `get_db_path` and `config_path`. Update `restore` to unlink the database and config files and output the correct status message.

```python
# Import updates:
from sgm.infrastructure.database import clear_db, create_account, init_db, get_account, get_accounts, update_credit_limit, get_marked_total, create_movement, create_transfer, rename_account, get_recent_logs, execute_render, get_render_history, delete_record, delete_account, get_all_table_data, import_from_csvs, get_db_path
from sgm.infrastructure.user_config import is_configured, save_config, load_config, config_path
```

And update `restore` command:

```python
@app.command("restore")
def restore(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True)
) -> None:
    """Delete all data and configuration, resetting Sigma to its first-run state."""
    if help:
        print(f"Usage: {ctx.command_path}")
        print(f"{ctx.command.help}")
        raise typer.Exit()
        
    typer.echo("WARNING: This will delete ALL data (accounts, movements, transfers) and your configuration.", err=True)
    typer.echo("This will reset Sigma to its first-run state.", err=True)
    typer.echo("This action CANNOT be undone.", err=True)
    
    try:
        confirmation = typer.prompt("Type 'RESTORE' to confirm deletion (or press Ctrl+C to cancel)")
        if confirmation != "RESTORE":
            typer.echo("Restore cancelled.")
            raise typer.Exit()
    except typer.Abort:
        typer.echo("\nRestore cancelled.")
        raise typer.Exit()
        
    # Delete database file
    db_path = get_db_path()
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception as e:
            typer.echo(f"Error deleting database: {e}", err=True)
            
    # Delete configuration file
    cfg_path = config_path()
    if cfg_path.exists():
        try:
            cfg_path.unlink()
        except Exception as e:
            typer.echo(f"Error deleting configuration: {e}", err=True)

    typer.echo("Sigma has been reset. All database files and configurations have been deleted.")
    typer.echo("You can now run 'sgm start' to set up Sigma again.")
```

**Step 2: Run test to verify it passes**

Run: `python3.12 -m pytest tests/smoke/test_cli_restore.py -v`
Expected: PASS

**Step 3: Commit implementation**

```bash
git add src/sgm/cli.py
git commit -m "feat: implement database and configuration file deletion on sgm restore"
```

---

### Task 3: Update Help Texts and Changelog

**Files:**
- Modify: [banner.py](file:///Users/fzunigam/dev/personal/sigma/src/sgm/interface/banner.py)
- Modify: [CHANGELOG.md](file:///Users/fzunigam/dev/personal/sigma/CHANGELOG.md)

**Step 1: Modify banner.py and CHANGELOG.md**

Update the description in `banner.py` from:
`Delete all data and leave the database empty`
to:
`Delete all data and configuration, resetting Sigma`

Add entry to `CHANGELOG.md` under `## [Unreleased]` under `### Changed`:
- `sgm restore` command modified to delete the sqlite database (`sigma.db`) and the config file (`config.toml`) instead of just emptying the tables, resetting Sigma to its first-run state.

**Step 2: Verify all tests in the suite pass**

Run: `python3.12 -m pytest -q`
Expected: PASS (all tests pass)

**Step 3: Commit documentation updates**

```bash
git add src/sgm/interface/banner.py CHANGELOG.md
git commit -m "docs: update help text and changelog for restore command changes"
```
