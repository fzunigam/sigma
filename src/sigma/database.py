"""Lifecycle of the database *file*: choose, create, open, migrate and restore.

Everything the user does with the file itself goes through here, so the rules
around synced folders (dated backups, advisory locking, refusing to overwrite
data) are applied in exactly one place.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from sigma import settings
from sigma.db import connection, schema
from sigma.db.errors import DatabaseFileError

SUFFIX = ".db"


def current() -> Path | None:
    """The database in use, or ``None`` if none is selected or the file is gone."""
    path = settings.database_path()
    if path is None or not path.exists():
        return None
    return path


def require_current() -> Path:
    path = current()
    if path is None:
        raise DatabaseFileError(
            "No hay una base de datos abierta. Elige o crea un archivo para empezar."
        )
    return path


def status() -> dict[str, Any]:
    """Everything the interface needs to decide between setup and normal use."""
    path = settings.database_path()
    active = current()
    legacy = settings.legacy_database()

    return {
        "path": str(path) if path else None,
        "name": path.stem if path else None,
        "folder": str(path.parent) if path else None,
        "is_open": active is not None,
        "missing": path is not None and active is None,
        "locked_by": connection.read_lock(active) if active else None,
        "recent": [
            {"path": str(item), "name": item.stem} for item in settings.recent_databases()
        ],
        "backups": [
            {"path": str(item), "name": item.name, "size": item.stat().st_size}
            for item in connection.list_backups(active)
        ]
        if active
        else [],
        "legacy_available": str(legacy) if legacy else None,
        "theme": settings.load_settings()["theme"],
    }


def create(path: Path) -> Path:
    """Create a new, empty database and make it the current one."""
    path = _normalise(path)
    try:
        schema.create_database(path)
    except FileExistsError as exc:
        raise DatabaseFileError(str(exc)) from exc
    except OSError as exc:
        raise DatabaseFileError(f"No se pudo crear el archivo: {exc}") from exc

    settings.set_database_path(path)
    connection.acquire_lock(path)
    return path


def open_existing(path: Path) -> Path:
    """Open an existing Sigma database, backing it up first."""
    path = _normalise(path)
    if not path.exists():
        raise DatabaseFileError(f"El archivo {path} no existe.")
    if schema.is_legacy_database(path):
        raise DatabaseFileError(
            "Ese archivo es de una versión anterior de Sigma. "
            "Usa la opción de migrar para convertirlo."
        )
    if not schema.is_sigma_database(path):
        raise DatabaseFileError("Ese archivo no es una base de datos de Sigma.")

    previous = current()
    if previous and previous != path:
        connection.release_lock(previous)

    connection.create_backup(path)
    settings.set_database_path(path)
    connection.acquire_lock(path)
    return path


def migrate_legacy(target: Path, source: Path | None = None) -> dict[str, Any]:
    """Convert the pre-1.0 database into a new file and open it.

    The original is left untouched, so a failed migration costs nothing.
    """
    source = source or settings.legacy_database()
    if source is None:
        raise DatabaseFileError("No se encontró una base de datos de la versión anterior.")

    target = _normalise(target)
    try:
        counts = schema.migrate_legacy_database(
            source, target, defaults=settings.legacy_preferences()
        )
    except FileExistsError as exc:
        raise DatabaseFileError(str(exc)) from exc
    except ValueError as exc:
        raise DatabaseFileError(str(exc)) from exc

    settings.set_database_path(target)
    connection.acquire_lock(target)
    return {"path": str(target), "migrated": counts}


def restore_backup(backup: Path) -> Path:
    """Replace the current database with one of its backups.

    The database being replaced is itself backed up first, so a restore can be
    undone by restoring the snapshot taken at this moment.
    """
    path = require_current()
    backup = Path(backup).expanduser()
    if backup not in connection.list_backups(path):
        raise DatabaseFileError("Ese respaldo no pertenece a la base de datos actual.")

    connection.create_backup(path)
    shutil.copyfile(backup, path)
    return path


def close() -> None:
    """Release the advisory lock. Called when the app window closes."""
    path = current()
    if path:
        connection.release_lock(path)


def _normalise(path: Path | str) -> Path:
    path = Path(path).expanduser()
    if not path.suffix:
        path = path.with_suffix(SUFFIX)
    return path
