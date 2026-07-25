from __future__ import annotations

from pathlib import Path

import pytest

from sigma.db import accounts, movements
from sigma.db.errors import NotFound, ValidationError


def balance(db: Path, account_id: str) -> int:
    return accounts.get_account(db, account_id)["balance"]


# --- Expenses and income ---------------------------------------------------


def test_expense_lowers_a_debit_balance(db: Path, wallet):
    movements.create_movement(db, "expense", 30_000, "Supermercado", "wallet")
    assert balance(db, "wallet") == 70_000


def test_income_raises_a_debit_balance(db: Path, wallet):
    movements.create_movement(db, "income", 500_000, "Sueldo", "wallet")
    assert balance(db, "wallet") == 600_000


def test_expense_on_a_credit_card_increases_debt(db: Path, card):
    movements.create_movement(db, "expense", 120_000, "Notebook", "card")
    account = accounts.get_account(db, "card")
    assert account["balance"] == 120_000
    assert account["available"] == 380_000


def test_income_on_a_credit_card_pays_it_down(db: Path, card):
    movements.create_movement(db, "expense", 120_000, "Notebook", "card")
    movements.create_movement(db, "income", 20_000, "Abono", "card")
    assert balance(db, "card") == 100_000


def test_expense_beyond_available_funds_is_rejected(db: Path, wallet):
    with pytest.raises(ValidationError, match="Saldo insuficiente"):
        movements.create_movement(db, "expense", 100_001, "Imposible", "wallet")
    assert balance(db, "wallet") == 100_000


def test_expense_beyond_credit_limit_is_rejected(db: Path, card):
    with pytest.raises(ValidationError, match="Cupo insuficiente"):
        movements.create_movement(db, "expense", 500_001, "Imposible", "card")
    assert balance(db, "card") == 0


def test_movement_validation(db: Path, wallet):
    with pytest.raises(ValidationError):
        movements.create_movement(db, "expense", 0, "Cero", "wallet")
    with pytest.raises(ValidationError):
        movements.create_movement(db, "expense", -5, "Negativo", "wallet")
    with pytest.raises(ValidationError):
        movements.create_movement(db, "expense", 100, "   ", "wallet")
    with pytest.raises(ValidationError):
        movements.create_movement(db, "gift", 100, "Tipo raro", "wallet")


def test_movements_are_pending_by_default(db: Path, wallet):
    movement = movements.create_movement(db, "expense", 1_000, "Café", "wallet")
    assert movement["pending"] == 1

    excluded = movements.create_movement(db, "expense", 1_000, "Café", "wallet", pending=False)
    assert excluded["pending"] == 0


def test_pending_flag_can_be_toggled(db: Path, wallet):
    movement = movements.create_movement(db, "expense", 1_000, "Café", "wallet")
    assert movements.set_movement_pending(db, movement["id"], False)["pending"] == 0
    assert movements.set_movement_pending(db, movement["id"], True)["pending"] == 1


def test_delete_reverses_the_balance_change(db: Path, wallet, card):
    expense = movements.create_movement(db, "expense", 30_000, "Supermercado", "wallet")
    on_card = movements.create_movement(db, "expense", 50_000, "Notebook", "card")

    movements.delete_movement(db, expense["id"])
    movements.delete_movement(db, on_card["id"])

    assert balance(db, "wallet") == 100_000
    assert balance(db, "card") == 0
    assert movements.list_activity(db) == []


def test_deleted_movement_cannot_be_fetched(db: Path, wallet):
    movement = movements.create_movement(db, "expense", 1_000, "Café", "wallet")
    movements.delete_movement(db, movement["id"])
    with pytest.raises(NotFound):
        movements.get_movement(db, movement["id"])


# --- Transfers -------------------------------------------------------------


def test_transfer_between_debit_accounts(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit", balance=0)
    movements.create_transfer(db, "wallet", "bank", 40_000)
    assert balance(db, "wallet") == 60_000
    assert balance(db, "bank") == 40_000


def test_transfer_to_a_credit_card_pays_the_debt(db: Path, wallet, card):
    movements.create_movement(db, "expense", 60_000, "Notebook", "card")
    movements.create_transfer(db, "wallet", "card", 50_000)
    assert balance(db, "wallet") == 50_000
    assert balance(db, "card") == 10_000


def test_transfer_from_a_credit_card_is_rejected(db: Path, wallet, card):
    with pytest.raises(ValidationError, match="desde una tarjeta de crédito"):
        movements.create_transfer(db, "card", "wallet", 1_000)


def test_overpaying_a_credit_card_is_rejected(db: Path, wallet, card):
    movements.create_movement(db, "expense", 10_000, "Compra", "card")
    with pytest.raises(ValidationError, match="saldo a favor"):
        movements.create_transfer(db, "wallet", "card", 20_000)


def test_transfer_needs_two_different_accounts(db: Path, wallet):
    with pytest.raises(ValidationError, match="cuentas distintas"):
        movements.create_transfer(db, "wallet", "wallet", 1_000)


def test_transfer_beyond_available_funds_is_rejected(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    with pytest.raises(ValidationError, match="Saldo insuficiente"):
        movements.create_transfer(db, "wallet", "bank", 200_000)


def test_delete_transfer_reverses_both_sides(db: Path, wallet, card):
    movements.create_movement(db, "expense", 60_000, "Notebook", "card")
    transfer = movements.create_transfer(db, "wallet", "card", 50_000)

    movements.delete_transfer(db, transfer["id"])

    assert balance(db, "wallet") == 100_000
    assert balance(db, "card") == 60_000


# --- Listing ---------------------------------------------------------------


def test_activity_mixes_movements_and_transfers_newest_first(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit", balance=10_000)
    movements.create_movement(db, "expense", 1_000, "Antiguo", "wallet", date="2026-01-05")
    movements.create_transfer(db, "wallet", "bank", 2_000, date="2026-03-10")
    movements.create_movement(db, "income", 3_000, "Reciente", "wallet", date="2026-05-20")

    activity = movements.list_activity(db)
    assert [row["date"] for row in activity] == ["2026-05-20", "2026-03-10", "2026-01-05"]
    assert [row["record"] for row in activity] == ["movement", "transfer", "movement"]


def test_activity_filters_by_month_and_limit(db: Path, wallet):
    movements.create_movement(db, "expense", 1_000, "Enero", "wallet", date="2026-01-15")
    movements.create_movement(db, "expense", 2_000, "Marzo", "wallet", date="2026-03-01")
    movements.create_movement(db, "expense", 3_000, "Marzo", "wallet", date="2026-03-20")

    assert len(movements.list_activity(db, month="2026-03")) == 2
    assert len(movements.list_activity(db, month="2026-02")) == 0
    assert len(movements.list_activity(db, limit=1)) == 1


def test_transfer_row_names_both_ends(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    movements.create_transfer(db, "wallet", "bank", 1_000)
    row = movements.list_activity(db)[0]
    assert row["account_name"] == "Efectivo"
    assert row["to_account_name"] == "Banco"


def test_month_summary_ignores_transfers(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    movements.create_movement(db, "income", 500_000, "Sueldo", "wallet", date="2026-04-01")
    movements.create_movement(db, "expense", 120_000, "Arriendo", "wallet", date="2026-04-05")
    movements.create_transfer(db, "wallet", "bank", 50_000, date="2026-04-06")

    assert movements.month_summary(db, "2026-04") == {
        "income": 500_000,
        "expense": 120_000,
        "net": 380_000,
    }


def test_month_summary_of_an_empty_month(db: Path, wallet):
    assert movements.month_summary(db, "2026-12") == {"income": 0, "expense": 0, "net": 0}
