"""
Single-instance guard for the PradoOS Desktop System Tray application.

Prevents duplicate tray icons and concurrent SQLite access on Windows/Linux
when a user double-clicks the desktop executable while PradoOS is already running
in the system tray, bringing the active Setup Card window to the foreground instead.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional
import urllib.request

from prado.config import get_config_dir, write_secure_file


class SingleInstanceGuard:
    """Tracks the active PradoOS Desktop loopback server so secondary launches activate it."""

    def __init__(self, instance_file: Optional[Path] = None) -> None:
        self._explicit_instance_file = instance_file

    @property
    def instance_file(self) -> Path:
        if self._explicit_instance_file is not None:
            return self._explicit_instance_file
        return get_config_dir() / "tray_instance.json"

    def try_activate_existing(self, timeout: float = 1.0) -> bool:
        """
        Attempts to signal an already-running PradoOS Desktop instance to show its window.
        Returns True if an existing instance responded with HTTP 200; removes stale lock
        files and returns False otherwise.
        """
        inst_path = self.instance_file
        if not inst_path.exists():
            return False

        try:
            raw = json.loads(inst_path.read_text(encoding="utf-8"))
            port = int(raw.get("port", 0))
            token = str(raw.get("token", ""))
        except Exception:
            self._unlink_quietly(inst_path)
            return False

        if port <= 0 or not token:
            self._unlink_quietly(inst_path)
            return False

        req = urllib.request.Request(
            url=f"http://127.0.0.1:{port}/api/window/show",
            data=b"{}",
            method="POST",
            headers={
                "X-Prado-Token": token,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if getattr(resp, "status", 200) == 200:
                    return True
        except Exception:
            pass

        # Existing instance is unreachable / crashed; clean up stale descriptor
        self._unlink_quietly(inst_path)
        return False

    def register(self, port: int, token: str) -> None:
        """Records the active loopback server descriptor with 0600 permissions."""
        payload = {
            "pid": os.getpid(),
            "port": int(port),
            "token": str(token),
        }
        write_secure_file(self.instance_file, json.dumps(payload), mode=0o600)

    def release(self) -> None:
        """Removes the instance descriptor if it belongs to this process."""
        inst_path = self.instance_file
        if not inst_path.exists():
            return
        try:
            raw = json.loads(inst_path.read_text(encoding="utf-8"))
            if int(raw.get("pid", -1)) == os.getpid():
                inst_path.unlink()
        except Exception:
            self._unlink_quietly(inst_path)

    @staticmethod
    def _unlink_quietly(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass
