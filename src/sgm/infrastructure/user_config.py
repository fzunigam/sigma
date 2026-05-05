from pathlib import Path


def config_path() -> Path:
    return Path.home() / ".config" / "sgm" / "config.toml"


def save_config(theme: str, display_name: str | None = None) -> None:
    if not theme.strip():
        raise ValueError("theme cannot be empty")

    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'theme = "{theme.strip()}"']
    if display_name:
        lines.append(f'display_name = "{display_name}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
