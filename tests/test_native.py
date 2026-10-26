import json
import re
from pathlib import Path

from sigma import native

COMMANDS = Path(__file__).parents[1] / "web" / "src" / "lib" / "commands.ts"


def test_menu_commands_exist_in_the_page():
    """Every menu item must send a command the page knows how to run."""
    source = COMMANDS.read_text()
    known = set(re.findall(r"\|\s*'([a-z:]+)'", source))
    sent = {item[1] for _, items in native.MENUS for item in items if item is not None}
    assert sent <= known


def test_dispatch_quotes_the_command():
    script = native._dispatch("go:resumen")
    assert "sigma:command" in script
    assert json.dumps("go:resumen") in script


def test_menu_shortcuts_do_not_collide():
    keys = [item[2] for _, items in native.MENUS for item in items if item is not None]
    assert len(keys) == len(set(keys))
