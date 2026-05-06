import re
import subprocess
import sys

import typer # type: ignore

from sgm import __version__
from sgm.infrastructure.user_config import save_config
from sgm.interface.banner import print_help, print_sgm, print_startup_text

app = typer.Typer(
    help="Sigma CLI finance tracker",
    add_completion=False,
    add_help_option=False,
    rich_markup_mode=None
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True),
) -> None:
    """Sigma CLI finance tracker."""
    if help:
        print_help()
        raise typer.Exit()
        
    if ctx.invoked_subcommand is None:
        print_sgm()


@app.command("start")
def start(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True)
) -> None:
    """First-run setup and preferences."""
    if help:
        print(f"Usage: {ctx.command_path}")
        print(f"{ctx.command.help}")
        raise typer.Exit()
        
    print_startup_text()
    save_config()
    typer.echo("Configuration saved. Ready to use Sigma!")


@app.command("version")
def version() -> None:
    """Show the version and exit."""
    typer.echo(f"sgm version v{__version__}")


@app.command("update")
def update(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True)
) -> None:
    """Update sgm to the latest version."""
    if help:
        print(f"Usage: {ctx.command_path}")
        print(f"{ctx.command.help}")
        raise typer.Exit()
    
    print("Checking for updates...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "sigma-finance"],
            capture_output=True,
            text=True,
            check=True
        )
        if "Requirement already satisfied" in result.stdout and "sigma-finance" in result.stdout and "Successfully installed" not in result.stdout:
            typer.echo(f"sgm is already at the latest version (v{__version__}).")
        else:
            match = re.search(r"sigma-finance-([\w\.-]+)", result.stdout)
            if match:
                typer.echo(f"Update complete! New version: v{match.group(1)}")
            else:
                typer.echo("Update complete!")
    except subprocess.CalledProcessError as e:
        typer.echo("Failed to update sgm. Please try running 'pip install --upgrade sigma-finance' manually.", err=True)
        if e.stderr:
            typer.echo(e.stderr, err=True)
        raise typer.Exit(1)