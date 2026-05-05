from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sgm.domain.errors import NoMarkedMovementsError
from sgm.domain.movements import MovementType


@dataclass(frozen=True)
class MarkedMovement:
    id: str
    type: MovementType
    amount: int
    marked: bool


@dataclass(frozen=True)
class RenderSnapshotMetadata:
    count: int
    rendered_at: datetime


@dataclass(frozen=True)
class RenderSnapshot:
    income_total: int
    expense_total: int
    net: int
    metadata: RenderSnapshotMetadata


def render_marked_movements(
    movements: Sequence[MarkedMovement],
    *,
    rendered_at: datetime | None = None,
) -> tuple[RenderSnapshot, list[str]]:
    marked_movements = [movement for movement in movements if movement.marked]

    if not marked_movements:
        raise NoMarkedMovementsError("Cannot render without marked movements")

    income_total = sum(
        movement.amount
        for movement in marked_movements
        if movement.type == MovementType.INCOME
    )
    expense_total = sum(
        movement.amount
        for movement in marked_movements
        if movement.type == MovementType.EXPENSE
    )
    snapshot = RenderSnapshot(
        income_total=income_total,
        expense_total=expense_total,
        net=income_total - expense_total,
        metadata=RenderSnapshotMetadata(
            count=len(marked_movements),
            rendered_at=rendered_at or datetime.now(UTC),
        ),
    )

    return snapshot, [movement.id for movement in marked_movements]
