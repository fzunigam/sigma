"""Valuation and performance for an investment account.

Everything here reads from the price/FX cache in ``sigma.db.investments`` —
never a live network call — so these functions are as fast and offline-safe
as any other read in Sigma.

The account's money-weighted return (IRR/XIRR) is computed from *transfers*
into and out of the account, not from its buys/sells/dividends. A buy just
turns cash into a holding of equal value, a dividend adds cash the account
already reflects in its ending value, and a sell turns a holding back into
cash — none of those change how much of the user's own money is invested, so
none of them belong in the cash-flow list. Only a transfer across the
account's boundary — money coming from or going back to another account —
is capital entering or leaving the investment, which is what IRR measures.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from sigma.db.connection import connect, today, transaction
from sigma.db.investments import (
    get_cash_usd,
    get_fx_rate,
    get_price,
    list_holdings,
    require_investment_account,
    to_major,
)


def account_metrics(db_path: Path, account_id: str) -> dict[str, Any]:
    """Value, gain, dividends and IRR for one investment account, all in CLP."""
    account = require_investment_account(db_path, account_id)
    fx_rate = get_fx_rate(db_path)

    positions = [
        _position_metrics(db_path, holding, fx_rate)
        for holding in list_holdings(db_path, account_id)
    ]
    holdings_value_clp = sum(p["market_value_clp"] for p in positions)
    cost_basis_clp = sum(p["cost_basis_clp"] for p in positions)

    cash_usd = get_cash_usd(db_path, account_id)
    cash_usd_clp = round(to_major(cash_usd, "USD") * fx_rate) if fx_rate else 0
    total_value_clp = account["balance"] + cash_usd_clp + holdings_value_clp

    return {
        "positions": positions,
        "cash_clp": account["balance"],
        "cash_usd_clp": cash_usd_clp,
        "total_value_clp": total_value_clp,
        "unrealized_gain_clp": holdings_value_clp - cost_basis_clp,
        "realized_gain_clp": _realized_gain_clp(db_path, account_id, fx_rate),
        "dividends_clp": _dividends_clp(db_path, account_id, fx_rate),
        "allocation": _allocation(positions, account["balance"], cash_usd_clp),
        "irr": _account_irr(db_path, account_id, total_value_clp),
        "fx_rate": fx_rate,
    }


def _position_metrics(
    db_path: Path, holding: dict[str, Any], fx_rate: float | None
) -> dict[str, Any]:
    price_row = get_price(db_path, holding["ticker"])
    current_price = price_row["price"] if price_row else holding["avg_cost"]
    market_value_major = holding["quantity"] * current_price
    cost_major = holding["quantity"] * holding["avg_cost"]

    if holding["currency"] == "USD":
        rate = fx_rate or 0.0
        market_value_clp = round(market_value_major * rate)
        cost_basis_clp = round(cost_major * rate)
    else:
        market_value_clp = round(market_value_major)
        cost_basis_clp = round(cost_major)

    gain_clp = market_value_clp - cost_basis_clp
    return {
        "ticker": holding["ticker"],
        "quantity": holding["quantity"],
        "avg_cost": holding["avg_cost"],
        "current_price": current_price,
        "currency": holding["currency"],
        "market_value_clp": market_value_clp,
        "cost_basis_clp": cost_basis_clp,
        "gain_clp": gain_clp,
        "gain_pct": round(gain_clp / cost_basis_clp * 100, 2) if cost_basis_clp else None,
        "stale": price_row is None,
    }


def _realized_gain_clp(db_path: Path, account_id: str, fx_rate: float | None) -> int:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT realized_gain, currency FROM investment_transactions"
            " WHERE account_id = ? AND kind = 'sell' AND deleted_at IS NULL",
            (account_id,),
        ).fetchall()
    total = 0.0
    for row in rows:
        gain_major = to_major(row["realized_gain"], row["currency"])
        total += gain_major * (fx_rate or 0.0) if row["currency"] == "USD" else gain_major
    return round(total)


def _dividends_clp(db_path: Path, account_id: str, fx_rate: float | None) -> int:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT clp_amount, usd_amount FROM investment_transactions"
            " WHERE account_id = ? AND kind = 'dividend' AND deleted_at IS NULL",
            (account_id,),
        ).fetchall()
    total = 0.0
    for row in rows:
        if row["clp_amount"] is not None:
            total += row["clp_amount"]
        elif row["usd_amount"] is not None:
            total += to_major(row["usd_amount"], "USD") * (fx_rate or 0.0)
    return round(total)


def _allocation(
    positions: list[dict[str, Any]], cash_clp: int, cash_usd_clp: int
) -> list[dict[str, Any]]:
    slices = [
        {"label": p["ticker"], "value_clp": p["market_value_clp"]}
        for p in positions
        if p["market_value_clp"]
    ]
    if cash_clp:
        slices.append({"label": "Efectivo (CLP)", "value_clp": cash_clp})
    if cash_usd_clp:
        slices.append({"label": "Efectivo (USD)", "value_clp": cash_usd_clp})
    return slices


def _account_irr(db_path: Path, account_id: str, total_value_clp: int) -> float | None:
    with connect(db_path) as conn:
        inflows = conn.execute(
            "SELECT date, amount FROM transfers WHERE to_account = ? AND deleted_at IS NULL",
            (account_id,),
        ).fetchall()
        outflows = conn.execute(
            "SELECT date, amount FROM transfers WHERE from_account = ? AND deleted_at IS NULL",
            (account_id,),
        ).fetchall()

    cashflows = [(row["date"], -row["amount"]) for row in inflows]
    cashflows += [(row["date"], row["amount"]) for row in outflows]
    if not cashflows:
        return None
    cashflows.append((today(), total_value_clp))
    return xirr(cashflows)


# --- The daily snapshot behind the portfolio chart ---------------------------


def record_value_snapshot(db_path: Path, account_id: str, value_clp: int) -> None:
    """One row per account per day; refreshing prices again today overwrites it."""
    with transaction(db_path) as conn:
        conn.execute(
            "INSERT INTO investment_value_history (account_id, date, value_clp)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT(account_id, date) DO UPDATE SET value_clp = excluded.value_clp",
            (account_id, today(), value_clp),
        )


def get_value_history(db_path: Path, account_id: str) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT date, value_clp FROM investment_value_history"
            " WHERE account_id = ? ORDER BY date",
            (account_id,),
        ).fetchall()
    return [dict(row) for row in rows]


# --- XIRR: a general money-weighted return over dated cash flows ------------


def xirr(cashflows: list[tuple[str, float]]) -> float | None:
    """The annualised rate that makes ``cashflows`` net to zero today.

    Each entry is ``(date, amount)`` — negative for money going out, positive
    for money coming back — solved with Newton-Raphson, the same approach
    behind Excel's XIRR. ``None`` if there is nothing to solve (fewer than two
    flows, or the iteration does not converge).
    """
    if len(cashflows) < 2:
        return None
    parsed = sorted((date.fromisoformat(when), amount) for when, amount in cashflows)
    t0 = parsed[0][0]

    rate = 0.1
    for _ in range(100):
        npv = _npv(rate, parsed, t0)
        derivative = _npv_derivative(rate, parsed, t0)
        if abs(derivative) < 1e-12:
            return None
        next_rate = rate - npv / derivative
        if next_rate <= -0.999:
            next_rate = -0.999
        if abs(next_rate - rate) < 1e-9:
            return next_rate
        rate = next_rate
    return None


def _years(when: date, t0: date) -> float:
    return (when - t0).days / 365


def _npv(rate: float, cashflows: list[tuple[date, float]], t0: date) -> float:
    return sum(amount / (1 + rate) ** _years(when, t0) for when, amount in cashflows)


def _npv_derivative(rate: float, cashflows: list[tuple[date, float]], t0: date) -> float:
    return sum(
        -_years(when, t0) * amount / (1 + rate) ** (_years(when, t0) + 1)
        for when, amount in cashflows
    )
