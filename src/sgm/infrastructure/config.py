from pathlib import Path


def default_db_path() -> Path:
    return Path.home() / ".local" / "share" / "sgm" / "sigma.db"
