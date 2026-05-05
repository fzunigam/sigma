from typer.testing import CliRunner

from sgm.cli import app

runner = CliRunner()


def test_account_create_then_list_uses_default_sqlite_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    create_result = runner.invoke(app, ["account", "create", "a1", "Checking", "debit", "1200"])
    list_result = runner.invoke(app, ["account", "list"])

    assert create_result.exit_code == 0
    assert list_result.exit_code == 0
    assert "a1" in list_result.stdout
    assert "Checking" in list_result.stdout
    assert "1200" in list_result.stdout


def test_movement_add_then_pending_uses_default_sqlite_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    account_result = runner.invoke(app, ["account", "create", "a1", "Cash", "debit", "0"])
    add_result = runner.invoke(
        app, ["movement", "add", "m1", "a1", "Salary", "1000", "income"]
    )
    marked_result = runner.invoke(app, ["pending"])

    assert account_result.exit_code == 0
    assert add_result.exit_code == 0
    assert marked_result.exit_code == 0
    assert "m1" in marked_result.stdout
    assert "Salary" in marked_result.stdout
    assert "income" in marked_result.stdout


def test_flat_render_command_runs_and_clears_pending(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner.invoke(app, ["account", "create", "a1", "Cash", "debit", "0"])
    runner.invoke(app, ["income", "a1", "1000", "Salary"])
    runner.invoke(app, ["expense", "a1", "250", "Groceries"])

    result = runner.invoke(app, ["render"])
    marked_after = runner.invoke(app, ["pending"])

    assert result.exit_code == 0
    assert marked_after.exit_code == 0
    assert "Net: 750" in result.stdout
    assert "(none)" in marked_after.stdout
