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
    assert "[System.Security.SecurityElement]::Escape" in script
    assert "Start-Sleep -Milliseconds 3500" in script
    assert captured["kwargs"].get("creationflags") == 0x08000000


def test_prompt_folder_picker_windows_topmost_and_no_window(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

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
        start=lambda: None,
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
        has_module=lambda name: name in ("webview", "clr_loader", "pythonnet"),
    )
    assert "--collect-all=webview" in args
    assert "--collect-all=clr_loader" in args
    assert "--collect-all=pythonnet" in args
    assert "--hidden-import=webview.platforms.edgechromium" in args
    assert "--hidden-import=webview.platforms.winforms" in args
    assert "--hidden-import=prado.ui.instance" in args
    assert "--hidden-import=pystray._win32" in args
