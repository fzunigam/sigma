"""Accounts: creation, editing, soft deletion and balance helpers.

Three kinds of account exist:

* ``debit`` — ``balance`` is money available. Spending lowers it.
* ``credit`` — ``balance`` is money *owed*. Spending raises it, up to
  ``credit_limit``; paying the card lowers it.
* ``investment`` — same rules as ``debit``: ``balance`` is CLP cash available,
  moved by ordinary transfers. USD cash and security holdings live in
  ``sigma.db.investments``, keyed by this account's id.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sigma.db.connection import connect, now, transaction
from sigma.db.errors import NotFound, ValidationError

COLUMNS = "id, name, kind, balance, credit_limit, created_at, deleted_at"


def list_accounts(db_path: Path, include_deleted: bool = False) -> list[dict[str, Any]]:
    where = "" if include_deleted else " WHERE deleted_at IS NULL"
    with connect(db_path) as conn:
        rows = conn.execute(f"SELECT {COLUMNS} FROM accounts{where} ORDER BY name").fetchall()
    return [_as_dict(row) for row in rows]


def get_account(db_path: Path, account_id: str) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            f"SELECT {COLUMNS} FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
    return _as_dict(row) if row else None


def require_account(db_path: Path, account_id: str, *, active: bool = True) -> dict[str, Any]:
    account = get_account(db_path, account_id)
    if account is None:
        raise NotFound(f"La cuenta '{account_id}' no existe.")
    if active and account["deleted_at"]:
        raise ValidationError(f"La cuenta '{account['name']}' está eliminada.")
    return account


def create_account(
    db_path: Path,
    account_id: str,
    name: str,
    kind: str,
    balance: int = 0,
    credit_limit: int = 0,
) -> dict[str, Any]:
    account_id = account_id.strip()
    name = name.strip()
    if not account_id:
        raise ValidationError("El identificador de la cuenta no puede estar vacío.")
    if not name:
        raise ValidationError("El nombre de la cuenta no puede estar vacío.")
    if kind not in ("debit", "credit", "investment"):
        raise ValidationError("El tipo de cuenta debe ser 'debit', 'credit' o 'investment'.")
    if kind in ("debit", "investment") and balance < 0:
        raise ValidationError("El saldo inicial no puede ser negativo.")
    if kind == "credit" and credit_limit < 0:
        raise ValidationError("El cupo no puede ser negativo.")
    if kind in ("debit", "investment"):
        credit_limit = 0

    with transaction(db_path) as conn:
        existing = conn.execute(
            "SELECT deleted_at FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if existing and existing["deleted_at"] is None:
            raise ValidationError(f"Ya existe una cuenta con el identificador '{account_id}'.")
        if existing:
            # Reviving a soft-deleted account keeps its history attached to it.
            conn.execute(
                "UPDATE accounts SET name = ?, kind = ?, balance = ?, credit_limit = ?,"
                " deleted_at = NULL WHERE id = ?",
                (name, kind, balance, credit_limit, account_id),
            )
        else:
            conn.execute(
                "INSERT INTO accounts (id, name, kind, balance, credit_limit, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (account_id, name, kind, balance, credit_limit, now()),
            )

    return require_account(db_path, account_id)


def update_account(
    db_path: Path,
    account_id: str,
    name: str | None = None,
    credit_limit: int | None = None,
) -> dict[str, Any]:
    account = require_account(db_path, account_id)

    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError("El nombre de la cuenta no puede estar vacío.")
    if credit_limit is not None:
        if account["kind"] != "credit":
            raise ValidationError("Solo las tarjetas de crédito tienen cupo.")
        if credit_limit < 0:
            raise ValidationError("El cupo no puede ser negativo.")
        if credit_limit < account["balance"]:
            raise ValidationError(
                "El cupo no puede ser menor que lo que ya has gastado en la tarjeta."
            )

    with transaction(db_path) as conn:
        if name is not None:
            conn.execute("UPDATE accounts SET name = ? WHERE id = ?", (name, account_id))
        if credit_limit is not None:
            conn.execute(
                "UPDATE accounts SET credit_limit = ? WHERE id = ?", (credit_limit, account_id)
            )

    return require_account(db_path, account_id)


def rename_account_id(db_path: Path, account_id: str, new_id: str) -> dict[str, Any]:
    """Change the short identifier, carrying every reference with it."""
    new_id = new_id.strip()
    if not new_id:
        raise ValidationError("El nuevo identificador no puede estar vacío.")
    require_account(db_path, account_id)
    if new_id == account_id:
        return require_account(db_path, account_id)

    with transaction(db_path) as conn:
        if conn.execute("SELECT 1 FROM accounts WHERE id = ?", (new_id,)).fetchone():
            raise ValidationError(f"Ya existe una cuenta con el identificador '{new_id}'.")
        # Deferred so the child rows can be repointed while the parent moves.
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("UPDATE accounts SET id = ? WHERE id = ?", (new_id, account_id))
        conn.execute(
            "UPDATE movements SET account_id = ? WHERE account_id = ?", (new_id, account_id)
        )
        conn.execute(
            "UPDATE transfers SET from_account = ? WHERE from_account = ?", (new_id, account_id)
        )
        conn.execute(
            "UPDATE transfers SET to_account = ? WHERE to_account = ?", (new_id, account_id)
        )
        conn.execute("PRAGMA foreign_keys = ON")

    return require_account(db_path, new_id)


def delete_account(db_path: Path, account_id: str) -> None:
    """Soft-delete the account, leaving its movements attached to it.

    The old implementation reassigned every record to a reserved ``deleted``
    account, which silently destroyed the information of *where* the money
    actually moved. Here the account simply stops being offered for new
    movements while its history stays readable.
    """
    require_account(db_path, account_id)
    with transaction(db_path) as conn:
        conn.execute("UPDATE accounts SET deleted_at = ? WHERE id = ?", (now(), account_id))


def apply_balance_change(conn, account_id: str, delta: int) -> None:
    """Add ``delta`` to an account balance inside an open transaction."""
    conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (delta, account_id))


def check_can_spend(account: dict[str, Any], amount: int) -> None:
    """Raise if ``amount`` cannot be spent from ``account``.

    ``debit`` and ``investment`` share the same rule: a balance that cannot go
    negative. Only ``credit`` spends against a limit instead.
    """
    if account["kind"] == "credit":
        available = account["credit_limit"] - account["balance"]
        if amount > available:
            raise ValidationError(
                f"Cupo insuficiente en '{account['name']}'. "
                f"Disponible: {available}, necesario: {amount}."
            )
    else:
        if account["balance"] < amount:
            raise ValidationError(
                f"Saldo insuficiente en '{account['name']}'. "
                f"Disponible: {account['balance']}, necesario: {amount}."
            )


def _as_dict(row) -> dict[str, Any]:
    account = dict(row)
    if account["kind"] == "credit":
        account["available"] = account["credit_limit"] - account["balance"]
    else:
        account["available"] = account["balance"]
    return account
