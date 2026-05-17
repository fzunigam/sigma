import zipfile
from pathlib import Path
from typer.testing import CliRunner
from sgm.cli import app
from sgm.infrastructure.database import init_db, clear_db, create_account

def test_cli_export_success(tmp_path, monkeypatch) -> None:
    # 1. Setup mock DB
    db_path = tmp_path / "sigma.db"
    from sgm.infrastructure import database
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)
    init_db(db_path)
    
    # Add some data
    create_account("wallet", "Cash", "debit", 1500)
    
    # 2. Define output path
    export_file = tmp_path / "export.zip"
    
    # 3. Run export command
    runner = CliRunner()
    result = runner.invoke(app, ["export", "--output", str(export_file)])
    
    # 4. Assertions
    assert result.exit_code == 0
    assert "Successfully exported data to" in result.output
    assert export_file.exists()
    
    # 5. Verify ZIP contents
    with zipfile.ZipFile(export_file, 'r') as zipf:
        file_list = zipf.namelist()
        expected_files = ["accounts.csv", "movements.csv", "movement_marks.csv", "transfers.csv", "render_history.csv"]
        for expected in expected_files:
            assert expected in file_list

def test_cli_export_help() -> None:
    result = CliRunner().invoke(app, ["export", "--help"])
    assert result.exit_code == 0
    assert "export" in result.output
    assert "Exports all data into a ZIP file" in result.output

def test_cli_export_default_path(tmp_path, monkeypatch) -> None:
    # 1. Setup mock DB
    db_path = tmp_path / "sigma.db"
    from sgm.infrastructure import database
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)
    init_db(db_path)
    
    # 2. Mock Home directory to point to tmp_path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    
    # 3. Run export command (defaults to Downloads or Home)
    runner = CliRunner()
    result = runner.invoke(app, ["export"])
    
    # 4. Assertions
    assert result.exit_code == 0
    assert "Successfully exported data to" in result.output
    
    # Check if file was created in tmp_path (since Downloads doesn't exist)
    exported_files = list(tmp_path.glob("sigma_export_*.zip"))
    assert len(exported_files) == 1
