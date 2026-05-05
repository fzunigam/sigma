from pathlib import Path

from sgm.infrastructure.user_config import config_path, save_config


def test_config_path_uses_home_config_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert config_path() == tmp_path / ".config" / "sgm" / "config.toml"


def test_save_config_creates_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    save_config(theme="blue", display_name="Fran")

    content = config_path().read_text(encoding="utf-8")
    assert 'theme = "blue"' in content
    assert 'display_name = "Fran"' in content
