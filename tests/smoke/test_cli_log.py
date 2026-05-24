from typing import Generator

import pytest
from typer.testing import CliRunner # type: ignore

from sgm.cli import app
from sgm.infrastructure.database import init_db

runner = CliRunner()

@pytest.fixture
def clean_db(tmp_path, monkeypatch) -> Generator[None, None, None]:
    db_path = tmp_path / "test.db"
    
    import sgm.infrastructure.database
    monkeypatch.setattr(sgm.infrastructure.database, "get_db_path", lambda: db_path)
    
    init_db(db_path)
    
    yield
    
def test_log_empty(clean_db):
    result = runner.invoke(app, ["log"])
    assert result.exit_code == 0
    assert "No recent movements found." in result.stdout

def test_log_command(clean_db):
    # Setup accounts
    result = runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "10000"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["acc", "add", "bank", "Bank", "debit", "5000"])
    assert result.exit_code == 0
    
    # Record movements and transfers
    result = runner.invoke(app, ["exp", "1000", "lunch", "yes", "wallet"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["inc", "2000", "salary", "no", "bank"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["tr", "wallet", "bank", "3000"])
    assert result.exit_code == 0
    
    # Check log
    import re
    result = runner.invoke(app, ["log"])
    assert result.exit_code == 0
    assert "Recent Logs" in result.stdout
    assert "lunch" in result.stdout
    assert "salary" in result.stdout
    assert "wallet -> bank" in result.stdout
    assert "expense" in result.stdout
    assert "income" in result.stdout
    assert "transfer" in result.stdout
    assert re.search(r"m-[0-9a-f]{8}", result.stdout) is not None
    assert re.search(r"t-[0-9a-f]{8}", result.stdout) is not None
