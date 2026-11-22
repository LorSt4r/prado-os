"""
Unit tests verifying Windows desktop readiness, no-console-flash subprocess flags,
SingleInstanceGuard, tray-only hidden window lifecycle, frozen Doctor probes,
and Windows PyInstaller packaging arguments.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from prado.auth.credentials import prompt_gui_input
from prado.config import PradoConfig, prompt_folder_picker_gui
from prado.notifications.desktop import DesktopNotifier
from prado.scheduler.daemon import SchtasksBackend
from prado.scheduler.doctor import DoctorEngine, ProbeStatus
from prado.ui.dialogs import open_file
from prado.ui.instance import SingleInstanceGuard
from prado.ui.server import PradoControlCenterAPI, PradoUIServer
from prado.ui.tray import PradoTrayApp


def test_schtasks_passes_create_no_window_on_windows(monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    backend = SchtasksBackend()
    assert backend.install(interval_seconds=3600) is True
    assert backend.start() is True
    assert backend.stop() is True
    assert backend.uninstall() is True
    backend.status()

    # install calls uninstall() + create, then start, stop, uninstall, status => >= 5 calls
    assert len(calls) >= 5
    for cmd, kwargs in calls:
        assert cmd[0] == "schtasks.exe"
        assert kwargs.get("creationflags") == 0x08000000


def test_desktop_notifier_windows_winrt_and_no_window(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    notifier = DesktopNotifier(app_name="PradoOS")
    monkeypatch.setattr(notifier, "is_available", lambda: True)

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    ok = notifier.notify(title="PradoOS", message="Sync <done>", subtitle="ETSIIT")
    assert ok is True
    cmd = captured["cmd"]
    assert cmd[:3] == [cmd[0], "-NoProfile", "-NonInteractive"]
    script = cmd[-1]
    assert "ToastNotificationManager" in script
    assert "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}" in script
    assert "[System.Security.SecurityElement]::Escape" in script
    assert "Start-Sleep -Milliseconds 3500" in script
    assert "$notify.Visible = $False" in script
    assert "finally" in script
    assert captured["kwargs"].get("creationflags") == 0x08000000


def test_headless_menu_item_is_callable():
    from prado.ui.tray import _HeadlessMenuItem

    invoked = []
    item = _HeadlessMenuItem("Open", lambda icon=None, it=None: invoked.append((icon, it)))
    item("dummy-icon")
    assert invoked == [("dummy-icon", item)]


def test_prompt_folder_picker_windows_fast_tkinter_and_powershell_fallback(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    # 1. Fast tkinter IFileOpenDialog path
    monkeypatch.setattr(
        "prado.config.get_localized_desktop_dir",
        lambda: Path(r"C:\Users\Student\Desktop"),
    )
    tk_root = MagicMock()
    fake_fd = SimpleNamespace(
        askdirectory=MagicMock(return_value=r"C:\Users\Student\PickedViaTk")
    )
    fake_tk = SimpleNamespace(Tk=MagicMock(return_value=tk_root), filedialog=fake_fd)
    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", fake_fd)
    picked_tk = prompt_folder_picker_gui("Scegli cartella")
    assert picked_tk is not None
    assert str(picked_tk) == r"C:\Users\Student\PickedViaTk"
    tk_root.attributes.assert_called_once_with("-topmost", True)
    tk_root.destroy.assert_called_once()

    # 2. PowerShell Form.TopMost fallback when tkinter cannot initialize
    monkeypatch.setitem(sys.modules, "tkinter", None)
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout=r"C:\Users\Student\UGR_Courses" + "\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    picked = prompt_folder_picker_gui("Elige carpeta")
    assert picked is not None
    assert str(picked) == r"C:\Users\Student\UGR_Courses"
    cmd = captured["cmd"]
    assert "-WindowStyle" in cmd
    assert cmd[cmd.index("-WindowStyle") + 1] == "Hidden"
    ps_script = cmd[-1]
    assert "$owner.TopMost = $true" in ps_script
    assert "ShowDialog($owner)" in ps_script
    assert captured["kwargs"].get("creationflags") == 0x08000000


@pytest.mark.parametrize("hidden", [False, True])
def test_prompt_gui_input_windows_hidden_console(monkeypatch, hidden):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout="valor\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    out = prompt_gui_input(prompt="Introduce", hidden=hidden)
    assert out == "valor"
    cmd = captured["cmd"]
    assert "-WindowStyle" in cmd
    assert cmd[cmd.index("-WindowStyle") + 1] == "Hidden"
    assert captured["kwargs"].get("creationflags") == 0x08000000


def test_open_file_opens_existing_without_mkdir_and_rejects_missing(tmp_path: Path, monkeypatch):
    missing = tmp_path / "missing.ics"
    assert open_file(missing) is False
    assert not missing.exists()

    ics = tmp_path / "deadlines.ics"
    ics.write_text("BEGIN:VCALENDAR\nEND:VCALENDAR\n", encoding="utf-8")

    calls = []
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: calls.append(args))
    assert open_file(ics) is True
    assert ics.is_file()
    assert calls == [["open", str(ics.resolve())]]


def test_single_instance_guard_lifecycle(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))

    shown_events = []
    api = PradoControlCenterAPI(
        cfg=PradoConfig(courses_root=tmp_path / "Courses"),
        on_show_window=lambda: shown_events.append("shown"),
    )
    server = PradoUIServer(api=api)
    server.start()
    try:
        guard = SingleInstanceGuard()
        guard.register(server.port, server.token)
        assert guard.instance_file.exists()

        data = json.loads(guard.instance_file.read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()
        assert data["port"] == server.port
        assert data["token"] == server.token

        assert guard.try_activate_existing() is True
        assert shown_events == ["shown"]

        guard.release()
        assert not guard.instance_file.exists()
    finally:
        server.stop()

    # Stale port cleans up descriptor and returns False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        unused_port = s.getsockname()[1]

    stale_guard = SingleInstanceGuard()
    stale_guard.instance_file.write_text(
        json.dumps({"pid": 999999, "port": unused_port, "token": "dead-token"}),
        encoding="utf-8",
    )
    assert stale_guard.try_activate_existing(timeout=0.3) is False
    assert not stale_guard.instance_file.exists()


def test_tray_windows_menu_default_and_webview_folder_picker(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setattr(sys, "platform", "win32")

    cfg = PradoConfig(courses_root=tmp_path / "Courses", language="es")
    app = PradoTrayApp(cfg=cfg)
    menu = app._build_menu()
    items = [it for it in menu.items if getattr(it, "text", "- - - -") != "- - - -"]

    settings_item = next(it for it in items if "Configuración" in str(it.text) or "Ajustes" in str(it.text) or "Config" in str(it.text))
    sync_item = next(it for it in items if "Sincronizar" in str(it.text))
    assert settings_item.default is True
    assert sync_item.default is False

    # Native IFileDialog via pywebview window on Windows
    chosen_dir = tmp_path / "SelectedByWebview"
    fake_window = MagicMock()
    fake_window.create_file_dialog.return_value = (str(chosen_dir),)
    app.window = fake_window
    monkeypatch.setattr("prado.ui.tray.webview", SimpleNamespace(FOLDER_DIALOG=20))

    picked = app._pick_folder_webview("Pick folder")
    assert picked == chosen_dir
    fake_window.create_file_dialog.assert_called_once_with(20, directory=str(cfg.courses_root))


def test_tray_only_creates_hidden_webview_window(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setattr("prado.ui.tray.is_headless_environment", lambda: False)

    created_windows = []

    class _DummyEvent:
        def __iadd__(self, fn):
            return self

    class _DummyWindow:
        def __init__(self, **kwargs):
            created_windows.append(kwargs)
            self.events = SimpleNamespace(closing=_DummyEvent())

        def destroy(self):
            pass

    fake_webview = SimpleNamespace(
        create_window=lambda **kwargs: _DummyWindow(**kwargs),
        start=lambda func=None: func() if callable(func) else None,
    )
    fake_icon_instance = MagicMock()
    fake_pystray = SimpleNamespace(
        Icon=MagicMock(return_value=fake_icon_instance),
        Menu=lambda *items: items,
        MenuItem=lambda *args, **kwargs: SimpleNamespace(args=args, kwargs=kwargs),
    )
    fake_pystray.Menu.SEPARATOR = None

    monkeypatch.setattr("prado.ui.tray.webview", fake_webview)
    monkeypatch.setattr("prado.ui.tray.pystray", fake_pystray)
    monkeypatch.setattr("prado.ui.tray._PYSTRAY_AVAILABLE", True)

    app = PradoTrayApp(cfg=PradoConfig(courses_root=tmp_path / "Courses", language="es"))
    monkeypatch.setattr(app, "_build_menu", lambda: ())
    monkeypatch.setattr(app._instance_guard, "try_activate_existing", lambda: False)

    app.run(tray_only=True)
    assert len(created_windows) == 1
    assert created_windows[0]["hidden"] is True
    fake_icon_instance.run_detached.assert_called_once()


def test_doctor_frozen_desktop_cleans_false_warnings(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "prefix", sys.base_prefix)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    cfg = PradoConfig()
    cfg.sync.auto_sync = True
    cfg.sync.auto_sync_interval_minutes = 60
    doc = DoctorEngine(config=cfg)

    py_res = doc.probe_python_env()
    assert py_res.status == ProbeStatus.OK
    assert py_res.details["is_frozen"] is True
    assert "Desktop Bundle" in py_res.message

    monkeypatch.setattr(
        "prado.scheduler.doctor.DaemonManager.status",
        lambda self: SimpleNamespace(
            installed=False,
            active=False,
            backend="schtasks",
            schedule="hourly",
            to_dict=lambda: {"installed": False, "active": False, "backend": "schtasks"},
        ),
    )
    daemon_res = doc.probe_daemon_status()
    assert daemon_res.status == ProbeStatus.OK
    assert "Desktop Auto-Sync active" in daemon_res.message


def test_build_desktop_windows_collects_webview_and_instance(tmp_path: Path):
    import importlib.util

    script_path = Path(__file__).resolve().parents[2] / "scripts" / "build_desktop.py"
    spec = importlib.util.spec_from_file_location("build_desktop", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    args = mod.collect_pyinstaller_args(
        repo_root=tmp_path,
        target_platform="win32",
        has_module=lambda name: name in ("webview", "clr_loader", "pythonnet", "cffi"),
    )
    assert "--collect-all=webview" in args
    assert "--collect-all=clr_loader" in args
    assert "--collect-all=pythonnet" in args
    assert "--collect-all=cffi" in args
    assert "--hidden-import=webview.platforms.edgechromium" in args
    assert "--hidden-import=webview.platforms.winforms" in args
    assert "--hidden-import=webview.guilib" in args
    assert "--hidden-import=_cffi_backend" in args
    assert "--hidden-import=tkinter" in args
    assert "--hidden-import=prado.ui.instance" in args
    assert "--hidden-import=pystray._win32" in args


def test_mfa_callback_cancel_and_factor_extraction(monkeypatch):
    from prado.auth.mfa import MfaResolver
    from prado.exceptions import MfaRequiredError

    called_fallback = []
    monkeypatch.setattr(
        "prado.auth.credentials.prompt_gui_input",
        lambda **kw: called_fallback.append(kw) or "123456",
    )

    resolver = MfaResolver(interactive=False, gui_mode=True, code_callback=lambda: None)
    with pytest.raises(MfaRequiredError, match="cancelled"):
        resolver.resolve_code()
    assert called_fallback == []

    html_totp = '<form action="/admin/tool/mfa/auth.php"><input type="hidden" name="factor" value="totp"></form>'
    assert MfaResolver.extract_mfa_factor(html_totp) == "totp"
    assert MfaResolver.extract_mfa_factor("<form></form>") == "email"


def test_desktop_folder_auto_subdir_and_4lang_sync_steps(tmp_path: Path, monkeypatch):
    from prado.i18n import t

    cfg_dir = tmp_path / "cfg"
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(cfg_dir))
    desktop = tmp_path / "Desktop"
    desktop.mkdir()

    api = PradoControlCenterAPI(
        cfg=PradoConfig(courses_root=tmp_path / "Courses", language="it"),
        folder_picker_callback=lambda prompt: desktop,
    )
    picked = api.pick_folder_native()
    assert picked["status"] == "success"
    assert Path(picked["path"]) == desktop.resolve() / "PRADO_UGR"

    # Existing PRADO folder or named subfolder stays as-is
    custom = tmp_path / "Appunti_Uni"
    custom.mkdir()
    (custom / "DASHBOARD.md").write_text("# Dash", encoding="utf-8")
    api2 = PradoControlCenterAPI(
        cfg=PradoConfig(courses_root=tmp_path / "Courses", language="en"),
        folder_picker_callback=lambda prompt: custom,
    )
    picked2 = api2.pick_folder_native()
    assert Path(picked2["path"]) == custom.resolve()

    for lang in ("es", "en", "it", "fr"):
        assert t("sync_step_auth", lang) != "sync_step_auth"
        assert t("picker_choose_folder", lang) != "picker_choose_folder"


def test_frontend_privacy_note_sync_done_modal_and_error_banner():
    from prado.ui.frontend import render_control_center_html

    html = render_control_center_html(token="test-tok")
    assert "privacyNoteBox" in html
    assert "privacy_inline_note" in html
    assert "syncDoneModal" in html
    assert "chkHideSyncDone" in html
    assert "st.sync.last_error" in html
    assert "Verifica codice" in html
    assert "Verifica (30 giorni)" not in html


def test_tray_logs_webview_failure_without_double_running_icon(tmp_path: Path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(cfg_dir))
    monkeypatch.setattr("prado.ui.tray.is_headless_environment", lambda: False)

    opened_urls = []
    monkeypatch.setattr("prado.ui.tray.open_url", lambda u: opened_urls.append(u) or True)

    fake_icon = MagicMock()
    fake_pystray = SimpleNamespace(
        Icon=MagicMock(return_value=fake_icon),
        Menu=lambda *items: items,
        MenuItem=lambda *args, **kwargs: SimpleNamespace(args=args, kwargs=kwargs),
    )
    fake_pystray.Menu.SEPARATOR = None

    class _DummyWindow:
        def __init__(self):
            self.events = SimpleNamespace(closing=MagicMock())

    def _failing_start(func=None):
        if callable(func):
            func()
        raise RuntimeError("WebView2 missing on test host")

    fake_webview = SimpleNamespace(
        create_window=lambda **kwargs: _DummyWindow(),
        start=_failing_start,
    )

    monkeypatch.setattr("prado.ui.tray.pystray", fake_pystray)
    monkeypatch.setattr("prado.ui.tray._PYSTRAY_AVAILABLE", True)
    monkeypatch.setattr("prado.ui.tray.webview", fake_webview)

    app = PradoTrayApp(cfg=PradoConfig(courses_root=tmp_path / "Courses", language="it"))
    monkeypatch.setattr(app, "_build_menu", lambda: ())
    monkeypatch.setattr(app._instance_guard, "try_activate_existing", lambda: False)

    # Stop loop quickly after webview failure if tray_started is True
    def stop_soon(*args, **kwargs):
        app._running = False

    monkeypatch.setattr("prado.ui.tray.time.sleep", stop_soon)
    app.run(tray_only=False)

    log_file = cfg_dir / "desktop.log"
    assert log_file.exists()
    assert "WebView2 missing on test host" in log_file.read_text(encoding="utf-8")
    assert len(opened_urls) == 1
    fake_icon.run_detached.assert_called_once()
    fake_icon.run.assert_not_called()
    app.stop()


def test_single_instance_os_lock_windows_mutex_and_proxy_bypass(tmp_path: Path, monkeypatch):
    import ctypes
    import urllib.request

    inst_file = tmp_path / "tray_instance.json"
    inst_file.write_text(json.dumps({"pid": 1234, "port": 54321, "token": "tok-1"}), encoding="utf-8")

    # 1. Windows named Mutex (ERROR_ALREADY_EXISTS = 183) blocks duplicate without deleting file
    monkeypatch.setattr(sys, "platform", "win32")
    closed_handles = []
    fake_kernel32 = SimpleNamespace(
        CreateMutexW=MagicMock(return_value=999),
        GetLastError=MagicMock(return_value=183),
        CloseHandle=MagicMock(side_effect=lambda h: closed_handles.append(h)),
    )
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(kernel32=fake_kernel32), raising=False)

    handlers_used = []
    real_build_opener = urllib.request.build_opener

    def _spy_build_opener(*handlers):
        handlers_used.extend(handlers)
        class _FakeOpener:
            def open(self, req, timeout=1.0):
                raise OSError("booting")
        return _FakeOpener()

    monkeypatch.setattr(urllib.request, "build_opener", _spy_build_opener)
    guard_win = SingleInstanceGuard(instance_file=inst_file)
    assert guard_win.acquire_or_activate(timeout=0.05, wait_for_ready=0.05) is False
    assert not inst_file.exists()  # stale cleanup runs once on initial try_activate_existing
    assert 999 in closed_handles
    assert any(isinstance(h, urllib.request.ProxyHandler) and h.proxies == {} for h in handlers_used)

    # Restore valid instance file for booting-mutex non-cleanup verification
    inst_file.write_text(json.dumps({"pid": 1234, "port": 54321, "token": "tok-2"}), encoding="utf-8")
    monkeypatch.setattr(guard_win, "try_activate_existing", lambda: False)
    assert guard_win.acquire_or_activate(timeout=0.05, wait_for_ready=0.05) is False
    assert inst_file.exists()  # Booting secondary check MUST NOT unlink active instance descriptor

    monkeypatch.setattr(urllib.request, "build_opener", real_build_opener)

    # 2. POSIX flock mutual exclusion
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "name", "posix")
    g1 = SingleInstanceGuard(instance_file=tmp_path / "posix_inst.json")
    g2 = SingleInstanceGuard(instance_file=tmp_path / "posix_inst.json")
    assert g1.acquire_lock() is True
    assert g2.acquire_lock() is False
    g1.release()
    assert g2.acquire_lock() is True
    g2.release()


def test_tray_stop_hides_icon_syncs_interval_and_normalizes_folder(tmp_path: Path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(cfg_dir))
    cfg = PradoConfig(courses_root=tmp_path / "Courses", language="it")
    app = PradoTrayApp(cfg=cfg)

    events = []
    class _TrackedIcon:
        def __init__(self):
            self._visible = True
        @property
        def visible(self):
            return self._visible
        @visible.setter
        def visible(self, val):
            self._visible = val
            events.append(("visible", val))
        def stop(self):
            events.append(("stop", True))

    app.icon = _TrackedIcon()
    app.stop()
    app.stop()  # idempotent second call
    assert events == [("visible", False), ("stop", True)]
    assert app.icon is None

    # Refresh interval as well as enabled flag on API status update
    app.api.cfg.sync.auto_sync = True
    app.api.cfg.sync.auto_sync_interval_minutes = 30
    app._on_api_status_change("idle", "12:00")
    assert app._auto_sync_enabled is True
    assert app._auto_sync_interval_mins == 30

    # Tray folder picker normalizes Desktop -> Desktop/PRADO_UGR
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    monkeypatch.setattr(app, "_pick_folder_webview", lambda prompt: desktop)
    monkeypatch.setattr("prado.ui.tray.threading.Thread", lambda target, daemon=True: SimpleNamespace(start=lambda: target()))
    app._on_pick_folder()
    assert app.cfg.courses_root == desktop.resolve() / "PRADO_UGR"


def test_folder_normalization_onedrive_and_onboarding_save(tmp_path: Path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(cfg_dir))
    monkeypatch.setenv("PRADO_KEYRING_BACKEND", "vault")

    onedrive = tmp_path / "OneDrive - Personal"
    onedrive.mkdir()
    assert PradoControlCenterAPI._normalize_picked_courses_root(onedrive) == onedrive.resolve() / "PRADO_UGR"

    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    api = PradoControlCenterAPI(
        cfg=PradoConfig(courses_root=tmp_path / "Init", language="it"),
        folder_picker_callback=lambda prompt: desktop,
    )
    picked = api.pick_folder_native()
    assert picked["status"] == "success"
    assert picked["auto_subfolder"] is True
    assert Path(picked["path"]) == desktop.resolve() / "PRADO_UGR"

    custom = tmp_path / "MisApuntes"
    custom.mkdir()
    api2 = PradoControlCenterAPI(
        cfg=PradoConfig(courses_root=tmp_path / "Init", language="es"),
        folder_picker_callback=lambda prompt: custom,
    )
    picked2 = api2.pick_folder_native()
    assert picked2["auto_subfolder"] is False

    res = api.save_onboarding_and_login(
        {
            "language": "it",
            "username": "student@correo.ugr.es",
            "password": "secret-password",
            "courses_root": str(desktop),
            "auto_sync": True,
            "auto_sync_interval_minutes": 60,
            "start_sync": False,
        }
    )
    assert res["status"] == "success"
    assert Path(res["courses_root"]) == desktop.resolve() / "PRADO_UGR"


def test_frontend_autosync_onboarding_and_folder_helper():
    from prado.ui.frontend import render_control_center_html

    html = render_control_center_html(token="tok-auto")
    assert "onbAutoSyncQuick" in html
    assert "folder_helper" in html
    assert "lbl_onb_autosync_title" in html
    assert "sync_done_next_2_auto" in html
    assert "sync_done_next_2_manual" in html
    assert "toast_auto_subfolder" in html
    assert "const effectiveAutoSync = isConnected ? Boolean(st.config.auto_sync) : true;" in html
