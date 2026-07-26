from __future__ import annotations

from pathlib import Path

import pytest

from sigma.db import accounts, movements, transfers
from sigma.db.errors import NotFound, ValidationError


def test_create_debit_account(db: Path):
    account = accounts.create_account(db, "wallet", "Efectivo", "debit", balance=50_000)
    assert account["kind"] == "debit"
    assert account["balance"] == 50_000
    assert account["credit_limit"] == 0
    assert account["available"] == 50_000


def test_credit_account_available_is_remaining_quota(db: Path):
    account = accounts.create_account(db, "card", "Tarjeta", "credit", credit_limit=300_000)
    assert account["available"] == 300_000


def test_create_rejects_duplicate_id(db: Path, wallet):
    with pytest.raises(ValidationError, match="Ya existe una cuenta"):
        accounts.create_account(db, "wallet", "Otra", "debit")


def test_create_rejects_bad_input(db: Path):
    with pytest.raises(ValidationError):
        accounts.create_account(db, "", "Sin id", "debit")
    with pytest.raises(ValidationError):
        accounts.create_account(db, "x", "", "debit")
    with pytest.raises(ValidationError):
        accounts.create_account(db, "x", "Tipo raro", "savings")
    with pytest.raises(ValidationError):
        accounts.create_account(db, "x", "Negativa", "debit", balance=-1)


def test_debit_account_ignores_credit_limit(db: Path):
    account = accounts.create_account(db, "w", "Efectivo", "debit", credit_limit=999)
    assert account["credit_limit"] == 0


def test_update_name_and_limit(db: Path, card):
    renamed = accounts.update_account(db, "card", name="Tarjeta Banco")
    assert renamed["name"] == "Tarjeta Banco"

    updated = accounts.update_account(db, "card", credit_limit=800_000)
    assert updated["credit_limit"] == 800_000


def test_limit_cannot_be_set_below_current_debt(db: Path, card):
    movements.create_movement(db, "expense", 200_000, "TV", "card")
    with pytest.raises(ValidationError, match="menor que lo que ya has gastado"):
        accounts.update_account(db, "card", credit_limit=100_000)


def test_limit_rejected_on_debit_account(db: Path, wallet):
    with pytest.raises(ValidationError, match="tarjetas de crédito"):
        accounts.update_account(db, "wallet", credit_limit=1_000)


def test_rename_id_carries_every_reference(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit", balance=10_000)
    movements.create_movement(db, "expense", 1_000, "Café", "wallet")
    transfers.create_transfer(db, "wallet", "bank", 2_000)
    transfers.create_transfer(db, "bank", "wallet", 500)

    accounts.rename_account_id(db, "wallet", "efectivo")

    assert accounts.get_account(db, "wallet") is None
    assert accounts.get_account(db, "efectivo")["name"] == "Efectivo"

    activity = movements.list_activity(db)
    referenced = {row["account_id"] for row in activity} | {
        row["to_account_id"] for row in activity if row["to_account_id"]
    }
    assert referenced == {"efectivo", "bank"}


def test_rename_rejects_taken_id(db: Path, wallet, card):
    with pytest.raises(ValidationError, match="Ya existe una cuenta"):
        accounts.rename_account_id(db, "wallet", "card")


def test_delete_keeps_history_readable(db: Path, wallet):
    movements.create_movement(db, "expense", 1_000, "Café", "wallet")
    accounts.delete_account(db, "wallet")

    assert accounts.list_accounts(db) == []
    assert len(accounts.list_accounts(db, include_deleted=True)) == 1

    # The movement still resolves to the account it actually happened on.
    activity = movements.list_activity(db)
    assert activity[0]["account_name"] == "Efectivo"


def test_deleted_account_rejects_new_movements(db: Path, wallet):
    accounts.delete_account(db, "wallet")
    with pytest.raises(ValidationError, match="está eliminada"):
        movements.create_movement(db, "expense", 1_000, "Café", "wallet")


def test_recreating_a_deleted_id_revives_the_account(db: Path, wallet):
    movements.create_movement(db, "expense", 1_000, "Café", "wallet")
    accounts.delete_account(db, "wallet")
    revived = accounts.create_account(db, "wallet", "Efectivo nuevo", "debit", balance=5_000)

    assert revived["deleted_at"] is None
    assert revived["balance"] == 5_000
    assert len(movements.list_activity(db)) == 1


def test_missing_account_raises_not_found(db: Path):
    with pytest.raises(NotFound):
        accounts.require_account(db, "nope")
