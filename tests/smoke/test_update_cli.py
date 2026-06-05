from typer.testing import CliRunner
from sgm.cli import app
from unittest.mock import patch, MagicMock
import sys

def test_update_command_registered():
    result = CliRunner().invoke(app, ["update", "--help"])
    assert result.exit_code == 0
    assert "Update sgm and the macOS desktop application to the latest version" in result.stdout

def test_update_command_frozen(monkeypatch):
    # Simulate a frozen PyInstaller application bundle on macOS
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "executable", "/Applications/Sigma.app/Contents/MacOS/sgm")

    # Mock the HTTP response from GitHub releases API
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"tag_name": "v9.9.9", "assets": []}'
    
    with patch("urllib.request.urlopen", return_value=mock_response), \
         patch("urllib.request.Request"), \
         patch("subprocess.run") as mock_run:
         
        result = CliRunner().invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Running from a compiled standalone application bundle. Skipping pip package upgrade." in result.stdout
        # Assert subprocess.run (used for pip) was NOT called
        mock_run.assert_not_called()

