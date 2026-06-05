from typer.testing import CliRunner
from sgm.cli import app

def test_app_command_registered():
    result = CliRunner().invoke(app, ["app", "--help"])
    assert result.exit_code == 0
    assert "Launch the Sigma desktop app in a native window" in result.stdout
