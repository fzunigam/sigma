import re
import subprocess
import sys

import click
import typer # type: ignore

from sgm import __version__
from sgm.infrastructure.database import clear_db, create_account, init_db
from sgm.infrastructure.user_config import is_configured, save_config
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
        
    if is_configured():
        typer.echo("Sigma is already configured. If you want to change something, you can visit 'sgm config'.")
        raise typer.Exit()
        
    print_startup_text()
    
    init_db()
    typer.echo("Database initialized.")
    
    typer.echo("\nLet's create your first account.")
    acc_id = typer.prompt("Account ID (e.g. 'wallet', 'cc')")
    acc_name = typer.prompt("Account Name (e.g. 'Cash', 'Credit Card')")
    acc_type = typer.prompt("Account Type ('debit' or 'credit')", type=click.Choice(["debit", "credit"]))
    
    acc_balance = typer.prompt("Initial Balance (CLP)", type=int)
    
    acc_limit = 0
    if acc_type == "credit":
        acc_limit = typer.prompt("Credit Limit (CLP)", type=int, default=0)
        
    try:
        create_account(acc_id, acc_name, acc_type, acc_balance, acc_limit)
        typer.echo(f"Account '{acc_name}' created successfully!")
        typer.echo("Configuration saved. Ready to use Sigma!")
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
    
    save_config()


@app.command("restore")
def restore(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True)
) -> None:
    """Delete all data and leave the database empty."""
    if help:
        print(f"Usage: {ctx.command_path}")
        print(f"{ctx.command.help}")
        raise typer.Exit()
        
    typer.echo("WARNING: This will delete ALL accounts, movements, transfers, and history.", err=True)
    typer.echo("This action CANNOT be undone.", err=True)
    
    try:
        confirmation = typer.prompt("Type 'RESTORE' to confirm deletion (or press Ctrl+C to cancel)")
        if confirmation != "RESTORE":
            typer.echo("Restore cancelled.")
            raise typer.Exit()
    except typer.Abort:
        typer.echo("\nRestore cancelled.")
        raise typer.Exit()
        
    clear_db()
    typer.echo("Database restored. All data has been deleted.")


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