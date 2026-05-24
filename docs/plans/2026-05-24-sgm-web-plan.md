# `sgm web` Local Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new CLI command `sgm web` that launches a local FastAPI server to serve a beautifully styled Next.js dashboard for Sigma.

**Architecture:** A FastAPI application serves local REST API routes under `/api/v1` and mounts the Next.js static output directory to serve the frontend as a single-page application (SPA). Next.js will be built using static export (`output: 'export'`), removing any Node.js runtime requirement for end users.

**Tech Stack:** FastAPI, Uvicorn, Pydantic, Next.js, React, TypeScript, Vanilla CSS.

---

### Task 1: Add Dependencies & Test Infrastructure

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/smoke/test_dependencies.py`

**Step 1: Write the failing test**
Create `tests/smoke/test_dependencies.py` to assert that FastAPI and Uvicorn can be imported:
```python
def test_web_dependencies():
    try:
        import fastapi
        import uvicorn
        assert fastapi.__version__
        assert uvicorn.__version__
    except ImportError as e:
        assert False, f"Missing dependency: {e}"
```

**Step 2: Run test to verify it fails**
Run: `python3.12 -m pytest tests/smoke/test_dependencies.py`
Expected: FAIL (FastAPI and Uvicorn not installed/configured).

**Step 3: Write minimal implementation**
1. Add `fastapi>=0.110.0` and `uvicorn>=0.28.0` to the `dependencies` list in `pyproject.toml`.
2. Run installation command: `python3.12 -m pip install -e .`

**Step 4: Run test to verify it passes**
Run: `python3.12 -m pytest tests/smoke/test_dependencies.py`
Expected: PASS.

**Step 5: Commit**
```bash
git add pyproject.toml tests/smoke/test_dependencies.py
git commit -m "feat: add fastapi and uvicorn dependencies"
```

---

### Task 2: Implement FastAPI Web Server

**Files:**
- Create: `src/sgm/interface/web/__init__.py`
- Create: `src/sgm/interface/web/server.py`
- Create: `tests/integration/test_web_server.py`

**Step 1: Write the failing test**
Create `tests/integration/test_web_server.py` using FastAPI's `TestClient` to call the `/api/v1/status` endpoint:
```python
from fastapi.testclient import TestClient
import pytest

def test_status_endpoint(monkeypatch, tmp_path):
    # Mock DB path to keep tests isolated
    from sgm.infrastructure.database import init_db
    db_file = tmp_path / "test_sigma.db"
    monkeypatch.setattr("sgm.infrastructure.database.get_db_path", lambda: db_file)
    init_db(db_file)
    
    from sgm.interface.web.server import app
    client = TestClient(app)
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "accounts" in data
    assert "marked_total" in data
```

**Step 2: Run test to verify it fails**
Run: `python3.12 -m pytest tests/integration/test_web_server.py`
Expected: FAIL (Module `sgm.interface.web.server` does not exist).

**Step 3: Write minimal implementation**
1. Create `src/sgm/interface/web/__init__.py` (empty or base imports).
2. Create `src/sgm/interface/web/server.py` and define the FastAPI application. Import database helpers from `sgm.infrastructure.database`.
   * Implement endpoints: `/api/v1/status`, `/api/v1/accounts`, `/api/v1/transactions`, `/api/v1/render`, and `/api/v1/config`.
   * Mount static files using `fastapi.staticfiles.StaticFiles`.
   * Write an exception handler for `HTTPException` or database exceptions, mapping validation failures to HTTP `400 Bad Request`.
   * Implement catch-all SPA routing: if path does not exist, return `index.html`.

**Step 4: Run test to verify it passes**
Run: `python3.12 -m pytest tests/integration/test_web_server.py`
Expected: PASS.

**Step 5: Commit**
```bash
git add src/sgm/interface/web/server.py src/sgm/interface/web/__init__.py tests/integration/test_web_server.py
git commit -m "feat: implement fastapi web server and api endpoints"
```

---

### Task 3: Add `sgm web` CLI Command

**Files:**
- Modify: `src/sgm/cli.py`
- Create: `tests/smoke/test_web_cli.py`

**Step 1: Write the failing test**
Create `tests/smoke/test_web_cli.py` to check that the `web` command exists and is registered:
```python
from typer.testing import CliRunner
from sgm.cli import app

runner = CliRunner()

def test_web_command_help():
    result = runner.invoke(app, ["web", "--help"])
    assert result.exit_code == 0
    assert "web" in result.output
```

**Step 2: Run test to verify it fails**
Run: `python3.12 -m pytest tests/smoke/test_web_cli.py`
Expected: FAIL (No such command "web").

**Step 3: Write minimal implementation**
1. Add `@app.command("web")` in `src/sgm/cli.py`.
2. Implement parameters: `--host` (default `127.0.0.1`), `--port` (default `8000`), and `--no-browser` (flag).
3. Import `uvicorn` and `webbrowser` inside the command.
4. Implement configuration check (`is_configured()`), initialize the database (`init_db()`), and check if the static assets folder contains `index.html` (displaying a warning if it doesn't).
5. Start Uvicorn: `uvicorn.run("sgm.interface.web.server:app", host=host, port=port)`.
6. Open browser on startup event using a thread or FastAPI startup hook.

**Step 4: Run test to verify it passes**
Run: `python3.12 -m pytest tests/smoke/test_web_cli.py`
Expected: PASS.

**Step 5: Commit**
```bash
git add src/sgm/cli.py tests/smoke/test_web_cli.py
git commit -m "feat: add web command to SGM CLI"
```

---

### Task 4: Scaffold Next.js Frontend

**Files:**
- Create: `web/package.json`
- Create: `web/next.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/src/app/layout.tsx`
- Create: `web/src/app/page.tsx`

**Step 1: Create package.json & Configuration**
Create `web/package.json`:
```json
{
  "name": "sigma-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "next": "^14.2.3"
  },
  "devDependencies": {
    "typescript": "^5.4.5",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0"
  }
}
```

Create `web/next.config.ts` (or `next.config.js`):
```typescript
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'export',
  distDir: '../src/sgm/interface/web/static',
  images: {
    unoptimized: true
  }
};

export default nextConfig;
```

**Step 2: Create Layout and Base Page**
Create basic Next.js page components in `web/src/app/page.tsx` and `web/src/app/layout.tsx` that output simple headers.

**Step 3: Run Next.js Build**
Run: `cd web && npm install && npm run build`
Expected: Build finishes successfully, and static files populate `src/sgm/interface/web/static/`.

**Step 4: Commit**
```bash
git add web/package.json web/next.config.ts web/tsconfig.json web/src/app/layout.tsx web/src/app/page.tsx
git commit -m "feat: scaffold next.js frontend application"
```

---

### Task 5: Build UI Dashboard Components (Web Design Guidelines)

**Files:**
- Create: `web/src/app/globals.css`
- Create/Modify: `web/src/app/page.tsx`
- Create: `web/src/components/Sidebar.tsx`
- Create: `web/src/components/QuickLogger.tsx`
- Create: `web/src/components/TransactionTable.tsx`
- Create: `web/src/components/RenderModal.tsx`

**Step 1: Build Vanilla CSS layout & Premium Theme**
Create `web/src/app/globals.css` using modern properties: CSS variables for theme colours, glassmorphism shadows, backdrop blurs, Outfit/Inter fonts, transitions for opacity/transform.

**Step 2: Build UI Components**
1. Implement Sidebar navigation to switch tabs (Dashboard vs. Accounts vs. History).
2. Implement Dashboard showing accounts grid, marked balance, and the prominent "Render Cycle" button.
3. Implement `QuickLogger` form (Income, Expense, Transfer) with input validation, proper amount parsing, automatic default accounts, and a submit loading spinner.
4. Implement `TransactionTable` displaying movements & transfers with `tabular-nums` alignment and row delete confirmations.
5. Apply all accessibility checks: aria-labels on icon buttons, keyboard focus rings, semantic labels.

**Step 3: Run build & verify**
Run: `cd web && npm run build`
Expected: Zero TypeScript/linting errors. Build compiles successfully to `static/`.

**Step 4: Commit**
```bash
git add web/src/
git commit -m "feat: implement frontend components and style system according to design guidelines"
```

---

### Task 7: End-to-End Integration & Lint Checks

**Files:**
- Create: `tests/smoke/test_web_integration.py`

**Step 1: Write integration smoke test**
Write a test that runs the FastAPI app, does client requests to log transactions, renmes accounts, deletes a transaction, triggers render, and asserts DB state updates correctly.

**Step 2: Run all checks**
Run: `python3.12 -m pytest`
Run: `python3.12 -m ruff check .`
Expected: All tests pass, and ruff returns clean status.

**Step 3: Commit**
```bash
git add tests/smoke/test_web_integration.py
git commit -m "test: add end-to-end integration test for local web server"
```
