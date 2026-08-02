"""Ask GitHub whether a newer Sigma has been published.

Sigma works offline and this is the only request it makes on its own, so it is
deliberately toothless: any failure — no internet, GitHub unreachable, a tag
that does not parse — is reported as "no update" and the app carries on as if
nothing had happened. Nothing about the user or the database is sent; it is a
plain GET of the public releases endpoint.

A successful answer is cached for the life of the process so reopening a view
does not re-check. Failures are not cached: connecting to the network after
launching should not require a restart to be noticed.

Installing what this module finds is :mod:`sigma.installer`.
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.request
from typing import Any

import certifi

from sigma import __version__
from sigma.db.errors import SigmaError

LATEST_RELEASE_API = "https://api.github.com/repos/fzunigam/sigma/releases/latest"
RELEASES_PAGE = "https://github.com/fzunigam/sigma/releases/latest"

# The one asset a release publishes. Anything else attached to it is not the app.
ASSET_NAME = "Sigma-AppleSilicon.app.zip"

TIMEOUT_SECONDS = 4
CACHE_SECONDS = 6 * 60 * 60

_cached: tuple[float, dict[str, Any]] | None = None


class UpdateError(SigmaError):
    """Installing a new version did not work out. → HTTP 400"""


def check() -> dict[str, Any]:
    """Compare the running version against the latest published release."""
    release = latest_release()
    version = release["version"] if release else None
    return {
        "current": __version__,
        "latest": version,
        "available": version is not None and is_newer(version, __version__),
        "url": RELEASES_PAGE,
    }


def latest_release() -> dict[str, Any] | None:
    """The newest published release, or ``None`` if GitHub cannot be read.

    ``{"version": "1.2.0", "download_url": "https://…/Sigma-…zip" | None}``
    """
    global _cached

    now = time.monotonic()
    if _cached is not None and now - _cached[0] < CACHE_SECONDS:
        return _cached[1]

    release = _fetch_latest_release()
    if release is not None:
        _cached = (now, release)
    return release


def ssl_context() -> ssl.SSLContext:
    """Verify certificates against certifi's bundle rather than OpenSSL's.

    Neither the python.org build of Python on macOS nor the interpreter
    PyInstaller packs into the .app is guaranteed to have a CA bundle where
    OpenSSL looks for one, and when it does not, verification fails on a
    perfectly healthy machine. certifi carries the bundle inside the app.
    """
    return ssl.create_default_context(cafile=certifi.where())


def is_newer(candidate: str, current: str) -> bool:
    parsed_candidate = _parse(candidate)
    parsed_current = _parse(current)
    if parsed_candidate is None or parsed_current is None:
        return False
    return parsed_candidate > parsed_current


def _fetch_latest_release() -> dict[str, Any] | None:
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Sigma"},
    )
    try:
        with urllib.request.urlopen(
            request, timeout=TIMEOUT_SECONDS, context=ssl_context()
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        # Every failure means the same thing here: we do not know, so say
        # nothing. Never let this reach the interface as an error.
        return None

    if not isinstance(payload, dict):
        return None
    tag = payload.get("tag_name")
    if not isinstance(tag, str) or not tag.strip():
        return None

    return {
        "version": tag.strip().lstrip("vV"),
        "download_url": _asset_url(payload.get("assets")),
    }


def _asset_url(assets: Any) -> str | None:
    if not isinstance(assets, list):
        return None
    for asset in assets:
        if isinstance(asset, dict) and asset.get("name") == ASSET_NAME:
            url = asset.get("browser_download_url")
            return url if isinstance(url, str) else None
    return None


def _parse(version: str) -> tuple[int, ...] | None:
    """``"1.2.10"`` as a comparable tuple. Anything odd is not comparable."""
    # A pre-release suffix (1.2.0-beta1) is not something Sigma publishes, and
    # guessing at its order is worse than staying quiet about it.
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return None
