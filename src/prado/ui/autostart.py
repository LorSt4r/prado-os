"""
Cross-platform Desktop Login Autostart Manager for PradoOS Tray App.

Registers or removes user-level login startup without admin privileges or terminal prompts:
- macOS: ~/Library/LaunchAgents/es.ugr.pradoos.tray.plist (RunAtLoad=True)
- Windows: HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\PradoOS
- Linux: ~/.config/autostart/pradoos.desktop
"""

from __future__ import annotations

import os
from pathlib import Path
import plistlib
import shlex
import subprocess
import sys
from typing import List, Optional

TRAY_LAUNCHD_LABEL = "es.ugr.pradoos.tray"
WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WINDOWS_VALUE_NAME = "PradoOS"


def get_autostart_command() -> List[str]:
    """Returns the executable command to launch PradoOS silently into the System Tray."""
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve()), "--tray-only"]
    return [sys.executable, "-m", "prado", "app", "--tray-only"]


def _macos_plist_path(home_dir: Optional[Path] = None) -> Path:
    base = home_dir or Path.home()
    return base / "Library" / "LaunchAgents" / f"{TRAY_LAUNCHD_LABEL}.plist"


def _linux_desktop_path(home_dir: Optional[Path] = None) -> Path:
    base = home_dir or Path.home()
    return base / ".config" / "autostart" / "pradoos.desktop"


def is_autostart_enabled(home_dir: Optional[Path] = None) -> bool:
    """Checks whether desktop login autostart is currently enabled for this user."""
    if sys.platform == "darwin":
        return _macos_plist_path(home_dir).exists()

    if sys.platform in ("win32", "cygwin") or os.name == "nt":
        try:
            import winreg  # type: ignore[import-not-found]

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, WINDOWS_VALUE_NAME)
                return bool(str(val).strip())
        except Exception:
            return False

    return _linux_desktop_path(home_dir).exists()


def set_autostart_enabled(enabled: bool, home_dir: Optional[Path] = None) -> bool:
    """Enables or disables user-level desktop login autostart."""
    cmd = get_autostart_command()

    if sys.platform == "darwin":
        plist_path = _macos_plist_path(home_dir)
        if enabled:
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            plist_data = {
                "Label": TRAY_LAUNCHD_LABEL,
                "ProgramArguments": cmd,
                "RunAtLoad": True,
                "KeepAlive": False,
                "ProcessType": "Interactive",
            }
            with open(plist_path, "wb") as f:
                plistlib.dump(plist_data, f)
            return True
        if plist_path.exists():
            plist_path.unlink()
        return False

    if sys.platform in ("win32", "cygwin") or os.name == "nt":
        import winreg  # type: ignore[import-not-found]

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, WINDOWS_VALUE_NAME, 0, winreg.REG_SZ, subprocess.list2cmdline(cmd))
                return True
            try:
                winreg.DeleteValue(key, WINDOWS_VALUE_NAME)
            except FileNotFoundError:
                pass
            return False

    desktop_path = _linux_desktop_path(home_dir)
    if enabled:
        desktop_path.parent.mkdir(parents=True, exist_ok=True)
        exec_line = " ".join(shlex.quote(part) for part in cmd)
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=PradoOS\n"
            "Comment=UGR PRADO Academic Sync Tray\n"
            f"Exec={exec_line}\n"
            "Terminal=false\n"
            "X-GNOME-Autostart-enabled=true\n"
        )
        desktop_path.write_text(content, encoding="utf-8")
        return True
    if desktop_path.exists():
        desktop_path.unlink()
    return False
