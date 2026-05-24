from typer.testing import CliRunner
from sgm.cli import app

def test_web_command_registered():
    result = CliRunner().invoke(app, ["web", "--help"])
    assert result.exit_code == 0
    assert "Start the local web dashboard server" in result.stdout
