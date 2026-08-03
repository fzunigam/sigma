"""Creating and correcting buys, sells, dividends and currency exchanges.

Reads and the shared internals (cash bookkeeping, holding recomputation) live
in ``sigma.db.investments`` — this module is only the write path, mirroring
how ``sigma.db.transfers`` builds on helpers from ``sigma.db.movements``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sigma.db.connection import now, today, transaction
from sigma.db.errors import ValidationError
from sigma.db.investments import (
    apply_effect,
    cash_effects,
    check_cash_available,
    check_currency,
    check_positive,
    clean_ticker,
    get_holding,
    get_investment_transaction,
    recompute_holding,
    require_investment_account,
    to_minor,
)
from sigma.db.schema import new_id


def create_buy(
    db_path: Path,
    account_id: str,
    ticker: str,
    quantity: float,
    price: float,
    currency: str,
    date: str | None = None,
    fees: int = 0,
) -> dict[str, Any]:
    ticker = clean_ticker(ticker)
    check_currency(currency)
    check_positive(quantity, "La cantidad debe ser mayor que cero.")
    check_positive(price, "El precio debe ser mayor que cero.")
    if fees < 0:
        raise ValidationError("La comisión no puede ser negativa.")
    account = require_investment_account(db_path, account_id)

    txn = {"kind": "buy", "quantity": quantity, "price": price, "fees": fees, "currency": currency}
    ((_, delta),) = cash_effects(txn)

    transaction_id = new_id()
    with transaction(db_path) as conn:
        check_cash_available(conn, account, currency, -delta)
        conn.execute(
            "INSERT INTO investment_transactions"
            " (id, account_id, kind, ticker, quantity, price, fees, currency, date, created_at)"
            " VALUES (?, ?, 'buy', ?, ?, ?, ?, ?, ?, ?)",
            (
                transaction_id,
                account_id,
                ticker,
                quantity,
                price,
                fees,
                currency,
                date or today(),
                now(),
            ),
        )
        apply_effect(conn, account_id, txn, sign=1)
        recompute_holding(conn, account_id, ticker)

    return get_investment_transaction(db_path, transaction_id)


def create_sell(
    db_path: Path,
    account_id: str,
    ticker: str,
    quantity: float,
    price: float,
    date: str | None = None,
    fees: int = 0,
) -> dict[str, Any]:
    ticker = clean_ticker(ticker)
    check_positive(quantity, "La cantidad debe ser mayor que cero.")
    check_positive(price, "El precio debe ser mayor que cero.")
    if fees < 0:
        raise ValidationError("La comisión no puede ser negativa.")
    account = require_investment_account(db_path, account_id)

    holding = get_holding(db_path, account_id, ticker)
    available = holding["quantity"] if holding else 0.0
    if available < quantity - 1e-9:
        raise ValidationError(
            f"No tienes esa cantidad de {ticker} en '{account['name']}'."
            f" Tienes {available}, quieres vender {quantity}."
        )
    currency = holding["currency"]
    txn = {"kind": "sell", "quantity": quantity, "price": price, "fees": fees, "currency": currency}

    transaction_id = new_id()
    with transaction(db_path) as conn:
        conn.execute(
            "INSERT INTO investment_transactions"
            " (id, account_id, kind, ticker, quantity, price, fees, currency, date, created_at)"
            " VALUES (?, ?, 'sell', ?, ?, ?, ?, ?, ?, ?)",
            (
                transaction_id,
                account_id,
                ticker,
                quantity,
                price,
                fees,
                currency,
                date or today(),
                now(),
            ),
        )
        apply_effect(conn, account_id, txn, sign=1)
        recompute_holding(conn, account_id, ticker)

    return get_investment_transaction(db_path, transaction_id)


def create_dividend(
    db_path: Path,
    account_id: str,
    ticker: str,
    amount: float,
    currency: str,
    date: str | None = None,
) -> dict[str, Any]:
    ticker = clean_ticker(ticker)
    check_currency(currency)
    check_positive(amount, "El monto debe ser mayor que cero.")
    require_investment_account(db_path, account_id)

    credit = to_minor(amount, currency)
    clp_amount = credit if currency == "CLP" else None
    usd_amount = credit if currency == "USD" else None
    txn = {
        "kind": "dividend",
        "currency": currency,
        "clp_amount": clp_amount,
        "usd_amount": usd_amount,
    }

    transaction_id = new_id()
    with transaction(db_path) as conn:
        conn.execute(
            "INSERT INTO investment_transactions"
            " (id, account_id, kind, ticker, currency, clp_amount, usd_amount, date, created_at)"
            " VALUES (?, ?, 'dividend', ?, ?, ?, ?, ?, ?)",
            (
                transaction_id,
                account_id,
                ticker,
                currency,
                clp_amount,
                usd_amount,
                date or today(),
                now(),
            ),
        )
        apply_effect(conn, account_id, txn, sign=1)

    return get_investment_transaction(db_path, transaction_id)


def create_fx_exchange(
    db_path: Path,
    account_id: str,
    clp_amount: float,
    usd_amount: float,
    date: str | None = None,
) -> dict[str, Any]:
    """Convert CLP cash into USD cash, at whatever rate the user was actually
    charged. One-directional (CLP → USD) — see ``sigma.db.investments``."""
    check_positive(clp_amount, "El monto en pesos debe ser mayor que cero.")
    check_positive(usd_amount, "El monto en dólares debe ser mayor que cero.")
    account = require_investment_account(db_path, account_id)

    clp_amount_int = round(clp_amount)
    usd_amount_int = round(usd_amount * 100)
    txn = {"kind": "fx_exchange", "clp_amount": clp_amount_int, "usd_amount": usd_amount_int}

    transaction_id = new_id()
    with transaction(db_path) as conn:
        check_cash_available(conn, account, "CLP", clp_amount_int)
        conn.execute(
            "INSERT INTO investment_transactions"
            " (id, account_id, kind, currency, clp_amount, usd_amount, date, created_at)"
            " VALUES (?, ?, 'fx_exchange', 'USD', ?, ?, ?, ?)",
            (transaction_id, account_id, clp_amount_int, usd_amount_int, date or today(), now()),
        )
        apply_effect(conn, account_id, txn, sign=1)

    return get_investment_transaction(db_path, transaction_id)


def update_investment_transaction(
    db_path: Path,
    transaction_id: str,
    quantity: float | None = None,
    price: float | None = None,
    fees: int | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    """Correct a buy or sell in place. Dividends and currency exchanges are
    simple enough to delete and re-enter instead.

    The old effect on cash is undone and the new one reapplied, and the
    holding is recomputed from its full history afterwards — see
    ``sigma.db.investments.recompute_holding``.
    """
    txn = get_investment_transaction(db_path, transaction_id)
    if txn["kind"] not in ("buy", "sell"):
        raise ValidationError(
            "Solo se pueden corregir compras y ventas. Elimina y vuelve a registrar."
        )

    updated = dict(txn)
    if quantity is not None:
        updated["quantity"] = quantity
    if price is not None:
        updated["price"] = price
    if fees is not None:
        updated["fees"] = fees
    if date is not None:
        updated["date"] = date

    check_positive(updated["quantity"], "La cantidad debe ser mayor que cero.")
    check_positive(updated["price"], "El precio debe ser mayor que cero.")
    if updated["fees"] < 0:
        raise ValidationError("La comisión no puede ser negativa.")

    with transaction(db_path) as conn:
        apply_effect(conn, txn["account_id"], txn, sign=-1)
        conn.execute(
            "UPDATE investment_transactions"
            " SET quantity = ?, price = ?, fees = ?, date = ? WHERE id = ?",
            (
                updated["quantity"],
                updated["price"],
                updated["fees"],
                updated["date"],
                transaction_id,
            ),
        )
        apply_effect(conn, txn["account_id"], updated, sign=1)
        recompute_holding(conn, txn["account_id"], txn["ticker"])

    return get_investment_transaction(db_path, transaction_id)


def delete_investment_transaction(db_path: Path, transaction_id: str) -> None:
    txn = get_investment_transaction(db_path, transaction_id)
    with transaction(db_path) as conn:
        conn.execute(
            "UPDATE investment_transactions SET deleted_at = ? WHERE id = ?",
            (now(), transaction_id),
        )
        apply_effect(conn, txn["account_id"], txn, sign=-1)
        if txn["kind"] in ("buy", "sell"):
            recompute_holding(conn, txn["account_id"], txn["ticker"])
