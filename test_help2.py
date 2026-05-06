import typer
from src.sgm.interface.banner import print_help

app = typer.Typer(rich_markup_mode=None, help="Sigma CLI finance tracker")

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
) -> None:
    if ctx.invoked_subcommand is None:
        print_help()

@app.command("start")
def start() -> None:
    """First-run setup and preferences."""
    print("starting")

if __name__ == "__main__":
    app()
