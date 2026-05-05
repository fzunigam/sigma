from pathlib import Path
import tomllib


def test_pyproject_has_release_metadata() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]

    assert "license" in project
    assert "classifiers" in project
    assert "urls" in project
