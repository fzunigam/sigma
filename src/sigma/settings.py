"""Application settings: which database file to open, and how the app looks.

These are *app*-level settings and stay on this machine. Anything that belongs
to the data itself (such as the default accounts) lives inside the ``.db`` file,
so copying the database to another computer carries its configuration along.

``SIGMA_SETTINGS_DIR`` overrides the location, which the tests rely on.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

RECENT_LIMIT = 5

DEFAULT_SETTINGS: dict[str, Any] = {
    "database_path": None,
    "recent": [],
    "theme": "dark",
}

# Where pre-1.0 Sigma kept its data. Used to offer a migration on first run.
LEGACY_DATABASE_PATH = Path.home() / ".local" / "share" / "sgm" / "sigma.db"
LEGACY_CONFIG_PATH = Path.home() / ".config" / "sgm" / "config.toml"


def settings_dir() -> Path:
    override = os.environ.get("SIGMA_SETTINGS_DIR")
    if override:
        return Path(override)
    return Path.home() / "Library" / "Application Support" / "Sigma"


def settings_path() -> Path:
    return settings_dir() / "settings.json"


def load_settings() -> dict[str, Any]:
    path = settings_path()
    settings = dict(DEFAULT_SETTINGS)
    if path.exists():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # A corrupt settings file must never stop the app from starting:
            # the worst case is being asked to pick the database again.
            return settings
        if isinstance(stored, dict):
            settings.update({k: v for k, v in stored.items() if k in DEFAULT_SETTINGS})
    return settings


def save_settings(settings: dict[str, Any]) -> dict[str, Any]:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    return settings


def database_path() -> Path | None:
    """The database currently in use, or ``None`` if none has been chosen yet."""
    stored = load_settings()["database_path"]
    return Path(stored) if stored else None


def set_database_path(path: Path) -> dict[str, Any]:
    """Record ``path`` as the current database and push it onto the recents."""
    resolved = str(Path(path).expanduser().resolve())
    settings = load_settings()
    recent = [resolved] + [item for item in settings["recent"] if item != resolved]
    settings["database_path"] = resolved
    settings["recent"] = recent[:RECENT_LIMIT]
    return save_settings(settings)


def forget_database(path: Path) -> dict[str, Any]:
    """Drop a database from the recents, and from the current slot if it is there."""
    resolved = str(Path(path).expanduser().resolve())
    settings = load_settings()
    settings["recent"] = [item for item in settings["recent"] if item != resolved]
    if settings["database_path"] == resolved:
        settings["database_path"] = None
    return save_settings(settings)


def recent_databases() -> list[Path]:
    """Recently opened databases that still exist on disk."""
    return [Path(item) for item in load_settings()["recent"] if Path(item).exists()]


def set_theme(theme: str) -> dict[str, Any]:
    if theme not in ("dark", "light"):
        raise ValueError("El tema debe ser 'dark' o 'light'.")
    settings = load_settings()
    settings["theme"] = theme
    return save_settings(settings)


# --- Pre-1.0 leftovers -----------------------------------------------------


def legacy_database() -> Path | None:
    """The pre-1.0 database, if one is still sitting in the old location."""
    return LEGACY_DATABASE_PATH if LEGACY_DATABASE_PATH.exists() else None


def legacy_preferences() -> dict[str, str]:
    """Default accounts from the old ``config.toml``, in the new key names."""
    if not LEGACY_CONFIG_PATH.exists():
        return {}
    try:
        import tomllib

        config = tomllib.loads(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    defaults = config.get("defaults", {})
    mapped = {
        "default_expense_account": defaults.get("expense_acc", ""),
        "default_income_account": defaults.get("income_acc", ""),
    }
    return {key: value for key, value in mapped.items() if value}
