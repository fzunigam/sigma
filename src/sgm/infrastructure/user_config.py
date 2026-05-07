from pathlib import Path


def config_path() -> Path:
    return Path.home() / ".config" / "sgm" / "config.toml"


def is_configured() -> bool:
    return config_path().exists()

def save_config() -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure file is written
    path.write_text("\n", encoding="utf-8")

