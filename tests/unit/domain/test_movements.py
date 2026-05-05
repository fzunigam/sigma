import pytest

from sgm.domain.errors import DomainValidationError
from sgm.domain.movements import Movement, MovementType


def test_new_movement_is_marked_by_default() -> None:
    movement = Movement.new("Salary", 100_000, MovementType.INCOME, "a1")

    assert movement.marked is True


def test_movement_accepts_positive_integer_amount() -> None:
    movement = Movement.new("Salary", 1, MovementType.INCOME, "a1")

    assert movement.amount == 1


@pytest.mark.parametrize("invalid_amount", [0, -1, 1.5, "1000", None, True])
def test_movement_rejects_invalid_amount(invalid_amount: object) -> None:
    with pytest.raises(DomainValidationError):
        Movement.new("Salary", invalid_amount, MovementType.INCOME, "a1")  # type: ignore[arg-type]
