from __future__ import annotations

from pathlib import Path

import pytest

from sigma.db import accounts, movements, transfers
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



# --- Listing ---------------------------------------------------------------


def test_activity_mixes_movements_and_transfers_newest_first(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit", balance=10_000)
    movements.create_movement(db, "expense", 1_000, "Antiguo", "wallet", date="2026-01-05")
    transfers.create_transfer(db, "wallet", "bank", 2_000, date="2026-03-10")
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
    transfers.create_transfer(db, "wallet", "bank", 1_000)
    row = movements.list_activity(db)[0]
    assert row["account_name"] == "Efectivo"
    assert row["to_account_name"] == "Banco"


def test_month_summary_ignores_transfers(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    movements.create_movement(db, "income", 500_000, "Sueldo", "wallet", date="2026-04-01")
    movements.create_movement(db, "expense", 120_000, "Arriendo", "wallet", date="2026-04-05")
    transfers.create_transfer(db, "wallet", "bank", 50_000, date="2026-04-06")

    assert movements.month_summary(db, "2026-04") == {
        "income": 500_000,
        "expense": 120_000,
        "net": 380_000,
    }


def test_month_summary_of_an_empty_month(db: Path, wallet):
    assert movements.month_summary(db, "2026-12") == {"income": 0, "expense": 0, "net": 0}


# --- Editing ---------------------------------------------------------------


def test_edit_changes_the_amount_and_the_balance(db: Path, wallet):
    movement = movements.create_movement(db, "expense", 30_000, "Supermercado", "wallet")

    edited = movements.update_movement(db, movement["id"], amount=25_000)

    assert edited["amount"] == 25_000
    assert balance(db, "wallet") == 75_000


def test_edit_leaves_untouched_fields_alone(db: Path, wallet):
    movement = movements.create_movement(
        db, "expense", 30_000, "Supermercado", "wallet", date="2026-03-04"
    )

    edited = movements.update_movement(db, movement["id"], description="Feria")

    assert edited["description"] == "Feria"
    assert edited["amount"] == 30_000
    assert edited["date"] == "2026-03-04"
    assert balance(db, "wallet") == 70_000


def test_edit_can_turn_an_expense_into_income(db: Path, wallet):
    movement = movements.create_movement(db, "expense", 20_000, "Devolución", "wallet")

    movements.update_movement(db, movement["id"], kind="income")

    assert balance(db, "wallet") == 120_000


def test_edit_can_move_a_movement_to_another_account(db: Path, wallet, card):
    movement = movements.create_movement(db, "expense", 20_000, "Compra", "wallet")

    movements.update_movement(db, movement["id"], account_id="card")

    assert balance(db, "wallet") == 100_000
    assert balance(db, "card") == 20_000


def test_raising_an_expense_only_needs_the_difference(db: Path, wallet):
    """The old amount is given back before the new one is checked."""
    movement = movements.create_movement(db, "expense", 90_000, "Arriendo", "wallet")

    movements.update_movement(db, movement["id"], amount=95_000)

    assert balance(db, "wallet") == 5_000


def test_edit_beyond_available_funds_is_rejected(db: Path, wallet):
    movement = movements.create_movement(db, "expense", 30_000, "Supermercado", "wallet")

    with pytest.raises(ValidationError, match="Saldo insuficiente"):
        movements.update_movement(db, movement["id"], amount=150_000)

    assert balance(db, "wallet") == 70_000


def test_edit_validates_the_new_values(db: Path, wallet):
    movement = movements.create_movement(db, "expense", 1_000, "Café", "wallet")

    with pytest.raises(ValidationError, match="mayor que cero"):
        movements.update_movement(db, movement["id"], amount=0)
    with pytest.raises(ValidationError, match="descripción"):
        movements.update_movement(db, movement["id"], description="   ")
    with pytest.raises(ValidationError, match="'expense' o 'income'"):
        movements.update_movement(db, movement["id"], kind="transfer")


def test_a_reconciled_movement_cannot_go_back_to_pending(db: Path, wallet):
    from sigma.db import reconciliations

    movement = movements.create_movement(db, "expense", 1_000, "Café", "wallet")
    reconciliations.run_reconciliation(db)

    with pytest.raises(ValidationError, match="ya fue conciliado"):
        movements.update_movement(db, movement["id"], pending=True)


def test_a_reconciled_movement_can_still_be_corrected(db: Path, wallet):
    from sigma.db import reconciliations

    movement = movements.create_movement(db, "expense", 1_000, "Cafe", "wallet")
    reconciliations.run_reconciliation(db)

    edited = movements.update_movement(db, movement["id"], description="Café")

    assert edited["description"] == "Café"
    assert edited["pending"] == 0


def test_editing_an_unknown_movement_raises(db: Path, wallet):
    with pytest.raises(NotFound):
        movements.update_movement(db, "nope", amount=1)


# --- Searching -------------------------------------------------------------


def test_search_ignores_case_and_accents(db: Path, wallet):
    movements.create_movement(db, "expense", 1_000, "Café con leche", "wallet")
    movements.create_movement(db, "expense", 2_000, "Almuerzo", "wallet")

    found = movements.list_activity(db, search="cafe")

    assert [item["description"] for item in found] == ["Café con leche"]


def test_search_matches_the_account_name(db: Path, wallet, card):
    movements.create_movement(db, "expense", 1_000, "Compra", "card")
    movements.create_movement(db, "expense", 2_000, "Otra", "wallet")

    found = movements.list_activity(db, search="tarjeta")

    assert [item["description"] for item in found] == ["Compra"]


def test_search_looks_across_every_month(db: Path, wallet):
    movements.create_movement(db, "expense", 1_000, "Dentista", "wallet", date="2025-02-11")
    movements.create_movement(db, "expense", 2_000, "Dentista", "wallet", date="2026-06-30")

    assert len(movements.list_activity(db, search="dentista")) == 2


def test_search_finds_transfers_by_their_note_and_by_the_word(db: Path, wallet):
    accounts.create_account(db, "bank", "Banco", "debit")
    transfers.create_transfer(db, "wallet", "bank", 1_000, description="Ahorro del mes")

    assert len(movements.list_activity(db, search="ahorro")) == 1
    assert len(movements.list_activity(db, search="transferencia")) == 1
    assert len(movements.list_activity(db, search="arriendo")) == 0


def test_search_and_a_blank_term_are_not_the_same(db: Path, wallet):
    movements.create_movement(db, "expense", 1_000, "Café", "wallet")

    assert len(movements.list_activity(db, search="   ")) == 1
    assert len(movements.list_activity(db, search="zzz")) == 0
