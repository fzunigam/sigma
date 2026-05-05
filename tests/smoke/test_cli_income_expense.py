from typer.testing import CliRunner

from sgm.cli import app

runner = CliRunner()


def test_income_then_expense_are_logged_as_marked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner.invoke(app, ["account", "create", "cash", "Cash", "debit", "0"])
    income_result = runner.invoke(app, ["income", "cash", "100000", "Salary"])
    expense_result = runner.invoke(app, ["expense", "cash", "12000", "Groceries"])
    marked = runner.invoke(app, ["pending"])

    assert income_result.exit_code == 0
    assert expense_result.exit_code == 0
    assert "Salary" in marked.stdout
    assert "Groceries" in marked.stdout
