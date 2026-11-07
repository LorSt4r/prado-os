"""
PradoOS Desktop Orchestrator: Native WebView Control Center + System Tray App.

Combines:
1. Native Desktop Control Center window via `pywebview` (WebKit on macOS, Edge WebView2 on Windows,
   GTK WebKit2 on Linux, with seamless browser fallback).
2. Local loopback REST/Event server (`PradoUIServer` on `127.0.0.1:<ephemeral_port>`).
3. Persistent System Tray / Menu Bar icon (`pystray`) with thread-safe Cocoa/Win32 updates.
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys
import threading
import time
from typing import Any, Callable, Optional

try:
    import pystray
except ImportError:
    pystray = None  # type: ignore[assignment]

try:
    import webview
except ImportError:
    webview = None  # type: ignore[assignment]

from prado import __version__
from prado.config import PradoConfig, load_config, save_config
from prado.exceptions import AuthenticationRequiredError, InvalidCredentialsError
from prado.i18n import t
from prado.notifications.desktop import DesktopNotifier, is_headless_environment
from prado.ui.dialogs import open_folder, open_url, prompt_login_gui
from prado.ui.icon import create_tray_icon
from prado.ui.server import PradoControlCenterAPI, PradoUIServer


def _dispatch_ui_thread(fn: Callable[[], None], is_main_loop_running: bool = False) -> None:
    """
    Safely dispatches a UI mutation to the Cocoa main thread on macOS when the
    AppKit event loop is running, or executes directly in unit tests / other platforms.
    """
    if sys.platform == "darwin" and is_main_loop_running:
        try:
            from PyObjCTools import AppHelper

            AppHelper.callAfter(fn)
            return
        except Exception:
            pass
    try:
        fn()
    except Exception:
        pass


class PradoTrayApp:
    """
    Unified Desktop Application & System Tray controller for PradoOS.
    """

    def __init__(self, cfg: Optional[PradoConfig] = None) -> None:
        self.cfg: PradoConfig = cfg or load_config()
        self.status: str = "idle"  # "idle", "syncing", "error"
        self.last_sync_time: Optional[str] = None
        self.last_error: Optional[str] = None
        self._sync_lock = threading.Lock()
        self._running = True
        self._quitting = False
        self._main_loop_active = False
        self._auto_sync_enabled = False
        self._auto_sync_interval_mins = 60
        self.icon: Optional[pystray.Icon] = None
        self.notifier = DesktopNotifier(app_name="PradoOS")

        # Shared Control Center API & Local Loopback Server
        self.api = PradoControlCenterAPI(cfg=self.cfg, on_status_change=self._on_api_status_change)
        self.server: Optional[PradoUIServer] = None
        self.window: Optional[Any] = None

    def _on_api_status_change(self, new_status: str, last_sync: Optional[str]) -> None:
        mapped = "syncing" if new_status in ("syncing", "mfa_required") else ("error" if new_status == "error" else "idle")
        self.status = mapped
        if last_sync:
            self.last_sync_time = last_sync
        self._refresh_tray_ui()

    def _refresh_tray_ui(self) -> None:
        if not self.icon:
            return

        def _do_update() -> None:
            if self.icon:
                self.icon.icon = create_tray_icon(self.status)
                self.icon.update_menu()

        _dispatch_ui_thread(_do_update, is_main_loop_running=self._main_loop_active)

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
            # Primary Action: Open Control Center Window
            pystray.MenuItem(
                t("tray_open_control_center", lang),
                self._on_open_control_center,
                default=True,
            ),
            pystray.MenuItem(
                t("tray_sync_now", lang),
                self._on_sync_now,
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
    def _on_open_control_center(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self.open_control_center()

    def open_control_center(self, section: Optional[str] = None) -> str:
        """Ensures the local Control Center server is running and shows/opens the UI."""
        if self.server is None:
            self.server = PradoUIServer(api=self.api)
            self.server.start()

        target_url = self.server.url
        if section:
            target_url = f"{target_url}#{section}"

        if self.window is not None:
            try:
                self.window.show()
                self.window.restore()
                if section == "settings":
                    self.window.evaluate_js("openOnboardingModal(true)")
                elif section in ("dashboard", "courses", "mail", "calendar"):
                    self.window.evaluate_js(f"switchTab('{section}')")
                return target_url
            except Exception:
                pass

        open_url(target_url)
        return target_url

    def _on_sync_now(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self.trigger_sync()

    def _on_open_folder(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        open_folder(self.cfg.courses_root)

    def _on_open_calendar(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        cal_cfg = getattr(self.cfg, "calendar", None)
        gcal = getattr(cal_cfg, "google_calendar", None) if cal_cfg else None
        if gcal and getattr(gcal, "enabled", False) and getattr(gcal, "calendar_id", "auto") != "auto":
            open_url("https://calendar.google.com")
            return
        if self.api.gcalendar_enabled and self.api.gcalendar_id and self.api.gcalendar_id != "auto":
            open_url("https://calendar.google.com")
            return

        ics_path = self.cfg.courses_root / "deadlines.ics"
        if ics_path.exists():
            open_folder(ics_path)
        else:
            self.open_control_center("calendar")

    def _on_open_mail(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        if self.server is not None:
            self.open_control_center("mail")
        else:
            open_url("https://correo.ugr.es")

    def _on_toggle_notifications(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self.cfg.notifications.enabled = not self.cfg.notifications.enabled
        save_config(self.cfg)
        self._refresh_tray_ui()

    def _on_toggle_auto_sync(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self._auto_sync_enabled = not self._auto_sync_enabled
        self._refresh_tray_ui()

    def _on_open_settings(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        if self.server is not None:
            self.open_control_center("settings")
        else:
            threading.Thread(target=self._run_login_prompt, daemon=True).start()

    def _run_login_prompt(self) -> None:
        saved = prompt_login_gui(self.cfg)
        if saved:
            self.cfg = load_config()
            self.status = "idle"
            self._refresh_tray_ui()

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
            self._refresh_tray_ui()

            self.cfg = load_config()
            from prado.cli import _handle_sync

            cal_cfg = getattr(self.cfg, "calendar", None)
            gcal_cfg = getattr(cal_cfg, "google_calendar", None) if cal_cfg else None
            gcal_enabled = getattr(gcal_cfg, "enabled", self.api.gcalendar_enabled) if gcal_cfg else self.api.gcalendar_enabled
            gcal_id = getattr(gcal_cfg, "calendar_id", self.api.gcalendar_id) if gcal_cfg else self.api.gcalendar_id

            sync_args = argparse.Namespace(
                preset=self.cfg.sync.preset or None,
                dry_run=False,
                adopt=True,
                no_interactive=True,
                gui=True,
                code_callback=self.api._wait_for_mfa_code if self.server is not None else None,
                course=None,
                force=False,
                mail=self.cfg.mail.enabled,
                no_mail=not self.cfg.mail.enabled,
                gcalendar=gcal_enabled,
                gcalendar_token=None,
                calendar_id=gcal_id,
            )

            try:
                exit_code = _handle_sync(args=sync_args, json_mode=False)
            except (AuthenticationRequiredError, InvalidCredentialsError):
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
                if self.cfg.notifications.enabled:
                    self.notifier.notify(
                        title="PradoOS",
                        message=t("tray_sync_success_notification", self.cfg.language),
                    )
            else:
                self.status = "error"
                self.last_error = f"Exit code {exit_code}"
        except Exception as exc:
            self.status = "error"
            self.last_error = str(exc)
            if self.cfg.notifications.enabled:
                self.notifier.notify(
                    title="PradoOS",
                    message=t("tray_sync_error_notification", self.cfg.language, error=str(exc)),
                    urgency="critical",
                )
        finally:
            self._sync_lock.release()
            self._refresh_tray_ui()

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
                self.api.start_sync()

    # -------------------------------------------------------------------------
    # App Lifecycle (WebView Control Center + System Tray)
    # -------------------------------------------------------------------------
    def run(self, detached: bool = False, tray_only: bool = False) -> None:
        """
        Launches the PradoOS Control Center (native WebView window + System Tray icon).
        """
        if pystray is None:
            raise RuntimeError(
                "pystray is not installed. Install with 'pip install pystray pillow' to run the GUI app."
            )

        if is_headless_environment():
            raise RuntimeError(
                "Cannot launch PradoOS Desktop App in a headless or CI environment without a display server."
            )

        # 1. Start local Control Center loopback server (127.0.0.1:<port>)
        self.server = PradoUIServer(api=self.api)
        control_url = self.server.start()

        # 2. Initialize System Tray Icon
        initial_icon_img = create_tray_icon("idle")
        self.icon = pystray.Icon(
            name="PradoOS",
            icon=initial_icon_img,
            title="PradoOS — PRADO UGR",
            menu=self._build_menu(),
        )

        # 3. Start background auto-sync timer thread
        threading.Thread(target=self._auto_sync_loop, daemon=True).start()

        if detached:
            self.icon.run_detached()
            return

        self._main_loop_active = True

        # 4. If native WebView is available and not tray_only, open native Control Center window
        if webview is not None and not tray_only:
            try:
                self.icon.run_detached()
                self.window = webview.create_window(
                    title="PradoOS — Centro de Control Académico UGR",
                    url=control_url,
                    width=1180,
                    height=790,
                    min_size=(920, 620),
                )
                try:
                    self.window.events.closing += self._on_window_closing
                except Exception:
                    pass
                webview.start()
                self.stop()
                return
            except Exception:
                # Fallback if WebView backend fails to initialize: open in browser & run tray loop
                open_url(control_url)
                self.icon.run()
                return

        # Fallback when tray_only=True or pywebview is not installed
        if not tray_only:
            open_url(control_url)
        self.icon.run()

    def _on_window_closing(self) -> bool:
        """
        When the user closes the Control Center window (red X), hide it to the
        Menu Bar / System Tray instead of terminating the background daemon/tray,
        unless Quit was explicitly requested.
        """
        if self._quitting:
            return True
        if self.window is not None:
            try:
                self.window.hide()
                return False
            except Exception:
                pass
        return True

    def stop(self) -> None:
        """Stops the application, shuts down the local server, and closes the tray icon."""
        self._quitting = True
        self._running = False
        self._main_loop_active = False
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
        if self.server:
            self.server.stop()
            self.server = None
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass


def run_tray_app(detached: bool = False, tray_only: bool = False) -> int:
    """Entrypoint function for 'prado app', 'prado gui', and desktop executables."""
    try:
        app = PradoTrayApp()
        app.run(detached=detached, tray_only=tray_only)
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        sys.stderr.write(f"\n❌ PradoOS App Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_tray_app())
