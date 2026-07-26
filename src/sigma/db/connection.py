"""SQLite connection handling, tuned for database files kept in synced folders.

The database file is chosen by the user and typically lives inside a Google
Drive / Dropbox folder, so this module trades a little speed for safety:

* ``journal_mode=DELETE`` instead of WAL. WAL leaves ``-wal`` and ``-shm``
  sidecar files next to the database; sync clients upload them out of order and
  can leave the set inconsistent.
* ``synchronous=FULL`` so a write is on disk before the sync client sees it.
* Connections are opened per operation and closed immediately, keeping the
  window where the file is busy as short as possible.
"""

from __future__ import annotations

import os
import socket
import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

BACKUP_DIR_NAME = ".sigma-backups"
BACKUPS_KEPT = 10
LOCK_SUFFIX = ".lock"


def fold(text: str | None) -> str:
    """Lowercase and drop accents, so searching ``cafe`` finds ``Café``.

    SQLite's own ``LIKE`` only ignores case for ASCII, which in Spanish means
    half the words in the database would not match what the user typed.
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _configure(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("PRAGMA synchronous = FULL")
    conn.create_function("fold", 1, fold, deterministic=True)


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a read-oriented connection. Does not commit."""
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        _configure(conn)
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection that commits on success and rolls back on failure."""
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        _configure(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def now() -> str:
    """Timestamp used for ``created_at`` / ``deleted_at`` columns."""
    return datetime.now().isoformat(timespec="seconds")


def today() -> str:
    """Date used as the default for movements and transfers."""
    return datetime.now().date().isoformat()


# --- Backups ---------------------------------------------------------------


def backup_dir(db_path: Path) -> Path:
    return db_path.parent / BACKUP_DIR_NAME


def create_backup(
    db_path: Path, keep: int = BACKUPS_KEPT, once_per_day: bool = False
) -> Path | None:
    """Copy the database next to itself, under ``.sigma-backups/``.

    Uses SQLite's own backup API rather than a file copy so the snapshot is
    consistent even if something else is mid-write. Returns the backup path, or
    ``None`` if there was nothing to back up.

    ``once_per_day`` skips the copy when today's backup already exists. Opening
    the app is the common case, and backing up on every launch would burn
    through the ten kept slots in an afternoon; one per day keeps ten days of
    history, which is what makes a backup worth having.
    """
    if not db_path.exists() or db_path.stat().st_size == 0:
        return None
    if once_per_day and _backed_up_today(db_path):
        return None

    target_dir = backup_dir(db_path)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = _next_backup_path(db_path, target_dir)

    source = sqlite3.connect(db_path, timeout=10.0)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    _rotate_backups(db_path, keep)
    return target


def list_backups(db_path: Path) -> list[Path]:
    """Existing backups for this database, newest first."""
    target_dir = backup_dir(db_path)
    if not target_dir.is_dir():
        return []
    pattern = f"{db_path.stem}_*{db_path.suffix or '.db'}"
    return sorted(target_dir.glob(pattern), reverse=True)


def _backed_up_today(db_path: Path) -> bool:
    stamp = datetime.now().strftime("%Y-%m-%d")
    return any(f"_{stamp}_" in backup.name for backup in list_backups(db_path))


def _next_backup_path(db_path: Path, target_dir: Path) -> Path:
    """A free filename for a new backup.

    Backups taken within the same second get a ``_02``, ``_03`` … suffix. The
    underscore sorts after the dot of the extension, so plain lexicographic
    ordering still puts the newest backup first.
    """
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    suffix = db_path.suffix or ".db"
    candidate = target_dir / f"{db_path.stem}_{stamp}{suffix}"

    sequence = 2
    while candidate.exists():
        candidate = target_dir / f"{db_path.stem}_{stamp}_{sequence:02d}{suffix}"
        sequence += 1
    return candidate


def _rotate_backups(db_path: Path, keep: int) -> None:
    for stale in list_backups(db_path)[keep:]:
        stale.unlink(missing_ok=True)


# --- Multi-machine guard ---------------------------------------------------


def lock_path(db_path: Path) -> Path:
    return db_path.with_name(db_path.name + LOCK_SUFFIX)


def read_lock(db_path: Path) -> str | None:
    """Return the owner of an existing lock, or ``None`` if there is nobody to warn about.

    This is advisory only. A synced folder gives no real locking, but a lock
    held by another machine is a strong hint that the same file is open twice,
    which is exactly the situation that corrupts data.

    A lock left behind by a crash on *this* machine is not a warning worth
    showing, so one whose process is gone is treated as stale.
    """
    path = lock_path(db_path)
    if not path.exists():
        return None
    try:
        owner = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None

    if owner == _lock_owner():
        return None

    host, _, pid = owner.rpartition(":")
    if host == socket.gethostname() and not _process_alive(pid):
        return None
    return owner


def _process_alive(pid: str) -> bool:
    try:
        os.kill(int(pid), 0)
    except (ValueError, ProcessLookupError):
        return False
    except PermissionError:
        # Running, just owned by somebody else.
        return True
    return True


def acquire_lock(db_path: Path) -> None:
    lock_path(db_path).write_text(_lock_owner(), encoding="utf-8")


def release_lock(db_path: Path) -> None:
    path = lock_path(db_path)
    if path.exists() and read_lock(db_path) is None:
        path.unlink(missing_ok=True)


def _lock_owner() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"
