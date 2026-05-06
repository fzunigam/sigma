from typer.testing import CliRunner

from sgm.cli import app


def test_start_shows_brand_and_guidance() -> None:
    result = CliRunner().invoke(app, ["start"], input="\n")

    assert "configure" in result.stdout.lower()
    assert "Sigma" in result.stdout
