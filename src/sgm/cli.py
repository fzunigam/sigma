import typer

from sgm.infrastructure.user_config import save_config
from sgm.interface.banner import print_help, print_startup_text

app = typer.Typer(help="Sigma CLI finance tracker")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Sigma CLI finance tracker."""
    if ctx.invoked_subcommand is None:
        print_help()


@app.command("start")
def start() -> None:
    print_startup_text()
    name = typer.prompt("Display name", default="", show_default=False).strip()
    save_config(display_name=name or None)
    typer.echo("Configuration saved.")
