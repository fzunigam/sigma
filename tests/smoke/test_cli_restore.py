import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from sgm.cli import app

runner = CliRunner()


def test_restore_cancels_if_not_confirmed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    
    # Init DB and insert something
    result_start = runner.invoke(app, ["start"], input="wallet\nCash\ndebit\n0\n")
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
    result_start = runner.invoke(app, ["start"], input="wallet\nCash\ndebit\n0\n")
    assert result_start.exit_code == 0
    
    db_path = tmp_path / ".local" / "share" / "sgm" / "sigma.db"

    # Confirm restore
    result = runner.invoke(app, ["restore"], input="RESTORE\n")
    
    assert result.exit_code == 0
    assert "Database restored. All data has been deleted." in result.output
    
    # Check that data was deleted
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM accounts")
        count = cursor.fetchone()[0]
        assert count == 0