import pytest
import sqlite3
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
    create_account("cc", "Credit Card", "credit", 100000, 500000)
    
    # Pre-seed some marked movements
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # income marked (1000)
        cursor.execute("INSERT INTO movements (id, amount, description, account_id, type, created_at, updated_at) VALUES ('1', 1000, 'inc', 'wallet', 'income', '2026-05-01', '2026-05-01 12:00:00.000')")
        cursor.execute("INSERT INTO movement_marks (movement_id, marked) VALUES ('1', 1)")
        
        # expense marked (400)
        cursor.execute("INSERT INTO movements (id, amount, description, account_id, type, created_at, updated_at) VALUES ('2', 400, 'exp', 'wallet', 'expense', '2026-05-01', '2026-05-01 12:00:00.000')")
        cursor.execute("INSERT INTO movement_marks (movement_id, marked) VALUES ('2', 1)")
        
        # expense unmarked (500) -> should not affect total
        cursor.execute("INSERT INTO movements (id, amount, description, account_id, type, created_at, updated_at) VALUES ('3', 500, 'exp unmarked', 'wallet', 'expense', '2026-05-01', '2026-05-01 12:00:00.000')")
        cursor.execute("INSERT INTO movement_marks (movement_id, marked) VALUES ('3', 0)")
        conn.commit()
    
    yield
    clear_db(db_path)


def test_cli_status() -> None:
    result = CliRunner().invoke(app, ["status"])
    assert result.exit_code == 0
    # Available credit for cc: 500000 - 100000 = 400000
    assert "400000" in result.output
    # Balance for cc: 100000
    assert "100000" in result.output
    # Balance for wallet: 1500
    assert "1500" in result.output
    # Marked total: 1000 - 400 = 600
    assert "600" in result.output

def test_cli_status_no_accounts(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "empty.db"
    from sgm.infrastructure import database
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)
    init_db(db_path)

    result = CliRunner().invoke(app, ["status"])
    assert result.exit_code == 0
    assert "No accounts found" in result.output

def test_cli_status_help() -> None:
    result = CliRunner().invoke(app, ["status", "--help"])
    assert result.exit_code == 0
    assert "status" in result.output
    assert "Displays a rich table" in result.output
