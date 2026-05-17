from pathlib import Path

from typer.testing import CliRunner

from sgm.cli import app

runner = CliRunner()


def test_start_creates_user_config_and_db(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    # Input: 
    # n (Do you want to import?)
    # wallet (acc_id)
    # Cash (acc_name)
    # debit (acc_type)
    # 0 (acc_balance)
    result = runner.invoke(app, ["start"], input="n\nwallet\nCash\ndebit\n0\n")

    assert result.exit_code == 0
    assert (tmp_path / ".config" / "sgm" / "config.toml").exists()
    assert (tmp_path / ".local" / "share" / "sgm" / "sigma.db").exists()


def test_start_creates_credit_account(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    # Input:
    # n (Do you want to import?)
    # cc (acc_id)
    # Credit Card (acc_name)
    # credit (acc_type)
    # 0 (acc_balance)
    # 1000000 (acc_limit)
    result = runner.invoke(app, ["start"], input="n\ncc\nCredit Card\ncredit\n0\n1000000\n")

    assert result.exit_code == 0
    assert (tmp_path / ".config" / "sgm" / "config.toml").exists()
    assert (tmp_path / ".local" / "share" / "sgm" / "sigma.db").exists()
