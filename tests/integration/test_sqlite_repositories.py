from datetime import UTC, datetime
from pathlib import Path

from sgm.domain.accounts import Account, AccountType
from sgm.domain.movements import Movement, MovementType
from sgm.infrastructure.db import init_db
from sgm.infrastructure.repositories import (
    AccountRepository,
    MovementRepository,
    RenderHistoryRepository,
)


def test_init_db_creates_accounts_table(tmp_path: Path) -> None:
    connection = init_db(tmp_path / "sigma.db")

    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
    ).fetchone()

    assert row is not None


def test_account_insert_list_roundtrip(tmp_path: Path) -> None:
    connection = init_db(tmp_path / "sigma.db")
    repository = AccountRepository(connection)
    account = Account(id="a1", name="Checking", kind=AccountType.DEBIT, balance=125_000)

    repository.create(account)

    assert repository.list_all() == [account]


def test_movement_add_list_marked_returns_only_marked_rows(tmp_path: Path) -> None:
    connection = init_db(tmp_path / "sigma.db")
    account_repository = AccountRepository(connection)
    movement_repository = MovementRepository(connection)

    account_repository.create(
        Account(id="a1", name="Cash", kind=AccountType.DEBIT, balance=0)
    )
    movement_repository.add(
        Movement.new("Salary", 100_000, MovementType.INCOME, "a1"),
        movement_id="m1",
    )
    movement_repository.add(
        Movement(
            description="Coffee",
            amount=2_000,
            type=MovementType.EXPENSE,
            account_id="a1",
            marked=False,
        ),
        movement_id="m2",
    )

    marked_movements = movement_repository.list_marked()

    assert marked_movements == [
        {
            "id": "m1",
            "description": "Salary",
            "amount": 100_000,
            "type": "income",
            "account_id": "a1",
            "marked": True,
        }
    ]


def test_render_history_insert_list_roundtrip(tmp_path: Path) -> None:
    connection = init_db(tmp_path / "sigma.db")
    repository = RenderHistoryRepository(connection)
    rendered_at = datetime(2026, 5, 5, 12, 30, tzinfo=UTC)

    repository.add_snapshot(
        snapshot_id="s1",
        rendered_at=rendered_at,
        income_total=150_000,
        expense_total=40_000,
        net=110_000,
        count=2,
    )

    assert repository.list_all() == [
        {
            "id": "s1",
            "rendered_at": rendered_at.isoformat(),
            "income_total": 150_000,
            "expense_total": 40_000,
            "net": 110_000,
            "count": 2,
        }
    ]
