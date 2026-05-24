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