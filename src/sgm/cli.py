import typer # type: ignore

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
    name = typer.prompt("Display name", default="", show_default=False).strip()
    save_config(display_name=name or None)
    typer.echo("Configuration saved.")
