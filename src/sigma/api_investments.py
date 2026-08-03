"""HTTP routes for the Inversiones module, mounted onto the main app in
``sigma.api``. Kept in its own router so ``api.py`` stays under the project's
line guideline — this file has no business logic of its own, only translating
HTTP into calls to ``sigma.db.investments`` / ``investment_transactions`` /
``investment_metrics``, exactly like the rest of the API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from sigma import database
from sigma.db import accounts, investment_metrics, investment_transactions, investments
from sigma.db.errors import NotFound

router = APIRouter(prefix="/api/investments", tags=["investments"])

DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

# FastAPI needs all three hints together to emit a genuinely bodiless 204.
NO_CONTENT: dict[str, Any] = {
    "status_code": 204,
    "response_class": Response,
    "response_model": None,
}


class BuyCreate(BaseModel):
    account_id: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1, max_length=20)
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    currency: str = Field(..., pattern="^(CLP|USD)$")
    date: str | None = Field(default=None, pattern=DATE_PATTERN)
    fees: int = Field(default=0, ge=0)


class SellCreate(BaseModel):
    account_id: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1, max_length=20)
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    date: str | None = Field(default=None, pattern=DATE_PATTERN)
    fees: int = Field(default=0, ge=0)


class DividendCreate(BaseModel):
    account_id: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1, max_length=20)
    amount: float = Field(..., gt=0)
    currency: str = Field(..., pattern="^(CLP|USD)$")
    date: str | None = Field(default=None, pattern=DATE_PATTERN)


class FxExchangeCreate(BaseModel):
    account_id: str = Field(..., min_length=1)
    clp_amount: float = Field(..., gt=0)
    usd_amount: float = Field(..., gt=0)
    date: str | None = Field(default=None, pattern=DATE_PATTERN)


class InvestmentTransactionUpdate(BaseModel):
    quantity: float | None = Field(default=None, gt=0)
    price: float | None = Field(default=None, gt=0)
    fees: int | None = Field(default=None, ge=0)
    date: str | None = Field(default=None, pattern=DATE_PATTERN)


class RefreshRequest(BaseModel):
    tickers: list[str] = []


# --- Accounts, holdings, activity, metrics -----------------------------------


@router.get("/accounts")
def list_investment_accounts() -> list[dict[str, Any]]:
    db = database.require_current()
    return [
        {**account, "total_value_clp": _value_clp(db, account["id"])}
        for account in accounts.list_accounts(db)
        if account["kind"] == "investment"
    ]


def _value_clp(db: Path, account_id: str) -> int:
    return investment_metrics.account_metrics(db, account_id)["total_value_clp"]


@router.get("/accounts/{account_id}/holdings")
def account_holdings(account_id: str) -> list[dict[str, Any]]:
    return investments.list_holdings(database.require_current(), account_id)


@router.get("/accounts/{account_id}/activity")
def account_activity(account_id: str, limit: int | None = None) -> list[dict[str, Any]]:
    return investments.list_investment_activity(
        database.require_current(), account_id, limit=limit
    )


@router.get("/accounts/{account_id}/metrics")
def account_metrics(account_id: str) -> dict[str, Any]:
    return investment_metrics.account_metrics(database.require_current(), account_id)


@router.get("/accounts/{account_id}/history")
def account_history(account_id: str) -> list[dict[str, Any]]:
    return investment_metrics.get_value_history(database.require_current(), account_id)


# --- Transactions -------------------------------------------------------------


@router.post("/buy", status_code=201)
def create_buy(payload: BuyCreate) -> dict[str, Any]:
    return investment_transactions.create_buy(
        database.require_current(),
        payload.account_id,
        payload.ticker,
        payload.quantity,
        payload.price,
        payload.currency,
        date=payload.date,
        fees=payload.fees,
    )


@router.post("/sell", status_code=201)
def create_sell(payload: SellCreate) -> dict[str, Any]:
    return investment_transactions.create_sell(
        database.require_current(),
        payload.account_id,
        payload.ticker,
        payload.quantity,
        payload.price,
        date=payload.date,
        fees=payload.fees,
    )


@router.post("/dividend", status_code=201)
def create_dividend(payload: DividendCreate) -> dict[str, Any]:
    return investment_transactions.create_dividend(
        database.require_current(),
        payload.account_id,
        payload.ticker,
        payload.amount,
        payload.currency,
        date=payload.date,
    )


@router.post("/fx-exchange", status_code=201)
def create_fx_exchange(payload: FxExchangeCreate) -> dict[str, Any]:
    return investment_transactions.create_fx_exchange(
        database.require_current(),
        payload.account_id,
        payload.clp_amount,
        payload.usd_amount,
        date=payload.date,
    )


@router.patch("/transactions/{transaction_id}")
def update_transaction(
    transaction_id: str, payload: InvestmentTransactionUpdate
) -> dict[str, Any]:
    return investment_transactions.update_investment_transaction(
        database.require_current(),
        transaction_id,
        **payload.model_dump(exclude_unset=True),
    )


@router.delete("/transactions/{transaction_id}", **NO_CONTENT)
def delete_transaction(transaction_id: str) -> None:
    investment_transactions.delete_investment_transaction(
        database.require_current(), transaction_id
    )


# --- Prices --------------------------------------------------------------------


@router.post("/refresh")
def refresh(payload: RefreshRequest) -> dict[str, Any]:
    """Fetch current prices, cache them, and snapshot every investment
    account's value for the day — the only place Inversiones touches the
    network. Called once when the screen mounts."""
    db = database.require_current()
    tickers = payload.tickers or _all_held_tickers(db)
    result = investments.refresh_prices(db, tickers)

    for account in accounts.list_accounts(db):
        if account["kind"] != "investment":
            continue
        value = investment_metrics.account_metrics(db, account["id"])["total_value_clp"]
        investment_metrics.record_value_snapshot(db, account["id"], value)

    return {"prices": result}


def _all_held_tickers(db: Path) -> list[str]:
    tickers: set[str] = set()
    for account in accounts.list_accounts(db):
        if account["kind"] == "investment":
            tickers.update(h["ticker"] for h in investments.list_holdings(db, account["id"]))
    return sorted(tickers)


@router.get("/lookup/{ticker}")
def lookup(ticker: str) -> dict[str, Any]:
    quote = investments.lookup_ticker(database.require_current(), ticker)
    if quote is None:
        raise NotFound(f"No se encontró el ticker '{ticker.strip().upper()}'.")
    return quote
