try:
    import tomllib
except ImportError:
    import tomli as tomllib
from pathlib import Path
from typing import Any


def config_path() -> Path:
    return Path.home() / ".config" / "sgm" / "config.toml"


def is_configured() -> bool:
    return config_path().exists()

def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")
    try:
        return tomllib.loads(content)
    except Exception:
        return {}

def save_config(config_data: dict[str, Any] | None = None) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if config_data is None:
        if not path.exists():
            path.write_text("\n", encoding="utf-8")
        return
        
    lines = []
    if "defaults" in config_data:
        lines.append("[defaults]")
        for k, v in config_data["defaults"].items():
            if isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            else:
                lines.append(f'{k} = {v}')
        lines.append("")
                
    if "telegram" in config_data:
        lines.append("[telegram]")
        for k, v in config_data["telegram"].items():
            if isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            elif isinstance(v, list):
                list_str = ", ".join(f'"{item}"' if isinstance(item, str) else str(item) for item in v)
                lines.append(f'{k} = [{list_str}]')
            else:
                lines.append(f'{k} = {v}')
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


