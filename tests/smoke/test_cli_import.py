import zipfile
import sqlite3
from pathlib import Path
from typer.testing import CliRunner
from sgm.cli import app
from sgm.infrastructure.database import init_db, clear_db, create_account

def test_cli_import_from_zip(tmp_path, monkeypatch) -> None:
    # 1. Setup mock environment
    monkeypatch.setenv("HOME", str(tmp_path))
    db_path = tmp_path / ".local" / "share" / "sgm" / "sigma.db"
    config_path = tmp_path / ".config" / "sgm" / "config.toml"
    
    # Initialize and add data
    init_db(db_path)
    create_account("wallet", "Cash", "debit", 1500)
    
    # Export it
    export_file = tmp_path / "export.zip"
    runner = CliRunner()
    runner.invoke(app, ["export", "--output", str(export_file)])
    
    # 2. Clean up for "fresh start"
    if config_path.exists():
        config_path.unlink()
    clear_db(db_path)
    
    # 3. Run sgm start with import
    # Inputs:
    # "y" (Do you want to import?)
    # str(export_file) (Path to ZIP)
    result = runner.invoke(app, ["start"], input=f"y\n{export_file}\n")
    
    assert result.exit_code == 0
    assert "Data imported successfully!" in result.output
    
    # 4. Verify data was restored
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, balance FROM accounts WHERE id = 'wallet'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "wallet"
        assert row[1] == 1500

def test_cli_import_from_folder(tmp_path, monkeypatch) -> None:
    # 1. Setup mock environment
    monkeypatch.setenv("HOME", str(tmp_path))
    db_path = tmp_path / ".local" / "share" / "sgm" / "sigma.db"
    config_path = tmp_path / ".config" / "sgm" / "config.toml"
    
    # Create a folder with CSVs
    import_dir = tmp_path / "my_data"
    import_dir.mkdir()
    
    init_db(db_path)
    create_account("bank", "Bank", "debit", 5000)
    
    # Use internal database logic to get data and write CSVs manually for the test
    # or just use export to a folder? Export only does ZIP.
    # Let's use a ZIP then extract it.
    export_zip = tmp_path / "temp.zip"
    runner = CliRunner()
    runner.invoke(app, ["export", "--output", str(export_zip)])
    
    with zipfile.ZipFile(export_zip, 'r') as zipf:
        zipf.extractall(import_dir)
    
    # 2. Clean up for "fresh start"
    if config_path.exists():
        config_path.unlink()
    clear_db(db_path)
    
    # 3. Run sgm start with import from folder
    result = runner.invoke(app, ["start"], input=f"y\n{import_dir}\n")
    
    assert result.exit_code == 0
    assert "Data imported successfully!" in result.output
    
    # 4. Verify data
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, balance FROM accounts WHERE id = 'bank'")
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == 5000

def test_cli_import_invalid_zip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    bad_zip = tmp_path / "not_a_zip.txt"
    bad_zip.write_text("hello")
    
    runner = CliRunner()
    # Input: "y", then bad path, then manual setup info
    # manual setup: "fallback_acc", "Fallback", "debit", "100"
    result = runner.invoke(app, ["start"], input=f"y\n{bad_zip}\nfallback_acc\nFallback\ndebit\n100\n")
    
    assert "Import failed" in result.output
    assert "Falling back to manual account creation" in result.output
    assert "Account 'Fallback' created successfully!" in result.output
