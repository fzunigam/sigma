from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sigma import database, settings
from sigma.db import accounts, connection, movements, schema
from sigma.db.errors import DatabaseFileError
from sigma.db.schema import create_database, is_sigma_database


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SIGMA_SETTINGS_DIR", str(tmp_path / "config"))


@pytest.fixture
def drive(tmp_path: Path) -> Path:
    """Stands in for a synced folder such as Google Drive."""
    folder = tmp_path / "Drive"
    folder.mkdir()
    return folder


# --- Creating and opening --------------------------------------------------


def test_create_makes_a_database_and_selects_it(drive: Path):
    path = database.create(drive / "finanzas.db")

    assert is_sigma_database(path)
    assert database.current() == path
    assert settings.recent_databases() == [path]


def test_create_adds_the_extension_when_missing(drive: Path):
    assert database.create(drive / "finanzas").name == "finanzas.db"


def test_create_refuses_to_overwrite_existing_data(drive: Path):
    path = drive / "finanzas.db"
    create_database(path)

    with pytest.raises(DatabaseFileError, match="Ya existe un archivo"):
        database.create(path)


def test_open_selects_an_existing_database(drive: Path):
    path = drive / "finanzas.db"
    create_database(path)

    database.open_existing(path)

    assert database.current() == path


def test_open_rejects_a_file_that_is_not_a_sigma_database(drive: Path):
    stray = drive / "notas.db"
    stray.write_text("no soy sqlite")

    with pytest.raises(DatabaseFileError, match="no es una base de datos de Sigma"):
        database.open_existing(stray)


def test_open_rejects_a_pre_1_0_database(drive: Path):
    legacy = drive / "sigma.db"
    conn = sqlite3.connect(legacy)
    conn.executescript(
        "CREATE TABLE movements (id TEXT);"
        "CREATE TABLE movement_marks (movement_id TEXT, marked INTEGER);"
    )
    conn.commit()
    conn.close()

    with pytest.raises(DatabaseFileError, match="versión anterior"):
        database.open_existing(legacy)


def test_open_rejects_a_missing_file(drive: Path):
    with pytest.raises(DatabaseFileError, match="no existe"):
        database.open_existing(drive / "fantasma.db")


def test_require_current_fails_when_nothing_is_open():
    with pytest.raises(DatabaseFileError, match="No hay una base de datos abierta"):
        database.require_current()


def test_current_is_none_when_the_file_disappears(drive: Path):
    path = database.create(drive / "finanzas.db")
    path.unlink()

    assert database.current() is None
    assert database.status()["missing"] is True


# --- Backups ---------------------------------------------------------------


def test_opening_a_database_backs_it_up_first(drive: Path):
    path = database.create(drive / "finanzas.db")
    accounts.create_account(path, "wallet", "Efectivo", "debit", balance=1_000)

    database.open_existing(path)

    backups = connection.list_backups(path)
    assert len(backups) == 1
    assert backups[0].parent == drive / connection.BACKUP_DIR_NAME
    assert accounts.list_accounts(backups[0])[0]["balance"] == 1_000


def test_startup_backs_up_the_remembered_database(drive: Path):
    """Opening the app is the common case, so it must produce a backup too."""
    path = database.create(drive / "finanzas.db")
    accounts.create_account(path, "wallet", "Efectivo", "debit", balance=1_000)

    database.open_at_startup()

    assert len(connection.list_backups(path)) == 1


def test_startup_backs_up_only_once_a_day(drive: Path):
    path = database.create(drive / "finanzas.db")
    accounts.create_account(path, "wallet", "Efectivo", "debit")

    for _ in range(5):
        database.open_at_startup()

    assert len(connection.list_backups(path)) == 1


def test_startup_without_a_database_does_nothing(drive: Path):
    assert database.open_at_startup() is None


def test_backups_are_rotated(drive: Path):
    path = database.create(drive / "finanzas.db")
    accounts.create_account(path, "wallet", "Efectivo", "debit")

    for _ in range(connection.BACKUPS_KEPT + 4):
        connection.create_backup(path)

    assert len(connection.list_backups(path)) == connection.BACKUPS_KEPT


def test_backing_up_an_empty_file_does_nothing(drive: Path):
    empty = drive / "vacia.db"
    empty.touch()
    assert connection.create_backup(empty) is None


def test_restore_brings_back_the_snapshot(drive: Path):
    path = database.create(drive / "finanzas.db")
    accounts.create_account(path, "wallet", "Efectivo", "debit", balance=100_000)
    snapshot = connection.create_backup(path)

    movements.create_movement(path, "expense", 40_000, "Error", "wallet")
    assert accounts.get_account(path, "wallet")["balance"] == 60_000

    database.restore_backup(snapshot)

    assert accounts.get_account(path, "wallet")["balance"] == 100_000
    assert movements.list_activity(path) == []


def test_restore_backs_up_what_it_replaces(drive: Path):
    path = database.create(drive / "finanzas.db")
    accounts.create_account(path, "wallet", "Efectivo", "debit", balance=100_000)
    snapshot = connection.create_backup(path)
    movements.create_movement(path, "expense", 40_000, "Error", "wallet")

    database.restore_backup(snapshot)

    # The pre-restore state is recoverable from the newest backup.
    newest = connection.list_backups(path)[0]
    assert accounts.get_account(newest, "wallet")["balance"] == 60_000


def test_restore_rejects_a_foreign_backup(drive: Path, tmp_path: Path):
    database.create(drive / "finanzas.db")
    other = tmp_path / "ajena.db"
    create_database(other)

    with pytest.raises(DatabaseFileError, match="no pertenece"):
        database.restore_backup(other)


# --- Advisory lock ---------------------------------------------------------


def test_opening_takes_the_lock_and_it_reads_as_ours(drive: Path):
    path = database.create(drive / "finanzas.db")

    assert connection.lock_path(path).exists()
    assert connection.read_lock(path) is None  # None means "not somebody else"
    assert database.status()["locked_by"] is None


def test_a_lock_from_another_machine_is_reported(drive: Path):
    path = database.create(drive / "finanzas.db")
    connection.lock_path(path).write_text("otro-mac:999", encoding="utf-8")

    assert connection.read_lock(path) == "otro-mac:999"
    assert database.status()["locked_by"] == "otro-mac:999"


def test_switching_databases_releases_the_previous_lock(drive: Path):
    first = database.create(drive / "uno.db")
    second = drive / "dos.db"
    create_database(second)

    database.open_existing(second)

    assert not connection.lock_path(first).exists()
    assert connection.lock_path(second).exists()


def test_a_lock_left_by_a_crash_on_this_machine_is_ignored(drive: Path):
    """Force-quitting must not leave a permanent 'open elsewhere' warning."""
    import socket

    path = database.create(drive / "finanzas.db")
    dead_pid = _unused_pid()
    connection.lock_path(path).write_text(
        f"{socket.gethostname()}:{dead_pid}", encoding="utf-8"
    )

    assert connection.read_lock(path) is None
    assert database.status()["locked_by"] is None


def test_a_stale_lock_is_cleaned_up_on_release(drive: Path):
    import socket

    path = database.create(drive / "finanzas.db")
    connection.lock_path(path).write_text(
        f"{socket.gethostname()}:{_unused_pid()}", encoding="utf-8"
    )

    connection.release_lock(path)

    assert not connection.lock_path(path).exists()


def _unused_pid() -> int:
    """A pid that is certainly not running."""
    import os

    candidate = 99_999
    while True:
        try:
            os.kill(candidate, 0)
        except (ProcessLookupError, ValueError):
            return candidate
        candidate -= 1


def test_close_releases_the_lock(drive: Path):
    path = database.create(drive / "finanzas.db")
    database.close()
    assert not connection.lock_path(path).exists()


def test_releasing_leaves_another_machines_lock_alone(drive: Path):
    path = database.create(drive / "finanzas.db")
    connection.lock_path(path).write_text("otro-mac:999", encoding="utf-8")

    connection.release_lock(path)

    assert connection.lock_path(path).read_text() == "otro-mac:999"


# --- Synced-folder safety --------------------------------------------------


def test_no_wal_sidecar_files_are_left_behind(drive: Path):
    """WAL files are what Google Drive syncs badly, so they must never appear."""
    path = database.create(drive / "finanzas.db")
    accounts.create_account(path, "wallet", "Efectivo", "debit", balance=1_000)
    movements.create_movement(path, "expense", 100, "Café", "wallet")

    assert not (drive / "finanzas.db-wal").exists()
    assert not (drive / "finanzas.db-shm").exists()

    with connection.connect(path) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


# --- Legacy migration ------------------------------------------------------


def test_status_advertises_a_legacy_database(drive: Path, monkeypatch):
    legacy = drive / "sigma.db"
    legacy.touch()
    monkeypatch.setattr(settings, "LEGACY_DATABASE_PATH", legacy)

    assert database.status()["legacy_available"] == str(legacy)


def test_migrate_legacy_opens_the_result(drive: Path, monkeypatch, tmp_path: Path):
    legacy = _make_legacy_database(tmp_path / "sigma.db")
    monkeypatch.setattr(settings, "LEGACY_DATABASE_PATH", legacy)
    monkeypatch.setattr(settings, "LEGACY_CONFIG_PATH", tmp_path / "sin-config.toml")

    result = database.migrate_legacy(drive / "finanzas.db")

    assert result["migrated"]["accounts"] == 1
    assert database.current() == drive / "finanzas.db"
    assert accounts.get_account(database.current(), "wallet")["balance"] == 70_000


def test_migrate_legacy_without_a_source_fails_clearly(drive: Path, monkeypatch, tmp_path: Path):
    monkeypatch.setattr(settings, "LEGACY_DATABASE_PATH", tmp_path / "no-existe.db")

    with pytest.raises(DatabaseFileError, match="versión anterior"):
        database.migrate_legacy(drive / "finanzas.db")


def _make_legacy_database(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE accounts (
            id TEXT PRIMARY KEY, name TEXT, type TEXT, balance INTEGER,
            credit_limit INTEGER, updated_at TEXT, deleted_at TEXT);
        CREATE TABLE movements (
            id TEXT PRIMARY KEY, amount INTEGER, description TEXT, account_id TEXT,
            type TEXT, created_at TEXT, updated_at TEXT, deleted_at TEXT);
        CREATE TABLE movement_marks (movement_id TEXT PRIMARY KEY, marked INTEGER);
        CREATE TABLE transfers (
            id TEXT PRIMARY KEY, from_account TEXT, to_account TEXT, amount INTEGER,
            created_at TEXT, updated_at TEXT, deleted_at TEXT);
        CREATE TABLE render_history (
            id TEXT PRIMARY KEY, net_amount INTEGER, rendered_at TEXT,
            updated_at TEXT, deleted_at TEXT);
        INSERT INTO accounts VALUES ('wallet','Efectivo','debit',70000,0,'ts',NULL);
        """
    )
    conn.commit()
    conn.close()
    return path


# --- Format upgrades -------------------------------------------------------


def make_version_1_database(path: Path) -> None:
    """A file exactly as Sigma 1.0.0 left it: no ``transfers.description``."""
    create_database(path)
    with connection.transaction(path) as conn:
        conn.execute("DROP TABLE transfers")
        conn.execute(
            "CREATE TABLE transfers ("
            " id TEXT PRIMARY KEY,"
            " from_account TEXT NOT NULL REFERENCES accounts(id),"
            " to_account TEXT NOT NULL REFERENCES accounts(id),"
            " amount INTEGER NOT NULL CHECK (amount > 0),"
            " date TEXT NOT NULL, created_at TEXT NOT NULL, deleted_at TEXT)"
        )
        conn.execute("UPDATE meta SET value = '1' WHERE key = 'schema_version'")


def test_opening_an_older_file_upgrades_it(drive: Path):
    path = drive / "vieja.db"
    make_version_1_database(path)

    database.open_existing(path)

    assert schema.needs_upgrade(path) is False


def test_the_upgrade_is_backed_up_first(drive: Path):
    path = drive / "vieja.db"
    make_version_1_database(path)

    database.open_existing(path)

    assert len(connection.list_backups(path)) == 1


def test_opening_a_file_from_a_newer_sigma_is_refused(drive: Path):
    path = drive / "futura.db"
    create_database(path)
    with connection.transaction(path) as conn:
        conn.execute("UPDATE meta SET value = '99' WHERE key = 'schema_version'")

    with pytest.raises(DatabaseFileError, match="versión más nueva"):
        database.open_existing(path)


def test_startup_upgrades_the_remembered_file(drive: Path):
    path = drive / "vieja.db"
    make_version_1_database(path)
    settings.set_database_path(path)

    database.open_at_startup()

    assert schema.needs_upgrade(path) is False


def test_startup_survives_a_file_it_cannot_upgrade(drive: Path):
    """Launching must not fail because of what the settings remember."""
    path = drive / "futura.db"
    create_database(path)
    with connection.transaction(path) as conn:
        conn.execute("UPDATE meta SET value = '99' WHERE key = 'schema_version'")
    settings.set_database_path(path)

    assert database.open_at_startup() == path
