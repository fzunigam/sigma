from __future__ import annotations

import json
from pathlib import Path

import pytest

from sigma import settings


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SIGMA_SETTINGS_DIR", str(tmp_path / "config"))


def test_defaults_when_nothing_is_stored():
    assert settings.load_settings() == {
        "database_path": None,
        "recent": [],
        "theme": "dark",
    }
    assert settings.database_path() is None


def test_selecting_a_database_records_it_and_the_recents(tmp_path: Path):
    first = tmp_path / "uno.db"
    second = tmp_path / "dos.db"
    first.touch()
    second.touch()

    settings.set_database_path(first)
    settings.set_database_path(second)

    assert settings.database_path() == second.resolve()
    assert settings.recent_databases() == [second.resolve(), first.resolve()]


def test_reopening_a_database_moves_it_to_the_front(tmp_path: Path):
    first, second = tmp_path / "uno.db", tmp_path / "dos.db"
    first.touch()
    second.touch()

    settings.set_database_path(first)
    settings.set_database_path(second)
    settings.set_database_path(first)

    assert settings.recent_databases() == [first.resolve(), second.resolve()]


def test_recents_are_capped(tmp_path: Path):
    for index in range(settings.RECENT_LIMIT + 3):
        path = tmp_path / f"db{index}.db"
        path.touch()
        settings.set_database_path(path)

    assert len(settings.load_settings()["recent"]) == settings.RECENT_LIMIT


def test_recents_hide_files_that_no_longer_exist(tmp_path: Path):
    path = tmp_path / "borrada.db"
    path.touch()
    settings.set_database_path(path)
    path.unlink()

    assert settings.recent_databases() == []
    # The entry is still stored, so plugging the drive back in brings it back.
    assert settings.load_settings()["recent"] != []


def test_forgetting_a_database_clears_it_everywhere(tmp_path: Path):
    path = tmp_path / "uno.db"
    path.touch()
    settings.set_database_path(path)

    settings.forget_database(path)

    assert settings.database_path() is None
    assert settings.recent_databases() == []


def test_theme_round_trip():
    settings.set_theme("light")
    assert settings.load_settings()["theme"] == "light"
    with pytest.raises(ValueError):
        settings.set_theme("neon")


def test_a_corrupt_settings_file_falls_back_to_defaults():
    settings.save_settings(dict(settings.DEFAULT_SETTINGS))
    settings.settings_path().write_text("{ esto no es json", encoding="utf-8")

    assert settings.load_settings() == settings.DEFAULT_SETTINGS


def test_unknown_keys_in_the_settings_file_are_ignored():
    settings.settings_path().parent.mkdir(parents=True, exist_ok=True)
    settings.settings_path().write_text(
        json.dumps({"theme": "light", "algo_raro": 1}), encoding="utf-8"
    )

    loaded = settings.load_settings()
    assert loaded["theme"] == "light"
    assert "algo_raro" not in loaded


def test_legacy_preferences_are_mapped(tmp_path: Path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text('[defaults]\nincome_acc = "bci"\nexpense_acc = "wallet"\n')
    monkeypatch.setattr(settings, "LEGACY_CONFIG_PATH", config)

    assert settings.legacy_preferences() == {
        "default_expense_account": "wallet",
        "default_income_account": "bci",
    }


def test_legacy_preferences_tolerate_a_missing_or_broken_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "LEGACY_CONFIG_PATH", tmp_path / "no-existe.toml")
    assert settings.legacy_preferences() == {}

    broken = tmp_path / "roto.toml"
    broken.write_text("[defaults\nesto no es toml")
    monkeypatch.setattr(settings, "LEGACY_CONFIG_PATH", broken)
    assert settings.legacy_preferences() == {}
