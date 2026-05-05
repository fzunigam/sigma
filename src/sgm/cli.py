import typer

app = typer.Typer(help="Sigma CLI finance tracker")


@app.callback()
def main() -> None:
    """Sigma CLI finance tracker."""
