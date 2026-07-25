from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sigma.db import accounts, movements, preferences, reconciliations
from sigma.db.schema import (
    SCHEMA_VERSION,
    create_database,
    is_legacy_database,
    is_sigma_database,
    migrate_legacy_database,
)

LEGACY_SCHEMA = """
CREATE TABLE accounts (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL, balance INTEGER NOT NULL,
    credit_limit INTEGER DEFAULT 0, updated_at TEXT NOT NULL, deleted_at TEXT);
CREATE TABLE movements (
    id TEXT PRIMARY KEY, amount INTEGER NOT NULL, description TEXT NOT NULL,
    account_id TEXT NOT NULL, type TEXT NOT NULL, created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL, deleted_at TEXT);
CREATE TABLE movement_marks (movement_id TEXT PRIMARY KEY, marked INTEGER NOT NULL);
CREATE TABLE transfers (
    id TEXT PRIMARY KEY, from_account TEXT NOT NULL, to_account TEXT NOT NULL,
    amount INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    deleted_at TEXT);
CREATE TABLE render_history (
    id TEXT PRIMARY KEY, net_amount INTEGER NOT NULL, rendered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL, deleted_at TEXT);
"""


@pytest.fixture
def legacy_db(tmp_path: Path) -> Path:
    """A database in the pre-1.0 format, with one of everything."""
    path = tmp_path / "sigma.db"
    conn = sqlite3.connect(path)
    conn.executescript(LEGACY_SCHEMA)
    conn.executemany(
        "INSERT INTO accounts (id, name, type, balance, credit_limit, updated_at, deleted_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("wallet", "Efectivo", "debit", 70_000, 0, "2026-01-01 10:00:00", None),
            ("card", "Tarjeta", "credit", 120_000, 500_000, "2026-01-01 10:00:00", None),
            ("deleted", "Deleted Account", "debit", 0, 0, "2026-01-01 10:00:00", None),
            ("old", "Antigua", "debit", 0, 0, "2026-01-01 10:00:00", "2026-01-02 10:00:00"),
        ],
    )
    conn.executemany(
        "INSERT INTO movements"
        " (id, amount, description, account_id, type, created_at, updated_at, deleted_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("m1", 30_000, "Supermercado", "wallet", "expense", "2026-01-05", "ts1", None),
            ("m2", 120_000, "Notebook", "card", "expense", "2026-01-06T00:00:00", "ts2", None),
            ("m3", 5_000, "Borrado", "wallet", "expense", "2026-01-07", "ts3", "2026-01-08"),
            ("m4", 9_000, "Huérfano", "deleted", "expense", "2026-01-09", "ts4", None),
        ],
    )
    conn.executemany(
        "INSERT INTO movement_marks (movement_id, marked) VALUES (?, ?)",
        [("m1", 1), ("m2", 0), ("m3", 1), ("m4", 0)],
    )
    conn.execute(
        "INSERT INTO transfers"
        " (id, from_account, to_account, amount, created_at, updated_at, deleted_at)"
        " VALUES ('t1', 'wallet', 'card', 10000, '2026-01-10', 'ts5', NULL)"
    )
    conn.execute(
        "INSERT INTO render_history (id, net_amount, rendered_at, updated_at, deleted_at)"
        " VALUES ('r1', -45000, '2026-01-11', 'ts6', NULL)"
    )
    conn.commit()
    conn.close()
    return path


# --- Creation --------------------------------------------------------------


def test_create_database_writes_the_schema_version(db: Path):
    conn = sqlite3.connect(db)
    version = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    conn.close()
    assert version[0] == str(SCHEMA_VERSION)


def test_create_database_refuses_to_overwrite_existing_data(tmp_path: Path):
    path = tmp_path / "existing.db"
    path.write_bytes(b"no soy una base vacia")
    with pytest.raises(FileExistsError):
        create_database(path)


def test_database_recognition(db: Path, legacy_db: Path, tmp_path: Path):
    assert is_sigma_database(db)
    assert not is_legacy_database(db)

    assert is_legacy_database(legacy_db)
    assert not is_sigma_database(legacy_db)

    other = tmp_path / "cualquier.txt"
    other.write_text("no soy sqlite")
    assert not is_sigma_database(other)
    assert not is_legacy_database(other)

    assert not is_sigma_database(tmp_path / "no-existe.db")


def test_foreign_keys_are_enforced(db: Path):
    with pytest.raises(sqlite3.IntegrityError):
        from sigma.db.connection import transaction

        with transaction(db) as conn:
            conn.execute(
                "INSERT INTO movements"
                " (id, kind, amount, description, account_id, date, created_at)"
                " VALUES ('x', 'expense', 1, 'huérfano', 'no-existe', '2026-01-01', 'ts')"
            )


# --- Migration -------------------------------------------------------------


def test_migration_moves_every_table(legacy_db: Path, tmp_path: Path):
    target = tmp_path / "nueva.db"
    counts = migrate_legacy_database(legacy_db, target)

    assert counts == {
        "accounts": 4,
        "movements": 4,
        "transfers": 1,
        "reconciliations": 1,
    }
    assert is_sigma_database(target)


def test_migration_preserves_balances_and_kinds(legacy_db: Path, tmp_path: Path):
    target = tmp_path / "nueva.db"
    migrate_legacy_database(legacy_db, target)

    wallet = accounts.get_account(target, "wallet")
    assert wallet["kind"] == "debit"
    assert wallet["balance"] == 70_000

    card = accounts.get_account(target, "card")
    assert card["kind"] == "credit"
    assert card["balance"] == 120_000
    assert card["available"] == 380_000


def test_migration_maps_marks_to_pending(legacy_db: Path, tmp_path: Path):
    target = tmp_path / "nueva.db"
    migrate_legacy_database(legacy_db, target)

    assert reconciliations.pending_summary(db_path := target) == {"net": -30_000, "count": 1}
    assert [row["description"] for row in reconciliations.list_pending(db_path)] == [
        "Supermercado"
    ]


def test_migration_normalises_dates(legacy_db: Path, tmp_path: Path):
    target = tmp_path / "nueva.db"
    migrate_legacy_database(legacy_db, target)

    dates = {row["description"]: row["date"] for row in movements.list_activity(target)}
    assert dates["Supermercado"] == "2026-01-05"
    assert dates["Notebook"] == "2026-01-06"  # the old value carried a time part


def test_migration_keeps_soft_deleted_rows_deleted(legacy_db: Path, tmp_path: Path):
    target = tmp_path / "nueva.db"
    migrate_legacy_database(legacy_db, target)

    descriptions = {row["description"] for row in movements.list_activity(target)}
    assert "Borrado" not in descriptions


def test_migration_hides_the_reserved_deleted_account(legacy_db: Path, tmp_path: Path):
    target = tmp_path / "nueva.db"
    migrate_legacy_database(legacy_db, target)

    visible = {account["id"] for account in accounts.list_accounts(target)}
    assert visible == {"wallet", "card"}

    # Its records still resolve rather than disappearing.
    orphan = [r for r in movements.list_activity(target) if r["description"] == "Huérfano"]
    assert orphan and orphan[0]["account_id"] == "deleted"


def test_migration_carries_render_history_into_reconciliations(legacy_db: Path, tmp_path: Path):
    target = tmp_path / "nueva.db"
    migrate_legacy_database(legacy_db, target)

    history = reconciliations.list_reconciliations(target)
    assert len(history) == 1
    assert history[0]["net_amount"] == -45_000
    assert history[0]["date"] == "2026-01-11"


def test_migration_can_carry_the_old_default_accounts(legacy_db: Path, tmp_path: Path):
    target = tmp_path / "nueva.db"
    migrate_legacy_database(
        legacy_db,
        target,
        defaults={"default_expense_account": "wallet", "default_income_account": "card"},
    )

    assert preferences.load_preferences(target) == {
        "default_expense_account": "wallet",
        "default_income_account": "card",
    }


def test_migration_never_touches_the_source(legacy_db: Path, tmp_path: Path):
    before = legacy_db.read_bytes()
    migrate_legacy_database(legacy_db, tmp_path / "nueva.db")
    assert legacy_db.read_bytes() == before


def test_migration_rejects_a_database_that_is_not_legacy(db: Path, tmp_path: Path):
    with pytest.raises(ValueError, match="anterior a 1.0"):
        migrate_legacy_database(db, tmp_path / "nueva.db")
