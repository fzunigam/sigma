"""Per-database preferences, stored in the ``meta`` table.

These live inside the ``.db`` file rather than in the app's settings so that
moving or copying the database carries its configuration along with it.
"""

from __future__ import annotations

from pathlib import Path

from sigma.db.connection import connect, transaction

DEFAULTS = {
    "default_expense_account": "",
    "default_income_account": "",
}


def load_preferences(db_path: Path) -> dict[str, str]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT key, value FROM meta WHERE key IN (?, ?)", tuple(DEFAULTS)
        ).fetchall()
    stored = {row["key"]: row["value"] for row in rows}
    return {key: stored.get(key, fallback) for key, fallback in DEFAULTS.items()}


def save_preferences(db_path: Path, values: dict[str, str]) -> dict[str, str]:
    unknown = set(values) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"Preferencias desconocidas: {', '.join(sorted(unknown))}")
    with transaction(db_path) as conn:
        for key, value in values.items():
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
    return load_preferences(db_path)
