import pytest
from typer.testing import CliRunner

from sgm.cli import app
from sgm.infrastructure.database import init_db, clear_db, create_account

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "sigma.db"
    
    from sgm.infrastructure import database
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)
    
    init_db(db_path)
    
    # Pre-seed some accounts
    create_account("wallet", "Cash", "debit", 1500)
    create_account("cc", "Credit Card", "credit", 0, 500000)
    
    yield
    clear_db(db_path)


def test_cli_acc_list_all() -> None:
    result = CliRunner().invoke(app, ["acc", "list"])
    assert result.exit_code == 0
    assert "All Accounts" in result.output
    assert "wallet" in result.output
    assert "Cash" in result.output
    assert "1500" in result.output
    assert "cc" in result.output
    assert "Credit Card" in result.output
    assert "500000" in result.output

def test_cli_acc_list_specific() -> None:
    result = CliRunner().invoke(app, ["acc", "list", "cc"])
    assert result.exit_code == 0
    assert "Account Details: cc" in result.output
    assert "Credit Card" in result.output
    assert "500000" in result.output

def test_cli_acc_list_not_found() -> None:
    result = CliRunner().invoke(app, ["acc", "list", "nonexistent"])
    assert result.exit_code == 1
    assert "Error: Account with ID 'nonexistent' not found." in result.output

def test_cli_acc_list_empty(tmp_path, monkeypatch) -> None:
    # Use a new empty DB
    db_path = tmp_path / "empty.db"
    from sgm.infrastructure import database
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)
    init_db(db_path)
    
    result = CliRunner().invoke(app, ["acc", "list"])
    assert result.exit_code == 0
    assert "No accounts found" in result.output

def test_cli_acc_list_help() -> None:
    result = CliRunner().invoke(app, ["acc", "list", "--help"])
    assert result.exit_code == 0
    assert "acc list" in result.output
    assert "[acc_id]" in result.output
