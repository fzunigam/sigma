from pathlib import Path


def config_path() -> Path:
    return Path.home() / ".config" / "sgm" / "config.toml"


def save_config(display_name: str | None = None) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if display_name:
        lines.append(f'display_name = "{display_name}"')
    
    # Ensure file is written even if display_name is None
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

