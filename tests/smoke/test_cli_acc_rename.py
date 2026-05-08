import pytest
from typer.testing import CliRunner

from sgm.cli import app
from sgm.infrastructure.database import init_db, clear_db, get_account

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "sigma.db"
    
    from sgm.infrastructure import database
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)
    
    init_db(db_path)
    yield
    clear_db(db_path)


def test_cli_acc_rename_success() -> None:
    runner = CliRunner()
    runner.invoke(app, ["acc", "add", "cc", "Credit Card", "credit", "1000"])
    
    result = runner.invoke(app, ["acc", "rename", "cc", "bci"])
    assert result.exit_code == 0
    assert "Account 'cc' renamed to 'bci' successfully!" in result.output
    
    # Check that old ID no longer exists
    assert get_account("cc") is None
    # Check that new ID exists
    acc = get_account("bci")
    assert acc is not None
    assert acc["name"] == "Credit Card"


def test_cli_acc_rename_non_existent() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["acc", "rename", "invalid", "newid"])
    assert result.exit_code == 1
    assert "Error: Account with ID 'invalid' does not exist." in result.output


def test_cli_acc_rename_already_exists() -> None:
    runner = CliRunner()
    runner.invoke(app, ["acc", "add", "wallet1", "Wallet 1", "debit", "1000"])
    runner.invoke(app, ["acc", "add", "wallet2", "Wallet 2", "debit", "2000"])
    
    result = runner.invoke(app, ["acc", "rename", "wallet1", "wallet2"])
    assert result.exit_code == 1
    assert "Error: Account with ID 'wallet2' already exists." in result.output


def test_cli_acc_rename_same_id() -> None:
    runner = CliRunner()
    runner.invoke(app, ["acc", "add", "wallet", "Wallet", "debit", "1000"])
    
    result = runner.invoke(app, ["acc", "rename", "wallet", "wallet"])
    assert result.exit_code == 1
    assert "Error: New ID must be different from the old ID." in result.output


def test_cli_acc_rename_updates_relations() -> None:
    runner = CliRunner()
    runner.invoke(app, ["acc", "add", "acc1", "Account 1", "debit", "5000"])
    runner.invoke(app, ["acc", "add", "acc2", "Account 2", "debit", "0"])
    
    # Create movement
    runner.invoke(app, ["exp", "1000", "lunch", "yes", "acc1"])
    # Create transfer
    runner.invoke(app, ["tr", "acc1", "acc2", "1000"])
    
    # Rename acc1 to main
    result = runner.invoke(app, ["acc", "rename", "acc1", "main"])
    assert result.exit_code == 0
    
    from sgm.infrastructure.database import get_db_path
    import sqlite3
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT account_id FROM movements WHERE account_id = 'main'")
        assert len(cursor.fetchall()) == 1
        
        cursor.execute("SELECT from_account FROM transfers WHERE from_account = 'main'")
        assert len(cursor.fetchall()) == 1
        
        cursor.execute("SELECT to_account FROM transfers WHERE to_account = 'acc2'")
        assert len(cursor.fetchall()) == 1
