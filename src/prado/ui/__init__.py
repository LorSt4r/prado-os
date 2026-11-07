"""
PradoOS Desktop UI Package.

Provides native System Tray / Menu Bar application, GUI dialogs, and desktop integration.
"""

from __future__ import annotations

__all__ = ["PradoTrayApp", "run_tray_app"]


def __getattr__(name: str):
    if name in ("PradoTrayApp", "run_tray_app"):
        from prado.ui.tray import PradoTrayApp, run_tray_app

        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
