from typer.testing import CliRunner

from sgm.cli import app


def test_cli_help_renders() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "---commands" in result.stdout
    assert "start" in result.stdout
