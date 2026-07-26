"""Movements — expenses and income — and the timeline that lists them.

Writing a movement updates its account's balance, editing one rebuilds that
change from scratch, and deleting one reverses exactly what it did. Amounts
are whole Chilean pesos.

The activity listing lives here because it is what the interface reads: one
timeline with movements and transfers merged and sorted by date.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sigma.db.accounts import apply_balance_change, check_can_spend, require_account
from sigma.db.connection import connect, fold, now, today, transaction
from sigma.db.errors import NotFound, ValidationError
from sigma.db.schema import new_id

# How a transfer reads in the activity list. The note the user typed hangs off
# this word, so searching "transferencia" finds every one of them.
TRANSFER_LABEL = "Transferencia"

MAX_DESCRIPTION = 200


def balance_delta(kind: str, account_kind: str, amount: int) -> int:
    """How a movement of ``kind`` changes the balance of an account.

    For credit accounts ``balance`` is debt, so the sign flips: an expense adds
    to what you owe, and income (a payment to the card) subtracts from it.
    """
    sign = -1 if kind == "expense" else 1
    if account_kind == "credit":
        sign = -sign
    return sign * amount


# --- Validation shared with sigma.db.transfers -------------------------------


def _check_kind(kind: str) -> None:
    if kind not in ("expense", "income"):
        raise ValidationError("El tipo de movimiento debe ser 'expense' o 'income'.")


def check_amount(amount: int) -> None:
    if amount <= 0:
        raise ValidationError("El monto debe ser mayor que cero.")


def clean_description(text: str, *, required: bool = True) -> str:
    text = " ".join(text.split())
    if required and not text:
        raise ValidationError("La descripción no puede estar vacía.")
    return text[:MAX_DESCRIPTION]


# --- Movements -------------------------------------------------------------


def create_movement(
    db_path: Path,
    kind: str,
    amount: int,
    description: str,
    account_id: str,
    date: str | None = None,
    pending: bool = True,
) -> dict[str, Any]:
    _check_kind(kind)
    check_amount(amount)
    description = clean_description(description)

    account = require_account(db_path, account_id)
    if kind == "expense":
        check_can_spend(account, amount)

    movement_id = new_id()
    with transaction(db_path) as conn:
        conn.execute(
            "INSERT INTO movements"
            " (id, kind, amount, description, account_id, date, pending, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                movement_id,
                kind,
                amount,
                description,
                account_id,
                date or today(),
                int(pending),
                now(),
            ),
        )
        apply_balance_change(conn, account_id, balance_delta(kind, account["kind"], amount))

    return get_movement(db_path, movement_id)


def get_movement(db_path: Path, movement_id: str) -> dict[str, Any]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT m.*, a.name AS account_name, a.kind AS account_kind"
            " FROM movements m JOIN accounts a ON a.id = m.account_id"
            " WHERE m.id = ?",
            (movement_id,),
        ).fetchone()
    if row is None or row["deleted_at"]:
        raise NotFound("El movimiento no existe.")
    return dict(row)


def set_movement_pending(db_path: Path, movement_id: str, pending: bool) -> dict[str, Any]:
    """Include or exclude a movement from the next reconciliation."""
    movement = get_movement(db_path, movement_id)
    if movement["reconciliation_id"]:
        raise ValidationError("Este movimiento ya fue conciliado.")
    with transaction(db_path) as conn:
        conn.execute(
            "UPDATE movements SET pending = ? WHERE id = ?", (int(pending), movement_id)
        )
    return get_movement(db_path, movement_id)


def update_movement(
    db_path: Path,
    movement_id: str,
    kind: str | None = None,
    amount: int | None = None,
    description: str | None = None,
    account_id: str | None = None,
    date: str | None = None,
    pending: bool | None = None,
) -> dict[str, Any]:
    """Correct a movement in place. Every field is optional; the rest stays put.

    The balance is rebuilt rather than patched: the effect the movement had is
    undone on the account it used to touch, and the new effect is applied to the
    account it touches now. When both are the same account the two changes land
    on the same row and net out, which is exactly right.
    """
    movement = get_movement(db_path, movement_id)

    new_kind = kind or movement["kind"]
    new_amount = movement["amount"] if amount is None else amount
    new_date = date or movement["date"]
    new_pending = bool(movement["pending"]) if pending is None else pending
    new_description = (
        movement["description"] if description is None else clean_description(description)
    )

    _check_kind(new_kind)
    check_amount(new_amount)
    if movement["reconciliation_id"] and new_pending:
        raise ValidationError("Este movimiento ya fue conciliado.")

    # A movement on a deleted account can still be corrected, but it cannot be
    # moved onto one.
    source = require_account(db_path, movement["account_id"], active=False)
    target = (
        source
        if account_id in (None, source["id"])
        else require_account(db_path, account_id)
    )

    old_delta = balance_delta(movement["kind"], source["kind"], movement["amount"])
    new_delta = balance_delta(new_kind, target["kind"], new_amount)

    if new_kind == "expense":
        # Check against the balance the account would have without this movement,
        # so raising an expense by a little does not need room for all of it.
        without = dict(target)
        if target["id"] == source["id"]:
            without["balance"] -= old_delta
        check_can_spend(without, new_amount)

    with transaction(db_path) as conn:
        conn.execute(
            "UPDATE movements SET kind = ?, amount = ?, description = ?, account_id = ?,"
            " date = ?, pending = ? WHERE id = ?",
            (
                new_kind,
                new_amount,
                new_description,
                target["id"],
                new_date,
                int(new_pending),
                movement_id,
            ),
        )
        apply_balance_change(conn, source["id"], -old_delta)
        apply_balance_change(conn, target["id"], new_delta)

    return get_movement(db_path, movement_id)


def delete_movement(db_path: Path, movement_id: str) -> None:
    """Soft-delete a movement and undo its effect on the account balance.

    A movement that was already reconciled can still be deleted — mistakes need
    fixing — but the reconciliation keeps the net amount it recorded at the
    time, because it is a snapshot of what was true then.
    """
    movement = get_movement(db_path, movement_id)
    with transaction(db_path) as conn:
        conn.execute(
            "UPDATE movements SET deleted_at = ? WHERE id = ?", (now(), movement_id)
        )
        apply_balance_change(
            conn,
            movement["account_id"],
            -balance_delta(movement["kind"], movement["account_kind"], movement["amount"]),
        )


# --- Combined listing ------------------------------------------------------

_ACTIVITY_SQL = """
SELECT
    m.id            AS id,
    'movement'      AS record,
    m.kind          AS kind,
    m.amount        AS amount,
    m.description   AS description,
    m.account_id    AS account_id,
    a.name          AS account_name,
    NULL            AS to_account_id,
    NULL            AS to_account_name,
    m.date          AS date,
    m.pending       AS pending,
    m.reconciliation_id AS reconciliation_id,
    m.created_at    AS created_at
FROM movements m
JOIN accounts a ON a.id = m.account_id
WHERE m.deleted_at IS NULL {movement_filter}

UNION ALL

SELECT
    t.id            AS id,
    'transfer'      AS record,
    'transfer'      AS kind,
    t.amount        AS amount,
    t.description   AS description,
    t.from_account  AS account_id,
    f.name          AS account_name,
    t.to_account    AS to_account_id,
    d.name          AS to_account_name,
    t.date          AS date,
    0               AS pending,
    NULL            AS reconciliation_id,
    t.created_at    AS created_at
FROM transfers t
JOIN accounts f ON f.id = t.from_account
JOIN accounts d ON d.id = t.to_account
WHERE t.deleted_at IS NULL {transfer_filter}

ORDER BY date DESC, created_at DESC
"""


# What a transfer reads as when it is being searched: the label the interface
# shows, with the user's note attached, so both halves are findable.
_TRANSFER_TEXT = (
    f"CASE WHEN t.description = '' THEN '{TRANSFER_LABEL}'"
    f" ELSE '{TRANSFER_LABEL}: ' || t.description END"
)


def list_activity(
    db_path: Path,
    month: str | None = None,
    limit: int | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Movements and transfers on one timeline, newest first.

    ``month`` filters by ``YYYY-MM``, ``search`` matches the description or the
    account names ignoring case and accents, and ``limit`` caps the rows.
    """
    movement_params: list[Any] = []
    transfer_params: list[Any] = []
    movement_filter = transfer_filter = ""

    if month:
        movement_filter += " AND substr(m.date, 1, 7) = ?"
        transfer_filter += " AND substr(t.date, 1, 7) = ?"
        movement_params.append(month)
        transfer_params.append(month)

    term = (search or "").strip()
    if term:
        pattern = f"%{fold(term)}%"
        movement_filter += " AND (fold(m.description) LIKE ? OR fold(a.name) LIKE ?)"
        transfer_filter += (
            f" AND (fold({_TRANSFER_TEXT}) LIKE ?"
            " OR fold(f.name) LIKE ? OR fold(d.name) LIKE ?)"
        )
        movement_params += [pattern, pattern]
        transfer_params += [pattern, pattern, pattern]

    sql = _ACTIVITY_SQL.format(
        movement_filter=movement_filter, transfer_filter=transfer_filter
    )
    params = movement_params + transfer_params
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    with connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def month_summary(db_path: Path, month: str) -> dict[str, int]:
    """Income, expense and net for a ``YYYY-MM`` period. Transfers are excluded:
    moving money between your own accounts is not income or spending."""
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT"
            " COALESCE(SUM(CASE WHEN kind = 'income' THEN amount END), 0) AS income,"
            " COALESCE(SUM(CASE WHEN kind = 'expense' THEN amount END), 0) AS expense"
            " FROM movements"
            " WHERE deleted_at IS NULL AND substr(date, 1, 7) = ?",
            (month,),
        ).fetchone()
    income, expense = row["income"], row["expense"]
    return {"income": income, "expense": expense, "net": income - expense}
