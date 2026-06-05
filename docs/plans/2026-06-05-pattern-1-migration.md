# Pattern 1 Migration: GUI-First, CLI Bundled Inside

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the Sigma repository to the professional "GUI-First, CLI Bundled Inside" model (Pattern 1), where the App (`Sigma.app`) is the primary distribution channel containing both the GUI and the CLI, and automatically sets up symbolic linking.

**Approach:**
1. Create a CLI launcher script `src/sgm/cli_launcher.py`.
2. Update `src/sgm/app_launcher.py` to add and execute the `ensure_cli_symlink()` function on startup.
3. Create a custom PyInstaller specification file `Sigma.spec` that defines both `Sigma` (GUI) and `sgm` (CLI) executables and bundles them together inside `Sigma.app`.
4. Update `scripts/build_macos_app.sh` to build using `Sigma.spec`.
5. Update documentation (`README.md`, `CHANGELOG.md`, `AGENTS.md`, and `CLAUDE.md`) to align with the new distribution model.

---

### Task 1: Create the CLI Launcher

**Files:**
- Create: `src/sgm/cli_launcher.py`

*Write the python entrypoint for the CLI command inside the app bundle.*

```python
import os
import sys

# Ensure src/ is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sgm.cli import app

if __name__ == "__main__":
    app()
```

---

### Task 2: Implement Symlink Creation in the GUI Launcher

**Files:**
- Modify: `src/sgm/app_launcher.py`

*Add and call the `ensure_cli_symlink()` function when double-clicking the GUI app.*

---

### Task 3: Create custom PyInstaller Spec File

**Files:**
- Create: `Sigma.spec`

*Define a custom spec file to compile both executables (GUI and CLI) into the same macOS bundle.*

---

### Task 4: Update Build Script to use the Spec File

**Files:**
- Modify: `scripts/build_macos_app.sh`

*Modify the PyInstaller invocation to run `pyinstaller --noconfirm --clean Sigma.spec`.*

---

### Task 5: Update Documentation and Repository Readmes

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `docs/architecture.md`
- Modify: `docs/cli-usage.md`

---

### Task 6: Compile and Verify the new Bundle

*Run `make app` to build, copy to `/Applications/Sigma.app`, double-click the GUI, and verify the `sgm` CLI command is automatically linked and fully functional in the terminal.*
