from typer.testing import CliRunner

from sgm.cli import app


def test_start_shows_brand_and_guidance() -> None:
    result = CliRunner().invoke(app, ["start"], input="\nblue\n")

    assert "SIGMA" in result.stdout
    assert "to start configuring type sgm start" in result.stdout.lower()
