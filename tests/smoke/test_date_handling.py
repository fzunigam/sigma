import pytest
from typer.testing import CliRunner
from datetime import date

from sgm.cli import app
from sgm.infrastructure.database import init_db, clear_db, get_recent_logs

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    db_path = tmp_path / "sigma.db"
    from sgm.infrastructure import database
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)
    init_db(db_path)
    yield
    clear_db(db_path)

def test_exp_default_date() -> None:
    runner = CliRunner()
    runner.invoke(app, ["acc", "add", "w", "Wallet", "debit", "10000"])
    
    result = runner.invoke(app, ["exp", "1000", "lunch", "yes"])
    assert result.exit_code == 0
    assert "Recorded expense of 1000 ('lunch') in 'w'." in result.output
    
    logs = get_recent_logs(1)
    assert logs[0]["created_at"] == date.today().isoformat()

def test_exp_custom_date() -> None:
    runner = CliRunner()
    runner.invoke(app, ["acc", "add", "w", "Wallet", "debit", "10000"])
    
    custom_date = "2023-10-27"
    result = runner.invoke(app, ["exp", "1000", "lunch", "yes", "w", custom_date])
    assert result.exit_code == 0
    assert f"Recorded expense of 1000 ('lunch') in 'w' on {custom_date}." in result.output
    
    logs = get_recent_logs(1)
    assert logs[0]["created_at"] == custom_date

def test_exp_ambiguity_date_resolution() -> None:
    runner = CliRunner()
    runner.invoke(app, ["acc", "add", "w", "Wallet", "debit", "10000"])
    
    # Only one account exists, so acc_id is optional. 
    # Providing something that looks like a date should resolve it as the date.
    custom_date = "2023-10-27"
    result = runner.invoke(app, ["exp", "1000", "lunch", "yes", custom_date])
    assert result.exit_code == 0
    assert f"Recorded expense of 1000 ('lunch') in 'w' on {custom_date}." in result.output
    
    logs = get_recent_logs(1)
    assert logs[0]["created_at"] == custom_date

def test_tr_custom_date() -> None:
    runner = CliRunner()
    runner.invoke(app, ["acc", "add", "w1", "Wallet 1", "debit", "10000"])
    runner.invoke(app, ["acc", "add", "w2", "Wallet 2", "debit", "10000"])
    
    custom_date = "2023-10-28"
    result = runner.invoke(app, ["tr", "w1", "w2", "500", custom_date])
    assert result.exit_code == 0
    assert f"Transferred 500 from 'w1' to 'w2' on {custom_date}." in result.output
    
    logs = get_recent_logs(1)
    assert logs[0]["created_at"] == custom_date

def test_migration_from_iso_to_date(tmp_path, monkeypatch) -> None:
    import sqlite3
    db_path = tmp_path / "migration.db"
    monkeypatch.setattr("sgm.infrastructure.database.get_db_path", lambda: db_path)
    
    # 1. Create a DB with ISO timestamps manually
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE movements (id INTEGER PRIMARY KEY, amount INTEGER, description TEXT, account_id TEXT, type TEXT, created_at TEXT)")
        cursor.execute("CREATE TABLE movement_marks (movement_id INTEGER PRIMARY KEY, marked INTEGER)")
        cursor.execute("CREATE TABLE transfers (id INTEGER PRIMARY KEY, from_account TEXT, to_account TEXT, amount INTEGER, created_at TEXT)")
        cursor.execute("CREATE TABLE render_history (id INTEGER PRIMARY KEY, net_amount INTEGER, rendered_at TEXT)")
        
        iso_ts = "2023-10-27T10:00:00.000Z"
        cursor.execute("INSERT INTO movements (amount, description, account_id, type, created_at) VALUES (?, ?, ?, ?, ?)", (1000, "lunch", "w", "expense", iso_ts))
        cursor.execute("INSERT INTO transfers (from_account, to_account, amount, created_at) VALUES (?, ?, ?, ?)", ("w1", "w2", 500, iso_ts))
        cursor.execute("INSERT INTO render_history (net_amount, rendered_at) VALUES (?, ?)", (500, iso_ts))
        conn.commit()
    
    # 2. Run init_db which should migrate them
    init_db(db_path)
    
    # 3. Verify they are now date-only
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT created_at FROM movements")
        assert cursor.fetchone()[0] == "2023-10-27"
        cursor.execute("SELECT created_at FROM transfers")
        assert cursor.fetchone()[0] == "2023-10-27"
        cursor.execute("SELECT rendered_at FROM render_history")
        assert cursor.fetchone()[0] == "2023-10-27"
