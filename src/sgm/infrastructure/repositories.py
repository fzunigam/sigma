import sqlite3
from datetime import datetime

from sgm.domain.accounts import Account, AccountType
from sgm.domain.movements import Movement


class AccountRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(self, account: Account) -> None:
        self._connection.execute(
            """
            INSERT INTO accounts (id, name, kind, balance)
            VALUES (?, ?, ?, ?)
            """,
            (account.id, account.name, account.kind.value, account.balance),
        )
        self._connection.commit()

    def list_all(self) -> list[Account]:
        cursor = self._connection.execute(
            "SELECT id, name, kind, balance FROM accounts ORDER BY id"
        )
        return [
            Account(
                id=row["id"],
                name=row["name"],
                kind=AccountType(row["kind"]),
                balance=row["balance"],
            )
            for row in cursor.fetchall()
        ]


class MovementRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, movement: Movement, movement_id: str) -> None:
        self._connection.execute(
            """
            INSERT INTO movements (id, description, amount, type, account_id, marked)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                movement_id,
                movement.description,
                movement.amount,
                movement.type.value,
                movement.account_id,
                int(movement.marked),
            ),
        )
        self._connection.commit()

    def list_marked(self) -> list[dict[str, object]]:
        cursor = self._connection.execute(
            """
            SELECT id, description, amount, type, account_id, marked
            FROM movements
            WHERE marked = 1
            ORDER BY id
            """
        )
        return [
            {
                "id": row["id"],
                "description": row["description"],
                "amount": row["amount"],
                "type": row["type"],
                "account_id": row["account_id"],
                "marked": bool(row["marked"]),
            }
            for row in cursor.fetchall()
        ]


class RenderHistoryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add_snapshot(
        self,
        snapshot_id: str,
        rendered_at: datetime,
        income_total: int,
        expense_total: int,
        net: int,
        count: int,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO render_history (id, rendered_at, income_total, expense_total, net, count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                rendered_at.isoformat(),
                income_total,
                expense_total,
                net,
                count,
            ),
        )
        self._connection.commit()

    def list_all(self) -> list[dict[str, object]]:
        cursor = self._connection.execute(
            """
            SELECT id, rendered_at, income_total, expense_total, net, count
            FROM render_history
            ORDER BY rendered_at, id
            """
        )
        return [
            {
                "id": row["id"],
                "rendered_at": row["rendered_at"],
                "income_total": row["income_total"],
                "expense_total": row["expense_total"],
                "net": row["net"],
                "count": row["count"],
            }
            for row in cursor.fetchall()
        ]
