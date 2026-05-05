from datetime import UTC, datetime

import pytest

from sgm.application.render import MarkedMovement, render_marked_movements
from sgm.domain.errors import NoMarkedMovementsError
from sgm.domain.movements import MovementType


def test_render_computes_net_and_snapshot_metadata() -> None:
    rendered_at = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    movements = [
        MarkedMovement(id="m1", type=MovementType.INCOME, amount=1_500, marked=True),
        MarkedMovement(id="m2", type=MovementType.EXPENSE, amount=300, marked=True),
        MarkedMovement(id="m3", type=MovementType.INCOME, amount=2_000, marked=False),
        MarkedMovement(id="m4", type=MovementType.EXPENSE, amount=200, marked=True),
    ]

    snapshot, processed_ids = render_marked_movements(
        movements,
        rendered_at=rendered_at,
    )

    assert snapshot.income_total == 1_500
    assert snapshot.expense_total == 500
    assert snapshot.net == 1_000
    assert snapshot.metadata.count == 3
    assert snapshot.metadata.rendered_at == rendered_at
    assert processed_ids == ["m1", "m2", "m4"]


def test_render_raises_error_when_no_marked_movements() -> None:
    movements = [
        MarkedMovement(id="m1", type=MovementType.INCOME, amount=100, marked=False),
        MarkedMovement(id="m2", type=MovementType.EXPENSE, amount=50, marked=False),
    ]

    with pytest.raises(NoMarkedMovementsError):
        render_marked_movements(movements)


def test_render_processed_ids_preserve_stable_input_order() -> None:
    movements = [
        MarkedMovement(id="m3", type=MovementType.INCOME, amount=900, marked=True),
        MarkedMovement(id="m4", type=MovementType.EXPENSE, amount=100, marked=False),
        MarkedMovement(id="m1", type=MovementType.EXPENSE, amount=300, marked=True),
        MarkedMovement(id="m2", type=MovementType.INCOME, amount=700, marked=True),
    ]

    _, processed_ids = render_marked_movements(movements)

    assert processed_ids == ["m3", "m1", "m2"]
