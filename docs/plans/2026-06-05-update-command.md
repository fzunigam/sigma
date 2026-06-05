# Implementation Plan: `sgm update` Command

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the `sgm update` command to upgrade the CLI (via pip) and download/replace the compiled `Sigma.app` bundle from GitHub Releases.

**Approach:**
1. Write a smoke test in `tests/smoke/test_update_cli.py` that verifies the `update` command is registered and outputs its help message correctly.
2. Implement the `update_cmd` command in `src/sgm/cli.py` with version checks, pip upgrading, and `.app.zip` downloading/installation to `/Applications/Sigma.app`.
3. Verify that the tests pass.

---

### Task 1: Create the Update Command Smoke Test

**Files:**
- Create: `tests/smoke/test_update_cli.py`

```python
from typer.testing import CliRunner
from sgm.cli import app

def test_update_command_registered():
    result = CliRunner().invoke(app, ["update", "--help"])
    assert result.exit_code == 0
    assert "Check for updates and update both CLI and macOS Desktop App" in result.stdout
```

---

### Task 2: Implement the `update` Command in `cli.py`

**Files:**
- Modify: `src/sgm/cli.py`

*Implement `update_cmd` in `src/sgm/cli.py` using urllib and zipfile to fetch from GitHub and deploy.*
