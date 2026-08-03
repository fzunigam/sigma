"""Local HTTP API consumed by the interface running in the app window.

The server only ever listens on the loopback interface and talks to one
database at a time — the file the user selected. Every handler resolves that
path through :func:`sigma.database.require_current`, so switching databases
takes effect immediately with no restart.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from sigma import __version__, database, installer, settings, updates
from sigma.api_investments import router as investments_router
from sigma.db import (
    accounts,
    investment_metrics,
    movements,
    preferences,
    reconciliations,
    transfers,
)
from sigma.db.errors import DatabaseFileError, NotFound, SigmaError, ValidationError

STATIC_DIR = Path(__file__).parent / "web" / "static"

app = FastAPI(title="Sigma", version=__version__, docs_url=None, redoc_url=None)
app.include_router(investments_router)


# --- Error handling --------------------------------------------------------

STATUS_BY_ERROR = {NotFound: 404, ValidationError: 400, DatabaseFileError: 400}

# FastAPI needs all three hints together to emit a genuinely bodiless 204.
NO_CONTENT: dict[str, Any] = {
    "status_code": 204,
    "response_class": Response,
    "response_model": None,
}


@app.exception_handler(SigmaError)
async def handle_sigma_error(request: Request, exc: SigmaError) -> JSONResponse:
    status = next(
        (code for kind, code in STATUS_BY_ERROR.items() if isinstance(exc, kind)), 400
    )
    return JSONResponse({"detail": str(exc)}, status_code=status)


# --- Schemas ---------------------------------------------------------------


class PathPayload(BaseModel):
    path: str = Field(..., min_length=1)


class ThemePayload(BaseModel):
    theme: str = Field(..., pattern="^(dark|light)$")


class AccountCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=80)
    kind: str = Field(..., pattern="^(debit|credit|investment)$")
    balance: int = 0
    credit_limit: int = 0


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    credit_limit: int | None = None


class AccountIdUpdate(BaseModel):
    id: str = Field(..., min_length=1, max_length=40)


class MovementCreate(BaseModel):
    kind: str = Field(..., pattern="^(expense|income)$")
    amount: int = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=200)
    account_id: str | None = None
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    pending: bool = True


class MovementUpdate(BaseModel):
    """Every field optional: the interface sends only what the user changed."""

    kind: str | None = Field(default=None, pattern="^(expense|income)$")
    amount: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=1, max_length=200)
    account_id: str | None = Field(default=None, min_length=1)
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    pending: bool | None = None


class MovementPending(BaseModel):
    pending: bool


class TransferCreate(BaseModel):
    from_account: str = Field(..., min_length=1)
    to_account: str = Field(..., min_length=1)
    amount: int = Field(..., gt=0)
    description: str = Field(default="", max_length=200)
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class TransferUpdate(BaseModel):
    from_account: str | None = Field(default=None, min_length=1)
    to_account: str | None = Field(default=None, min_length=1)
    amount: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=200)
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PreferencesUpdate(BaseModel):
    default_expense_account: str = ""
    default_income_account: str = ""


# --- Database file ---------------------------------------------------------


@app.get("/api/database")
def database_status() -> dict[str, Any]:
    payload = database.status()
    payload["version"] = __version__
    return payload


@app.post("/api/database/create")
def database_create(payload: PathPayload) -> dict[str, Any]:
    database.create(Path(payload.path))
    return database_status()


@app.post("/api/database/open")
def database_open(payload: PathPayload) -> dict[str, Any]:
    database.open_existing(Path(payload.path))
    return database_status()


@app.post("/api/database/migrate")
def database_migrate(payload: PathPayload) -> dict[str, Any]:
    result = database.migrate_legacy(Path(payload.path))
    return {**database_status(), "migrated": result["migrated"]}


@app.post("/api/database/restore")
def database_restore(payload: PathPayload) -> dict[str, Any]:
    database.restore_backup(Path(payload.path))
    return database_status()


@app.put("/api/theme")
def update_theme(payload: ThemePayload) -> dict[str, Any]:
    settings.set_theme(payload.theme)
    return {"theme": payload.theme}


# --- New versions ----------------------------------------------------------
# Kept out of /api/database so the startup status call never waits on the
# network: the interface asks for this one on its own, once, and ignores it if
# it fails.


@app.get("/api/update")
def update_check() -> dict[str, Any]:
    return updates.check()


@app.post("/api/update/install")
def update_install() -> dict[str, Any]:
    """Leave the new version staged and ready. The window closes right after."""
    return installer.install()


# --- Summary ---------------------------------------------------------------


@app.get("/api/summary")
def summary(month: str | None = None) -> dict[str, Any]:
    db = database.require_current()
    month = month or date.today().strftime("%Y-%m")
    account_list = [_with_investment_value(db, a) for a in accounts.list_accounts(db)]

    return {
        "accounts": account_list,
        "totals": _totals(account_list),
        "pending": reconciliations.pending_summary(db),
        "month": {"period": month, **movements.month_summary(db, month)},
        "recent": movements.list_activity(db, limit=8),
        "reconciliations": reconciliations.list_reconciliations(db, limit=6),
        "preferences": preferences.load_preferences(db),
    }


def _with_investment_value(db: Path, account: dict[str, Any]) -> dict[str, Any]:
    """An investment account's ``balance`` is only its CLP cash — showing that
    alone next to a debit/credit balance would read as "no money here" even
    with a full portfolio in USD and stocks. ``total_value_clp`` is the number
    the interface actually displays for it."""
    if account["kind"] != "investment":
        return account
    value = investment_metrics.account_metrics(db, account["id"])["total_value_clp"]
    return {**account, "total_value_clp": value}


def _totals(account_list: list[dict[str, Any]]) -> dict[str, int]:
    """Cash on hand, card debt, investments at their last cached value, and
    what is actually yours once debt is paid. Uses the price/FX cache only —
    never a network call, so Resumen stays instant and works offline."""
    available = sum(a["balance"] for a in account_list if a["kind"] == "debit")
    debt = sum(a["balance"] for a in account_list if a["kind"] == "credit")
    investment_total = sum(
        a["total_value_clp"] for a in account_list if a["kind"] == "investment"
    )
    return {
        "available": available,
        "debt": debt,
        "investments": investment_total,
        "net": available - debt + investment_total,
    }


# --- Accounts --------------------------------------------------------------


@app.get("/api/accounts")
def list_accounts(include_deleted: bool = False) -> list[dict[str, Any]]:
    return accounts.list_accounts(database.require_current(), include_deleted=include_deleted)


@app.post("/api/accounts", status_code=201)
def create_account(payload: AccountCreate) -> dict[str, Any]:
    return accounts.create_account(
        database.require_current(),
        payload.id,
        payload.name,
        payload.kind,
        balance=payload.balance,
        credit_limit=payload.credit_limit,
    )


@app.patch("/api/accounts/{account_id}")
def update_account(account_id: str, payload: AccountUpdate) -> dict[str, Any]:
    return accounts.update_account(
        database.require_current(),
        account_id,
        name=payload.name,
        credit_limit=payload.credit_limit,
    )


@app.put("/api/accounts/{account_id}/id")
def rename_account_id(account_id: str, payload: AccountIdUpdate) -> dict[str, Any]:
    return accounts.rename_account_id(database.require_current(), account_id, payload.id)


@app.delete("/api/accounts/{account_id}", **NO_CONTENT)
def delete_account(account_id: str) -> None:
    accounts.delete_account(database.require_current(), account_id)


# --- Movements and transfers ----------------------------------------------


@app.get("/api/movements")
def list_movements(
    month: str | None = None, limit: int | None = None, search: str | None = None
) -> list[dict[str, Any]]:
    return movements.list_activity(
        database.require_current(), month=month, limit=limit, search=search
    )


@app.post("/api/movements", status_code=201)
def create_movement(payload: MovementCreate) -> dict[str, Any]:
    db = database.require_current()
    account_id = payload.account_id or _default_account(db, payload.kind)
    return movements.create_movement(
        db,
        payload.kind,
        payload.amount,
        payload.description,
        account_id,
        date=payload.date,
        pending=payload.pending,
    )


@app.patch("/api/movements/{movement_id}")
def update_movement(movement_id: str, payload: MovementUpdate) -> dict[str, Any]:
    return movements.update_movement(
        database.require_current(),
        movement_id,
        **payload.model_dump(exclude_unset=True),
    )


@app.put("/api/movements/{movement_id}/pending")
def set_movement_pending(movement_id: str, payload: MovementPending) -> dict[str, Any]:
    return movements.set_movement_pending(
        database.require_current(), movement_id, payload.pending
    )


@app.delete("/api/movements/{movement_id}", **NO_CONTENT)
def delete_movement(movement_id: str) -> None:
    movements.delete_movement(database.require_current(), movement_id)


@app.post("/api/transfers", status_code=201)
def create_transfer(payload: TransferCreate) -> dict[str, Any]:
    return transfers.create_transfer(
        database.require_current(),
        payload.from_account,
        payload.to_account,
        payload.amount,
        date=payload.date,
        description=payload.description,
    )


@app.patch("/api/transfers/{transfer_id}")
def update_transfer(transfer_id: str, payload: TransferUpdate) -> dict[str, Any]:
    return transfers.update_transfer(
        database.require_current(),
        transfer_id,
        **payload.model_dump(exclude_unset=True),
    )


@app.delete("/api/transfers/{transfer_id}", **NO_CONTENT)
def delete_transfer(transfer_id: str) -> None:
    transfers.delete_transfer(database.require_current(), transfer_id)


def _default_account(db: Path, kind: str) -> str:
    """Fall back to the configured default, then to the only account there is."""
    stored = preferences.load_preferences(db)
    key = "default_expense_account" if kind == "expense" else "default_income_account"
    if stored[key]:
        return stored[key]

    available = accounts.list_accounts(db)
    if len(available) == 1:
        return available[0]["id"]
    raise ValidationError("Elige una cuenta para registrar el movimiento.")


# --- Reconciliations -------------------------------------------------------


@app.get("/api/reconciliations")
def list_reconciliations(limit: int | None = None) -> list[dict[str, Any]]:
    return reconciliations.list_reconciliations(database.require_current(), limit=limit)


@app.get("/api/reconciliations/pending")
def list_pending() -> dict[str, Any]:
    db = database.require_current()
    return {
        "summary": reconciliations.pending_summary(db),
        "movements": reconciliations.list_pending(db),
    }


@app.post("/api/reconciliations", status_code=201)
def run_reconciliation() -> dict[str, Any]:
    return reconciliations.run_reconciliation(database.require_current())


@app.get("/api/reconciliations/{reconciliation_id}/movements")
def reconciliation_movements(reconciliation_id: str) -> list[dict[str, Any]]:
    return reconciliations.reconciliation_movements(
        database.require_current(), reconciliation_id
    )


# --- Preferences -----------------------------------------------------------


@app.get("/api/preferences")
def get_preferences() -> dict[str, str]:
    return preferences.load_preferences(database.require_current())


@app.put("/api/preferences")
def update_preferences(payload: PreferencesUpdate) -> dict[str, str]:
    db = database.require_current()
    for account_id in (payload.default_expense_account, payload.default_income_account):
        if account_id:
            accounts.require_account(db, account_id)
    return preferences.save_preferences(db, payload.model_dump())


# --- Static interface ------------------------------------------------------
# Mounted last so it never shadows an /api route.


@app.get("/", include_in_schema=False, response_model=None)
def index() -> FileResponse | JSONResponse:
    entry = STATIC_DIR / "index.html"
    if entry.exists():
        return FileResponse(entry)
    return JSONResponse(
        {"detail": "La interfaz no está compilada. Ejecuta 'make web' o 'npm run build'."},
        status_code=503,
    )


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
