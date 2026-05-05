from pathlib import Path

from sgm.infrastructure.config import default_db_path


def test_default_db_path_uses_home_local_share(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert default_db_path() == tmp_path / ".local" / "share" / "sgm" / "sigma.db"
