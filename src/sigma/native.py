"""The parts of the window that make Sigma feel like a Mac app, not a web page.

- A translucent sidebar: an ``NSVisualEffectView`` sits behind the web view,
  which stops painting its own background. The page keeps its content area
  opaque, so only the sidebar shows the material.
- A real menu bar in Spanish, with the app's keyboard shortcuts listed where
  macOS users look for them. Menu items send a command to the page; the page
  owns what each command does (see ``web/src/lib/commands.ts``).
- The window appearance follows the in-app theme, so the material, the traffic
  lights and the menus match the light or dark interface.

Everything here is cosmetic: a failure leaves a plain, working window.
"""

from __future__ import annotations

import json
from typing import Any

# Labels for pywebview's built-in menus.
LOCALIZATION = {
    "cocoa.menu.about": "Acerca de",
    "cocoa.menu.services": "Servicios",
    "cocoa.menu.view": "Visualización",
    "cocoa.menu.edit": "Edición",
    "cocoa.menu.hide": "Ocultar",
    "cocoa.menu.hideOthers": "Ocultar otros",
    "cocoa.menu.showAll": "Mostrar todo",
    "cocoa.menu.quit": "Salir de",
    "cocoa.menu.fullscreen": "Pantalla completa",
    "cocoa.menu.cut": "Cortar",
    "cocoa.menu.copy": "Copiar",
    "cocoa.menu.paste": "Pegar",
    "cocoa.menu.selectAll": "Seleccionar todo",
}

# (menu title, [(item title, command, key, extra modifiers)]). A ``None`` item is a separator.
MENUS: list[tuple[str, list[tuple[str, str, str, int] | None]]] = [
    (
        "Archivo",
        [
            ("Nuevo movimiento", "new", "n", 0),
            ("Buscar movimientos", "find", "f", 0),
        ],
    ),
    (
        "Ir",
        [
            ("Resumen", "go:resumen", "1", 0),
            ("Movimientos", "go:movimientos", "2", 0),
            ("Cuentas", "go:cuentas", "3", 0),
            None,
            ("Ajustes", "go:ajustes", ",", 0),
        ],
    ),
]

SIDEBAR_MATERIAL = 7  # NSVisualEffectMaterialSidebar


def setup(window: Any) -> None:
    """Hook vibrancy and the menu bar into the window's lifecycle."""
    try:
        from PyObjCTools import AppHelper
    except ImportError:
        return

    def on_loaded() -> None:
        _add_vibrancy(window)
        _add_menus(window)

    # AppKit objects may only be touched from the main thread.
    window.events.loaded += lambda: AppHelper.callAfter(on_loaded)


def set_appearance(window: Any, theme: str) -> None:
    """Match the native chrome to the in-app theme."""
    try:
        import AppKit
        from PyObjCTools import AppHelper
    except ImportError:
        return

    name = AppKit.NSAppearanceNameDarkAqua if theme == "dark" else AppKit.NSAppearanceNameAqua

    def apply() -> None:
        native = getattr(window, "native", None)
        if native is not None:
            native.setAppearance_(AppKit.NSAppearance.appearanceNamed_(name))

    AppHelper.callAfter(apply)


def _add_vibrancy(window: Any) -> None:
    import AppKit

    native = window.native
    content = native.contentView()  # The WKWebView, once the page has loaded.
    frame_view = content.superview()
    # Tells the page it may let the material through (see `html[data-native]`).
    # Sent on every load: a reload starts from a fresh document.
    _send(content, "document.documentElement.dataset.native = ''")
    if any(isinstance(view, AppKit.NSVisualEffectView) for view in frame_view.subviews()):
        return

    effect = AppKit.NSVisualEffectView.alloc().initWithFrame_(content.frame())
    effect.setMaterial_(SIDEBAR_MATERIAL)
    effect.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
    effect.setState_(AppKit.NSVisualEffectStateFollowsWindowActiveState)
    effect.setAutoresizingMask_(AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
    frame_view.addSubview_positioned_relativeTo_(effect, AppKit.NSWindowBelow, content)

    content.setValue_forKey_(False, "drawsBackground")


def _add_menus(window: Any) -> None:
    import AppKit

    main_menu = AppKit.NSApplication.sharedApplication().mainMenu()
    if main_menu is None or main_menu.itemWithTitle_("Ir") is not None:
        return

    target = _command_target(window)
    for index, (title, items) in enumerate(MENUS):
        menu = AppKit.NSMenu.alloc().initWithTitle_(title)
        for item in items:
            if item is None:
                menu.addItem_(AppKit.NSMenuItem.separatorItem())
                continue
            label, command, key, modifiers = item
            entry = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                label, "runCommand:", key
            )
            entry.setKeyEquivalentModifierMask_(AppKit.NSEventModifierFlagCommand | modifiers)
            entry.setTarget_(target)
            entry.setRepresentedObject_(command)
            menu.addItem_(entry)
        holder = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, None, "")
        holder.setSubmenu_(menu)
        # Right after the app menu, as in any Mac app: Archivo, then the rest.
        position = 1 if index == 0 else main_menu.numberOfItems()
        main_menu.insertItem_atIndex_(holder, position)

    _add_undo(main_menu)


def _add_undo(main_menu: Any) -> None:
    """pywebview's Edit menu has no undo, so ⌘Z would do nothing in a text field."""
    import AppKit

    # pywebview titles the submenu, not the item that holds it.
    submenu = next(
        (
            item.submenu()
            for item in main_menu.itemArray()
            if item.submenu() is not None
            and item.submenu().title() == LOCALIZATION["cocoa.menu.edit"]
        ),
        None,
    )
    if submenu is None:
        return
    redo = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Rehacer", "redo:", "z")
    redo.setKeyEquivalentModifierMask_(
        AppKit.NSEventModifierFlagCommand | AppKit.NSEventModifierFlagShift
    )
    submenu.insertItem_atIndex_(AppKit.NSMenuItem.separatorItem(), 0)
    submenu.insertItem_atIndex_(redo, 0)
    submenu.insertItemWithTitle_action_keyEquivalent_atIndex_("Deshacer", "undo:", "z", 0)


_target: Any = None


def _command_target(window: Any) -> Any:
    """An Objective-C object whose ``runCommand:`` forwards to the page."""
    global _target
    if _target is not None:
        return _target

    import AppKit

    class SigmaCommandTarget(AppKit.NSObject):
        def runCommand_(self, sender):
            _send(window.native.contentView(), _dispatch(str(sender.representedObject())))

    _target = SigmaCommandTarget.alloc().init()
    return _target


def _dispatch(command: str) -> str:
    detail = json.dumps(command)
    return f"window.dispatchEvent(new CustomEvent('sigma:command', {{ detail: {detail} }}))"


def _send(web_view: Any, script: str) -> None:
    # Straight to WKWebView: pywebview's evaluate_js blocks waiting for the main
    # thread, which is the thread this runs on.
    web_view.evaluateJavaScript_completionHandler_(script, None)
