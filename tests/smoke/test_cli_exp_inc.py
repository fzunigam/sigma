import pytest
from typer.testing import CliRunner

from sgm.cli import app
from sgm.infrastructure.database import init_db, clear_db, get_marked_total

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "sigma.db"
    
    from sgm.infrastructure import database
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)
    
    init_db(db_path)
    yield
    clear_db(db_path)

def test_cli_exp_and_inc_success() -> None:
    runner = CliRunner()
    
    # Needs an account first
    runner.invoke(app, ["acc", "add", "cc", "Credit Card", "credit", "0"])
    runner.invoke(app, ["acc", "set-limit", "cc", "100000"])
    
    result_exp = runner.invoke(app, ["exp", "5000", "lunch", "yes", "cc"])
    assert result_exp.exit_code == 0
    assert "Recorded expense of 5000 ('lunch') in 'cc'" in result_exp.output
    
    result_inc = runner.invoke(app, ["inc", "20000", "paycheck", "yes", "cc"])
    assert result_inc.exit_code == 0
    assert "Recorded income of 20000 ('paycheck') in 'cc'" in result_inc.output
    
    # Verify marked total is income - expense = 20000 - 5000 = 15000
    assert get_marked_total() == 15000

def test_cli_exp_amount_must_be_positive() -> None:
    runner = CliRunner()
    runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "10000"])
    
    result = runner.invoke(app, ["exp", "--", "-5000", "lunch", "yes", "wallet"])
    assert result.exit_code == 1
    assert "Error: Amount must be positive." in result.output

def test_cli_exp_missing_acc_id_multiple_accounts() -> None:
    runner = CliRunner()
    runner.invoke(app, ["acc", "add", "w1", "Wallet 1", "debit", "10000"])
    runner.invoke(app, ["acc", "add", "w2", "Wallet 2", "debit", "10000"])
    
    result = runner.invoke(app, ["exp", "5000", "lunch", "yes"])
    assert result.exit_code == 1
    assert "Error: Multiple accounts exist. You must specify the account ID." in result.output

def test_cli_exp_missing_acc_id_one_account() -> None:
    runner = CliRunner()
    runner.invoke(app, ["acc", "add", "w1", "Wallet 1", "debit", "10000"])
    
    result = runner.invoke(app, ["exp", "5000", "lunch", "yes"])
    assert result.exit_code == 0
    assert "Recorded expense of 5000 ('lunch') in 'w1'" in result.output

def test_cli_inc_no_accounts() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["inc", "5000", "lunch", "yes"])
    assert result.exit_code == 1
    assert "Error: No accounts exist. Use 'sgm acc add' first." in result.output
