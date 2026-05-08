from typing import Generator

import pytest
from typer.testing import CliRunner # type: ignore

from sgm.cli import app
from sgm.infrastructure.database import init_db

runner = CliRunner()

@pytest.fixture
def clean_db(tmp_path) -> Generator[None, None, None]:
    db_path = tmp_path / "test.db"
    
    import sgm.infrastructure.database
    sgm.infrastructure.database.get_db_path = lambda: db_path
    
    init_db(db_path)
    
    yield
    
def test_tr_command(clean_db):
    # Setup accounts
    result = runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "10000"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["acc", "add", "bank", "Bank", "debit", "5000"])
    assert result.exit_code == 0
    
    # Transfer
    result = runner.invoke(app, ["tr", "wallet", "bank", "3000"])
    assert result.exit_code == 0
    assert "Transferred 3000 from 'wallet' to 'bank'." in result.stdout
    
    # Check balances
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # wallet should be 7000
    # bank should be 8000
    assert "7000" in result.stdout
    assert "8000" in result.stdout

def test_tr_insufficient_funds(clean_db):
    result = runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "1000"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["acc", "add", "bank", "Bank", "debit", "5000"])
    assert result.exit_code == 0
    
    result = runner.invoke(app, ["tr", "wallet", "bank", "3000"])
    assert result.exit_code == 1
    assert "Error: Insufficient funds in account 'wallet'." in result.output

def test_tr_invalid_account(clean_db):
    result = runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "10000"])
    assert result.exit_code == 0
    
    result = runner.invoke(app, ["tr", "wallet", "fake", "3000"])
    assert result.exit_code == 1
    assert "Error: Account with ID 'fake' does not exist." in result.output
    
def test_tr_same_account(clean_db):
    result = runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "10000"])
    assert result.exit_code == 0
    
    result = runner.invoke(app, ["tr", "wallet", "wallet", "3000"])
    assert result.exit_code == 1
    assert "Error: Source and destination accounts must be different." in result.output
    
def test_tr_negative_amount(clean_db):
    result = runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "10000"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["acc", "add", "bank", "Bank", "debit", "5000"])
    assert result.exit_code == 0
    
    # Use -- to prevent Typer from parsing -500 as an option
    result = runner.invoke(app, ["tr", "wallet", "bank", "--", "-500"])
    assert result.exit_code == 1
    assert "Error: Amount must be positive." in result.output
