"""
Native System Tray / Menu Bar Application for PradoOS.

Runs discreetly in the macOS Menu Bar, Windows System Tray, or Linux Notification Area.
Eliminates the terminal barrier for students, offering 1-click synchronization,
direct folder access, calendar integration, webmail shortcuts, and credential management.
"""

from __future__ import annotations

import argparse
import datetime
import os
from pathlib import Path
import sys
import threading
import time
from typing import Any, Optional

try:
    import pystray
except ImportError:
    pystray = None  # type: ignore[assignment]

from prado import __version__
from prado.config import PradoConfig, load_config, save_config
from prado.exceptions import AuthenticationRequiredError, InvalidCredentialsError
from prado.i18n import t
from prado.notifications.desktop import DesktopNotifier, is_headless_environment
from prado.ui.dialogs import open_folder, open_url, prompt_login_gui
from prado.ui.icon import create_tray_icon


class PradoTrayApp:
    """
    Lightweight, background-friendly system tray application for PradoOS.
    """

    def __init__(self, cfg: Optional[PradoConfig] = None) -> None:
        self.cfg: PradoConfig = cfg or load_config()
        self.status: str = "idle"  # "idle", "syncing", "error"
        self.last_sync_time: Optional[str] = None
        self.last_error: Optional[str] = None
        self._sync_lock = threading.Lock()
        self._running = True
        self._auto_sync_enabled = False
        self._auto_sync_interval_mins = 60
        self.icon: Optional[pystray.Icon] = None
        self.notifier = DesktopNotifier(app_name="PradoOS")

    # -------------------------------------------------------------------------
    # Status & Labels (i18n aware)
    # -------------------------------------------------------------------------
    def _get_status_text(self) -> str:
        lang = self.cfg.language or "es"
        if self.status == "syncing":
            return t("tray_status_syncing", lang)
        elif self.status == "error":
            return t("tray_status_error", lang)
        return t("tray_status_idle", lang)

    def _get_last_sync_text(self) -> str:
        lang = self.cfg.language or "es"
        if self.last_sync_time:
            return t("tray_last_sync", lang, time=self.last_sync_time)
        return t("tray_last_sync", lang, time="--:--")

    # -------------------------------------------------------------------------
    # Menu Construction
    # -------------------------------------------------------------------------
    def _build_menu(self) -> pystray.Menu:
        lang = self.cfg.language or "es"

        return pystray.Menu(
            # Header
            pystray.MenuItem(f"PradoOS v{__version__}", action=None, enabled=False),
            pystray.MenuItem(lambda item: self._get_status_text(), action=None, enabled=False),
            pystray.MenuItem(lambda item: self._get_last_sync_text(), action=None, enabled=False),
            pystray.Menu.SEPARATOR,
            # Core Actions
            pystray.MenuItem(
                t("tray_sync_now", lang),
                self._on_sync_now,
                default=True,
            ),
            pystray.MenuItem(
                t("tray_open_folder", lang),
                self._on_open_folder,
            ),
            pystray.MenuItem(
                t("tray_open_calendar", lang),
                self._on_open_calendar,
            ),
            pystray.MenuItem(
                t("tray_open_mail", lang),
                self._on_open_mail,
            ),
            pystray.Menu.SEPARATOR,
            # Settings & Preferences
            pystray.MenuItem(
                t("tray_notifications", lang),
                self._on_toggle_notifications,
                checked=lambda item: self.cfg.notifications.enabled,
            ),
            pystray.MenuItem(
                t("tray_auto_sync", lang),
                self._on_toggle_auto_sync,
                checked=lambda item: self._auto_sync_enabled,
            ),
            pystray.MenuItem(
                t("tray_settings", lang),
                self._on_open_settings,
            ),
            pystray.MenuItem(
                t("tray_github", lang),
                self._on_open_github,
            ),
            pystray.Menu.SEPARATOR,
            # Exit
            pystray.MenuItem(
                t("tray_quit", lang),
                self._on_quit,
            ),
        )

    # -------------------------------------------------------------------------
    # Menu Callbacks
    # -------------------------------------------------------------------------
    def _on_sync_now(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self.trigger_sync()

    def _on_open_folder(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        open_folder(self.cfg.courses_root)

    def _on_open_calendar(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        gcal = self.cfg.calendar.google_calendar
        if gcal.enabled and gcal.calendar_id and gcal.calendar_id != "auto":
            open_url("https://calendar.google.com")
            return

        ics_path = self.cfg.courses_root / "deadlines.ics"
        if ics_path.exists():
            open_folder(ics_path)
        else:
            open_url("https://calendar.google.com")

    def _on_open_mail(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        open_url("https://correo.ugr.es")

    def _on_toggle_notifications(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self.cfg.notifications.enabled = not self.cfg.notifications.enabled
        save_config(self.cfg)
        if self.icon:
            self.icon.update_menu()

    def _on_toggle_auto_sync(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self._auto_sync_enabled = not self._auto_sync_enabled
        if self.icon:
            self.icon.update_menu()

    def _on_open_settings(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        # Launch GUI login prompt in a separate thread to keep UI responsive
        threading.Thread(target=self._run_login_prompt, daemon=True).start()

    def _run_login_prompt(self) -> None:
        saved = prompt_login_gui(self.cfg)
        if saved:
            self.cfg = load_config()
            self.status = "idle"
            if self.icon:
                self.icon.icon = create_tray_icon("idle")
                self.icon.update_menu()

    def _on_open_github(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        open_url("https://github.com/LorSt4r/prado-os")

    def _on_quit(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self.stop()

    # -------------------------------------------------------------------------
    # Synchronization Pipeline (Background Worker)
    # -------------------------------------------------------------------------
    def trigger_sync(self) -> bool:
        """Triggers a background synchronization if one is not already running."""
        if not self._sync_lock.acquire(blocking=False):
            return False

        threading.Thread(target=self._run_sync_worker, daemon=True).start()
        return True

    def _run_sync_worker(self) -> None:
        try:
            self.status = "syncing"
            if self.icon:
                self.icon.icon = create_tray_icon("syncing")
                self.icon.update_menu()

            # Refresh config
            self.cfg = load_config()

            from prado.cli import _handle_sync

            sync_args = argparse.Namespace(
                preset=self.cfg.sync.preset or None,
                dry_run=False,
                adopt=True,
                no_interactive=True,
                course=None,
                force=False,
                mail=self.cfg.mail.enabled,
                no_mail=not self.cfg.mail.enabled,
                gcalendar=self.cfg.calendar.google_calendar.enabled,
                gcalendar_token=None,
                calendar_id=self.cfg.calendar.google_calendar.calendar_id,
            )

            try:
                exit_code = _handle_sync(args=sync_args, json_mode=False)
            except (AuthenticationRequiredError, InvalidCredentialsError):
                # Credentials missing or expired: prompt via native dialog
                saved = prompt_login_gui(self.cfg)
                if saved:
                    self.cfg = load_config()
                    exit_code = _handle_sync(args=sync_args, json_mode=False)
                else:
                    raise

            if exit_code == 0:
                self.status = "idle"
                self.last_sync_time = datetime.datetime.now().strftime("%H:%M")
                self.last_error = None
                if self.icon:
                    self.icon.icon = create_tray_icon("idle")
                if self.cfg.notifications.enabled:
                    self.notifier.notify(
                        title="PradoOS",
                        message=t("tray_sync_success_notification", self.cfg.language),
                    )
            else:
                self.status = "error"
                self.last_error = f"Exit code {exit_code}"
                if self.icon:
                    self.icon.icon = create_tray_icon("error")
        except Exception as exc:
            self.status = "error"
            self.last_error = str(exc)
            if self.icon:
                self.icon.icon = create_tray_icon("error")
            if self.cfg.notifications.enabled:
                self.notifier.notify(
                    title="PradoOS",
                    message=t("tray_sync_error_notification", self.cfg.language, error=str(exc)),
                    urgency="critical",
                )
        finally:
            self._sync_lock.release()
            if self.icon:
                self.icon.update_menu()

    # -------------------------------------------------------------------------
    # Background Auto-Sync Timer Loop
    # -------------------------------------------------------------------------
    def _auto_sync_loop(self) -> None:
        last_check = time.time()
        while self._running:
            time.sleep(10)
            if not self._auto_sync_enabled:
                last_check = time.time()
                continue

            interval_sec = self._auto_sync_interval_mins * 60
            if time.time() - last_check >= interval_sec:
                last_check = time.time()
                self.trigger_sync()

    # -------------------------------------------------------------------------
    # App Lifecycle
    # -------------------------------------------------------------------------
    def run(self, detached: bool = False) -> None:
        """
        Launches the system tray menu bar app.
        In GUI environments, enters the main event loop.
        """
        if pystray is None:
            raise RuntimeError(
                "pystray is not installed. Install with 'pip install pystray pillow' to run the GUI app."
            )

        if is_headless_environment():
            raise RuntimeError(
                "Cannot launch System Tray App in a headless or CI environment without a display server."
            )

        initial_icon_img = create_tray_icon("idle")
        self.icon = pystray.Icon(
            name="PradoOS",
            icon=initial_icon_img,
            title="PradoOS — PRADO UGR",
            menu=self._build_menu(),
        )

        # Launch auto-sync background timer thread
        threading.Thread(target=self._auto_sync_loop, daemon=True).start()

        if detached:
            self.icon.run_detached()
        else:
            self.icon.run()

    def stop(self) -> None:
        """Stops the application and closes the tray icon."""
        self._running = False
        if self.icon:
            self.icon.stop()


def run_tray_app(detached: bool = False) -> int:
    """Entrypoint function for 'prado app', 'prado gui', and console scripts."""
    try:
        app = PradoTrayApp()
        app.run(detached=detached)
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        sys.stderr.write(f"\n❌ PradoOS App Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_tray_app())
