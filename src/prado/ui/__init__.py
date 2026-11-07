"""
PradoOS Desktop UI Package.

Provides the Native WebView Control Center (`PradoUIServer` + `PradoControlCenterAPI`),
System Tray / Menu Bar application (`PradoTrayApp`), GUI dialogs, and desktop icons.
"""

from __future__ import annotations

__all__ = [
    "PradoControlCenterAPI",
    "PradoTrayApp",
    "PradoUIServer",
    "run_tray_app",
]


def __getattr__(name: str):
    if name in ("PradoTrayApp", "run_tray_app"):
        from prado.ui.tray import PradoTrayApp, run_tray_app

        return locals()[name]
    if name in ("PradoControlCenterAPI", "PradoUIServer"):
        from prado.ui.server import PradoControlCenterAPI, PradoUIServer

        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
