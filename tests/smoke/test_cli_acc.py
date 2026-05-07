import pytest
from typer.testing import CliRunner

from sgm.cli import app
from sgm.infrastructure.database import init_db, clear_db

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "sigma.db"
    
    # Mock get_db_path
    from sgm.infrastructure import database
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)
    
    init_db(db_path)
    yield
    clear_db(db_path)


def test_cli_acc_add_success() -> None:
    result = CliRunner().invoke(app, ["acc", "add", "wallet", "Cash", "debit", "1500"])
    assert result.exit_code == 0
    assert "Account 'Cash' created successfully!" in result.output

def test_cli_acc_add_invalid_type() -> None:
    result = CliRunner().invoke(app, ["acc", "add", "wallet", "Cash", "invalid_type", "1500"])
    assert result.exit_code != 0
    assert "Invalid value for" in result.output
    assert "TYPE:{debit|credit}" in result.output

def test_cli_acc_add_duplicate() -> None:
    runner = CliRunner()
    result1 = runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "1500"])
    assert result1.exit_code == 0
    
    result2 = runner.invoke(app, ["acc", "add", "wallet", "Another Cash", "debit", "5000"])
    assert result2.exit_code == 1
    assert "Error: Account with ID 'wallet' already exists" in result2.output

def test_cli_acc_add_help() -> None:
    result = CliRunner().invoke(app, ["acc", "add", "--help"])
    assert result.exit_code == 0
    assert "acc add" in result.output
    assert "<id> <name> <type> <bal>" in result.output
