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
    console.print("---start")
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Command", style="cyan bold")
    table.add_column("Description")
    
    table.add_row("start", "First-run setup and preferences")
    table.add_row("status", "Displays balances, credit limits, and marked total")
    table.add_row("web", "Start the web app")
    table.add_row("restore", "Delete all data and configuration, resetting Sigma")
    table.add_row("update", "Update sgm to the latest version")
    
    console.print(table)
    console.print()
    console.print("Type [bold cyan]sgm --help[/bold cyan] for more details on commands and options.")
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
    console.print("  start         First-run setup and preferences")
    console.print("  status        Displays balances, credit limits, and marked total")
    console.print("  render        Sums marked movements and logs history")
    console.print()
    console.print("  exp           Records an expense")
    console.print("  inc           Records an income")
    console.print("  tr            Executes a transfer between accounts")
    console.print()
    console.print("  log           Lists the most recent movements")
    console.print("  history       Displays a table of previous render results")
    console.print("  delete        Permanently removes a movement or transfer by ID")
    console.print()
    console.print("  acc add       Adds a new account with an initial balance")
    console.print("  acc list      Detailed view of account metadata")
    console.print("  acc rename    Updates the unique identifier for an account")
    console.print("  acc set-limit Updates the rolling credit limit")
    console.print("  acc delete    Deletes an account and preserves history in ghost account")
    console.print()
    console.print("  config        Interactive configuration for default accounts")
    console.print("  export        Export DB tables to a ZIP of CSVs")
    console.print("  restore       Delete all data and configuration, resetting Sigma")
    console.print("  update        Update sgm to the latest version")
    console.print("  version       Show the version and exit")
    console.print()