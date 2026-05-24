from typer.testing import CliRunner
from sgm.cli import app

runner = CliRunner()

def test_web_command_not_configured(monkeypatch, tmp_path):
    # Mock is_configured to return False
    monkeypatch.setattr("sgm.cli.is_configured", lambda: False)
    
    result = runner.invoke(app, ["web"])
    assert result.exit_code == 1
    assert "Error: Sigma configuration file not found" in result.output

def test_web_command_running(monkeypatch, tmp_path):
    # Mock is_configured to return True
    monkeypatch.setattr("sgm.cli.is_configured", lambda: True)
    
    # Mock init_db
    init_called = False
    def mock_init_db():
        nonlocal init_called
        init_called = True
    monkeypatch.setattr("sgm.cli.init_db", mock_init_db)
    
    # Mock uvicorn.run to prevent it from actually running a blocking loop in tests
    uvicorn_args = {}
    def mock_uvicorn_run(web_app, host, port, log_level):
        uvicorn_args["host"] = host
        uvicorn_args["port"] = port
        uvicorn_args["web_app"] = web_app
        # Do not block, return immediately for the test
        return
        
    monkeypatch.setattr("uvicorn.run", mock_uvicorn_run)
    
    result = runner.invoke(app, ["web", "--host", "127.0.0.2", "--port", "9000", "--no-browser"])
    assert result.exit_code == 0
    assert "Starting Sigma local dashboard server on http://127.0.0.2:9000" in result.output
    assert init_called
    assert uvicorn_args["host"] == "127.0.0.2"
    assert uvicorn_args["port"] == 9000
    assert uvicorn_args["web_app"] is not None
