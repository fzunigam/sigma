import re
import subprocess
import sys

import click
import typer # type: ignore
from rich.console import Console # type: ignore
from rich.table import Table # type: ignore

from sgm import __version__
from sgm.infrastructure.database import clear_db, create_account, init_db, get_account, get_accounts, update_credit_limit, get_marked_total, create_movement
from sgm.infrastructure.user_config import is_configured, save_config
from sgm.interface.banner import print_help, print_sgm, print_startup_text

app = typer.Typer(
    help="Sigma CLI finance tracker",
    add_completion=False,
    add_help_option=False,
    rich_markup_mode=None
)

acc_app = typer.Typer(
    help="Account configuration",
    add_completion=False,
    add_help_option=False,
    rich_markup_mode=None
)
app.add_typer(acc_app, name="acc")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True),
) -> None:
    """Sigma CLI finance tracker."""
    if help:
        print_help()
        raise typer.Exit()
        
    if is_configured():
        init_db()
        
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


@app.command("status")
def status(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True)
) -> None:
    """Displays a rich table of balances, credit limits, and the current marked total."""
    if help:
        print(f"Usage: {ctx.command_path}")
        print(f"{ctx.command.help}")
        raise typer.Exit()
        
    console = Console()
    accounts = get_accounts()
    marked_total = get_marked_total()
    
    if not accounts:
        typer.echo("No accounts found. Use 'sgm acc add' to create one.")
        raise typer.Exit()
        
    table = Table(title="Account Status")
    table.add_column("Account", style="cyan bold")
    table.add_column("Type")
    table.add_column("Balance", justify="right")
    table.add_column("Available Credit", justify="right")
    
    for acc in accounts:
        avail_credit = ""
        if acc["type"] == "credit":
            avail = acc["credit_limit"] - acc["balance"]
            avail_credit = str(avail)
        table.add_row(
            acc["name"],
            acc["type"],
            str(acc["balance"]),
            avail_credit
        )
        
    console.print(table)
    console.print()
    console.print(f"Marked total for next render: [bold {'green' if marked_total >= 0 else 'red'}]{marked_total}[/]")


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


def _resolve_account(acc_id: str | None) -> str:
    if acc_id is not None:
        return acc_id
    accounts = get_accounts()
    if not accounts:
        typer.echo("Error: No accounts exist. Use 'sgm acc add' first.", err=True)
        raise typer.Exit(1)
    if len(accounts) == 1:
        return accounts[0]["id"]
    
    typer.echo("Error: Multiple accounts exist. You must specify the account ID.", err=True)
    raise typer.Exit(1)


def exp_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} <amount> <desc> <mark> [acc_id]")
        print("Records an expense. The <mark> choice (yes/no) flags the item for the next render.")
        raise typer.Exit()

@app.command("exp")
def exp(
    ctx: typer.Context,
    amount: int = typer.Argument(..., help="Amount of the expense (CLP)"),
    desc: str = typer.Argument(..., help="Description of the expense"),
    mark: str = typer.Argument(..., help="Flag for next render ('yes' or 'no')", click_type=click.Choice(["yes", "no"])),
    acc_id: str | None = typer.Argument(None, help="Account ID (optional if only 1 account exists)"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=exp_help_callback)
) -> None:
    """Records an expense."""
    if amount <= 0:
        typer.echo("Error: Amount must be positive.", err=True)
        raise typer.Exit(1)
        
    resolved_acc_id = _resolve_account(acc_id)
    marked = mark == "yes"
    
    try:
        create_movement(amount, desc, resolved_acc_id, "expense", marked)
        typer.echo(f"Recorded expense of {amount} ('{desc}') in '{resolved_acc_id}'.")
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def inc_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} <amount> <desc> <mark> [acc_id]")
        print("Records an income. The <mark> choice (yes/no) flags the item for the next render.")
        raise typer.Exit()

@app.command("inc")
def inc(
    ctx: typer.Context,
    amount: int = typer.Argument(..., help="Amount of the income (CLP)"),
    desc: str = typer.Argument(..., help="Description of the income"),
    mark: str = typer.Argument(..., help="Flag for next render ('yes' or 'no')", click_type=click.Choice(["yes", "no"])),
    acc_id: str | None = typer.Argument(None, help="Account ID (optional if only 1 account exists)"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=inc_help_callback)
) -> None:
    """Records an income."""
    if amount <= 0:
        typer.echo("Error: Amount must be positive.", err=True)
        raise typer.Exit(1)
        
    resolved_acc_id = _resolve_account(acc_id)
    marked = mark == "yes"
    
    try:
        create_movement(amount, desc, resolved_acc_id, "income", marked)
        typer.echo(f"Recorded income of {amount} ('{desc}') in '{resolved_acc_id}'.")
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


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


def acc_add_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} <id> <name> <type> <bal>")
        print("Adds a new account with an initial balance.")
        raise typer.Exit()

@acc_app.command("add")
def acc_add(
    ctx: typer.Context,
    id: str = typer.Argument(..., help="Unique identifier for the account"),
    name: str = typer.Argument(..., help="Display name for the account"),
    type: str = typer.Argument(..., help="Account type ('debit' or 'credit')", click_type=click.Choice(["debit", "credit"])),
    bal: int = typer.Argument(..., help="Initial balance (CLP)"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=acc_add_help_callback)
) -> None:
    """Adds a new account with an initial balance."""
    try:
        create_account(id, name, type, bal)
        typer.echo(f"Account '{name}' created successfully!")
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def acc_list_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} [acc_id]")
        print("Detailed view of account metadata. Lists all accounts if [acc_id] is omitted.")
        raise typer.Exit()

@acc_app.command("list")
def acc_list(
    ctx: typer.Context,
    acc_id: str | None = typer.Argument(None, help="Unique identifier for the account"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=acc_list_help_callback)
) -> None:
    """Detailed view of account metadata. Lists all accounts if [acc_id] is omitted."""
    console = Console()
    
    if acc_id:
        acc = get_account(acc_id)
        if not acc:
            typer.echo(f"Error: Account with ID '{acc_id}' not found.", err=True)
            raise typer.Exit(1)
        
        table = Table(title=f"Account Details: {acc_id}")
        table.add_column("Property", style="cyan bold")
        table.add_column("Value")
        for key, value in acc.items():
            table.add_row(key, str(value))
        console.print(table)
    else:
        accounts = get_accounts()
        if not accounts:
            typer.echo("No accounts found. Use 'sgm acc add' to create one.")
            raise typer.Exit()
            
        table = Table(title="All Accounts")
        table.add_column("ID", style="cyan bold")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Balance", justify="right")
        table.add_column("Credit Limit", justify="right")
        
        for acc in accounts:
            table.add_row(
                acc["id"],
                acc["name"],
                acc["type"],
                str(acc["balance"]),
                str(acc["credit_limit"])
            )
        console.print(table)


def acc_set_limit_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} <acc_id> <limit>")
        print("Updates the rolling credit limit (Credit accounts only).")
        raise typer.Exit()

@acc_app.command("set-limit")
def acc_set_limit(
    ctx: typer.Context,
    acc_id: str = typer.Argument(..., help="Unique identifier for the account"),
    limit: int = typer.Argument(..., help="New credit limit (CLP)"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=acc_set_limit_help_callback)
) -> None:
    """Updates the rolling credit limit (Credit accounts only)."""
    acc = get_account(acc_id)
    if not acc:
        typer.echo(f"Error: Account with ID '{acc_id}' not found.", err=True)
        raise typer.Exit(1)
        
    if acc["type"] != "credit":
        typer.echo(f"Error: Account '{acc_id}' is a debit account. Only credit accounts can have a credit limit.", err=True)
        raise typer.Exit(1)
        
    update_credit_limit(acc_id, limit)
    typer.echo(f"Credit limit for '{acc_id}' updated to {limit} successfully!")