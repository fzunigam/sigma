from pathlib import Path

from sgm.infrastructure.config import default_db_path


def test_default_db_path_has_expected_shape() -> None:
    path = default_db_path()

    assert path == Path.home() / ".local" / "share" / "sgm" / "sigma.db"
    assert path.parts[-4:] == (".local", "share", "sgm", "sigma.db")


def test_default_db_path_respects_custom_home(monkeypatch, tmp_path: Path) -> None:
    custom_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(custom_home))

    assert default_db_path() == custom_home / ".local" / "share" / "sgm" / "sigma.db"
