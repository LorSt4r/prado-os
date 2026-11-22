"""
Single-instance guard for the PradoOS Desktop System Tray application.

Prevents duplicate tray icons and concurrent SQLite access on Windows/Linux
when a user double-clicks the desktop executable while PradoOS is already running
in the system tray, bringing the active Setup Card window to the foreground instead.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Optional
import urllib.request

from prado.config import get_config_dir, write_secure_file


class SingleInstanceGuard:
    """Tracks the active PradoOS Desktop process and loopback server across launches."""

    def __init__(self, instance_file: Optional[Path] = None) -> None:
        self._explicit_instance_file = instance_file
        self._win_mutex_handle: Optional[int] = None
        self._lock_fh: Optional[Any] = None

    @property
    def instance_file(self) -> Path:
        if self._explicit_instance_file is not None:
            return self._explicit_instance_file
        return get_config_dir() / "tray_instance.json"

    def _mutex_name(self) -> str:
        if self._explicit_instance_file is None and not os.environ.get("PRADO_CONFIG_DIR"):
            return "Local\\PradoOS_Desktop_SingleInstance"
        digest = hashlib.sha256(str(self.instance_file.resolve()).encode("utf-8")).hexdigest()[:12]
        return f"Local\\PradoOS_Desktop_SingleInstance_{digest}"

    def acquire_lock(self) -> bool:
        """
        Acquires an OS-level non-blocking lock (Windows named Mutex or POSIX flock)
        so rapid double-clicks during startup cannot spawn duplicate tray icons.
        """
        is_windows = sys.platform in ("win32", "cygwin") or os.name == "nt"
        if is_windows:
            if self._win_mutex_handle:
                return True
            try:
                kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
                handle = kernel32.CreateMutexW(None, False, self._mutex_name())
                last_err = kernel32.GetLastError()
                if not handle:
                    return True
                if last_err == 183:  # ERROR_ALREADY_EXISTS
                    kernel32.CloseHandle(handle)
                    return False
                self._win_mutex_handle = int(handle)
                return True
            except Exception:
                return True

        if self._lock_fh is not None:
            return True
        try:
            import fcntl

            lock_path = self.instance_file.with_suffix(".lock")
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            fh = open(lock_path, "a+", encoding="utf-8")
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (BlockingIOError, OSError):
                fh.close()
                return False
            try:
                fh.seek(0)
                fh.truncate()
                fh.write(str(os.getpid()))
                fh.flush()
            except OSError:
                pass
            self._lock_fh = fh
            return True
        except Exception:
            return True

    def _send_activate_request(self, timeout: float = 1.0, cleanup_stale: bool = True) -> bool:
        """
        Sends POST /api/window/show bypassing system proxies.
        When `cleanup_stale` is True, invalid/unreachable instance descriptors are removed.
        """
        inst_path = self.instance_file
        if not inst_path.exists():
            return False

        try:
            raw = json.loads(inst_path.read_text(encoding="utf-8"))
            port = int(raw.get("port", 0))
            token = str(raw.get("token", ""))
        except Exception:
            if cleanup_stale:
                self._unlink_quietly(inst_path)
            return False

        if port <= 0 or not token:
            if cleanup_stale:
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
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=timeout) as resp:
                if getattr(resp, "status", 200) == 200:
                    return True
        except Exception:
            pass

        if cleanup_stale:
            self._unlink_quietly(inst_path)
        return False

    def try_activate_existing(self, timeout: float = 1.0) -> bool:
        """
        Attempts to signal an already-running PradoOS Desktop instance to show its window.
        Returns True if an existing instance responded with HTTP 200; removes stale lock
        files and returns False otherwise.
        """
        return self._send_activate_request(timeout=timeout, cleanup_stale=True)

    def acquire_or_activate(self, timeout: float = 1.5, wait_for_ready: float = 3.0) -> bool:
        """
        Atomically either becomes the primary instance (returning True) or wakes up the
        existing/booting primary instance (returning False).
        """
        if self.try_activate_existing():
            return False

        if self.acquire_lock():
            return True

        deadline = time.monotonic() + max(0.0, float(wait_for_ready))
        while time.monotonic() < deadline:
            if self._send_activate_request(timeout=timeout, cleanup_stale=False):
                return False
            time.sleep(0.15)
        self._send_activate_request(timeout=timeout, cleanup_stale=False)
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
        """Removes the instance descriptor if it belongs to this process and frees OS locks."""
        inst_path = self.instance_file
        if inst_path.exists():
            try:
                raw = json.loads(inst_path.read_text(encoding="utf-8"))
                if int(raw.get("pid", -1)) == os.getpid():
                    inst_path.unlink()
            except Exception:
                self._unlink_quietly(inst_path)

        if self._win_mutex_handle is not None:
            handle = self._win_mutex_handle
            self._win_mutex_handle = None
            try:
                ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
            except Exception:
                pass

        if self._lock_fh is not None:
            fh = self._lock_fh
            self._lock_fh = None
            try:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                fh.close()
            except Exception:
                pass

    @staticmethod
    def _unlink_quietly(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass
