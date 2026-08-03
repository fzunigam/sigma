"""Holdings and reads for an ``investment``-kind account, plus the internals
shared with ``sigma.db.investment_transactions``.

An investment account's ``balance`` (in ``accounts``) is its CLP cash, moved by
ordinary transfers exactly like a debit account — see ``sigma.db.accounts``.
Everything else lives here and in ``investment_transactions``: USD cash
(``investment_cash_usd``), holdings (``investment_holdings``) and the
transactions that produced them (``investment_transactions``).

Money that is not CLP is stored in minor units (USD cents); ``to_minor`` /
``to_major`` convert between that and the whole-currency numbers (``price``,
share quantities) a person actually types in. ``clp_amount``/``usd_amount`` on
a transaction hold a plain money amount for the kinds that have no per-share
price — dividends and currency exchanges — in whichever of the two applies.

Unlike ``accounts.balance``, a holding's ``quantity``/``avg_cost`` cannot be
patched with a delta: average cost depends on the order of every buy and sell,
so editing or deleting one recomputes the whole holding from its transaction
history (``recompute_holding``), including the ``realized_gain`` stored on
every past sell of that ticker.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from sigma import prices
from sigma.db.accounts import apply_balance_change, require_account
from sigma.db.connection import connect, now, transaction
from sigma.db.errors import NotFound, ValidationError

CURRENCIES = ("CLP", "USD")


# --- Validation, shared with sigma.db.investment_transactions ---------------


def clean_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValidationError("El ticker no puede estar vacío.")
    return ticker


def check_currency(currency: str) -> None:
    if currency not in CURRENCIES:
        raise ValidationError("La moneda debe ser 'CLP' o 'USD'.")


def check_positive(value: float, message: str) -> None:
    if value <= 0:
        raise ValidationError(message)


def require_investment_account(db_path: Path, account_id: str) -> dict[str, Any]:
    account = require_account(db_path, account_id)
    if account["kind"] != "investment":
        raise ValidationError(f"La cuenta '{account['name']}' no es una cuenta de inversión.")
    return account


# --- Money in minor units ----------------------------------------------------


def to_minor(amount: float, currency: str) -> int:
    """Whole-currency amount → integer minor units (USD cents; CLP has none)."""
    return round(amount * 100) if currency == "USD" else round(amount)


def to_major(amount: int, currency: str) -> float:
    """Integer minor units → whole-currency amount."""
    return amount / 100 if currency == "USD" else float(amount)


def get_cash_usd(db_path: Path, account_id: str) -> int:
    """USD cash for an account, in cents. 0 if nothing has touched it yet."""
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT balance FROM investment_cash_usd WHERE account_id = ?", (account_id,)
        ).fetchone()
    return row["balance"] if row else 0


def _cash_balance(conn: sqlite3.Connection, account: dict[str, Any], currency: str) -> int:
    if currency == "CLP":
        return account["balance"]
    row = conn.execute(
        "SELECT balance FROM investment_cash_usd WHERE account_id = ?", (account["id"],)
    ).fetchone()
    return row["balance"] if row else 0


def check_cash_available(
    conn: sqlite3.Connection, account: dict[str, Any], currency: str, amount: int
) -> None:
    available = _cash_balance(conn, account, currency)
    if available < amount:
        raise ValidationError(
            f"Saldo insuficiente en '{account['name']}' ({currency})."
            f" Disponible: {available}, necesario: {amount}."
        )


def _apply_cash_change(
    conn: sqlite3.Connection, account_id: str, currency: str, delta: int
) -> None:
    if currency == "CLP":
        apply_balance_change(conn, account_id, delta)
    else:
        conn.execute(
            "INSERT INTO investment_cash_usd (account_id, balance) VALUES (?, ?)"
            " ON CONFLICT(account_id) DO UPDATE SET balance = balance + excluded.balance",
            (account_id, delta),
        )


def cash_effects(txn: dict[str, Any]) -> list[tuple[str, int]]:
    """(currency, delta) pairs that applying ``txn`` has on the account's cash."""
    kind = txn["kind"]
    if kind == "buy":
        cost = to_minor(txn["quantity"] * txn["price"], txn["currency"]) + txn["fees"]
        return [(txn["currency"], -cost)]
    if kind == "sell":
        proceeds = to_minor(txn["quantity"] * txn["price"], txn["currency"]) - txn["fees"]
        return [(txn["currency"], proceeds)]
    if kind == "dividend":
        amount = txn["clp_amount"] if txn["currency"] == "CLP" else txn["usd_amount"]
        return [(txn["currency"], amount)]
    return [("CLP", -txn["clp_amount"]), ("USD", txn["usd_amount"])]  # fx_exchange


def apply_effect(
    conn: sqlite3.Connection, account_id: str, txn: dict[str, Any], sign: int = 1
) -> None:
    for currency, delta in cash_effects(txn):
        _apply_cash_change(conn, account_id, currency, sign * delta)


# --- Holdings, recomputed from history ---------------------------------------


def list_holdings(db_path: Path, account_id: str) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM investment_holdings WHERE account_id = ? ORDER BY ticker",
            (account_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_holding(db_path: Path, account_id: str, ticker: str) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM investment_holdings WHERE account_id = ? AND ticker = ?",
            (account_id, ticker),
        ).fetchone()
    return dict(row) if row else None


def recompute_holding(conn: sqlite3.Connection, account_id: str, ticker: str) -> None:
    """Replay every buy/sell of ``ticker`` in order to rebuild its holding.

    Average cost is path-dependent, so this is not a delta update: it is the
    only correct way to reflect an edit or deletion of a past transaction. As
    it walks the history it also refreshes ``realized_gain`` on every sell,
    since a change earlier in the timeline can change what a later sell
    actually realised.
    """
    rows = conn.execute(
        "SELECT id, kind, quantity, price, fees, currency FROM investment_transactions"
        " WHERE account_id = ? AND ticker = ? AND kind IN ('buy', 'sell')"
        " AND deleted_at IS NULL ORDER BY date, created_at",
        (account_id, ticker),
    ).fetchall()

    quantity = 0.0
    avg_cost = 0.0
    currency = None
    for row in rows:
        currency = row["currency"]
        fees_major = to_major(row["fees"], currency)
        if row["kind"] == "buy":
            total_cost = quantity * avg_cost + row["quantity"] * row["price"] + fees_major
            quantity += row["quantity"]
            avg_cost = total_cost / quantity if quantity > 1e-9 else 0.0
        else:
            realized_gain = to_minor(
                row["quantity"] * (row["price"] - avg_cost) - fees_major, currency
            )
            conn.execute(
                "UPDATE investment_transactions SET realized_gain = ? WHERE id = ?",
                (realized_gain, row["id"]),
            )
            quantity -= row["quantity"]
            if quantity <= 1e-9:
                quantity = 0.0
                avg_cost = 0.0

    if quantity <= 1e-9:
        conn.execute(
            "DELETE FROM investment_holdings WHERE account_id = ? AND ticker = ?",
            (account_id, ticker),
        )
    else:
        conn.execute(
            "INSERT INTO investment_holdings (account_id, ticker, quantity, avg_cost, currency)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(account_id, ticker) DO UPDATE SET"
            " quantity = excluded.quantity, avg_cost = excluded.avg_cost,"
            " currency = excluded.currency",
            (account_id, ticker, quantity, avg_cost, currency),
        )


# --- Reading transactions ----------------------------------------------------


def get_investment_transaction(db_path: Path, transaction_id: str) -> dict[str, Any]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM investment_transactions WHERE id = ?", (transaction_id,)
        ).fetchone()
    if row is None or row["deleted_at"]:
        raise NotFound("La transacción no existe.")
    return dict(row)


def list_investment_activity(
    db_path: Path, account_id: str | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    where = " WHERE deleted_at IS NULL"
    params: list[Any] = []
    if account_id:
        where += " AND account_id = ?"
        params.append(account_id)
    sql = f"SELECT * FROM investment_transactions{where} ORDER BY date DESC, created_at DESC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


# --- Prices and FX, cached from sigma.prices ---------------------------------


def get_price(db_path: Path, ticker: str) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM security_prices WHERE ticker = ?", (ticker,)
        ).fetchone()
    return dict(row) if row else None


def get_fx_rate(db_path: Path, pair: str = "USDCLP") -> float | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT rate FROM fx_rates WHERE pair = ?", (pair,)).fetchone()
    return row["rate"] if row else None


def lookup_ticker(db_path: Path, ticker: str) -> dict[str, Any] | None:
    """Validate a new ticker straight from Yahoo, not the cache, so a typo is
    caught right away. ``None`` if the symbol does not exist or there is no
    connection — the caller shows that as a field error, not a crash.

    A successful answer is cached too: it already cost a network round trip,
    and without this a ticker bought moments ago would show as stale until
    the next time Inversiones refreshes.
    """
    ticker = clean_ticker(ticker)
    quote = prices.fetch_quote(ticker)
    if quote is not None:
        with transaction(db_path) as conn:
            _cache_security_price(conn, ticker, quote, now())
    return quote


def _cache_security_price(
    conn: sqlite3.Connection, ticker: str, quote: dict[str, Any], fetched_at: str
) -> None:
    conn.execute(
        "INSERT INTO security_prices (ticker, name, currency, price, fetched_at)"
        " VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(ticker) DO UPDATE SET"
        " name = excluded.name, currency = excluded.currency,"
        " price = excluded.price, fetched_at = excluded.fetched_at",
        (ticker, quote["name"], quote["currency"], quote["price"], fetched_at),
    )


def refresh_prices(db_path: Path, tickers: list[str]) -> dict[str, bool]:
    """Fetch current prices for ``tickers`` plus the USD/CLP rate, and cache
    whichever ones answered.

    Every network call happens before any connection is opened, per the
    module note in ``sigma.db.connection`` about not holding one across I/O.
    Never raises: a ticker Yahoo could not price simply keeps its last cached
    value, which is what makes this safe to call every time Inversiones opens.
    """
    symbols = list(dict.fromkeys(tickers)) + [prices.USD_CLP_SYMBOL]
    quotes = {symbol: prices.fetch_quote(symbol) for symbol in symbols}
    fetched_at = now()

    with transaction(db_path) as conn:
        for symbol, quote in quotes.items():
            if quote is None:
                continue
            if symbol == prices.USD_CLP_SYMBOL:
                conn.execute(
                    "INSERT INTO fx_rates (pair, rate, fetched_at) VALUES ('USDCLP', ?, ?)"
                    " ON CONFLICT(pair) DO UPDATE SET"
                    " rate = excluded.rate, fetched_at = excluded.fetched_at",
                    (quote["price"], fetched_at),
                )
            else:
                _cache_security_price(conn, symbol, quote, fetched_at)

    return {ticker: quotes.get(ticker) is not None for ticker in tickers}
