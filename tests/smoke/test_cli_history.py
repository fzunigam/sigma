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
    
def test_history_empty(clean_db):
    result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "No render history found." in result.stdout

def test_history_command(clean_db):
    # Setup account
    runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "10000"])
    
    # Record movement
    runner.invoke(app, ["exp", "1000", "lunch", "yes", "wallet"])
    
    # Render
    result = runner.invoke(app, ["render"])
    assert result.exit_code == 0
    assert "Rendered 1 movements." in result.stdout
    assert "Net amount logged: -1000" in result.stdout
    
    # Check history
    import re
    result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "Render History" in result.stdout
    assert re.search(r"\b[0-9a-f]{8}\b", result.stdout) is not None
    assert "-1000" in result.stdout
