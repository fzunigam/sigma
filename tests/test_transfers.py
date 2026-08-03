from __future__ import annotations

from pathlib import Path

import pytest

from sigma.db import accounts, movements, transfers
from sigma.db.errors import ValidationError


def balance(db: Path, account_id: str) -> int:
    return accounts.get_account(db, account_id)["balance"]


# --- Creating --------------------------------------------------------------


def test_transfer_between_debit_accounts(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit", balance=0)
    transfers.create_transfer(db, "wallet", "bank", 40_000)
    assert balance(db, "wallet") == 60_000
    assert balance(db, "bank") == 40_000


def test_transfer_to_a_credit_card_pays_the_debt(db: Path, wallet, card):
    movements.create_movement(db, "expense", 60_000, "Notebook", "card")
    transfers.create_transfer(db, "wallet", "card", 50_000)
    assert balance(db, "wallet") == 50_000
    assert balance(db, "card") == 10_000


def test_transfer_from_a_credit_card_is_rejected(db: Path, wallet, card):
    with pytest.raises(ValidationError, match="desde una tarjeta de crédito"):
        transfers.create_transfer(db, "card", "wallet", 1_000)


def test_transfer_to_an_investment_account_adds_to_its_cash(db: Path, wallet, fintual):
    """An investment account behaves like a debit account for transfers: it
    gains what it receives, unlike a credit card, which owes less instead."""
    transfers.create_transfer(db, "wallet", "fintual", 40_000)
    assert balance(db, "wallet") == 60_000
    assert balance(db, "fintual") == 1_000_000 + 40_000


def test_transfer_from_an_investment_account_reduces_its_cash(db: Path, wallet, fintual):
    transfers.create_transfer(db, "fintual", "wallet", 40_000)
    assert balance(db, "fintual") == 1_000_000 - 40_000
    assert balance(db, "wallet") == 140_000


def test_overpaying_a_credit_card_is_rejected(db: Path, wallet, card):
    movements.create_movement(db, "expense", 10_000, "Compra", "card")
    with pytest.raises(ValidationError, match="saldo a favor"):
        transfers.create_transfer(db, "wallet", "card", 20_000)


def test_transfer_needs_two_different_accounts(db: Path, wallet):
    with pytest.raises(ValidationError, match="cuentas distintas"):
        transfers.create_transfer(db, "wallet", "wallet", 1_000)


def test_transfer_beyond_available_funds_is_rejected(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    with pytest.raises(ValidationError, match="Saldo insuficiente"):
        transfers.create_transfer(db, "wallet", "bank", 200_000)


def test_delete_transfer_reverses_both_sides(db: Path, wallet, card):
    movements.create_movement(db, "expense", 60_000, "Notebook", "card")
    transfer = transfers.create_transfer(db, "wallet", "card", 50_000)

    transfers.delete_transfer(db, transfer["id"])

    assert balance(db, "wallet") == 100_000
    assert balance(db, "card") == 60_000


def test_a_transfer_can_carry_a_description(db: Path, wallet, card):
    movements.create_movement(db, "expense", 60_000, "Notebook", "card")

    transfer = transfers.create_transfer(
        db, "wallet", "card", 50_000, description="  Pago   tarjeta  "
    )

    assert transfer["description"] == "Pago tarjeta"


def test_a_transfer_without_a_description_is_fine(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    assert transfers.create_transfer(db, "wallet", "bank", 1_000)["description"] == ""


# --- Editing ---------------------------------------------------------------


def test_edit_a_transfer_amount_moves_both_balances(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    transfer = transfers.create_transfer(db, "wallet", "bank", 40_000)

    transfers.update_transfer(db, transfer["id"], amount=25_000)

    assert balance(db, "wallet") == 75_000
    assert balance(db, "bank") == 25_000


def test_edit_a_transfer_destination(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    accounts.create_account(db, "savings", "Ahorro", "debit")
    transfer = transfers.create_transfer(db, "wallet", "bank", 40_000)

    transfers.update_transfer(db, transfer["id"], to_account="savings")

    assert balance(db, "bank") == 0
    assert balance(db, "savings") == 40_000
    assert balance(db, "wallet") == 60_000


def test_edit_a_card_payment_keeps_the_debt_straight(db: Path, wallet, card):
    movements.create_movement(db, "expense", 60_000, "Notebook", "card")
    transfer = transfers.create_transfer(db, "wallet", "card", 50_000)

    transfers.update_transfer(db, transfer["id"], amount=30_000)

    assert balance(db, "card") == 30_000
    assert balance(db, "wallet") == 70_000


def test_raising_a_transfer_only_needs_the_difference(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    transfer = transfers.create_transfer(db, "wallet", "bank", 90_000)

    transfers.update_transfer(db, transfer["id"], amount=95_000)

    assert balance(db, "wallet") == 5_000
    assert balance(db, "bank") == 95_000


def test_edit_a_transfer_beyond_available_funds_is_rejected(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    transfer = transfers.create_transfer(db, "wallet", "bank", 40_000)

    with pytest.raises(ValidationError, match="Saldo insuficiente"):
        transfers.update_transfer(db, transfer["id"], amount=150_000)

    assert balance(db, "wallet") == 60_000


def test_edit_cannot_overpay_a_card(db: Path, wallet, card):
    movements.create_movement(db, "expense", 20_000, "Compra", "card")
    transfer = transfers.create_transfer(db, "wallet", "card", 10_000)

    with pytest.raises(ValidationError, match="saldo a favor"):
        transfers.update_transfer(db, transfer["id"], amount=50_000)


def test_edit_cannot_point_a_transfer_at_itself(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    transfer = transfers.create_transfer(db, "wallet", "bank", 1_000)

    with pytest.raises(ValidationError, match="cuentas distintas"):
        transfers.update_transfer(db, transfer["id"], to_account="wallet")


def test_edit_cannot_move_a_transfer_onto_a_deleted_account(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    accounts.create_account(db, "old", "Antigua", "debit")
    accounts.delete_account(db, "old")
    transfer = transfers.create_transfer(db, "wallet", "bank", 1_000)

    with pytest.raises(ValidationError, match="eliminada"):
        transfers.update_transfer(db, transfer["id"], to_account="old")
