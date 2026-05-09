from typing import Generator
import pytest
from typer.testing import CliRunner
from sgm.cli import app
from sgm.infrastructure.database import init_db, get_account

runner = CliRunner()

@pytest.fixture
def clean_db(tmp_path, monkeypatch) -> Generator[None, None, None]:
    db_path = tmp_path / "test.db"
    import sgm.infrastructure.database
    monkeypatch.setattr(sgm.infrastructure.database, "get_db_path", lambda: db_path)
    init_db(db_path)
    yield

def test_delete_movement(clean_db):
    # Setup
    runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "10000"])
    runner.invoke(app, ["exp", "1000", "lunch", "yes", "wallet"])
    
    # Verify balance
    acc = get_account("wallet")
    assert acc["balance"] == 9000
    
    # Delete movement
    result = runner.invoke(app, ["delete", "m-1"])
    assert result.exit_code == 0
    assert "Deleted record 'm-1'" in result.stdout
    
    # Verify balance reversed
    acc = get_account("wallet")
    assert acc["balance"] == 10000
    
    # Verify log is empty
    result = runner.invoke(app, ["log"])
    assert "No recent movements found." in result.stdout

def test_delete_transfer(clean_db):
    # Setup
    runner.invoke(app, ["acc", "add", "w1", "W1", "debit", "10000"])
    runner.invoke(app, ["acc", "add", "w2", "W2", "debit", "5000"])
    runner.invoke(app, ["tr", "w1", "w2", "3000"])
    
    # Verify balances
    assert get_account("w1")["balance"] == 7000
    assert get_account("w2")["balance"] == 8000
    
    # Delete transfer
    result = runner.invoke(app, ["delete", "t-1"])
    assert result.exit_code == 0
    assert "Deleted record 't-1'" in result.stdout
    
    # Verify balances reversed
    assert get_account("w1")["balance"] == 10000
    assert get_account("w2")["balance"] == 5000
    
    # Verify log is empty
    result = runner.invoke(app, ["log"])
    assert "No recent movements found." in result.stdout

def test_delete_not_found(clean_db):
    result = runner.invoke(app, ["delete", "m-99"])
    assert result.exit_code == 1
    assert "Error: Record 'm-99' not found." in result.output

def test_delete_invalid_id(clean_db):
    result = runner.invoke(app, ["delete", "invalid"])
    assert result.exit_code == 1
    assert "Error: Invalid ID format" in result.output
