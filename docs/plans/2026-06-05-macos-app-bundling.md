# Standalone macOS App Bundling Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Package the Sigma web dashboard and FastAPI backend as a standalone macOS double-clickable app (`dist/Sigma.app`) with a custom Dock icon.

**Approach:**
1. Create a minimal Python entrypoint script `src/sgm/app_launcher.py` that imports and runs the `app_cmd` function from `src/sgm/cli.py` directly.
2. Create a bash script `scripts/build_macos_app.sh` that compiles the `logo.png` into a macOS `icon.icns` file using native tools (`sips` and `iconutil`), and then compiles the app bundle with PyInstaller.
3. Update the `Makefile` with a `make app` target.
4. Run the build script and verify the output bundle.

---

### Task 1: Create the Python App Launcher Entrypoint

**Files:**
- Create: `src/sgm/app_launcher.py`

*Implement a clean Python script that starts the Typer command parser programmatically for the `app` command.*

```python
import os
import sys

# Ensure src/ is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sgm.cli import app_cmd
import typer

if __name__ == "__main__":
    # Simulate invoking the app command directly
    app_cmd(ctx=typer.Context(typer.Typer()))
```

---

### Task 2: Create the Bash Packaging Script

**Files:**
- Create: `scripts/build_macos_app.sh`

*Create a bash script that handles: (1) creating the `logo.icns` from `static/logo.png`, and (2) invoking PyInstaller with the correct parameters.*

---

### Task 3: Update Makefile

**Files:**
- Modify: `Makefile`

*Add `app` target to compile the desktop bundle.*

---

### Task 4: Run build and verify output

*Run the build and verify the double-clickable `dist/Sigma.app` bundle.*
