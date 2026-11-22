"""
Desktop application launcher entry point for PyInstaller standalone bundles.
"""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional


def run_gui_diagnostics(output_file: Optional[str] = None) -> int:
    """
    Verifies that bundled desktop GUI dependencies (webview, pystray, tkinter,
    and Windows pythonnet/EdgeWebView2 backend) import and initialize cleanly.
    """
    is_win = sys.platform in ("win32", "cygwin") or os.name == "nt"
    report: Dict[str, Any] = {
        "platform": sys.platform,
        "frozen": bool(getattr(sys, "frozen", False)),
        "imports": {},
        "errors": {},
        "windows_guilib_ok": None,
        "ok": False,
    }

    modules_to_check = ["webview", "pystray", "tkinter"]
    if is_win:
        modules_to_check.extend(
            [
                "clr",
                "clr_loader",
                "webview.platforms.edgechromium",
                "webview.platforms.winforms",
            ]
        )

    for mod_name in modules_to_check:
        try:
            importlib.import_module(mod_name)
            report["imports"][mod_name] = True
        except Exception as exc:
            report["imports"][mod_name] = False
            report["errors"][mod_name] = f"{type(exc).__name__}: {exc}"

    if is_win and report["imports"].get("webview"):
        try:
            import webview.guilib as guilib

            guilib.initialize()
            report["windows_guilib_ok"] = True
        except Exception as exc:
            report["windows_guilib_ok"] = False
            report["errors"]["webview.guilib"] = f"{type(exc).__name__}: {exc}"

    report["ok"] = bool(
        report["imports"].get("webview")
        and report["imports"].get("pystray")
        and (not is_win or report.get("windows_guilib_ok") is True)
    )

    payload = json.dumps(report, indent=2)
    if output_file:
        out_path = Path(output_file).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")

    try:
        if sys.stdout is not None:
            sys.stdout.write(payload + "\n")
            sys.stdout.flush()
    except Exception:
        pass

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    diag_arg = next((a for a in sys.argv[1:] if a == "--diagnose-gui" or a.startswith("--diagnose-gui=")), None)
    if diag_arg is not None:
        out_file = diag_arg.split("=", 1)[1] if "=" in diag_arg else None
        sys.exit(run_gui_diagnostics(output_file=out_file))

    from prado.ui.tray import run_tray_app

    sys.exit(run_tray_app(tray_only="--tray-only" in sys.argv[1:]))
