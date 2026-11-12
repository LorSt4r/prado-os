"""
PradoOS Desktop Orchestrator: Rich Hierarchical System Tray + Compact Setup Card.

Follows the Dropbox / Tailscale / Google Drive Desktop architecture:
1. 100% of daily controls live in the OS Menu Bar / System Tray (`pystray`) with
   native cascading submenus for Enrolled Courses, Upcoming Deadlines, UGR Mail
   Auto-Forwarding, Folder Preset (Mirror/Smart), Language (ES/EN/IT/FR), and Doctor.
2. A single compact native window (520x630px via `pywebview`) for quick Account Setup
   and live 6-digit MFA verification.
"""

from __future__ import annotations

import argparse
import datetime
from pathlib import Path
import sys
import threading
import time
from typing import Any, Callable, List, Optional

class _HeadlessMenuItem:
    """Fallback MenuItem representation when running on headless Linux without X11."""

    def __init__(
        self,
        text: Any,
        action: Any = None,
        checked: Any = None,
        radio: bool = False,
        default: bool = False,
        visible: bool = True,
        enabled: bool = True,
    ) -> None:
        self._text = text
        self.submenu = action if isinstance(action, _HeadlessMenu) else None
        self.action = None if self.submenu is not None else action
        self.checked = checked
        self.radio = radio
        self.default = default
        self.visible = visible
        self.enabled = enabled

    @property
    def text(self) -> str:
        return str(self._text(self)) if callable(self._text) else str(self._text)


class _HeadlessMenu:
    """Fallback Menu representation when running on headless Linux without X11."""

    SEPARATOR: Any = None

    def __init__(self, *items: Any) -> None:
        self.items = tuple(items)

    def __iter__(self):
        return iter(self.items)


_HeadlessMenu.SEPARATOR = _HeadlessMenuItem("- - - -", None)


class _HeadlessPystrayStub:
    Menu = _HeadlessMenu
    MenuItem = _HeadlessMenuItem
    Icon = None


try:
    import pystray

    _PYSTRAY_AVAILABLE = True
except Exception:
    pystray = _HeadlessPystrayStub  # type: ignore[assignment]
    _PYSTRAY_AVAILABLE = False

try:
    import webview
except Exception:
    webview = None  # type: ignore[assignment]

from prado import __version__
from prado.config import PradoConfig, load_config, save_config
from prado.exceptions import AuthenticationRequiredError, InvalidCredentialsError
from prado.i18n import t
from prado.notifications.desktop import DesktopNotifier, is_headless_environment
from prado.onboarding.wizard import prompt_folder_picker_gui
from prado.state import StateDatabase
from prado.ui.dialogs import open_folder, open_url, prompt_login_gui
from prado.ui.icon import create_tray_icon
from prado.ui.server import PradoControlCenterAPI, PradoUIServer, parse_deadlines_from_ics


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
    Unified System Tray / Menu Bar controller + Compact Setup Card for PradoOS.
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
        self._auto_sync_enabled = bool(getattr(self.cfg.sync, "auto_sync", False))
        self._auto_sync_interval_mins = max(
            5, int(getattr(self.cfg.sync, "auto_sync_interval_minutes", 60) or 60)
        )
        self.icon: Optional[pystray.Icon] = None
        self.notifier = DesktopNotifier(app_name="PradoOS")

        # Shared API & Local Loopback Server for the compact Setup / 2FA window
        self.api = PradoControlCenterAPI(cfg=self.cfg, on_status_change=self._on_api_status_change)
        self.server: Optional[PradoUIServer] = None
        self.window: Optional[Any] = None

    def _on_api_status_change(self, new_status: str, last_sync: Optional[str]) -> None:
        self.cfg = self.api.cfg
        self._auto_sync_enabled = bool(getattr(self.cfg.sync, "auto_sync", False))
        mapped = "syncing" if new_status in ("syncing", "mfa_required") else ("error" if new_status == "error" else "idle")
        self.status = mapped
        if last_sync:
            self.last_sync_time = last_sync
        if new_status == "mfa_required" and self.window is not None:
            try:
                self.window.show()
                self.window.restore()
            except Exception:
                pass
        self._refresh_tray_ui()

    def _refresh_tray_ui(self) -> None:
        if not self.icon:
            return

        def _do_update() -> None:
            if self.icon:
                self.icon.icon = create_tray_icon(
                    self.status, monochrome=(sys.platform == "darwin")
                )
                self._apply_macos_template_icon(self.icon)
                self.icon.menu = self._build_menu()
                self.icon.update_menu()

        _dispatch_ui_thread(_do_update, is_main_loop_running=self._main_loop_active)

    @staticmethod
    def _apply_macos_template_icon(icon_obj: Any) -> None:
        """
        Marks the Cocoa NSImage backing `pystray.Icon` as a monochrome template image
        and wraps `_assert_image` so the first frame rendered by `run_detached()` is also a template.
        """
        if sys.platform != "darwin" or icon_obj is None:
            return
        try:
            if not getattr(icon_obj, "_prado_template_wrapped", False):
                orig_assert = getattr(icon_obj, "_assert_image", None)
                if callable(orig_assert):
                    def _wrapped_assert() -> None:
                        orig_assert()
                        ns_img = getattr(icon_obj, "_icon_image", None)
                        if ns_img is not None and hasattr(ns_img, "setTemplate_"):
                            ns_img.setTemplate_(True)
                            st_item = getattr(icon_obj, "_status_item", None)
                            if st_item is not None and hasattr(st_item, "button"):
                                st_item.button().setImage_(ns_img)

                    setattr(icon_obj, "_assert_image", _wrapped_assert)
                    setattr(icon_obj, "_prado_template_wrapped", True)

            ns_img = getattr(icon_obj, "_icon_image", None)
            if ns_img is not None and hasattr(ns_img, "setTemplate_"):
                ns_img.setTemplate_(True)
                st_item = getattr(icon_obj, "_status_item", None)
                if st_item is not None and hasattr(st_item, "button"):
                    st_item.button().setImage_(ns_img)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Status & Labels (i18n aware)
    # -------------------------------------------------------------------------
    def _get_status_text(self) -> str:
        lang = self.cfg.language or "es"
        if self.status == "syncing":
            return t("tray_status_syncing", lang)
        elif self.status == "error":
            err = self.last_error or getattr(self.api, "last_error", None)
            base = t("tray_status_error", lang)
            return f"{base}: {str(err)[:36]}" if err else base
        return f"{t('tray_status_idle', lang)} · {self.last_sync_time or '--:--'}"

    def _get_last_sync_text(self) -> str:
        lang = self.cfg.language or "es"
        if self.last_sync_time:
            return t("tray_last_sync", lang, time=self.last_sync_time)
        return t("tray_last_sync", lang, time="--:--")

    # -------------------------------------------------------------------------
    # Hierarchical Submenu Builders (Courses, Deadlines, Mail, Language)
    # -------------------------------------------------------------------------
    def _build_courses_submenu(self, lang: str) -> tuple[str, pystray.Menu]:
        course_items: List[Any] = []
        courses_found = 0
        try:
            state_db = StateDatabase()
            courses = state_db.list_all_courses()
            for c in courses:
                courses_found += 1
                label = f"📂 {c.fullname[:44]}"

                def _make_open_course(cname: str, sname: str) -> Callable[..., None]:
                    def _cb(icon: Any = None, item: Any = None) -> None:
                        for cand in (cname, sname):
                            if cand and (self.cfg.courses_root / cand).exists():
                                open_folder(self.cfg.courses_root / cand)
                                return
                        open_folder(self.cfg.courses_root)

                    return _cb

                course_items.append(pystray.MenuItem(label, _make_open_course(c.fullname, c.shortname or "")))
        except Exception:
            pass

        if not course_items and self.cfg.courses_root.exists():
            try:
                for sub in sorted(self.cfg.courses_root.iterdir()):
                    if sub.is_dir() and not sub.name.startswith("."):
                        courses_found += 1

                        def _make_open_dir(p: Path) -> Callable[..., None]:
                            return lambda icon=None, item=None: open_folder(p)

                        course_items.append(pystray.MenuItem(f"📂 {sub.name[:44]}", _make_open_dir(sub)))
            except Exception:
                pass

        if not course_items:
            course_items.append(pystray.MenuItem(t("tray_courses_empty", lang), action=None, enabled=False))

        course_items.extend(
            [
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    t("tray_preset_mirror", lang),
                    lambda icon=None, item=None: self._set_preset("mirror"),
                    checked=lambda item: (self.cfg.sync.preset or "mirror") == "mirror",
                ),
                pystray.MenuItem(
                    t("tray_preset_smart", lang),
                    lambda icon=None, item=None: self._set_preset("smart"),
                    checked=lambda item: self.cfg.sync.preset == "smart",
                ),
                pystray.MenuItem(
                    t("tray_change_folder", lang),
                    self._on_pick_folder,
                ),
            ]
        )
        title = t("tray_courses_menu", lang, count=courses_found)
        return title, pystray.Menu(*course_items)

    def _open_deadline_course(self, course_name: str) -> None:
        """Opens the course folder matching a deadline, or falls back to deadlines.ics."""
        needle = (course_name or "").strip().lower()
        if needle and self.cfg.courses_root.exists():
            norm_needle = needle.replace(" ", "_")
            try:
                for sub in sorted(self.cfg.courses_root.iterdir()):
                    if not sub.is_dir() or sub.name.startswith("."):
                        continue
                    sname = sub.name.lower()
                    if needle in sname or norm_needle in sname or sname in needle:
                        open_folder(sub)
                        return
            except Exception:
                pass
            try:
                state_db = StateDatabase()
                for c in state_db.list_all_courses():
                    if needle in (c.fullname or "").lower() or needle in (c.shortname or "").lower():
                        for cand in (c.fullname, c.shortname or ""):
                            if cand and (self.cfg.courses_root / cand).exists():
                                open_folder(self.cfg.courses_root / cand)
                                return
            except Exception:
                pass
        self._on_open_calendar()

    def _build_deadlines_submenu(self, lang: str) -> tuple[str, pystray.Menu]:
        ics_path = self.cfg.courses_root / "deadlines.ics"
        events = parse_deadlines_from_ics(ics_path)
        dl_items: List[Any] = []

        for ev in events[:6]:
            prefix = "🚨" if ev.get("kind") == "EXAM" else "📝"
            days = ev.get("days_left", 0)
            days_str = f"{days}d" if days >= 0 else t("tray_deadline_overdue", lang)
            course_label = str(ev.get("course", ""))
            lbl = f"{prefix} {ev['due_iso'][:10]} — [{course_label[:18]}] {ev['title'][:28]} ({days_str})"

            def _make_dl_cb(cname: str) -> Callable[..., None]:
                return lambda icon=None, item=None: self._open_deadline_course(cname)

            dl_items.append(pystray.MenuItem(lbl, _make_dl_cb(course_label)))

        if not dl_items:
            dl_items.append(pystray.MenuItem(t("tray_deadlines_empty", lang), action=None, enabled=False))

        dl_items.extend(
            [
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(t("tray_sync_gcal", lang), self._on_sync_gcalendar),
                pystray.MenuItem(t("tray_open_ics", lang), self._on_open_calendar),
                pystray.MenuItem(t("tray_open_gcal_web", lang), lambda icon=None, item=None: open_url("https://calendar.google.com")),
            ]
        )
        title = t("tray_deadlines_menu", lang, count=len(events))
        return title, pystray.Menu(*dl_items)

    def _build_mail_submenu(self, lang: str) -> pystray.Menu:
        target = f"(→ {self.cfg.mail.forward_to})" if self.cfg.mail.forward_to else ""
        return pystray.Menu(
            pystray.MenuItem(
                t("tray_mail_forward_toggle", lang, target=target).strip(),
                self._on_toggle_mail_forwarding,
                checked=lambda item: bool(self.cfg.mail.forward_enabled),
            ),
            pystray.MenuItem(
                t("tray_mail_check_now", lang),
                self._on_check_mail_now,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                t("tray_open_mail", lang),
                self._on_open_mail,
            ),
        )

    def _build_language_submenu(self) -> pystray.Menu:
        langs = [
            ("es", "🇪🇸 Español"),
            ("en", "🇬🇧 English"),
            ("it", "🇮🇹 Italiano"),
            ("fr", "🇫🇷 Français"),
        ]
        items = []
        for code, label in langs:

            def _make_lang_cb(c: str) -> Callable[..., None]:
                return lambda icon=None, item=None: self._set_language(c)

            items.append(
                pystray.MenuItem(
                    label,
                    _make_lang_cb(code),
                    checked=lambda item, c=code: (self.cfg.language or "es") == c,
                )
            )
        return pystray.Menu(*items)

    # -------------------------------------------------------------------------
    # Main System Tray Menu Construction (<= 10 top-level items per desktop HIG)
    # -------------------------------------------------------------------------
    def _build_help_submenu(self, lang: str) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(
                t("tray_auto_sync", lang),
                self._on_toggle_auto_sync,
                checked=lambda item: self._auto_sync_enabled,
            ),
            pystray.MenuItem(
                t("tray_notifications", lang),
                self._on_toggle_notifications,
                checked=lambda item: self.cfg.notifications.enabled,
            ),
            pystray.MenuItem(
                t("tray_lang_menu", lang),
                self._build_language_submenu(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                t("tray_doctor", lang),
                self._on_run_doctor,
            ),
            pystray.MenuItem(
                t("tray_github", lang),
                self._on_open_github,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"PradoOS v{__version__}", action=None, enabled=False),
        )

    def _build_menu(self) -> pystray.Menu:
        lang = self.cfg.language or "es"
        courses_title, courses_menu = self._build_courses_submenu(lang)
        deadlines_title, deadlines_menu = self._build_deadlines_submenu(lang)

        entries: List[Any] = [
            pystray.MenuItem(lambda item: self._get_status_text(), action=None, enabled=False),
        ]
        if self.status == "error":
            entries.append(
                pystray.MenuItem(
                    t("tray_error_action", lang),
                    self._on_open_settings,
                )
            )

        entries.extend(
            [
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    t("tray_sync_now", lang),
                    self._on_sync_now,
                    default=True,
                ),
                pystray.MenuItem(
                    t("tray_open_folder", lang),
                    self._on_open_folder,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(courses_title, courses_menu),
                pystray.MenuItem(deadlines_title, deadlines_menu),
                pystray.MenuItem(t("tray_mail_menu", lang), self._build_mail_submenu(lang)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    t("tray_settings", lang),
                    self._on_open_settings,
                ),
                pystray.MenuItem(
                    t("tray_help_menu", lang),
                    self._build_help_submenu(lang),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    t("tray_quit", lang),
                    self._on_quit,
                ),
            ]
        )
        return pystray.Menu(*entries)

    # -------------------------------------------------------------------------
    # Menu Callbacks
    # -------------------------------------------------------------------------
    def _on_open_control_center(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self.open_control_center()

    def open_control_center(self, section: Optional[str] = None) -> str:
        """Shows the compact Setup & Quick-Configure card."""
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
                return target_url
            except Exception:
                pass

        open_url(target_url)
        return target_url

    def _on_sync_now(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self.trigger_sync()

    def _on_open_folder(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        open_folder(self.cfg.courses_root)

    def _set_preset(self, preset: str) -> None:
        if preset in ("mirror", "smart"):
            self.cfg.sync.preset = preset
            save_config(self.cfg)
            self._refresh_tray_ui()

    def _on_pick_folder(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        def _worker() -> None:
            chosen = prompt_folder_picker_gui()
            if chosen:
                self.cfg.courses_root = chosen
                self.cfg.courses_root.mkdir(parents=True, exist_ok=True)
                save_config(self.cfg)
                self._refresh_tray_ui()

        threading.Thread(target=_worker, daemon=True).start()

    def _on_open_calendar(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        ics_path = self.cfg.courses_root / "deadlines.ics"
        if not ics_path.exists():
            self.api.run_calendar_action("open_ics")
            return
        open_folder(ics_path)

    def _on_sync_gcalendar(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        def _worker() -> None:
            lang = self.cfg.language or "es"
            res = self.api.run_calendar_action("gcalendar")
            if self.cfg.notifications.enabled:
                msg = (
                    t("tray_gcal_synced", lang)
                    if res.get("status") == "success"
                    else t("tray_gcal_error", lang, error=str(res.get("error", "")))
                )
                self.notifier.notify(title="PradoOS Calendar", message=msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_toggle_mail_forwarding(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        if not self.cfg.mail.forward_to and not self.cfg.mail.forward_enabled:
            self.open_control_center("settings")
            return
        self.cfg.mail.forward_enabled = not self.cfg.mail.forward_enabled
        save_config(self.cfg)
        self._refresh_tray_ui()

    def _on_check_mail_now(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        def _worker() -> None:
            lang = self.cfg.language or "es"
            res = self.api.fetch_mail_inbox(refresh=True)
            if self.cfg.notifications.enabled and res.get("status") == "success":
                self.notifier.notify(
                    title=t("tray_mail_unread_title", lang),
                    message=t("tray_mail_unread_msg", lang, count=res.get("unread", 0)),
                )

        threading.Thread(target=_worker, daemon=True).start()

    def _on_open_mail(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        open_url("https://webmailest.ugr.es")

    def _set_language(self, lang_code: str) -> None:
        self.cfg.language = lang_code
        save_config(self.cfg)
        self.api.update_language(lang_code)
        self._refresh_tray_ui()

    def _on_run_doctor(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        def _worker() -> None:
            lang = self.cfg.language or "es"
            res = self.api.run_doctor()
            probes = res.get("probes", [])
            ok_count = sum(1 for p in probes if p.get("status") == "OK")
            self.notifier.notify(
                title="PradoOS Doctor",
                message=t("tray_doctor_result", lang, ok=ok_count, total=len(probes)),
            )

        threading.Thread(target=_worker, daemon=True).start()

    def _on_toggle_notifications(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self.cfg.notifications.enabled = not self.cfg.notifications.enabled
        save_config(self.cfg)
        self._refresh_tray_ui()

    def _on_toggle_auto_sync(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self._auto_sync_enabled = not self._auto_sync_enabled
        self.cfg.sync.auto_sync = self._auto_sync_enabled
        save_config(self.cfg)
        self._refresh_tray_ui()

    def _on_open_settings(self, icon: Optional[pystray.Icon] = None, item: Any = None) -> None:
        self.open_control_center("settings")

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
    # App Lifecycle (System Tray + Compact Setup Card)
    # -------------------------------------------------------------------------
    def run(self, detached: bool = False, tray_only: bool = False) -> None:
        """
        Launches PradoOS in the OS Menu Bar / System Tray + Compact Setup Card.
        """
        if is_headless_environment():
            raise RuntimeError(
                "Cannot launch PradoOS Desktop App in a headless or CI environment without a display server."
            )

        if not _PYSTRAY_AVAILABLE or getattr(pystray, "Icon", None) is None:
            raise RuntimeError(
                "pystray is not installed. Install with 'pip install pystray pillow' to run the GUI app."
            )

        # 1. Start local loopback server for the compact Setup / 2FA window
        self.server = PradoUIServer(api=self.api)
        control_url = self.server.start()

        # 2. Initialize System Tray Icon (monochrome template on macOS HIG)
        initial_icon_img = create_tray_icon(
            "idle", monochrome=(sys.platform == "darwin")
        )
        self.icon = pystray.Icon(
            name="PradoOS",
            icon=initial_icon_img,
            title="PradoOS — PRADO UGR",
            menu=self._build_menu(),
        )
        self._apply_macos_template_icon(self.icon)

        # 3. Start background auto-sync timer thread
        threading.Thread(target=self._auto_sync_loop, daemon=True).start()

        if detached:
            self.icon.run_detached()
            return

        self._main_loop_active = True

        # 4. Open compact single-screen Setup Card (520x630px) alongside the System Tray
        if webview is not None and not tray_only:
            try:
                self.icon.run_detached()
                self.window = webview.create_window(
                    title=t("tray_window_title", self.cfg.language or "es"),
                    url=control_url,
                    width=525,
                    height=640,
                    min_size=(460, 560),
                    resizable=True,
                )
                try:
                    self.window.events.closing += self._on_window_closing
                except Exception:
                    pass
                webview.start()
                self.stop()
                return
            except Exception:
                open_url(control_url)
                self.icon.run()
                return

        if not tray_only:
            open_url(control_url)
        self.icon.run()

    def _on_window_closing(self) -> bool:
        """
        When the user closes the compact Setup Card (red X), hide it to the
        Menu Bar / System Tray instead of terminating the background daemon/tray.
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
