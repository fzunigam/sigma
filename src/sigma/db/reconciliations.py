"""Reconciliations: closing a batch of movements into an auditable snapshot.

Movements are created "pending" by default. Running a reconciliation records the
net of every pending movement, stamps those movements with the reconciliation's
id and clears their pending flag. Unlike the pre-1.0 ``render_history``, the
link survives: a past reconciliation can always be opened to see exactly which
movements it closed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sigma.db.connection import connect, now, today, transaction
from sigma.db.errors import NotFound, ValidationError
from sigma.db.schema import new_id


def pending_summary(db_path: Path) -> dict[str, int]:
    """Net and count of everything waiting to be reconciled."""
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT"
            " COALESCE(SUM(CASE WHEN kind = 'income' THEN amount ELSE -amount END), 0) AS net,"
            " COUNT(*) AS count"
            " FROM movements"
            " WHERE deleted_at IS NULL AND pending = 1 AND reconciliation_id IS NULL",
        ).fetchone()
    return {"net": row["net"], "count": row["count"]}


def list_pending(db_path: Path) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT m.*, a.name AS account_name FROM movements m"
            " JOIN accounts a ON a.id = m.account_id"
            " WHERE m.deleted_at IS NULL AND m.pending = 1 AND m.reconciliation_id IS NULL"
            " ORDER BY m.date DESC, m.created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def run_reconciliation(db_path: Path, date: str | None = None) -> dict[str, Any]:
    """Close every pending movement into a new reconciliation."""
    summary = pending_summary(db_path)
    if summary["count"] == 0:
        raise ValidationError("No hay movimientos pendientes de conciliar.")

    reconciliation_id = new_id()
    with transaction(db_path) as conn:
        conn.execute(
            "INSERT INTO reconciliations (id, net_amount, movement_count, date, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (reconciliation_id, summary["net"], summary["count"], date or today(), now()),
        )
        conn.execute(
            "UPDATE movements SET pending = 0, reconciliation_id = ?"
            " WHERE deleted_at IS NULL AND pending = 1 AND reconciliation_id IS NULL",
            (reconciliation_id,),
        )

    return get_reconciliation(db_path, reconciliation_id)


def list_reconciliations(db_path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM reconciliations ORDER BY date DESC, created_at DESC"
    params: list[Any] = []
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with connect(db_path) as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def get_reconciliation(db_path: Path, reconciliation_id: str) -> dict[str, Any]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM reconciliations WHERE id = ?", (reconciliation_id,)
        ).fetchone()
    if row is None:
        raise NotFound("La conciliación no existe.")
    return dict(row)


def reconciliation_movements(db_path: Path, reconciliation_id: str) -> list[dict[str, Any]]:
    """The movements closed by a given reconciliation."""
    get_reconciliation(db_path, reconciliation_id)
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT m.*, a.name AS account_name FROM movements m"
            " JOIN accounts a ON a.id = m.account_id"
            " WHERE m.reconciliation_id = ? AND m.deleted_at IS NULL"
            " ORDER BY m.date DESC, m.created_at DESC",
            (reconciliation_id,),
        ).fetchall()
    return [dict(row) for row in rows]
