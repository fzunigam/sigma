"""Ask GitHub whether a newer Sigma has been published.

Sigma works offline and this is the only request it ever makes, so it is
deliberately toothless: any failure — no internet, GitHub unreachable, a tag
that does not parse — is reported as "no update" and the app carries on as if
nothing had happened. Nothing about the user or the database is sent; it is a
plain GET of the public releases endpoint.

A successful answer is cached for the life of the process so reopening a view
does not re-check. Failures are not cached: connecting to the network after
launching should not require a restart to be noticed.
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.request
from typing import Any

import certifi

from sigma import __version__

LATEST_RELEASE_API = "https://api.github.com/repos/fzunigam/sigma/releases/latest"
RELEASES_PAGE = "https://github.com/fzunigam/sigma/releases/latest"

TIMEOUT_SECONDS = 4
CACHE_SECONDS = 6 * 60 * 60

_cached: tuple[float, dict[str, Any]] | None = None


def check() -> dict[str, Any]:
    """Compare the running version against the latest published release."""
    global _cached

    now = time.monotonic()
    if _cached is not None and now - _cached[0] < CACHE_SECONDS:
        return _cached[1]

    latest = latest_version()
    result = {
        "current": __version__,
        "latest": latest,
        "available": latest is not None and _is_newer(latest, __version__),
        "url": RELEASES_PAGE,
    }
    if latest is not None:
        _cached = (now, result)
    return result


def latest_version() -> str | None:
    """The version of the newest release, or ``None`` if it cannot be read."""
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Sigma"},
    )
    try:
        with urllib.request.urlopen(
            request, timeout=TIMEOUT_SECONDS, context=_ssl_context()
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        # Every failure means the same thing here: we do not know, so say
        # nothing. Never let this reach the interface as an error.
        return None

    tag = payload.get("tag_name") if isinstance(payload, dict) else None
    if not isinstance(tag, str) or not tag.strip():
        return None
    return tag.strip().lstrip("vV")


def _ssl_context() -> ssl.SSLContext:
    """Verify the certificate against certifi's bundle rather than OpenSSL's.

    Neither the python.org build of Python on macOS nor the interpreter
    PyInstaller packs into the .app is guaranteed to have a CA bundle where
    OpenSSL looks for one, and when it does not, verification fails on a
    perfectly healthy machine. certifi carries the bundle inside the app.
    """
    return ssl.create_default_context(cafile=certifi.where())


def _is_newer(candidate: str, current: str) -> bool:
    parsed_candidate = _parse(candidate)
    parsed_current = _parse(current)
    if parsed_candidate is None or parsed_current is None:
        return False
    return parsed_candidate > parsed_current


def _parse(version: str) -> tuple[int, ...] | None:
    """``"1.2.10"`` as a comparable tuple. Anything odd is not comparable."""
    # A pre-release suffix (1.2.0-beta1) is not something Sigma publishes, and
    # guessing at its order is worse than staying quiet about it.
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return None
