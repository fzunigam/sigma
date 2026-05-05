from typer.testing import CliRunner

from sgm.cli import app


def test_cli_help_renders() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Sigma" in result.stdout
