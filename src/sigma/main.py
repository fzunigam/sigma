"""Application entry point.

Starts the local API on a loopback port, then opens a native window pointing at
it. The window *is* the app: there is no browser tab, no terminal, and nothing
listening outside this machine.
"""

from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path

from sigma import __version__, database
from sigma.bridge import Bridge

HOST = "127.0.0.1"
WINDOW_TITLE = "Sigma"
WINDOW_SIZE = (1180, 780)
MIN_WINDOW_SIZE = (900, 620)


def free_port() -> int:
    """Ask the OS for an unused port instead of guessing a fixed one."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((HOST, 0))
        return probe.getsockname()[1]


def serve(port: int) -> None:
    import uvicorn

    from sigma.api import app

    uvicorn.run(app, host=HOST, port=port, log_level="warning", access_log=False)


def set_dock_icon() -> None:
    """Use the bundled logo in the Dock when running from source."""
    icon = Path(__file__).parent / "web" / "static" / "logo.png"
    if not icon.exists():
        return
    try:
        from AppKit import NSApplication, NSImage

        image = NSImage.alloc().initWithContentsOfFile_(str(icon))
        if image:
            NSApplication.sharedApplication().setApplicationIconImage_(image)
    except Exception:
        # Cosmetic only; never let it stop the app from opening.
        pass


def main() -> int:
    try:
        import webview
    except ImportError:
        print(
            "Falta pywebview. Instala las dependencias con:\n"
            '  python3.12 -m pip install -e ".[dev]"',
            file=sys.stderr,
        )
        return 1

    port = free_port()
    threading.Thread(target=serve, args=(port,), daemon=True).start()
    set_dock_icon()

    bridge = Bridge()
    window = webview.create_window(
        WINDOW_TITLE,
        f"http://{HOST}:{port}",
        js_api=bridge,
        width=WINDOW_SIZE[0],
        height=WINDOW_SIZE[1],
        min_size=MIN_WINDOW_SIZE,
    )
    bridge.attach(window)

    try:
        webview.start()
    finally:
        # Drop the advisory lock so the file does not look busy on the next open.
        database.close()

    return 0


if __name__ == "__main__":
    print(f"Sigma {__version__}")
    raise SystemExit(main())
