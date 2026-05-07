from pathlib import Path

from typer.testing import CliRunner

from sgm.cli import app

runner = CliRunner()


def test_start_creates_user_config_and_db(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    # Input: acc_id, acc_name, acc_type, acc_balance
    result = runner.invoke(app, ["start"], input="wallet\nCash\ndebit\n0\n")

    assert result.exit_code == 0
    assert (tmp_path / ".config" / "sgm" / "config.toml").exists()
    assert (tmp_path / ".local" / "share" / "sgm" / "sigma.db").exists()


def test_start_creates_credit_account(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    # Input: acc_id, acc_name, acc_type, acc_balance, acc_limit
    result = runner.invoke(app, ["start"], input="cc\nCredit Card\ncredit\n0\n1000000\n")

    assert result.exit_code == 0
    assert (tmp_path / ".config" / "sgm" / "config.toml").exists()
    assert (tmp_path / ".local" / "share" / "sgm" / "sigma.db").exists()
