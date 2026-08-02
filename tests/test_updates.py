from __future__ import annotations

import io
import json
import urllib.error

import pytest

from sigma import updates


@pytest.fixture(autouse=True)
def clear_cache():
    """The cache lives for the process, so tests must not inherit each other's."""
    updates._cached = None
    yield
    updates._cached = None


def fake_github(monkeypatch, payload: object, calls: list | None = None):
    """Answer the releases endpoint with ``payload`` instead of hitting GitHub."""

    def urlopen(request, timeout=None, context=None):
        if calls is not None:
            calls.append(request.full_url)
        body = json.dumps(payload).encode("utf-8")
        return io.BytesIO(body)

    monkeypatch.setattr(updates.urllib.request, "urlopen", urlopen)


def fake_offline(monkeypatch, calls: list | None = None):
    def urlopen(request, timeout=None, context=None):
        if calls is not None:
            calls.append(request.full_url)
        raise urllib.error.URLError("no internet")

    monkeypatch.setattr(updates.urllib.request, "urlopen", urlopen)


# --- Comparing versions ----------------------------------------------------


def test_a_newer_tag_is_offered(monkeypatch):
    monkeypatch.setattr(updates, "__version__", "1.1.1")
    fake_github(monkeypatch, {"tag_name": "v1.2.0"})

    result = updates.check()

    assert result["available"] is True
    assert result["latest"] == "1.2.0"
    assert result["current"] == "1.1.1"
    assert result["url"] == updates.RELEASES_PAGE


def test_the_same_version_is_not_an_update(monkeypatch):
    monkeypatch.setattr(updates, "__version__", "1.1.1")
    fake_github(monkeypatch, {"tag_name": "v1.1.1"})

    assert updates.check()["available"] is False


def test_an_older_tag_is_not_an_update(monkeypatch):
    """Someone running a build newer than the last release, e.g. from source."""
    monkeypatch.setattr(updates, "__version__", "1.2.0")
    fake_github(monkeypatch, {"tag_name": "v1.1.1"})

    assert updates.check()["available"] is False


def test_versions_compare_by_number_not_by_text(monkeypatch):
    monkeypatch.setattr(updates, "__version__", "1.9.0")
    fake_github(monkeypatch, {"tag_name": "v1.10.0"})

    assert updates.check()["available"] is True


def test_a_tag_that_does_not_parse_is_ignored(monkeypatch):
    monkeypatch.setattr(updates, "__version__", "1.1.1")
    fake_github(monkeypatch, {"tag_name": "v2.0.0-beta1"})

    result = updates.check()

    assert result["available"] is False
    assert result["latest"] == "2.0.0-beta1"


def test_a_response_without_a_tag_is_ignored(monkeypatch):
    fake_github(monkeypatch, {"message": "Not Found"})

    result = updates.check()

    assert result["latest"] is None
    assert result["available"] is False


# --- Without internet ------------------------------------------------------


def test_no_connection_reports_no_update_instead_of_failing(monkeypatch):
    fake_offline(monkeypatch)

    result = updates.check()

    assert result["latest"] is None
    assert result["available"] is False
    assert result["current"] == updates.__version__


def test_a_failed_check_is_not_cached(monkeypatch):
    """Connecting after launch should be noticed without restarting the app."""
    calls: list[str] = []
    fake_offline(monkeypatch, calls)
    updates.check()

    monkeypatch.setattr(updates, "__version__", "1.1.1")
    fake_github(monkeypatch, {"tag_name": "v1.2.0"}, calls)

    assert updates.check()["available"] is True
    assert len(calls) == 2


def test_a_successful_check_is_cached(monkeypatch):
    calls: list[str] = []
    fake_github(monkeypatch, {"tag_name": "v1.2.0"}, calls)

    updates.check()
    updates.check()

    assert len(calls) == 1
