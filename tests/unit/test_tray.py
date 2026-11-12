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
    assert len(items) >= 12

    # Status & Last sync texts
    assert "Al día" in app._get_status_text()
    assert "--:--" in app._get_last_sync_text()

    # Change to syncing
    app.status = "syncing"
    assert "Sincronizando" in app._get_status_text()

    # Change to error
    app.status = "error"
    assert "Error" in app._get_status_text()

    # Verify cascading submenus exist (Courses, Deadlines, Mail, Language)
    submenu_titles = [str(it.text) for it in items if getattr(it, "submenu", None) is not None]
    assert any("Asignaturas" in t for t in submenu_titles)
    assert any("Entregas" in t for t in submenu_titles)
    assert any("Correo UGR" in t for t in submenu_titles)
    assert any("Idioma" in t for t in submenu_titles)


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
