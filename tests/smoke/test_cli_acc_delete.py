from typer.testing import CliRunner
import pytest
from sgm.cli import app
from sgm.infrastructure.database import get_account, get_accounts, get_recent_logs, init_db

runner = CliRunner()

@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Isolate the database and config to a temporary directory."""
    test_db = tmp_path / "sigma.db"
    test_config = tmp_path / "config.json"
    
    # Mock paths
    monkeypatch.setattr("sgm.infrastructure.database.get_db_path", lambda: test_db)
    monkeypatch.setattr("sgm.infrastructure.user_config.config_path", lambda: test_config)
    
    # Initialize config to bypass start wizard
    import json
    test_config.parent.mkdir(parents=True, exist_ok=True)
    with open(test_config, "w") as f:
        json.dump({"configured": True}, f)
        
    init_db(test_db)


def test_acc_delete_success(monkeypatch):
    # Setup initial accounts and movements
    runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "1000"])
    runner.invoke(app, ["acc", "add", "bank", "Bank Account", "debit", "0"])
    
    # Log movement
    runner.invoke(app, ["exp", "500", "lunch", "no", "wallet"])
    # Log transfer
    runner.invoke(app, ["tr", "wallet", "bank", "200"])
    
    # Verify pre-deletion state
    accounts = get_accounts()
    assert len(accounts) == 2
    assert get_account("wallet")["balance"] == 300
    
    logs = get_recent_logs(5)
    assert len(logs) == 2
    
    # Mock confirmation to return "DELETE"
    monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "DELETE")
    
    # Delete 'wallet'
    result = runner.invoke(app, ["acc", "delete", "wallet"])
    assert result.exit_code == 0
    assert "Account 'wallet' deleted successfully" in result.output
    
    # Verify it is removed from accounts
    accounts = get_accounts()
    assert len(accounts) == 1
    assert accounts[0]["id"] == "bank"
    assert get_account("wallet") is None
    
    # Verify the hidden 'deleted' account exists but doesn't show in list
    deleted_acc = get_account("deleted")
    assert deleted_acc is not None
    assert deleted_acc["id"] == "deleted"
    
    # Verify logs are reassigned to 'deleted'
    logs = get_recent_logs(5)
    assert len(logs) == 2
    
    # The movement should have account_id = 'deleted'
    movement = next(log for log in logs if log["type"] == "expense")
    assert movement["account_id"] == "deleted"
    
    # The transfer should have from_account = 'deleted'
    # description is "from_account -> to_account"
    transfer = next(log for log in logs if log["type"] == "transfer")
    assert "deleted -> bank" in transfer["description"]


def test_acc_delete_cancel(monkeypatch):
    runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "1000"])
    
    # Mock confirmation to return "NO"
    monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "NO")
    
    result = runner.invoke(app, ["acc", "delete", "wallet"])
    assert result.exit_code == 0
    assert "Account deletion cancelled" in result.output
    
    # Verify it still exists
    assert get_account("wallet") is not None


def test_acc_delete_not_found():
    result = runner.invoke(app, ["acc", "delete", "missing"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_recreate_deleted_account(monkeypatch):
    runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "1000"])
    
    monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "DELETE")
    runner.invoke(app, ["acc", "delete", "wallet"])
    
    # Recreate the same ID but with different initial balance
    result = runner.invoke(app, ["acc", "add", "wallet", "New Wallet", "debit", "5000"])
    assert result.exit_code == 0
    assert "Account 'New Wallet' created successfully" in result.output
    
    # Verify the balance is the new one, not the old 1000
    acc = get_account("wallet")
    assert acc["balance"] == 5000
    assert acc["name"] == "New Wallet"


def test_prevent_manipulating_deleted_account():
    # Attempt to add an account named 'deleted'
    result = runner.invoke(app, ["acc", "add", "deleted", "Ghost", "debit", "0"])
    assert result.exit_code == 1
    assert "Cannot create an account with the reserved ID 'deleted'" in result.output
    
    # First, let's create a normal account and delete it to force 'deleted' account creation
    runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "1000"])
    
    # Use standard input mocking for the confirmation
    result = runner.invoke(app, ["acc", "delete", "wallet"], input="DELETE\n")
    assert result.exit_code == 0
    
    # Now try to delete 'deleted'
    result = runner.invoke(app, ["acc", "delete", "deleted"], input="DELETE\n")
    assert result.exit_code == 1
    assert "Cannot delete the reserved 'deleted' account" in result.output
    
    # Try to rename 'deleted'
    result = runner.invoke(app, ["acc", "rename", "deleted", "ghost"])
    assert result.exit_code == 1
    assert "Cannot rename to or from the reserved ID 'deleted'" in result.output
    
    # Try to rename something to 'deleted'
    runner.invoke(app, ["acc", "add", "cc", "CC", "credit", "0"])
    result = runner.invoke(app, ["acc", "rename", "cc", "deleted"])
    assert result.exit_code == 1
    assert "Cannot rename to or from the reserved ID 'deleted'" in result.output
