from pathlib import Path

from typer.testing import CliRunner

from sgm.cli import app

runner = CliRunner()


def test_start_creates_user_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(app, ["start"], input="\nblue\n")

    assert result.exit_code == 0
    assert (tmp_path / ".config" / "sgm" / "config.toml").exists()
