"""Database schema, creation and migration from the pre-1.0 format."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from sigma.db.connection import connect, now, transaction

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE accounts (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    kind         TEXT NOT NULL CHECK (kind IN ('debit', 'credit')),
    balance      INTEGER NOT NULL DEFAULT 0,
    credit_limit INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL,
    deleted_at   TEXT
);

CREATE TABLE reconciliations (
    id             TEXT PRIMARY KEY,
    net_amount     INTEGER NOT NULL,
    movement_count INTEGER NOT NULL DEFAULT 0,
    date           TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE TABLE movements (
    id                TEXT PRIMARY KEY,
    kind              TEXT NOT NULL CHECK (kind IN ('expense', 'income')),
    amount            INTEGER NOT NULL CHECK (amount > 0),
    description       TEXT NOT NULL,
    account_id        TEXT NOT NULL REFERENCES accounts(id),
    date              TEXT NOT NULL,
    pending           INTEGER NOT NULL DEFAULT 1,
    reconciliation_id TEXT REFERENCES reconciliations(id),
    created_at        TEXT NOT NULL,
    deleted_at        TEXT
);

CREATE TABLE transfers (
    id           TEXT PRIMARY KEY,
    from_account TEXT NOT NULL REFERENCES accounts(id),
    to_account   TEXT NOT NULL REFERENCES accounts(id),
    amount       INTEGER NOT NULL CHECK (amount > 0),
    date         TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    deleted_at   TEXT
);

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX idx_movements_date ON movements(date);
CREATE INDEX idx_movements_pending ON movements(pending) WHERE deleted_at IS NULL;
CREATE INDEX idx_transfers_date ON transfers(date);
"""


def create_database(db_path: Path) -> None:
    """Create an empty Sigma database at ``db_path``.

    Raises ``FileExistsError`` if a non-empty file is already there, so an
    accidental pick in the save dialog can never wipe existing data.
    """
    if db_path.exists() and db_path.stat().st_size > 0:
        raise FileExistsError(f"Ya existe un archivo con datos en {db_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with transaction(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )


def is_sigma_database(db_path: Path) -> bool:
    """True if the file is a Sigma database in the current format."""
    if not db_path.exists():
        return False
    try:
        with connect(db_path) as conn:
            return _table_names(conn) >= {"accounts", "movements", "reconciliations", "meta"}
    except sqlite3.DatabaseError:
        return False


def is_legacy_database(db_path: Path) -> bool:
    """True if the file is a pre-1.0 Sigma database (``movement_marks`` era)."""
    if not db_path.exists():
        return False
    try:
        with connect(db_path) as conn:
            tables = _table_names(conn)
            return "movement_marks" in tables and "meta" not in tables
    except sqlite3.DatabaseError:
        return False


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


# --- Migration from the pre-1.0 format -------------------------------------


def migrate_legacy_database(
    source: Path,
    target: Path,
    defaults: dict[str, str] | None = None,
) -> dict[str, int]:
    """Copy a pre-1.0 database into a fresh 1.0 database at ``target``.

    ``source`` is never modified. Returns the number of rows migrated per table
    so the caller can show a summary and the tests can assert on it.

    Structural changes handled here:

    * ``accounts.type`` becomes ``accounts.kind``.
    * ``movement_marks.marked`` folds into ``movements.pending``.
    * ``movements.created_at`` held the movement's *date*; it becomes ``date``,
      and the real audit timestamp comes from the old ``updated_at``.
    * ``render_history`` becomes ``reconciliations``. Old rows recorded only a
      net amount, so the link back to their movements cannot be recovered:
      already-rendered movements land with ``pending = 0`` and no
      ``reconciliation_id``.
    """
    if not is_legacy_database(source):
        raise ValueError(f"{source} no es una base de datos Sigma anterior a 1.0")

    create_database(target)
    counts = {"accounts": 0, "movements": 0, "transfers": 0, "reconciliations": 0}

    with connect(source) as old, transaction(target) as new:
        for row in old.execute("SELECT * FROM accounts"):
            deleted_at = row["deleted_at"]
            # The old code reassigned orphaned records to a reserved 'deleted'
            # account and left it visible-but-filtered. Keep the row so those
            # records still resolve, but mark it deleted so it stays out of the way.
            if row["id"] == "deleted" and not deleted_at:
                deleted_at = row["updated_at"]
            new.execute(
                "INSERT INTO accounts"
                " (id, name, kind, balance, credit_limit, created_at, deleted_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    row["id"],
                    row["name"],
                    row["type"],
                    row["balance"],
                    row["credit_limit"] or 0,
                    row["updated_at"],
                    deleted_at,
                ),
            )
            counts["accounts"] += 1

        for row in old.execute("SELECT * FROM render_history ORDER BY rendered_at"):
            if row["deleted_at"]:
                continue
            new.execute(
                "INSERT INTO reconciliations (id, net_amount, movement_count, date, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (row["id"], row["net_amount"], 0, row["rendered_at"], row["updated_at"]),
            )
            counts["reconciliations"] += 1

        movements = old.execute(
            "SELECT m.*, COALESCE(mk.marked, 0) AS marked"
            " FROM movements m LEFT JOIN movement_marks mk ON mk.movement_id = m.id"
        )
        for row in movements:
            new.execute(
                "INSERT INTO movements"
                " (id, kind, amount, description, account_id, date, pending, reconciliation_id,"
                "  created_at, deleted_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)",
                (
                    row["id"],
                    row["type"],
                    row["amount"],
                    row["description"],
                    row["account_id"],
                    _date_only(row["created_at"]),
                    int(row["marked"]),
                    row["updated_at"],
                    row["deleted_at"],
                ),
            )
            counts["movements"] += 1

        for row in old.execute("SELECT * FROM transfers"):
            new.execute(
                "INSERT INTO transfers"
                " (id, from_account, to_account, amount, date, created_at, deleted_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    row["id"],
                    row["from_account"],
                    row["to_account"],
                    row["amount"],
                    _date_only(row["created_at"]),
                    row["updated_at"],
                    row["deleted_at"],
                ),
            )
            counts["transfers"] += 1

        for key, value in (defaults or {}).items():
            new.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value)
            )
        new.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('migrated_at', ?)", (now(),)
        )

    return counts


def _date_only(value: str) -> str:
    """Legacy rows stored dates as ``YYYY-MM-DD`` but a few carried a time part."""
    return value.split("T")[0].split(" ")[0]


def new_id() -> str:
    return str(uuid.uuid4())
