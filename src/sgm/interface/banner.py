from rich.console import Console # type: ignore
from rich.table import Table # type: ignore

from sgm import __version__

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
    console.print("Let's configure [bold cyan]Sigma[/bold cyan]")

def print_help() -> None:
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

    console.print(table)
    console.print()
    
    # Print the Commands section
    console.print("---commands")
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Command", style="cyan bold")
    table.add_column("Description")
    
    table.add_row("start", "First-run setup and preferences")
    
    console.print(table)
    console.print()
