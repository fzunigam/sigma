from pathlib import Path

from typer.testing import CliRunner

from sgm.cli import app

runner = CliRunner()


def _invoke(db_path: Path, args: list[str]):
    return runner.invoke(app, ["--db", str(db_path), *args])


def test_render_help_lists_run_command() -> None:
    result = runner.invoke(app, ["render", "--help"])

    assert result.exit_code == 0
    assert "run" in result.stdout


def test_account_create_then_list_uses_sqlite_db(tmp_path: Path) -> None:
    db_path = tmp_path / "sigma.db"
    create_result = _invoke(db_path, ["account", "create", "a1", "Checking", "debit", "1200"])
    list_result = _invoke(db_path, ["account", "list"])

    assert create_result.exit_code == 0
    assert list_result.exit_code == 0
    assert "a1" in list_result.stdout
    assert "Checking" in list_result.stdout
    assert "1200" in list_result.stdout


def test_movement_add_then_list_marked_uses_sqlite_db(tmp_path: Path) -> None:
    db_path = tmp_path / "sigma.db"
    account_result = _invoke(
        db_path, ["account", "create", "a1", "Cash", "debit", "0"]
    )
    add_result = _invoke(
        db_path, ["movement", "add", "m1", "a1", "Salary", "1000", "income"]
    )
    marked_result = _invoke(db_path, ["movement", "list-marked"])

    assert account_result.exit_code == 0
    assert add_result.exit_code == 0
    assert marked_result.exit_code == 0
    assert "m1" in marked_result.stdout
    assert "Salary" in marked_result.stdout
    assert "income" in marked_result.stdout


def test_render_run_succeeds_and_prints_net(tmp_path: Path) -> None:
    db_path = tmp_path / "sigma.db"
    _invoke(db_path, ["account", "create", "a1", "Cash", "debit", "0"])
    _invoke(db_path, ["movement", "add", "m1", "a1", "Salary", "1000", "income"])
    _invoke(db_path, ["movement", "add", "m2", "a1", "Groceries", "250", "expense"])

    result = _invoke(db_path, ["render", "run", "s1"])
    marked_after = _invoke(db_path, ["movement", "list-marked"])

    assert result.exit_code == 0
    assert marked_after.exit_code == 0
    assert "Net: 750" in result.stdout
    assert "(none)" in marked_after.stdout
