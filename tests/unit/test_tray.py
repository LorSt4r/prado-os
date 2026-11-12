"""
Unit tests for PradoOS System Tray / Menu Bar Application.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from prado.config import PradoConfig
from prado.ui.icon import create_tray_icon
from prado.ui.tray import PradoTrayApp, run_tray_app


def test_tray_app_initialization(tmp_path: Path):
    cfg = PradoConfig(courses_root=tmp_path / "Courses", language="es")
    app = PradoTrayApp(cfg=cfg)

    assert app.status == "idle"
    assert app.last_sync_time is None
    assert app.last_error is None
    assert not app._auto_sync_enabled
    assert app.cfg.courses_root == tmp_path / "Courses"


def test_tray_menu_structure_and_labels(tmp_path: Path):
    cfg = PradoConfig(courses_root=tmp_path / "Courses", language="es")
    app = PradoTrayApp(cfg=cfg)
    menu = app._build_menu()

    items = list(menu.items)
    non_sep_items = [it for it in items if getattr(it, "text", "- - - -") != "- - - -"]
    assert 7 <= len(non_sep_items) <= 10

    # Status & Last sync texts
    assert "Al día" in app._get_status_text()
    assert "--:--" in app._get_last_sync_text()

    # Change to syncing
    app.status = "syncing"
    assert "Sincronizando" in app._get_status_text()

    # Change to error -> actionable recovery item appears and top-level count remains <= 10
    app.status = "error"
    app.last_error = "Credenciales inválidas"
    assert "Error" in app._get_status_text()
    assert "Credenciales inválidas" in app._get_status_text()
    err_menu_items = list(app._build_menu().items)
    err_non_sep = [it for it in err_menu_items if getattr(it, "text", "- - - -") != "- - - -"]
    assert len(err_non_sep) <= 10
    assert any("Revisar cuenta" in str(it.text) for it in err_non_sep)

    # Verify cascading submenus exist (Courses, Deadlines, Mail, Help->Language)
    submenu_titles = [str(it.text) for it in items if getattr(it, "submenu", None) is not None]
    assert any("Asignaturas" in t for t in submenu_titles)
    assert any("Entregas" in t for t in submenu_titles)
    assert any("Correo UGR" in t for t in submenu_titles)
    assert any("Preferencias y Ayuda" in t for t in submenu_titles)
    help_item = next(it for it in items if "Preferencias y Ayuda" in str(it.text))
    help_subtitles = [str(sub.text) for sub in help_item.submenu.items]
    assert any("Idioma" in t for t in help_subtitles)
    assert any("Diagnóstico" in t for t in help_subtitles)


def test_tray_open_settings_always_uses_setup_card(tmp_path: Path, monkeypatch):
    cfg = PradoConfig(courses_root=tmp_path / "Courses", language="es")
    app = PradoTrayApp(cfg=cfg)
    app.server = None
    called = []
    monkeypatch.setattr(app, "open_control_center", lambda section=None: called.append(section) or "http://127.0.0.1:12345")
    app._on_open_settings()
    assert called == ["settings"]


def test_monochrome_tray_icon_states():
    for st in ("idle", "syncing", "error"):
        img = create_tray_icon(state=st, size=44, monochrome=True)
        assert img.size == (44, 44)
        assert img.getpixel((0, 0))[3] == 0  # Transparent corners for HIG template
        alpha_bytes = img.getchannel("A").tobytes()
        assert sum(1 for a in alpha_bytes if a > 0) > 40  # Non-empty opaque silhouette


def test_tray_menu_i18n(tmp_path: Path):
    for lang, expected_status in [
        ("en", "Up to date"),
        ("it", "Aggiornato"),
        ("fr", "À jour"),
        ("es", "Al día"),
    ]:
        cfg = PradoConfig(courses_root=tmp_path / "Courses", language=lang)
        app = PradoTrayApp(cfg=cfg)
        assert expected_status in app._get_status_text()


def test_tray_toggle_notifications(tmp_path: Path, monkeypatch):
    cfg = PradoConfig(courses_root=tmp_path / "Courses", language="es")
    cfg.notifications.enabled = False
    app = PradoTrayApp(cfg=cfg)
    app.icon = MagicMock()

    # Mock save_config so it doesn't write to real home
    monkeypatch.setattr("prado.ui.tray.save_config", lambda c: None)

    app._on_toggle_notifications()
    assert app.cfg.notifications.enabled is True
    app.icon.update_menu.assert_called_once()

    app._on_toggle_notifications()
    assert app.cfg.notifications.enabled is False


def test_tray_toggle_auto_sync(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = PradoConfig(courses_root=tmp_path / "Courses", language="es")
    app = PradoTrayApp(cfg=cfg)
    app.icon = MagicMock()

    assert not app._auto_sync_enabled
    app._on_toggle_auto_sync()
    assert app._auto_sync_enabled is True
    assert app.cfg.sync.auto_sync is True
    app.icon.update_menu.assert_called_once()

    # Verify persistence across reload
    reloaded = PradoTrayApp()
    assert reloaded._auto_sync_enabled is True

    app._on_toggle_auto_sync()
    assert not app._auto_sync_enabled
    assert app.cfg.sync.auto_sync is False


def test_tray_deadline_opens_matching_course_folder(tmp_path: Path, monkeypatch):
    courses_dir = tmp_path / "Courses"
    target_course = courses_dir / "Visión por Computador"
    target_course.mkdir(parents=True, exist_ok=True)
    ics = courses_dir / "deadlines.ics"
    ics.write_text(
        "BEGIN:VCALENDAR\r\n"
        "BEGIN:VEVENT\r\n"
        "SUMMARY:[Visión por Computador] Entrega P2\r\n"
        "DTSTART:20261201T225900Z\r\n"
        "CATEGORIES:Visión por Computador\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n",
        encoding="utf-8",
    )
    opened = []
    monkeypatch.setattr("prado.ui.tray.open_folder", lambda p: opened.append(Path(p)) or True)
    app = PradoTrayApp(cfg=PradoConfig(courses_root=courses_dir, language="es"))
    _, dl_menu = app._build_deadlines_submenu("es")
    first_item = list(dl_menu.items)[0]
    first_item(None)
    assert opened == [target_course]


def test_tray_trigger_sync_non_blocking():
    app = PradoTrayApp()

    with patch.object(app, "_run_sync_worker") as mock_worker:
        success = app.trigger_sync()
        assert success is True

        # Second call while lock is held returns False
        success2 = app.trigger_sync()
        assert success2 is False


def test_tray_headless_rejection(monkeypatch):
    monkeypatch.setenv("CI", "true")
    app = PradoTrayApp()

    with pytest.raises(RuntimeError, match="headless or CI environment"):
        app.run()


def test_cli_app_and_gui_dispatch(monkeypatch):
    from prado.cli import main

    # Test prado app dispatch
    called_detached = []

    def mock_run_tray_app(detached=False):
        called_detached.append(detached)
        return 0

    monkeypatch.setattr("prado.ui.tray.run_tray_app", mock_run_tray_app)

    rc1 = main(["app", "--detached"])
    assert rc1 == 0
    assert called_detached == [True]

    rc2 = main(["gui"])
    assert rc2 == 0
    assert called_detached == [True, False]


def test_tray_syncs_cfg_and_auto_sync_on_api_status_change(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = PradoConfig(courses_root=tmp_path / "Courses", language="es")
    cfg.sync.auto_sync = False
    app = PradoTrayApp(cfg=cfg)
    app.icon = MagicMock()

    updated_cfg = PradoConfig(courses_root=tmp_path / "Courses", language="en")
    updated_cfg.sync.auto_sync = True
    app.api = MagicMock()
    app.api.cfg = updated_cfg

    app._on_api_status_change("idle", "14:20")
    assert app.cfg is updated_cfg
    assert app._auto_sync_enabled is True
    assert app.last_sync_time == "14:20"
    app.icon.update_menu.assert_called()


def test_apply_macos_template_icon_wraps_assert_image(monkeypatch):
    nsimage = MagicMock()
    btn = MagicMock()
    status_item = MagicMock()
    status_item.button.return_value = btn

    class _DummyIcon:
        def __init__(self):
            self._icon_image = nsimage
            self._status_item = status_item
            self.orig_calls = 0

        def _assert_image(self):
            self.orig_calls += 1

    icon_obj = _DummyIcon()
    monkeypatch.setattr("sys.platform", "darwin")

    PradoTrayApp._apply_macos_template_icon(icon_obj)
    assert getattr(icon_obj, "_prado_template_wrapped", False) is True
    assert nsimage.setTemplate_.call_count == 1
    nsimage.setTemplate_.assert_called_with(True)
    btn.setImage_.assert_called_with(nsimage)

    # First pystray redraw calls wrapped _assert_image, which re-applies template flag
    icon_obj._assert_image()
    assert icon_obj.orig_calls == 1
    assert nsimage.setTemplate_.call_count == 2

    # Second call to _apply_macos_template_icon does not double-wrap
    PradoTrayApp._apply_macos_template_icon(icon_obj)
    icon_obj._assert_image()
    assert icon_obj.orig_calls == 2


def test_tray_open_mail_targets_ugr_webmail(monkeypatch):
    opened_urls = []
    monkeypatch.setattr("prado.ui.tray.open_url", lambda url: opened_urls.append(url) or True)
    app = PradoTrayApp()
    app._on_open_mail()
    assert opened_urls == ["https://webmailest.ugr.es"]


def test_tray_courses_submenu_opens_slug_folder(tmp_path: Path, monkeypatch):
    from prado.state import CourseRecord, StateDatabase

    cfg_dir = tmp_path / "cfg"
    courses_dir = tmp_path / "UGR_Courses"
    ed_dir = courses_dir / "ED_C"
    ed_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(cfg_dir))

    db = StateDatabase()
    db.upsert_course(
        CourseRecord(
            course_id=15819,
            fullname="ESTRUCTURA DE DATOS - 2627 (Grupo C)",
            shortname="ESTRUCTURA DE DATOS (2627)-296_11_22_2627_C",
            is_active=1,
        )
    )

    opened = []
    monkeypatch.setattr("prado.ui.tray.open_folder", lambda p: opened.append(Path(p)) or True)
    app = PradoTrayApp(cfg=PradoConfig(courses_root=courses_dir, language="it"))
    _, courses_menu = app._build_courses_submenu("it")
    first_item = list(courses_menu.items)[0]
    first_item(None)
    assert opened == [ed_dir]


def test_tray_doctor_opens_control_center_and_runs_diagnostics(monkeypatch):
    import time

    app = PradoTrayApp()
    opened_sections = []
    monkeypatch.setattr(app, "open_control_center", lambda section=None: opened_sections.append(section) or "http://127.0.0.1:0/")

    mock_api = MagicMock()
    mock_api.run_doctor_diagnostics.return_value = {
        "status": "success",
        "probes": [{"status": "OK"}, {"status": "WARN"}],
    }
    app.api = mock_api
    notifs = []
    app.notifier = MagicMock()
    app.notifier.notify.side_effect = lambda **kw: notifs.append(kw)

    app._on_run_doctor()
    time.sleep(0.1)
    assert opened_sections == ["doctor"]
    mock_api.run_doctor_diagnostics.assert_called_once()
    assert len(notifs) == 1
    assert "1/2" in notifs[0]["message"]


def test_open_url_uses_native_open_on_macos(monkeypatch):
    from prado.ui.dialogs import open_url

    calls = []
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("subprocess.Popen", lambda args, **kw: calls.append(args))
    assert open_url("https://webmailest.ugr.es") is True
    assert calls == [["open", "https://webmailest.ugr.es"]]
