from typer.testing import CliRunner
from sgm.cli import app
from sgm.infrastructure.database import init_db
from sgm.infrastructure import database

runner = CliRunner()

def test_cli_render_no_marked_movements(monkeypatch, tmp_path):
    db_path = tmp_path / "test_sigma.db"
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)
    init_db(db_path)

    result = runner.invoke(app, ["render"])
    assert result.exit_code == 0
    assert "No marked movements to render." in result.stdout

def test_cli_render_with_marked_movements(monkeypatch, tmp_path):
    db_path = tmp_path / "test_sigma.db"
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)
    init_db(db_path)

    runner.invoke(app, ["acc", "add", "cc", "Debit Card", "debit", "10000"])
    runner.invoke(app, ["exp", "500", "lunch", "yes", "cc"])
    runner.invoke(app, ["inc", "2000", "salary", "yes", "cc"])
    runner.invoke(app, ["exp", "100", "coffee", "no", "cc"])

    result = runner.invoke(app, ["render"])
    assert result.exit_code == 0
    assert "Rendered 2 movements." in result.stdout
    assert "Net amount logged: 1500" in result.stdout

    # Running it again should have 0 to render
    result2 = runner.invoke(app, ["render"])
    assert result2.exit_code == 0
    assert "No marked movements to render." in result2.stdout
