import pytest
from typer.testing import CliRunner

from sgm.cli import app
from sgm.infrastructure.database import init_db, clear_db, create_account, get_account

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

def test_cli_acc_set_limit_success() -> None:
    result = CliRunner().invoke(app, ["acc", "set-limit", "cc", "1000000"])
    assert result.exit_code == 0
    assert "updated to 1000000 successfully" in result.output
    
    acc = get_account("cc")
    assert acc is not None
    assert acc["credit_limit"] == 1000000

def test_cli_acc_set_limit_debit_fails() -> None:
    result = CliRunner().invoke(app, ["acc", "set-limit", "wallet", "5000"])
    assert result.exit_code == 1
    assert "Error: Account 'wallet' is a debit account" in result.output
    assert "Only credit accounts can have a credit limit" in result.output
    
    # Limit shouldn't have changed
    acc = get_account("wallet")
    assert acc is not None
    assert acc["credit_limit"] == 0

def test_cli_acc_set_limit_not_found() -> None:
    result = CliRunner().invoke(app, ["acc", "set-limit", "nonexistent", "1000"])
    assert result.exit_code == 1
    assert "Error: Account with ID 'nonexistent' not found" in result.output

def test_cli_acc_set_limit_help() -> None:
    result = CliRunner().invoke(app, ["acc", "set-limit", "--help"])
    assert result.exit_code == 0
    assert "acc set-limit" in result.output
    assert "<acc_id> <limit>" in result.output
