from typer.testing import CliRunner
from sgm.cli import app

def test_update_command_registered():
    result = CliRunner().invoke(app, ["update", "--help"])
    assert result.exit_code == 0
    assert "Update sgm and the macOS desktop application to the latest version" in result.stdout
