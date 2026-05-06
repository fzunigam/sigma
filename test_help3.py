import typer
from src.sgm.interface.banner import print_help

app = typer.Typer(
    add_completion=False,
    add_help_option=False,
    rich_markup_mode=None
)

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", is_eager=True),
) -> None:
    if help:
        print_help()
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        print_help()

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
    print("starting")

if __name__ == "__main__":
    app()
