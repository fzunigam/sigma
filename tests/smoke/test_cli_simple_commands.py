from typer.testing import CliRunner

from sgm.cli import app

runner = CliRunner()


def test_help_shows_simple_commands_not_db_flag() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "expense" in result.stdout
    assert "income" in result.stdout
    assert "--db" not in result.stdout


def test_expense_command_shape(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner.invoke(app, ["account", "create", "cash", "Cash", "debit", "0"])
    result = runner.invoke(app, ["expense", "cash", "2500", "Lunch"])

    assert result.exit_code == 0
