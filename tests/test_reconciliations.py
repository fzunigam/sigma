from __future__ import annotations

from pathlib import Path

import pytest

from sigma.db import movements, reconciliations
from sigma.db.errors import ValidationError


def test_pending_summary_nets_income_against_expense(db: Path, wallet):
    movements.create_movement(db, "income", 500_000, "Sueldo", "wallet")
    movements.create_movement(db, "expense", 120_000, "Arriendo", "wallet")

    assert reconciliations.pending_summary(db) == {"net": 380_000, "count": 2}


def test_excluded_movements_stay_out_of_the_pending_total(db: Path, wallet):
    movements.create_movement(db, "expense", 10_000, "Cuenta", "wallet")
    movements.create_movement(db, "expense", 20_000, "Aparte", "wallet", pending=False)

    assert reconciliations.pending_summary(db) == {"net": -10_000, "count": 1}


def test_running_a_reconciliation_closes_the_pending_movements(db: Path, wallet):
    movements.create_movement(db, "income", 500_000, "Sueldo", "wallet")
    movements.create_movement(db, "expense", 120_000, "Arriendo", "wallet")

    result = reconciliations.run_reconciliation(db)

    assert result["net_amount"] == 380_000
    assert result["movement_count"] == 2
    assert reconciliations.pending_summary(db) == {"net": 0, "count": 0}


def test_reconciliation_keeps_the_link_to_its_movements(db: Path, wallet):
    movements.create_movement(db, "income", 500_000, "Sueldo", "wallet")
    movements.create_movement(db, "expense", 120_000, "Arriendo", "wallet")
    movements.create_movement(db, "expense", 5_000, "Aparte", "wallet", pending=False)

    result = reconciliations.run_reconciliation(db)
    closed = reconciliations.reconciliation_movements(db, result["id"])

    assert {row["description"] for row in closed} == {"Sueldo", "Arriendo"}
    assert all(row["reconciliation_id"] == result["id"] for row in closed)


def test_reconciling_twice_only_takes_what_is_new(db: Path, wallet):
    movements.create_movement(db, "expense", 10_000, "Primera", "wallet")
    first = reconciliations.run_reconciliation(db)

    movements.create_movement(db, "expense", 4_000, "Segunda", "wallet")
    second = reconciliations.run_reconciliation(db)

    assert first["net_amount"] == -10_000
    assert second["net_amount"] == -4_000
    assert second["movement_count"] == 1
    assert len(reconciliations.list_reconciliations(db)) == 2


def test_reconciling_with_nothing_pending_is_rejected(db: Path, wallet):
    with pytest.raises(ValidationError, match="No hay movimientos pendientes"):
        reconciliations.run_reconciliation(db)


def test_reconciled_movements_cannot_be_re_flagged(db: Path, wallet):
    movement = movements.create_movement(db, "expense", 10_000, "Compra", "wallet")
    reconciliations.run_reconciliation(db)

    with pytest.raises(ValidationError, match="ya fue conciliado"):
        movements.set_movement_pending(db, movement["id"], True)


def test_deleting_a_reconciled_movement_leaves_the_snapshot_intact(db: Path, wallet):
    """A reconciliation records what was true when it ran; fixing a mistake
    afterwards corrects the balance without rewriting history."""
    movement = movements.create_movement(db, "expense", 10_000, "Error", "wallet")
    result = reconciliations.run_reconciliation(db)

    movements.delete_movement(db, movement["id"])

    assert reconciliations.get_reconciliation(db, result["id"])["net_amount"] == -10_000
    assert reconciliations.reconciliation_movements(db, result["id"]) == []


def test_list_pending_returns_only_open_movements(db: Path, wallet):
    movements.create_movement(db, "expense", 1_000, "Abierta", "wallet")
    movements.create_movement(db, "expense", 2_000, "Excluida", "wallet", pending=False)

    pending = reconciliations.list_pending(db)
    assert [row["description"] for row in pending] == ["Abierta"]
    assert pending[0]["account_name"] == "Efectivo"
