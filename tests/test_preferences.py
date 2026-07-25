from __future__ import annotations

from pathlib import Path

import pytest

from sigma.db import preferences


def test_defaults_are_empty_on_a_new_database(db: Path):
    assert preferences.load_preferences(db) == {
        "default_expense_account": "",
        "default_income_account": "",
    }


def test_preferences_round_trip(db: Path):
    saved = preferences.save_preferences(db, {"default_expense_account": "wallet"})
    assert saved["default_expense_account"] == "wallet"
    assert saved["default_income_account"] == ""

    assert preferences.load_preferences(db)["default_expense_account"] == "wallet"


def test_saving_twice_overwrites(db: Path):
    preferences.save_preferences(db, {"default_income_account": "a"})
    preferences.save_preferences(db, {"default_income_account": "b"})
    assert preferences.load_preferences(db)["default_income_account"] == "b"


def test_unknown_keys_are_rejected(db: Path):
    with pytest.raises(ValueError, match="Preferencias desconocidas"):
        preferences.save_preferences(db, {"theme": "dark"})
