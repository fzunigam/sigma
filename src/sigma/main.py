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


def blend_titlebar(window) -> None:
    """Let the page run under a transparent title bar, keeping the traffic lights.

    The sidebar already leaves room for the buttons, so the window reads as one
    surface instead of a grey strip on top of the app.
    """
    try:
        import AppKit
        from PyObjCTools import AppHelper
    except ImportError:
        return

    class TitlebarDragArea(AppKit.NSView):
        """Invisible strip that gives back what the web view swallows: drag and zoom."""

        def mouseDown_(self, event):
            if event.clickCount() == 2:
                self.window().performZoom_(None)
            else:
                self.window().performWindowDragWithEvent_(event)

    def style() -> None:
        native = window.native
        native.setStyleMask_(native.styleMask() | AppKit.NSWindowStyleMaskFullSizeContentView)
        native.setTitlebarAppearsTransparent_(True)
        native.setTitleVisibility_(AppKit.NSWindowTitleHidden)
        # pywebview paints the title bar with the window color; undo it so the page shows.
        for view in native.contentView().superview().subviews():
            if type(view).__name__ == "NSTitlebarContainerView":
                view.setBackgroundColor_(AppKit.NSColor.clearColor())

    def add_drag_area() -> None:
        # pywebview makes the web view the content view only once the page loads.
        # From then on it covers the title bar and would eat every click there, so
        # the strip sits just above it in the window frame.
        native = window.native
        content = native.contentView()
        frame_view = content.superview()
        if any(isinstance(view, TitlebarDragArea) for view in frame_view.subviews()):
            return
        frame = content.frame()
        height = frame.size.height - native.contentLayoutRect().size.height
        strip = TitlebarDragArea.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, frame.size.height - height, frame.size.width, height)
        )
        strip.setAutoresizingMask_(AppKit.NSViewWidthSizable | AppKit.NSViewMinYMargin)
        frame_view.addSubview_positioned_relativeTo_(strip, AppKit.NSWindowAbove, content)

    # AppKit objects may only be touched from the main thread.
    window.events.before_show += lambda: AppHelper.callAfter(style)
    window.events.loaded += lambda: AppHelper.callAfter(add_drag_area)


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

    # Back up and claim the remembered database before anything can write to it.
    database.open_at_startup()

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
    blend_titlebar(window)

    try:
        webview.start()
    finally:
        # Drop the advisory lock so the file does not look busy on the next open.
        database.close()

    return 0


if __name__ == "__main__":
    print(f"Sigma {__version__}")
    raise SystemExit(main())
