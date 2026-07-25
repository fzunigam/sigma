"""Movements (expenses and income) and transfers between accounts.

Both kinds of record update account balances as they are written, and deleting
one reverses exactly the change it made. Amounts are whole Chilean pesos.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sigma.db.accounts import apply_balance_change, check_can_spend, require_account
from sigma.db.connection import connect, now, today, transaction
from sigma.db.errors import NotFound, ValidationError
from sigma.db.schema import new_id


def balance_delta(kind: str, account_kind: str, amount: int) -> int:
    """How a movement of ``kind`` changes the balance of an account.

    For credit accounts ``balance`` is debt, so the sign flips: an expense adds
    to what you owe, and income (a payment to the card) subtracts from it.
    """
    sign = -1 if kind == "expense" else 1
    if account_kind == "credit":
        sign = -sign
    return sign * amount


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
    if kind not in ("expense", "income"):
        raise ValidationError("El tipo de movimiento debe ser 'expense' o 'income'.")
    if amount <= 0:
        raise ValidationError("El monto debe ser mayor que cero.")
    description = description.strip()
    if not description:
        raise ValidationError("La descripción no puede estar vacía.")

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


# --- Transfers -------------------------------------------------------------


def create_transfer(
    db_path: Path,
    from_account: str,
    to_account: str,
    amount: int,
    date: str | None = None,
) -> dict[str, Any]:
    if amount <= 0:
        raise ValidationError("El monto debe ser mayor que cero.")
    if from_account == to_account:
        raise ValidationError("El origen y el destino deben ser cuentas distintas.")

    source = require_account(db_path, from_account)
    target = require_account(db_path, to_account)

    if source["kind"] == "credit":
        raise ValidationError("No se puede transferir desde una tarjeta de crédito.")
    check_can_spend(source, amount)
    if target["kind"] == "credit" and target["balance"] < amount:
        raise ValidationError(
            f"El abono deja a '{target['name']}' con saldo a favor. "
            f"Deuda actual: {target['balance']}, abono: {amount}."
        )

    transfer_id = new_id()
    with transaction(db_path) as conn:
        conn.execute(
            "INSERT INTO transfers (id, from_account, to_account, amount, date, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (transfer_id, from_account, to_account, amount, date or today(), now()),
        )
        apply_balance_change(conn, from_account, -amount)
        apply_balance_change(conn, to_account, amount if target["kind"] == "debit" else -amount)

    return get_transfer(db_path, transfer_id)


def get_transfer(db_path: Path, transfer_id: str) -> dict[str, Any]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT t.*, f.name AS from_name, d.name AS to_name, d.kind AS to_kind"
            " FROM transfers t"
            " JOIN accounts f ON f.id = t.from_account"
            " JOIN accounts d ON d.id = t.to_account"
            " WHERE t.id = ?",
            (transfer_id,),
        ).fetchone()
    if row is None or row["deleted_at"]:
        raise NotFound("La transferencia no existe.")
    return dict(row)


def delete_transfer(db_path: Path, transfer_id: str) -> None:
    transfer = get_transfer(db_path, transfer_id)
    with transaction(db_path) as conn:
        conn.execute(
            "UPDATE transfers SET deleted_at = ? WHERE id = ?", (now(), transfer_id)
        )
        apply_balance_change(conn, transfer["from_account"], transfer["amount"])
        apply_balance_change(
            conn,
            transfer["to_account"],
            -transfer["amount"] if transfer["to_kind"] == "debit" else transfer["amount"],
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
    ''              AS description,
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


def list_activity(
    db_path: Path, month: str | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    """Movements and transfers on one timeline, newest first.

    ``month`` filters by ``YYYY-MM``; ``limit`` caps the number of rows.
    """
    params: list[Any] = []
    if month:
        movement_filter = "AND substr(m.date, 1, 7) = ?"
        transfer_filter = "AND substr(t.date, 1, 7) = ?"
        params = [month, month]
    else:
        movement_filter = transfer_filter = ""

    sql = _ACTIVITY_SQL.format(
        movement_filter=movement_filter, transfer_filter=transfer_filter
    )
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
