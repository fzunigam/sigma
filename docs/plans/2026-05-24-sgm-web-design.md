# Design Document: Local Web Interface (`sgm web`)

**Date**: 2026-05-24  
**Status**: Approved

## Context & Objectives
Sigma is currently a local-first CLI personal finance tracker. While the CLI is fast and optimized for quick logging, some users prefer a visual dashboard to audit transactions, view balances, and log entries without typing CLI commands. 

This feature adds a new command `sgm web` that spins up a localhost web application. It uses a **FastAPI backend** running locally, serving a compiled **Next.js static export** (HTML/CSS/JS SPA) so that the end user has zero Node.js runtime dependencies.

---

## 1. Architecture & Directory Structure
The frontend lives in `web/` during development. When built, the static files are compiled directly into the python package folder under `src/sgm/interface/web/static/` so they are packaged and distributed easily.

```
sigma/
├── pyproject.toml                     # Python dependencies (adds fastapi, uvicorn)
├── src/
│   └── sgm/
│       ├── cli.py                     # Adds `web` command
│       └── interface/
│           └── web/
│               ├── __init__.py
│               ├── server.py          # FastAPI application
│               └── static/            # Placed in .gitignore; populated on build
└── web/                               # Next.js React/TypeScript project
    ├── package.json
    ├── next.config.ts                 # Set to output: 'export'
    └── src/
        ├── app/                       # Layouts and pages
        └── components/                # UI components (forms, tables, cards)
```

---

## 2. Backend API Endpoints
The FastAPI server binds to localhost (default `127.0.0.1:8000`) and serves the following endpoints:

*   **Dashboard & Config**:
    *   `GET /api/v1/status`: Fetch accounts, current balances, credit limits, and marked totals.
    *   `GET /api/v1/config`: Fetch default accounts for income/expenses.
    *   `PUT /api/v1/config`: Save default accounts.
*   **Accounts**:
    *   `GET /api/v1/accounts`: List all accounts.
    *   `POST /api/v1/accounts`: Create an account.
    *   `PUT /api/v1/accounts/{id}/rename`: Rename account ID.
    *   `PUT /api/v1/accounts/{id}/limit`: Update credit limit.
    *   `DELETE /api/v1/accounts/{id}`: Safely delete account.
*   **Transactions**:
    *   `GET /api/v1/transactions`: Query unified log of movements & transfers.
    *   `POST /api/v1/transactions/expense`: Log expense movement.
    *   `POST /api/v1/transactions/income`: Log income movement.
    *   `POST /api/v1/transactions/transfer`: Log transfer.
    *   `DELETE /api/v1/transactions/{id}`: Delete transaction by ID.
*   **Rendering**:
    *   `POST /api/v1/render`: Run render cycle (clearing marked items).
    *   `GET /api/v1/render/history`: List past render snapshots.

---

## 3. Frontend UI Design (Next.js & Vanilla CSS)
In accordance with the Vercel Web Interface Guidelines and core aesthetics:
*   **Theme**: Slate-dark base with emerald green accents for income/positive states, and rose-gold accents for expense/negative states. Glassmorphism details with frosted borders and backdrop blurs.
*   **Typography**: Google Font **Outfit** for headings and **Inter** for UI text. Numbers and balances use `font-variant-numeric: tabular-nums` to ensure exact column alignment.
*   **Accessibility**: Icon buttons have `aria-label`, inputs use semantic labels, and focus rings (`focus-visible:ring-emerald-500`) are active. Loaders show standard ellipses `…`.
*   **Quick Logger**: Simple tabbed card to quickly input expenses, income, or transfers. Automatically defaults accounts based on configuration.
*   **Animation**: Smooth transition durations on hover/active states (never `transition: all`, explicitly targeting properties).

---

## 4. CLI Subcommand (`sgm web`)
*   **Syntax**: `sgm web [--host TEXT] [--port INTEGER] [--no-browser]`
*   **Behavior**:
    1. Verify database configuration is complete (prompt `sgm start` if not).
    2. Initialize DB files if not already created.
    3. Programmatically start Uvicorn.
    4. Auto-open default browser to `http://{host}:{port}` (unless `--no-browser` is specified) once server is active.
