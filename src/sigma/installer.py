"""Install a published release over the copy of Sigma that is running.

The people who use Sigma should not have to know what a zip is. This module
does what they would otherwise do by hand: download the release, check it is
intact, put it in place of the installed app and open it again.

Three rules shape it:

* **Nothing is replaced while the app is running.** The swap happens in a
  detached shell script that first waits for this process to exit. Python
  stages everything, launches the script and quits; the script does the move.
* **The old bundle is never thrown away until the new one is in place.** It is
  moved aside inside the staging folder, and put back if the copy fails.
* **A broken download must not reach ``/Applications``.** The bundle is checked
  before anything is touched: its signature has to validate and its version has
  to be the one that was promised.

The database is not involved at any point: it lives in a file the user chose,
outside the app.
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from sigma import __version__, updates
from sigma.updates import UpdateError

DOWNLOAD_TIMEOUT_SECONDS = 120

# Waits up to twenty seconds for the window to go away, then gives up rather
# than replacing a bundle that is still in use.
SWAP_SCRIPT = """#!/bin/bash
# Written by sigma/installer.py. Lives in a temporary folder, together with
# the downloaded bundle and the one being replaced.
set -u

for _ in $(seq 1 200); do
  kill -0 "$SIGMA_PID" 2>/dev/null || break
  sleep 0.1
done
if kill -0 "$SIGMA_PID" 2>/dev/null; then
  exit 1
fi

rm -rf "$SIGMA_PREVIOUS"
mv "$SIGMA_TARGET" "$SIGMA_PREVIOUS" || exit 1

if ! ditto "$SIGMA_NEW" "$SIGMA_TARGET"; then
  # Put back what was working before and reopen it: never leave the machine
  # without an app because a copy failed halfway.
  rm -rf "$SIGMA_TARGET"
  mv "$SIGMA_PREVIOUS" "$SIGMA_TARGET"
  open "$SIGMA_TARGET"
  exit 1
fi

open "$SIGMA_TARGET"
"""


def install() -> dict[str, Any]:
    """Download the newest release and hand the swap to a detached script.

    Returns as soon as the new bundle is verified and staged. Closing the
    window is the caller's job — the script is already waiting for it.
    """
    target = installed_bundle()

    release = updates.latest_release()
    if release is None:
        raise UpdateError(
            "No se pudo comprobar si hay una versión nueva. Revisa tu conexión a internet."
        )

    version = release["version"]
    if not updates.is_newer(version, __version__):
        raise UpdateError("Sigma ya está en la última versión.")
    if not release["download_url"]:
        raise UpdateError(
            f"La versión {version} no trae un archivo para descargar. "
            "Descárgala desde GitHub y arrástrala a tu carpeta Aplicaciones."
        )

    require_writable(target)

    staging = Path(tempfile.mkdtemp(prefix="sigma-update-"))
    try:
        archive = _download(release["download_url"], staging / updates.ASSET_NAME)
        bundle = _unpack(archive, staging / "nueva")
        _verify(bundle, version)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    _launch_swap(bundle, target, staging)
    return {"version": version, "installed_at": str(target)}


def installed_bundle() -> Path:
    """The ``.app`` this process is running from."""
    if not getattr(sys, "frozen", False):
        raise UpdateError(
            "Esta copia de Sigma se está ejecutando desde el código fuente, "
            "así que no puede actualizarse sola."
        )

    # …/Sigma.app/Contents/MacOS/Sigma → …/Sigma.app
    bundle = Path(sys.executable).resolve().parents[2]
    if bundle.suffix != ".app":
        raise UpdateError(
            "No se encontró la aplicación instalada. Descarga la versión nueva "
            "desde GitHub y arrástrala a tu carpeta Aplicaciones."
        )
    return bundle


def require_writable(bundle: Path) -> None:
    """Refuse early if the swap would need an administrator password.

    An app dragged into ``/Applications`` by its owner is writable; one put
    there with ``sudo`` belongs to root. Asking for the password is a whole
    privileged path this app has no other use for, so it says so instead.
    """
    if not os.access(bundle, os.W_OK) or not os.access(bundle.parent, os.W_OK):
        raise UpdateError(
            f"Sigma no tiene permiso para reemplazarse en {bundle.parent}. "
            "Descarga la versión nueva desde GitHub y arrástrala tú a esa carpeta."
        )


def _download(url: str, destination: Path) -> Path:
    request = urllib.request.Request(url, headers={"User-Agent": "Sigma"})
    try:
        with urllib.request.urlopen(
            request, timeout=DOWNLOAD_TIMEOUT_SECONDS, context=updates.ssl_context()
        ) as response, destination.open("wb") as file:
            shutil.copyfileobj(response, file)
    except Exception as exc:
        raise UpdateError(
            "No se pudo descargar la versión nueva. Revisa tu conexión e inténtalo de nuevo."
        ) from exc
    return destination


def _unpack(archive: Path, destination: Path) -> Path:
    """Expand with ``ditto``: plain unzip flattens the symlinks in a bundle."""
    result = subprocess.run(
        ["ditto", "-x", "-k", str(archive), str(destination)],
        capture_output=True,
        check=False,
    )
    bundles = sorted(destination.glob("*.app")) if destination.exists() else []
    if result.returncode != 0 or not bundles:
        raise UpdateError(
            "El archivo descargado llegó dañado. Inténtalo de nuevo en un momento."
        )
    return bundles[0]


def _verify(bundle: Path, expected_version: str) -> None:
    """Check the bundle before it is allowed anywhere near ``/Applications``."""
    signature = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(bundle)],
        capture_output=True,
        check=False,
    )
    if signature.returncode != 0:
        raise UpdateError(
            "El archivo descargado llegó dañado: macOS no lo abriría. "
            "Inténtalo de nuevo en un momento."
        )

    found = bundle_version(bundle)
    if found != expected_version:
        raise UpdateError(
            f"El archivo descargado no es la versión {expected_version}. "
            "Descárgala desde GitHub y arrástrala a tu carpeta Aplicaciones."
        )


def bundle_version(bundle: Path) -> str | None:
    """``CFBundleShortVersionString`` of an app bundle, if it can be read."""
    plist = bundle / "Contents" / "Info.plist"
    try:
        with plist.open("rb") as file:
            return plistlib.load(file).get("CFBundleShortVersionString")
    except Exception:
        return None


def _launch_swap(new_bundle: Path, target: Path, staging: Path) -> None:
    """Start the detached script that waits for this process to exit.

    The paths travel in the environment rather than inside the script text, so
    there is nothing to quote and nothing to get wrong.
    """
    script = staging / "reemplazar.sh"
    script.write_text(SWAP_SCRIPT, encoding="utf-8")
    script.chmod(0o755)

    environment = {
        "PATH": "/usr/bin:/bin",
        "SIGMA_PID": str(os.getpid()),
        "SIGMA_NEW": str(new_bundle),
        "SIGMA_TARGET": str(target),
        # Kept, not deleted: if the new version turns out not to open, the
        # previous one is still sitting there until macOS clears the folder.
        "SIGMA_PREVIOUS": str(staging / "anterior.app"),
    }

    log = (staging / "reemplazar.log").open("w")
    subprocess.Popen(  # noqa: S603 — fixed script, paths passed as environment
        ["/bin/bash", str(script)],
        env=environment,
        stdout=log,
        stderr=subprocess.STDOUT,
        # Its own session, so closing the window does not take it down with us.
        start_new_session=True,
    )
