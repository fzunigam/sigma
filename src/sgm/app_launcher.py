import os
import sys

# Ensure src/ is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sgm.cli import app_cmd
import typer

if __name__ == "__main__":
    # Simulate invoking the app command directly
    app_cmd(ctx=typer.Context(typer.Typer()))
