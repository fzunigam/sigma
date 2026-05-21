from pathlib import Path

from typer.testing import CliRunner

from sgm.cli import app

runner = CliRunner()


def test_config_prompts_and_saves_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    # First initialize DB and add accounts
    runner.invoke(app, ["start"], input="n\nwallet\nCash\ndebit\n5000\n")
    runner.invoke(app, ["acc", "add", "bci", "BCI", "debit", "0"])

    # Run config command
    # inputs:
    # 1. income account
    # 2. expense account
    result = runner.invoke(app, ["config"], input="bci\nwallet\n")

    assert result.exit_code == 0
    assert "Configure default accounts." in result.stdout
    assert "Configuration saved successfully." in result.stdout

    # Now verify that defaults are applied
    # Log an expense without account ID
    result_exp = runner.invoke(app, ["exp", "5000", "lunch", "yes"])
    assert result_exp.exit_code == 0
    assert "in 'wallet'" in result_exp.stdout

    # Log an income without account ID
    result_inc = runner.invoke(app, ["inc", "10000", "salary", "yes"])
    assert result_inc.exit_code == 0
    assert "in 'bci'" in result_inc.stdout


def test_config_invalid_account(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    runner.invoke(app, ["start"], input="n\nwallet\nCash\ndebit\n0\n")

    # Run config command with an invalid account
    runner.invoke(app, ["config"], input="fake\nwallet\n")
    
    # Either the output mixed stderr or we can check the file
    config_file = tmp_path / ".config" / "sgm" / "config.toml"
    assert config_file.exists()
    content = config_file.read_text()
    assert "fake" not in content
    assert "wallet" in content


def test_config_helper_functions() -> None:
    from sgm.cli import mask_token, format_allowed_users

    # Verify masking behavior
    assert mask_token("") == "Not configured"
    assert mask_token("short") == "****"
    assert mask_token("1234567890abcdef") == "123456...cdef"

    # Verify allowed users formatting
    assert format_allowed_users([]) == "None (bot ignores messages)"
    assert format_allowed_users([123, 456]) == "123, 456"

