"""Transfers: moving money between the user's own accounts.

A transfer is not income and not spending — it is the same money in a different
place — so it never appears in the month totals or in a reconciliation. Paying a
credit card is a transfer towards it: the debt goes down instead of up.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sigma.db.accounts import apply_balance_change, check_can_spend, require_account
from sigma.db.connection import connect, now, today, transaction
from sigma.db.errors import NotFound, ValidationError
from sigma.db.movements import check_amount, clean_description
from sigma.db.schema import new_id


def create_transfer(
    db_path: Path,
    from_account: str,
    to_account: str,
    amount: int,
    date: str | None = None,
    description: str = "",
) -> dict[str, Any]:
    check_amount(amount)
    if from_account == to_account:
        raise ValidationError("El origen y el destino deben ser cuentas distintas.")
    description = clean_description(description, required=False)

    source = require_account(db_path, from_account)
    target = require_account(db_path, to_account)
    _check_transfer_accounts(source, target, source["balance"], target["balance"], amount)

    transfer_id = new_id()
    with transaction(db_path) as conn:
        conn.execute(
            "INSERT INTO transfers"
            " (id, from_account, to_account, amount, description, date, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                transfer_id,
                from_account,
                to_account,
                amount,
                description,
                date or today(),
                now(),
            ),
        )
        from_delta, to_delta = _transfer_deltas(target["kind"], amount)
        apply_balance_change(conn, from_account, from_delta)
        apply_balance_change(conn, to_account, to_delta)

    return get_transfer(db_path, transfer_id)


def _check_transfer_accounts(
    source: dict[str, Any],
    target: dict[str, Any],
    source_balance: int,
    target_balance: int,
    amount: int,
) -> None:
    """Validate both ends of a transfer against the balances given.

    The balances are passed in rather than read from the accounts because when a
    transfer is *edited* the relevant state is the one it would have without the
    transfer, not the one it has now.
    """
    if source["kind"] == "credit":
        raise ValidationError("No se puede transferir desde una tarjeta de crédito.")
    check_can_spend({**source, "balance": source_balance}, amount)
    if target["kind"] == "credit" and target_balance < amount:
        raise ValidationError(
            f"El abono deja a '{target['name']}' con saldo a favor. "
            f"Deuda actual: {target_balance}, abono: {amount}."
        )


def _transfer_deltas(to_kind: str, amount: int) -> tuple[int, int]:
    """How a transfer of ``amount`` moves each side's balance.

    The source is always a debit account, so it simply loses the money. The
    destination gains it, unless it is a card, where receiving money means owing
    less.
    """
    return -amount, (amount if to_kind == "debit" else -amount)


def update_transfer(
    db_path: Path,
    transfer_id: str,
    from_account: str | None = None,
    to_account: str | None = None,
    amount: int | None = None,
    date: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Correct a transfer in place, undoing its old effect on both accounts."""
    transfer = get_transfer(db_path, transfer_id)

    new_from = from_account or transfer["from_account"]
    new_to = to_account or transfer["to_account"]
    new_amount = transfer["amount"] if amount is None else amount
    new_date = date or transfer["date"]
    new_description = (
        transfer["description"]
        if description is None
        else clean_description(description, required=False)
    )

    check_amount(new_amount)
    if new_from == new_to:
        raise ValidationError("El origen y el destino deben ser cuentas distintas.")

    involved = _involved_accounts(db_path, transfer, new_from, new_to)
    balances = {account_id: item["balance"] for account_id, item in involved.items()}

    # Rewind the transfer so both ends are validated as if it had never happened.
    old_from_delta, old_to_delta = _transfer_deltas(
        involved[transfer["to_account"]]["kind"], transfer["amount"]
    )
    balances[transfer["from_account"]] -= old_from_delta
    balances[transfer["to_account"]] -= old_to_delta

    _check_transfer_accounts(
        involved[new_from],
        involved[new_to],
        balances[new_from],
        balances[new_to],
        new_amount,
    )

    new_from_delta, new_to_delta = _transfer_deltas(involved[new_to]["kind"], new_amount)

    with transaction(db_path) as conn:
        conn.execute(
            "UPDATE transfers SET from_account = ?, to_account = ?, amount = ?,"
            " description = ?, date = ? WHERE id = ?",
            (new_from, new_to, new_amount, new_description, new_date, transfer_id),
        )
        apply_balance_change(conn, transfer["from_account"], -old_from_delta)
        apply_balance_change(conn, transfer["to_account"], -old_to_delta)
        apply_balance_change(conn, new_from, new_from_delta)
        apply_balance_change(conn, new_to, new_to_delta)

    return get_transfer(db_path, transfer_id)


def _involved_accounts(
    db_path: Path, transfer: dict[str, Any], new_from: str, new_to: str
) -> dict[str, dict[str, Any]]:
    """Every account either end of the edit touches, loaded once.

    The two the transfer already uses are accepted even if they were deleted —
    the transfer exists and has to be undone — while an account it is being
    moved onto has to be one that can still be used.
    """
    accounts: dict[str, dict[str, Any]] = {}
    for account_id in (transfer["from_account"], transfer["to_account"]):
        accounts[account_id] = require_account(db_path, account_id, active=False)
    for account_id in (new_from, new_to):
        if account_id not in accounts:
            accounts[account_id] = require_account(db_path, account_id)
    return accounts


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
    from_delta, to_delta = _transfer_deltas(transfer["to_kind"], transfer["amount"])
    with transaction(db_path) as conn:
        conn.execute(
            "UPDATE transfers SET deleted_at = ? WHERE id = ?", (now(), transfer_id)
        )
        apply_balance_change(conn, transfer["from_account"], -from_delta)
        apply_balance_change(conn, transfer["to_account"], -to_delta)


