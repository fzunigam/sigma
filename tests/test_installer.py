from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

from sigma import installer, updates
from sigma.updates import UpdateError


def fake_bundle(path: Path, version: str = "1.0.0", marker: str = "vieja") -> Path:
    """An app-shaped folder: enough for everything except a real signature."""
    contents = path / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "MacOS" / "Sigma").write_text(marker, encoding="utf-8")
    with (contents / "Info.plist").open("wb") as file:
        plistlib.dump({"CFBundleShortVersionString": version}, file)
    return path


def stub_command(folder: Path, name: str, script: str) -> None:
    """Put an executable earlier in PATH than the real one."""
    folder.mkdir(exist_ok=True)
    command = folder / name
    command.write_text(f"#!/bin/bash\n{script}\n", encoding="utf-8")
    command.chmod(0o755)


# --- Finding what to replace -----------------------------------------------


def test_running_from_source_cannot_update_itself():
    """A checkout has no bundle to swap, and git is the way to update it."""
    with pytest.raises(UpdateError, match="código fuente"):
        installer.install()


def test_the_bundle_is_found_from_the_running_executable(tmp_path, monkeypatch):
    bundle = fake_bundle(tmp_path / "Sigma.app")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(bundle / "Contents" / "MacOS" / "Sigma"))

    assert installer.installed_bundle() == bundle


def test_an_executable_outside_a_bundle_is_refused(tmp_path, monkeypatch):
    loose = tmp_path / "algun" / "lugar" / "Sigma"
    loose.parent.mkdir(parents=True)
    loose.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(loose))

    with pytest.raises(UpdateError, match="No se encontró la aplicación instalada"):
        installer.installed_bundle()


def test_a_folder_that_needs_an_administrator_is_refused(tmp_path):
    """Sigma asks the user to drag it instead of asking for a password."""
    applications = tmp_path / "Applications"
    bundle = fake_bundle(applications / "Sigma.app")
    applications.chmod(0o555)
    try:
        with pytest.raises(UpdateError, match="no tiene permiso"):
            installer.require_writable(bundle)
    finally:
        applications.chmod(0o755)


# --- Refusing before downloading anything ----------------------------------


@pytest.fixture
def installed(tmp_path, monkeypatch) -> Path:
    """A writable fake install, so the guards can be reached one by one."""
    bundle = fake_bundle(tmp_path / "Applications" / "Sigma.app")
    monkeypatch.setattr(installer, "installed_bundle", lambda: bundle)
    monkeypatch.setattr(installer, "__version__", "1.1.1")
    return bundle


def test_without_connection_nothing_is_installed(installed, monkeypatch):
    monkeypatch.setattr(updates, "latest_release", lambda: None)

    with pytest.raises(UpdateError, match="conexión"):
        installer.install()


def test_the_latest_version_is_not_reinstalled(installed, monkeypatch):
    monkeypatch.setattr(
        updates, "latest_release", lambda: {"version": "1.1.1", "download_url": "https://x"}
    )

    with pytest.raises(UpdateError, match="ya está en la última versión"):
        installer.install()


def test_a_release_without_a_file_to_download_is_refused(installed, monkeypatch):
    monkeypatch.setattr(
        updates, "latest_release", lambda: {"version": "1.2.0", "download_url": None}
    )

    with pytest.raises(UpdateError, match="no trae un archivo para descargar"):
        installer.install()


# --- Checking the download -------------------------------------------------


def test_a_bundle_of_the_wrong_version_is_rejected(tmp_path, monkeypatch):
    """Defends against a release whose asset does not match its own tag."""
    bundle = fake_bundle(tmp_path / "Sigma.app", version="9.9.9")
    monkeypatch.setattr(
        installer.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0)
    )

    with pytest.raises(UpdateError, match="no es la versión 1.2.0"):
        installer._verify(bundle, "1.2.0")


def test_an_unpacked_folder_without_an_app_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(
        installer.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0)
    )
    empty = tmp_path / "nueva"
    empty.mkdir()

    with pytest.raises(UpdateError, match="llegó dañado"):
        installer._unpack(tmp_path / "algo.zip", empty)


def test_the_version_is_read_from_the_bundle(tmp_path):
    bundle = fake_bundle(tmp_path / "Sigma.app", version="1.2.0")

    assert installer.bundle_version(bundle) == "1.2.0"
    assert installer.bundle_version(tmp_path / "NoExiste.app") is None


# --- Staging ---------------------------------------------------------------


def test_a_verified_release_is_staged_and_the_swap_is_launched(
    installed, tmp_path, monkeypatch
):
    """The app is still untouched when install() returns: the script waits."""
    downloaded = fake_bundle(tmp_path / "descarga" / "Sigma.app", version="1.2.0", marker="nueva")
    launched: list[dict] = []

    monkeypatch.setattr(
        updates,
        "latest_release",
        lambda: {"version": "1.2.0", "download_url": "https://x/Sigma.zip"},
    )
    monkeypatch.setattr(installer, "_download", lambda url, destination: destination)
    monkeypatch.setattr(installer, "_unpack", lambda archive, destination: downloaded)
    monkeypatch.setattr(installer, "_verify", lambda bundle, version: None)
    monkeypatch.setattr(
        installer.subprocess, "Popen", lambda *args, **kwargs: launched.append(kwargs)
    )

    result = installer.install()

    assert result["version"] == "1.2.0"
    assert (installed / "Contents" / "MacOS" / "Sigma").read_text() == "vieja"
    environment = launched[0]["env"]
    assert environment["SIGMA_TARGET"] == str(installed)
    assert environment["SIGMA_NEW"] == str(downloaded)
    assert environment["SIGMA_PID"] == str(os.getpid())


# --- The swap itself -------------------------------------------------------


def run_swap(tmp_path, target: Path, new: Path, extra_path: Path | None = None):
    """Run the real script against a process that has already exited."""
    finished = subprocess.Popen(["/usr/bin/true"])
    finished.wait()

    script = tmp_path / "reemplazar.sh"
    script.write_text(installer.SWAP_SCRIPT, encoding="utf-8")
    script.chmod(0o755)

    stubs = tmp_path / "bin"
    stub_command(stubs, "open", f'echo "$1" >> "{tmp_path}/abierta.txt"')
    path = f"{stubs}:{extra_path}:/usr/bin:/bin" if extra_path else f"{stubs}:/usr/bin:/bin"

    return subprocess.run(
        ["/bin/bash", str(script)],
        env={
            "PATH": path,
            "SIGMA_PID": str(finished.pid),
            "SIGMA_NEW": str(new),
            "SIGMA_TARGET": str(target),
            "SIGMA_PREVIOUS": str(tmp_path / "anterior.app"),
        },
        capture_output=True,
        text=True,
    )


def test_the_swap_replaces_the_app_and_opens_it(tmp_path):
    target = fake_bundle(tmp_path / "Applications" / "Sigma.app", marker="vieja")
    new = fake_bundle(tmp_path / "descarga" / "Sigma.app", version="1.2.0", marker="nueva")

    result = run_swap(tmp_path, target, new)

    assert result.returncode == 0
    assert (target / "Contents" / "MacOS" / "Sigma").read_text() == "nueva"
    assert installer.bundle_version(target) == "1.2.0"
    assert (tmp_path / "abierta.txt").read_text().strip() == str(target)


def test_a_failed_copy_puts_the_working_app_back(tmp_path):
    """Nobody is left without an application because a copy broke halfway."""
    target = fake_bundle(tmp_path / "Applications" / "Sigma.app", marker="vieja")
    new = fake_bundle(tmp_path / "descarga" / "Sigma.app", version="1.2.0", marker="nueva")
    broken = tmp_path / "roto"
    stub_command(broken, "ditto", "exit 1")

    result = run_swap(tmp_path, target, new, extra_path=broken)

    assert result.returncode == 1
    assert (target / "Contents" / "MacOS" / "Sigma").read_text() == "vieja"
    assert (tmp_path / "abierta.txt").read_text().strip() == str(target)


def test_the_swap_never_touches_an_app_that_is_still_running(tmp_path, monkeypatch):
    """The loop gives up instead of replacing a bundle in use."""
    target = fake_bundle(tmp_path / "Applications" / "Sigma.app", marker="vieja")
    new = fake_bundle(tmp_path / "descarga" / "Sigma.app", marker="nueva")

    # One turn of the wait loop instead of twenty seconds of it.
    script = tmp_path / "reemplazar.sh"
    script.write_text(installer.SWAP_SCRIPT.replace("seq 1 200", "seq 1 1"), encoding="utf-8")
    alive = subprocess.Popen(["/bin/sleep", "5"])
    try:
        result = subprocess.run(
            ["/bin/bash", str(script)],
            env={
                "PATH": "/usr/bin:/bin",
                "SIGMA_PID": str(alive.pid),
                "SIGMA_NEW": str(new),
                "SIGMA_TARGET": str(target),
                "SIGMA_PREVIOUS": str(tmp_path / "anterior.app"),
            },
            capture_output=True,
        )
    finally:
        alive.terminate()
        alive.wait()

    assert result.returncode == 1
    assert (target / "Contents" / "MacOS" / "Sigma").read_text() == "vieja"
