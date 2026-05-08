from rich.console import Console # type: ignore
from rich.table import Table # type: ignore

from sgm import __version__
from sgm.infrastructure.database import get_db_path

def print_banner_text() -> None:
    logo = """\
 ███████╗ ██╗  ██████╗  ███╗   ███╗  █████╗ 
 ██╔════╝ ██║ ██╔════╝  ████╗ ████║ ██╔══██╗
 ███████╗ ██║ ██║  ███╗ ██╔████╔██║ ███████║
 ╚════██║ ██║ ██║   ██║ ██║╚██╔╝██║ ██╔══██║
 ███████║ ██║ ╚██████╔╝ ██║ ╚═╝ ██║ ██║  ██║
 ╚══════╝ ╚═╝  ╚═════╝  ╚═╝     ╚═╝ ╚═╝  ╚═╝"""
    
    console = Console()
    
    # Print the ASCII art
    console.print()
    console.print(f"[bold cyan]{logo}[/bold cyan]")
    console.print()

def print_startup_text() -> None:
    console = Console()
    console.print("Welcome to [bold cyan]Sigma[/bold cyan], your CLI finance tracker!")
    console.print("Let's configure it!")

def print_sgm() -> None:
    console = Console()
    print_banner_text()
    
    # Print the version and description
    console.print("  track your money, easy way")
    console.print()
    
    # Print the About section
    console.print("---about")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Command", style="cyan bold")
    table.add_column("Description")

    table.add_row("docs", "github.com/fzunigam/sigma")
    table.add_row("version", f"v{__version__}")
    table.add_row("db", str(get_db_path()))

    console.print(table)
    console.print()
    
    # Print the Commands section
    console.print("---commands")
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Command", style="cyan bold")
    table.add_column("Description")
    
    table.add_row("start", "First-run setup and preferences")
    table.add_row("acc add", "Adds a new account with an initial balance")
    table.add_row("acc list", "Detailed view of account metadata")
    table.add_row("restore", "Delete all data and leave the database empty")
    table.add_row("update", "Update sgm to the latest version")
    
    console.print(table)
    console.print()

def print_help() -> None:
    console = Console()
    console.print()
    console.print("Usage: [bold cyan]sgm[/bold cyan] [OPTIONS] COMMAND [ARGS]")
    console.print()
    console.print("[bold cyan]---options:[/bold cyan]")
    console.print("  -h, --help  Show this message and exit")
    console.print()
    console.print("[bold cyan]---commands:[/bold cyan]")
    console.print("  start       First-run setup and preferences")
    console.print("  status      Displays balances, credit limits, and marked total")
    console.print("  acc add     Adds a new account with an initial balance")
    console.print("  acc list    Detailed view of account metadata")
    console.print("  acc set-limit Updates the rolling credit limit")
    console.print("  restore     Delete all data and leave the database empty")
    console.print("  update      Update sgm to the latest version")
    console.print("  version     Show the version and exit")
    console.print()