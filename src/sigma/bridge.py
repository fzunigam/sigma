"""Native macOS file dialogs, exposed to the interface through pywebview.

The web layer cannot open a real Finder dialog, and `<input type="file">` only
yields an upload — never a path the app can keep writing to. It is also
unreliable inside WKWebView. So the dialogs are opened by pywebview and the
chosen path is handed back to JavaScript as ``window.pywebview.api``.

Every method returns a plain dict so the frontend can treat a cancelled dialog
(``{"path": None}``) the same way as a successful one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

DIALOG_FILTER = ("Base de datos Sigma (*.db)", "*.db")


class Bridge:
    """Methods callable from JavaScript via ``window.pywebview.api``."""

    def __init__(self) -> None:
        self._window: Any = None

    def attach(self, window: Any) -> None:
        self._window = window

    # -- Dialogs ------------------------------------------------------------

    def choose_database(self) -> dict[str, str | None]:
        """Ask for an existing ``.db`` file to open."""
        import webview

        result = self._dialog(webview.OPEN_DIALOG, allow_multiple=False)
        return {"path": result}

    def choose_new_database(self) -> dict[str, str | None]:
        """Ask where to save a new database.

        Defaults to the user's Google Drive folder when one is present, since
        keeping the file in a synced folder is the whole point of choosing it.
        """
        import webview

        result = self._dialog(
            webview.SAVE_DIALOG,
            directory=str(_default_folder()),
            save_filename="finanzas.db",
        )
        return {"path": result}

    def open_releases(self) -> dict[str, bool]:
        """Open the downloads page in the default browser.

        Takes no URL on purpose: JavaScript inside the window must not be able
        to hand `open` an arbitrary target. Following the link inside the
        window would replace the app with a web page and leave no way back.
        """
        import subprocess

        from sigma.updates import RELEASES_PAGE

        subprocess.run(["open", RELEASES_PAGE], check=False)
        return {"ok": True}

    def quit(self) -> dict[str, bool]:
        """Close the window, which ends the process.

        Used after staging an update: the script that swaps the bundle is
        already waiting for this process to go away. Closing happens on its own
        thread so the call from JavaScript can return first.
        """
        import threading

        if self._window is not None:
            threading.Timer(0.1, self._window.destroy).start()
        return {"ok": True}

    def reveal(self, path: str) -> dict[str, bool]:
        """Show a file in Finder."""
        import subprocess

        target = Path(path).expanduser()
        if not target.exists():
            return {"ok": False}
        subprocess.run(["open", "-R", str(target)], check=False)
        return {"ok": True}

    # -- Internals ----------------------------------------------------------

    def _dialog(self, dialog_type: int, **kwargs: Any) -> str | None:
        if self._window is None:
            return None
        result = self._window.create_file_dialog(
            dialog_type, file_types=(DIALOG_FILTER[0], "Todos los archivos (*.*)"), **kwargs
        )
        if not result:
            return None
        # OPEN_DIALOG returns a sequence, SAVE_DIALOG a single path.
        return str(result[0]) if isinstance(result, (list, tuple)) else str(result)


def _default_folder() -> Path:
    """Google Drive's local folder if it exists, otherwise the home directory."""
    candidates = [
        Path.home() / "Library" / "CloudStorage",
        Path.home() / "Google Drive",
        Path.home() / "Documents",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return Path.home()
