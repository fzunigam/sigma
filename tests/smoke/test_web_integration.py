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

def test_web_command_auto_compile(monkeypatch, tmp_path):
    # Mock is_configured to return True
    monkeypatch.setattr("sgm.cli.is_configured", lambda: True)
    monkeypatch.setattr("sgm.cli.init_db", lambda: None)
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: None)
    
    # Mock index_file not existing
    import os
    orig_exists = os.path.exists
    def mock_exists(path):
        if path.endswith("index.html"):
            return False
        if path.endswith("package.json"):
            return True
        if path.endswith("node_modules"):
            return False
        return orig_exists(path)
    monkeypatch.setattr("os.path.exists", mock_exists)
    
    # Mock shutil.which to find npm
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/npm" if cmd == "npm" else None)
    
    # Mock subprocess.run
    called_cmds = []
    def mock_run(cmd, *args, **kwargs):
        called_cmds.append(cmd)
        class MockCompletedProcess:
            returncode = 0
        return MockCompletedProcess()
    monkeypatch.setattr("subprocess.run", mock_run)
    
    # Temporarily remove PYTEST_CURRENT_TEST to let it trigger
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        
    result = runner.invoke(app, ["web", "--no-browser"])
    assert result.exit_code == 0
    assert "Web dashboard static assets not found. Compiling frontend dashboard automatically..." in result.output
    assert "Installing web dependencies..." in result.output
    assert "Building web dashboard..." in result.output
    assert "Web dashboard compiled successfully!" in result.output
    assert len(called_cmds) == 2
    assert "install" in called_cmds[0]
    assert "build" in called_cmds[1]
