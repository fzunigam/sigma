import csv
import re
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import click # type: ignore
import typer # type: ignore
from rich.console import Console # type: ignore
from rich.table import Table # type: ignore

from sgm import __version__
from sgm.infrastructure.database import create_account, init_db, get_account, get_accounts, update_credit_limit, get_marked_total, create_movement, create_transfer, rename_account, get_recent_logs, execute_render, get_render_history, delete_record, delete_account, get_all_table_data, import_from_csvs, get_db_path
from sgm.infrastructure.user_config import is_configured, save_config, load_config, config_path
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

bot_app = typer.Typer(
    help="Telegram Bot configuration and control",
    add_completion=False,
    add_help_option=False,
    rich_markup_mode=None
)
app.add_typer(bot_app, name="bot")



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
    
    do_import = typer.confirm("\nDo you want to import existing data from a ZIP or folder?", default=False)
    
    if do_import:
        import_path_str = typer.prompt("Path to ZIP file or folder containing CSVs")
        import_path = Path(import_path_str).expanduser().resolve()
        
        try:
            import_from_csvs(import_path)
            typer.echo("Data imported successfully!")
            save_config()
            typer.echo("Configuration saved. Ready to use Sigma!")
            raise typer.Exit()
        except (ValueError, FileNotFoundError, sqlite3.Error) as e:
            typer.echo(f"Import failed: {e}", err=True)
            typer.echo("Falling back to manual account creation.")
    
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
    """Delete all data and configuration, resetting Sigma to its first-run state."""
    if help:
        print(f"Usage: {ctx.command_path}")
        print(f"{ctx.command.help}")
        raise typer.Exit()
        
    typer.echo("WARNING: This will delete ALL data (accounts, movements, transfers) and your configuration.", err=True)
    typer.echo("This will reset Sigma to its first-run state.", err=True)
    typer.echo("This action CANNOT be undone.", err=True)
    
    try:
        confirmation = typer.prompt("Type 'RESTORE' to confirm deletion (or press Ctrl+C to cancel)")
        if confirmation != "RESTORE":
            typer.echo("Restore cancelled.")
            raise typer.Exit()
    except typer.Abort:
        typer.echo("\nRestore cancelled.")
        raise typer.Exit()
        
    # Delete database file
    db_path = get_db_path()
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception as e:
            typer.echo(f"Error deleting database: {e}", err=True)
            
    # Delete configuration file
    cfg_path = config_path()
    if cfg_path.exists():
        try:
            cfg_path.unlink()
        except Exception as e:
            typer.echo(f"Error deleting configuration: {e}", err=True)

    typer.echo("Sigma has been reset. All database files and configurations have been deleted.")
    typer.echo("You can now run 'sgm start' to set up Sigma again.")


@app.command("version")
def version() -> None:
    """Show the version and exit."""
    typer.echo(f"sgm version v{__version__}")


def config_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path}")
        print("Opens the sgm global settings (default accounts).")
        raise typer.Exit()

def mask_token(token: str) -> str:
    """Mask Telegram bot token for secure display."""
    if not token:
        return "Not configured"
    if len(token) <= 10:
        return "****"
    return f"{token[:6]}...{token[-4:]}"


def format_allowed_users(users: list) -> str:
    """Format the list of allowed Telegram user IDs."""
    if not users:
        return "None (bot ignores messages)"
    return ", ".join(map(str, users))


def get_key() -> str:
    """Reads a single key or escape sequence from standard input on Unix/Mac."""
    import os
    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1)
        if ch == b'\x1b':
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                ch2 = os.read(fd, 1)
                if ch2 == b'[':
                    r, _, _ = select.select([fd], [], [], 0.05)
                    if r:
                        ch3 = os.read(fd, 1)
                        if ch3 == b'A':
                            return "up"
                        elif ch3 == b'B':
                            return "down"
                        elif ch3 == b'C':
                            return "right"
                        elif ch3 == b'D':
                            return "left"
                        return f"esc[{ch3.decode('utf-8', errors='ignore')}"
                    return "esc["
                return f"esc{ch2.decode('utf-8', errors='ignore')}"
            return "escape"
        elif ch in (b'\r', b'\n'):
            return "enter"
        elif ch in (b'\x7f', b'\x08'):
            return "backspace"
        elif ch == b'\x03':  # Ctrl+C
            raise KeyboardInterrupt
        try:
            return ch.decode('utf-8')
        except UnicodeDecodeError:
            return ch.decode('utf-8', errors='ignore')
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def interactive_input(prompt: str, default: str = "") -> str | None:
    """Reads line input from terminal with inline editing and Esc-to-cancel support."""
    sys.stdout.write(prompt)
    sys.stdout.flush()

    current = list(default)
    pos = len(current)

    sys.stdout.write("".join(current))
    sys.stdout.flush()

    while True:
        try:
            key = get_key()
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            sys.stdout.flush()
            raise KeyboardInterrupt

        if key == "enter":
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(current)
        elif key in ("escape", "q"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            return None
        elif key == "backspace":
            if pos > 0:
                current.pop(pos - 1)
                pos -= 1
        elif key == "left":
            if pos > 0:
                pos -= 1
        elif key == "right":
            if pos < len(current):
                pos += 1
        elif len(key) == 1 and key.isprintable() and key != '\t':
            current.insert(pos, key)
            pos += 1

        # Redraw
        sys.stdout.write("\r\x1b[K")
        sys.stdout.write(prompt + "".join(current))
        offset = len(current) - pos
        if offset > 0:
            sys.stdout.write(f"\x1b[{offset}D")
        sys.stdout.flush()


def draw_menu(options: list[str], selected_idx: int, header: str = "") -> int:
    """Draw menu options, highlighting the selected index in cyan. Returns line count."""
    lines = 0
    if header:
        print(header)
        lines += len(header.splitlines()) + 1

    for i, opt in enumerate(options):
        if i == selected_idx:
            print(f"  > \x1b[1;36m{opt}\x1b[0m")
        else:
            print(f"    {opt}")
        lines += 1
    return lines


def clear_printed_lines(count: int) -> None:
    """Clear count lines up from the current cursor position."""
    if count > 0:
        sys.stdout.write(f"\x1b[{count}A\r\x1b[J")
        sys.stdout.flush()


def run_interactive_menu(options: list[str], header: str, initial_idx: int = 0) -> int | None:
    """Runs interactive menu loop and returns the selected index or None."""
    selected_idx = initial_idx
    count = 0
    while True:
        count = draw_menu(options, selected_idx, header)
        try:
            key = get_key()
        except KeyboardInterrupt:
            clear_printed_lines(count)
            raise KeyboardInterrupt

        clear_printed_lines(count)

        if key == "up":
            selected_idx = (selected_idx - 1) % len(options)
        elif key == "down":
            selected_idx = (selected_idx + 1) % len(options)
        elif key == "enter":
            return selected_idx
        elif key in ("escape", "q"):
            return None


@app.command("config")
def config_cmd(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=config_help_callback)
) -> None:
    """Opens the sgm global settings configuration wizard."""
    config_data = load_config()
    defaults = config_data.get("defaults", {})
    telegram_cfg = config_data.get("telegram", {})

    current_inc = defaults.get("income_acc", "")
    current_exp = defaults.get("expense_acc", "")
    current_token = telegram_cfg.get("token", "")
    current_users = telegram_cfg.get("allowed_users", [])

    # Check if we are running in an interactive terminal
    if not sys.stdin.isatty():
        # Fallback sequential prompt mode for scripting and automated tests
        typer.echo("Configure default accounts.")
        inc_acc = typer.prompt("Default Income Account ID", default=current_inc, type=str)
        if inc_acc and not get_account(inc_acc):
            typer.echo(f"Warning: Account '{inc_acc}' not found. Default not set.", err=True)
            inc_acc = current_inc

        exp_acc = typer.prompt("Default Expense Account ID", default=current_exp, type=str)
        if exp_acc and not get_account(exp_acc):
            typer.echo(f"Warning: Account '{exp_acc}' not found. Default not set.", err=True)
            exp_acc = current_exp

        if "defaults" not in config_data:
            config_data["defaults"] = {}

        config_data["defaults"]["income_acc"] = inc_acc
        config_data["defaults"]["expense_acc"] = exp_acc
        save_config(config_data)
        typer.echo("Configuration saved successfully.")
        return

    main_header = (
        "\n\x1b[1;36m--- Sigma Configuration ---\x1b[0m\n"
        "Use Up/Down arrows to navigate, Enter to select, Esc/Q to exit.\n"
    )

    selected_main_idx = 0
    while True:
        # Construct updated menu options dynamically
        menu_options = [
            f"Default Income Account  (Current: \x1b[36m{current_inc or 'Not set'}\x1b[0m)",
            f"Default Expense Account (Current: \x1b[36m{current_exp or 'Not set'}\x1b[0m)",
            f"Telegram Bot Token      (Current: \x1b[36m{mask_token(current_token)}\x1b[0m)",
            f"Telegram Allowed Users  (Current: \x1b[36m{format_allowed_users(current_users)}\x1b[0m)",
        ]

        choice = run_interactive_menu(menu_options, main_header, initial_idx=selected_main_idx)
        if choice is None:
            # Exited main menu
            print("\x1b[1;32m✓ Configuration saved and closed.\x1b[0m")
            break

        selected_main_idx = choice

        if choice == 0:
            accounts = get_accounts()
            if not accounts:
                print("\n\x1b[1;31mError: No accounts found. Use 'sgm acc add' to create one first.\x1b[0m")
                print("Press any key to return...")
                get_key()
                sys.stdout.write("\x1b[3A\r\x1b[J")
                sys.stdout.flush()
                continue

            acc_options = [f"{acc['id']} ({acc['name']})" for acc in accounts] + ["(Clear Default)"]
            sub_header = (
                "\n\x1b[1;36m--- Select Default Income Account ---\x1b[0m\n"
                "Use Up/Down arrows to navigate, Enter to select, Esc/Q to cancel.\n"
            )

            sub_idx = 0
            for i, acc in enumerate(accounts):
                if acc['id'] == current_inc:
                    sub_idx = i
                    break
            if current_inc == "":
                sub_idx = len(accounts)

            sel = run_interactive_menu(acc_options, sub_header, initial_idx=sub_idx)
            if sel is not None:
                if sel == len(accounts):
                    current_inc = ""
                else:
                    current_inc = accounts[sel]['id']

                if "defaults" not in config_data:
                    config_data["defaults"] = {}
                config_data["defaults"]["income_acc"] = current_inc
                save_config(config_data)

                success_msg = f"\n\x1b[1;32m✓ Default Income Account updated to '{current_inc or 'None'}'\x1b[0m\n"
                print(success_msg)
                import time
                time.sleep(0.8)
                sys.stdout.write("\x1b[3A\r\x1b[J")
                sys.stdout.flush()

        elif choice == 1:
            accounts = get_accounts()
            if not accounts:
                print("\n\x1b[1;31mError: No accounts found. Use 'sgm acc add' to create one first.\x1b[0m")
                print("Press any key to return...")
                get_key()
                sys.stdout.write("\x1b[3A\r\x1b[J")
                sys.stdout.flush()
                continue

            acc_options = [f"{acc['id']} ({acc['name']})" for acc in accounts] + ["(Clear Default)"]
            sub_header = (
                "\n\x1b[1;36m--- Select Default Expense Account ---\x1b[0m\n"
                "Use Up/Down arrows to navigate, Enter to select, Esc/Q to cancel.\n"
            )

            sub_idx = 0
            for i, acc in enumerate(accounts):
                if acc['id'] == current_exp:
                    sub_idx = i
                    break
            if current_exp == "":
                sub_idx = len(accounts)

            sel = run_interactive_menu(acc_options, sub_header, initial_idx=sub_idx)
            if sel is not None:
                if sel == len(accounts):
                    current_exp = ""
                else:
                    current_exp = accounts[sel]['id']

                if "defaults" not in config_data:
                    config_data["defaults"] = {}
                config_data["defaults"]["expense_acc"] = current_exp
                save_config(config_data)

                success_msg = f"\n\x1b[1;32m✓ Default Expense Account updated to '{current_exp or 'None'}'\x1b[0m\n"
                print(success_msg)
                import time
                time.sleep(0.8)
                sys.stdout.write("\x1b[3A\r\x1b[J")
                sys.stdout.flush()

        elif choice == 2:
            print("\n\x1b[1;36m--- Configure Telegram Bot Token ---\x1b[0m")
            print(f"Current token: \x1b[36m{mask_token(current_token)}\x1b[0m")
            print("Enter new token (leave empty and press Enter to clear, Esc/Q to cancel):")

            prompt_str = "\x1b[1;36mToken > \x1b[0m"
            new_token = interactive_input(prompt_str, default=current_token)

            if new_token is not None:
                current_token = new_token.strip()
                if "telegram" not in config_data:
                    config_data["telegram"] = {}
                config_data["telegram"]["token"] = current_token
                save_config(config_data)

                success_msg = "\n\x1b[1;32m✓ Telegram Bot Token updated.\x1b[0m\n"
                print(success_msg)
                import time
                time.sleep(0.8)
                sys.stdout.write("\x1b[8A\r\x1b[J")
                sys.stdout.flush()
            else:
                sys.stdout.write("\x1b[5A\r\x1b[J")
                sys.stdout.flush()

        elif choice == 3:
            sub_idx = 0
            while True:
                user_list_str = format_allowed_users(current_users)
                sub_header = (
                    f"\n\x1b[1;36m--- Telegram Allowed Users ---\x1b[0m\n"
                    f"Current allowed IDs: \x1b[36m{user_list_str}\x1b[0m\n"
                    f"Use Up/Down arrows to navigate, Enter to select, Esc/Q to return.\n"
                )
                sub_options = [
                    "Add User ID",
                    "Remove User ID",
                    "Back to Main Menu"
                ]

                sub_choice = run_interactive_menu(sub_options, sub_header, initial_idx=sub_idx)
                if sub_choice is None or sub_choice == 2:
                    break

                sub_idx = sub_choice

                if sub_choice == 0:
                    print("\n\x1b[1;36m--- Add Allowed Telegram User ID ---\x1b[0m")
                    print("Enter Telegram User ID (numbers only, Esc/Q to cancel):")

                    prompt_str = "\x1b[1;36mUser ID > \x1b[0m"
                    new_uid_str = interactive_input(prompt_str, default="")
                    if new_uid_str is not None:
                        new_uid_str = new_uid_str.strip()
                        if not new_uid_str:
                            sys.stdout.write("\x1b[4A\r\x1b[J")
                            sys.stdout.flush()
                            continue

                        try:
                            uid = int(new_uid_str)
                            if uid in current_users:
                                print("\n\x1b[1;33mWarning: User ID already allowed.\x1b[0m\n")
                                import time
                                time.sleep(1.0)
                                sys.stdout.write("\x1b[7A\r\x1b[J")
                                sys.stdout.flush()
                            else:
                                current_users.append(uid)
                                if "telegram" not in config_data:
                                    config_data["telegram"] = {}
                                config_data["telegram"]["allowed_users"] = current_users
                                save_config(config_data)

                                print(f"\n\x1b[1;32m✓ User ID {uid} added.\x1b[0m\n")
                                import time
                                time.sleep(0.8)
                                sys.stdout.write("\x1b[7A\r\x1b[J")
                                sys.stdout.flush()
                        except ValueError:
                            print("\n\x1b[1;31mError: User ID must be a valid integer.\x1b[0m\n")
                            import time
                            time.sleep(1.0)
                            sys.stdout.write("\x1b[7A\r\x1b[J")
                            sys.stdout.flush()
                    else:
                        sys.stdout.write("\x1b[4A\r\x1b[J")
                        sys.stdout.flush()

                elif sub_choice == 1:
                    if not current_users:
                        print("\n\x1b[1;31mError: No user IDs configured to remove.\x1b[0m")
                        print("Press any key to return...")
                        get_key()
                        sys.stdout.write("\x1b[3A\r\x1b[J")
                        sys.stdout.flush()
                        continue

                    remove_options = [str(uid) for uid in current_users] + ["(Cancel)"]
                    remove_header = (
                        "\n\x1b[1;36m--- Select User ID to Remove ---\x1b[0m\n"
                        "Use Up/Down arrows to navigate, Enter to select, Esc/Q to cancel.\n"
                    )

                    rem_sel = run_interactive_menu(remove_options, remove_header, initial_idx=0)
                    if rem_sel is not None and rem_sel < len(current_users):
                        removed_uid = current_users.pop(rem_sel)
                        if "telegram" not in config_data:
                            config_data["telegram"] = {}
                        config_data["telegram"]["allowed_users"] = current_users
                        save_config(config_data)

                        print(f"\n\x1b[1;32m✓ User ID {removed_uid} removed.\x1b[0m\n")
                        import time
                        time.sleep(0.8)
                        sys.stdout.write("\x1b[3A\r\x1b[J")
                        sys.stdout.flush()


def _resolve_account(acc_id: str | None, tx_type: str | None = None) -> str:
    if acc_id is not None:
        return acc_id
        
    if tx_type:
        config_data = load_config()
        defaults = config_data.get("defaults", {})
        
        if tx_type == "income" and "income_acc" in defaults:
            return defaults["income_acc"]
        if tx_type == "expense" and "expense_acc" in defaults:
            return defaults["expense_acc"]
            
    accounts = get_accounts()
    if not accounts:
        typer.echo("Error: No accounts exist. Use 'sgm acc add' first.", err=True)
        raise typer.Exit(1)
    if len(accounts) == 1:
        return accounts[0]["id"]
    
    typer.echo("Error: Multiple accounts exist. You must specify the account ID.", err=True)
    raise typer.Exit(1)


def _resolve_account_and_date(acc_id: str | None, date_str: str | None, tx_type: str | None = None) -> tuple[str, str | None]:
    """
    Handles ambiguity between acc_id and date when both are optional.
    If date_str is None and acc_id looks like a date (YYYY-MM-DD),
    it treats acc_id as the date and resolves the account.
    """
    import re
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    
    resolved_date = date_str
    actual_acc_id = acc_id
    
    if date_str is None and acc_id is not None and date_pattern.match(acc_id):
        resolved_date = acc_id
        actual_acc_id = None
        
    resolved_acc_id = _resolve_account(actual_acc_id, tx_type=tx_type)
    return resolved_acc_id, resolved_date


def exp_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} <amount> <desc> <mark> [acc_id] [date]")
        print("Records an expense. The <mark> choice (yes/no) flags the item for the next render.")
        print("The date is optional (format: YYYY-MM-DD) and defaults to today.")
        raise typer.Exit()

@app.command("exp")
def exp(
    ctx: typer.Context,
    amount: int = typer.Argument(..., help="Amount of the expense (CLP)"),
    desc: str = typer.Argument(..., help="Description of the expense"),
    mark: str = typer.Argument(..., help="Flag for next render ('yes' or 'no')", click_type=click.Choice(["yes", "no"])),
    acc_id: str | None = typer.Argument(None, help="Account ID (optional if only 1 account exists)"),
    date: str | None = typer.Argument(None, help="Date of the expense (YYYY-MM-DD, optional)"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=exp_help_callback)
) -> None:
    """Records an expense."""
    if amount <= 0:
        typer.echo("Error: Amount must be positive.", err=True)
        raise typer.Exit(1)
        
    resolved_acc_id, resolved_date = _resolve_account_and_date(acc_id, date, tx_type="expense")
    marked = mark == "yes"
    
    try:
        create_movement(amount, desc, resolved_acc_id, "expense", marked, created_at=resolved_date)
        msg = f"Recorded expense of {amount} ('{desc}') in '{resolved_acc_id}'"
        if resolved_date:
            msg += f" on {resolved_date}."
        else:
            msg += "."
        typer.echo(msg)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def inc_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} <amount> <desc> <mark> [acc_id] [date]")
        print("Records an income. The <mark> choice (yes/no) flags the item for the next render.")
        print("The date is optional (format: YYYY-MM-DD) and defaults to today.")
        raise typer.Exit()

@app.command("inc")
def inc(
    ctx: typer.Context,
    amount: int = typer.Argument(..., help="Amount of the income (CLP)"),
    desc: str = typer.Argument(..., help="Description of the income"),
    mark: str = typer.Argument(..., help="Flag for next render ('yes' or 'no')", click_type=click.Choice(["yes", "no"])),
    acc_id: str | None = typer.Argument(None, help="Account ID (optional if only 1 account exists)"),
    date: str | None = typer.Argument(None, help="Date of the income (YYYY-MM-DD, optional)"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=inc_help_callback)
) -> None:
    """Records an income."""
    if amount <= 0:
        typer.echo("Error: Amount must be positive.", err=True)
        raise typer.Exit(1)
        
    resolved_acc_id, resolved_date = _resolve_account_and_date(acc_id, date, tx_type="income")
    marked = mark == "yes"
    
    try:
        create_movement(amount, desc, resolved_acc_id, "income", marked, created_at=resolved_date)
        msg = f"Recorded income of {amount} ('{desc}') in '{resolved_acc_id}'"
        if resolved_date:
            msg += f" on {resolved_date}."
        else:
            msg += "."
        typer.echo(msg)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def tr_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} <from> <to> <amount> [date]")
        print("Executes a transfer between accounts.")
        print("The date is optional (format: YYYY-MM-DD) and defaults to today.")
        raise typer.Exit()

@app.command("tr")
def tr(
    ctx: typer.Context,
    from_acc: str = typer.Argument(..., help="Source account ID"),
    to_acc: str = typer.Argument(..., help="Destination account ID"),
    amount: int = typer.Argument(..., help="Amount to transfer (CLP)"),
    date: str | None = typer.Argument(None, help="Date of the transfer (YYYY-MM-DD, optional)"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=tr_help_callback)
) -> None:
    """Executes a transfer between accounts."""
    if amount <= 0:
        typer.echo("Error: Amount must be positive.", err=True)
        raise typer.Exit(1)
        
    if from_acc == to_acc:
        typer.echo("Error: Source and destination accounts must be different.", err=True)
        raise typer.Exit(1)
        
    try:
        create_transfer(from_acc, to_acc, amount, created_at=date)
        msg = f"Transferred {amount} from '{from_acc}' to '{to_acc}'"
        if date:
            msg += f" on {date}."
        else:
            msg += "."
        typer.echo(msg)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def render_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path}")
        print("Sums all marked movements, logs the result to history, and unmarks all items.")
        raise typer.Exit()

@app.command("render")
def render_cmd(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=render_help_callback)
) -> None:
    """Sums all marked movements, logs the result to history, and unmarks all items."""
    net_amount, count = execute_render()
    if count == 0:
        typer.echo("No marked movements to render.")
    else:
        typer.echo(f"Rendered {count} movements.")
        typer.echo(f"Net amount logged: {net_amount}")


def log_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} [limit]")
        print("Lists the most recent movements. (Default: 15).")
        raise typer.Exit()

@app.command("log")
def log_cmd(
    ctx: typer.Context,
    limit: int = typer.Argument(15, help="Number of records to show"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=log_help_callback)
) -> None:
    """Lists the most recent movements."""
    console = Console()
    records = get_recent_logs(limit)
    
    if not records:
        typer.echo("No recent movements found.")
        raise typer.Exit()
        
    table = Table(title=f"Recent Logs (last {min(limit, len(records))})")
    table.add_column("ID", style="cyan")
    table.add_column("Date", style="dim")
    table.add_column("Type")
    table.add_column("Account")
    table.add_column("Amount", justify="right")
    table.add_column("Description")
    
    for rec in records:
        type_str = rec["type"]
        if type_str == "income":
            type_fmt = "[green]income[/]"
        elif type_str == "expense":
            type_fmt = "[red]expense[/]"
        elif type_str == "transfer":
            type_fmt = "[blue]transfer[/]"
        else:
            type_fmt = type_str
            
        date_str = rec["created_at"][:16].replace("T", " ")
        
        table.add_row(
            rec["unique_id"],
            date_str,
            type_fmt,
            rec["account_id"],
            str(rec["amount"]),
            rec["description"]
        )
        
    console.print(table)


def history_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path}")
        print("Displays a table of previous render results with dates and total sums.")
        raise typer.Exit()

@app.command("history")
def history_cmd(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=history_help_callback)
) -> None:
    """Displays a table of previous render results with dates and total sums."""
    console = Console()
    history = get_render_history()
    
    if not history:
        typer.echo("No render history found.")
        raise typer.Exit()
        
    table = Table(title="Render History")
    table.add_column("ID", style="cyan")
    table.add_column("Date", style="dim")
    table.add_column("Net Amount", justify="right")
    
    for entry in history:
        date_str = entry["rendered_at"][:10]
        net = entry["net_amount"]
        net_fmt = f"[bold {'green' if net >= 0 else 'red'}]{net}[/]"
        
        table.add_row(
            str(entry["id"]),
            date_str,
            net_fmt
        )
        
    console.print(table)


def delete_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} <id>")
        print("Permanently removes a movement or transfer by ID.")
        raise typer.Exit()

@app.command("delete")
def delete_cmd(
    ctx: typer.Context,
    unique_id: str = typer.Argument(..., help="Unique ID of the record to delete (e.g. m-1, t-1)"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=delete_help_callback)
) -> None:
    """Permanently removes a movement or transfer by ID."""
    try:
        delete_record(unique_id)
        typer.echo(f"Deleted record '{unique_id}'.")
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


@app.command("export")
def export(
    ctx: typer.Context,
    output: Path = typer.Option(None, "--output", "-o", help="Path to save the ZIP file"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True)
) -> None:
    """Exports all data into a ZIP file with CSV tables."""
    if help:
        print(f"Usage: {ctx.command_path} [--output <path>]")
        print(f"{ctx.command.help}")
        raise typer.Exit()

    console = Console()
    
    # 1. Determine output path
    if output is None:
        downloads_path = Path.home() / "Downloads"
        if not downloads_path.exists():
            downloads_path = Path.home()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = downloads_path / f"sigma_export_{timestamp}.zip"
    
    # 2. Fetch all data
    try:
        all_data = get_all_table_data()
    except Exception as e:
        console.print(f"[red]Error fetching data: {e}[/red]")
        raise typer.Exit(1)
        
    # 3. Create ZIP with CSVs
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            csv_files = []
            
            for table_name, rows in all_data.items():
                csv_file = tmp_path / f"{table_name}.csv"
                csv_files.append(csv_file)
                
                if rows:
                    fieldnames = rows[0].keys()
                    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                else:
                    # Create empty file with just the table name or specific headers if we had them
                    csv_file.touch()
            
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for csv_file in csv_files:
                    zipf.write(csv_file, arcname=csv_file.name)
                    
        console.print(f"[green]Successfully exported data to:[/green] [bold]{output.absolute()}[/bold]")
    except Exception as e:
        console.print(f"[red]Error creating export file: {e}[/red]")
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


def acc_rename_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} <old_id> <new_id>")
        print("Updates the unique identifier for an account.")
        raise typer.Exit()

@acc_app.command("rename")
def acc_rename(
    ctx: typer.Context,
    old_id: str = typer.Argument(..., help="Current unique identifier for the account"),
    new_id: str = typer.Argument(..., help="New unique identifier for the account"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=acc_rename_help_callback)
) -> None:
    """Updates the unique identifier for an account."""
    if old_id == new_id:
        typer.echo("Error: New ID must be different from the old ID.", err=True)
        raise typer.Exit(1)
        
    try:
        rename_account(old_id, new_id)
        typer.echo(f"Account '{old_id}' renamed to '{new_id}' successfully!")
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def acc_delete_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} <id>")
        print("Deletes an account and reassigns its history to a ghost account.")
        raise typer.Exit()

@acc_app.command("delete")
def acc_delete(
    ctx: typer.Context,
    id: str = typer.Argument(..., help="Unique identifier for the account to delete"),
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=acc_delete_help_callback)
) -> None:
    """Deletes an account and reassigns its history to a ghost account."""
    acc = get_account(id)
    if not acc:
        typer.echo(f"Error: Account with ID '{id}' not found.", err=True)
        raise typer.Exit(1)
        
    typer.echo(f"WARNING: You are about to delete account '{id}'.", err=True)
    typer.echo("Its history will be moved to a hidden 'deleted' account and the ID will be freed.", err=True)
    
    try:
        confirmation = typer.prompt("Type 'DELETE' to confirm (or press Ctrl+C to cancel)")
        if confirmation != "DELETE":
            typer.echo("Account deletion cancelled.")
            raise typer.Exit()
    except typer.Abort:
        typer.echo("\nAccount deletion cancelled.")
        raise typer.Exit()
        
    try:
        delete_account(id)
        typer.echo(f"Account '{id}' deleted successfully.")
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


def bot_setup_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path}")
        print("Interactively configures the Telegram Bot integration.")
        raise typer.Exit()

@bot_app.command("setup")
def bot_setup(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=bot_setup_help_callback)
) -> None:
    """Interactively configures the Telegram Bot integration."""
    config_data = load_config()
    telegram_cfg = config_data.get("telegram", {})
    
    current_token = telegram_cfg.get("token", "")
    current_users = telegram_cfg.get("allowed_users", [])
    current_users_str = ", ".join(map(str, current_users))
    
    typer.echo("--- Sigma Telegram Bot Setup ---")
    token = typer.prompt("Telegram Bot Token (from @BotFather)", default=current_token, type=str)
    
    users_input = typer.prompt("Allowed Telegram User IDs (comma-separated)", default=current_users_str, type=str)
    allowed_users = []
    if users_input.strip():
        for uid_str in users_input.split(","):
            uid_str = uid_str.strip()
            if uid_str:
                try:
                    allowed_users.append(int(uid_str))
                except ValueError:
                    typer.echo(f"Warning: '{uid_str}' is not a valid integer ID. Skipping.", err=True)
                    
    if "telegram" not in config_data:
        config_data["telegram"] = {}
        
    config_data["telegram"]["token"] = token
    config_data["telegram"]["allowed_users"] = allowed_users
    
    save_config(config_data)
    typer.echo("Telegram configuration saved successfully.")


def bot_run_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path}")
        print("Starts the Telegram Bot event loop (blocking).")
        raise typer.Exit()

@bot_app.command("run")
def bot_run(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True, callback=bot_run_help_callback)
) -> None:
    """Starts the Telegram Bot event loop."""
    config_data = load_config()
    telegram_cfg = config_data.get("telegram", {})
    token = telegram_cfg.get("token", "")
    allowed_users = telegram_cfg.get("allowed_users", [])
    
    if not token:
        typer.echo("Error: Telegram bot token is not configured.", err=True)
        typer.echo("Please run 'sgm bot setup' first.", err=True)
        raise typer.Exit(1)
        
    if not allowed_users:
        typer.echo("Warning: No allowed Telegram users configured.", err=True)
        typer.echo("The bot will ignore all messages.", err=True)
        
    typer.echo("Initializing database...")
    init_db()
    
    from sgm.infrastructure.database import get_db_path
    db_path = get_db_path()
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
        typer.echo("Database WAL mode enabled for concurrent write safety.")
    except Exception as e:
        typer.echo(f"Warning: Could not enable WAL mode: {e}", err=True)

    typer.echo("Starting Telegram Bot...")
    from sgm.telegram_bot import run_telegram_bot
    try:
        run_telegram_bot(token, allowed_users)
    except KeyboardInterrupt:
        typer.echo("\nStopping Telegram Bot.")
    except Exception as e:
        typer.echo(f"Error starting Telegram Bot: {e}", err=True)
        raise typer.Exit(1)


def web_help_callback(ctx: typer.Context, value: bool) -> None:
    if value:
        print(f"Usage: {ctx.command_path} [OPTIONS]")
        print("Start the local web dashboard server.")
        raise typer.Exit()

@app.command("web")
def web_cmd(
    ctx: typer.Context,
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port number"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not automatically open the browser"),
    help: bool = typer.Option(False, "--help", is_eager=True, callback=web_help_callback)
) -> None:
    """Start the local web dashboard server."""
    if not is_configured():
        typer.echo("Error: Sigma configuration file not found.", err=True)
        typer.echo("Please run 'sgm start' to initialize configuration.", err=True)
        raise typer.Exit(1)

    init_db()

    # Verify static files exist
    import os
    from sgm.interface.web.server import app as web_app
    static_dir = os.path.join(os.path.dirname(__file__), "interface", "web", "static")
    index_file = os.path.join(static_dir, "index.html")
    if not os.path.exists(index_file):
        # Detect if we have the web source directory to build assets automatically
        web_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "web"))
        if os.path.exists(os.path.join(web_src_dir, "package.json")) and not os.environ.get("PYTEST_CURRENT_TEST"):
            typer.echo("Web dashboard static assets not found. Compiling frontend dashboard automatically...", err=True)
            import shutil
            import subprocess
            
            npm_cmd = shutil.which("npm")
            if not npm_cmd:
                typer.echo("Error: 'npm' command not found. Cannot compile frontend dashboard automatically.", err=True)
                typer.echo("Please install Node.js/npm and run 'npm run build' in the web/ directory.", err=True)
                raise typer.Exit(1)
            
            try:
                node_modules_dir = os.path.join(web_src_dir, "node_modules")
                if not os.path.exists(node_modules_dir):
                    typer.echo("Installing web dependencies...", err=True)
                    subprocess.run([npm_cmd, "install"], cwd=web_src_dir, check=True)
                
                typer.echo("Building web dashboard...", err=True)
                subprocess.run([npm_cmd, "run", "build"], cwd=web_src_dir, check=True)
                typer.echo("Web dashboard compiled successfully!", err=True)
            except subprocess.CalledProcessError as e:
                typer.echo(f"Error compiling web dashboard: {e}", err=True)
                raise typer.Exit(1)
        else:
            typer.echo("Warning: Web dashboard static assets (index.html) not found.", err=True)
            typer.echo("The server will run, but you should compile static files using 'cd web && npm run build'.", err=True)

    import uvicorn
    import threading
    import time
    import webbrowser

    def open_browser():
        time.sleep(1.0)
        webbrowser.open(f"http://{host}:{port}")

    if not no_browser:
        threading.Thread(target=open_browser, daemon=True).start()

    typer.echo(f"Starting Sigma local dashboard server on http://{host}:{port}")
    try:
        from sgm.infrastructure.database import get_db_path
        web_app.state.db_path = get_db_path()
        uvicorn.run(web_app, host=host, port=port, log_level="info")
    except Exception as e:
        typer.echo(f"Error starting web server: {e}", err=True)
        raise typer.Exit(1)