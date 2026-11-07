"""
Unit tests for PradoOS GUI dialogs and icon generator.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from prado.config import PradoConfig
from prado.ui.dialogs import open_folder, open_url, prompt_login_gui
from prado.ui.icon import create_tray_icon, generate_desktop_assets


def test_create_tray_icon():
    for state in ("idle", "syncing", "error"):
        img = create_tray_icon(state=state, size=64)
        assert img.size == (64, 64)
        assert img.mode == "RGBA"

    small_img = create_tray_icon(state="idle", size=22)
    assert small_img.size == (22, 22)


def test_generate_desktop_assets(tmp_path: Path):
    assets = generate_desktop_assets(tmp_path)
    assert "png" in assets
    assert assets["png"].exists()
    assert assets["png"].stat().st_size > 0

    assert "ico" in assets
    assert assets["ico"].exists()
    assert assets["ico"].stat().st_size > 0


def test_open_folder(tmp_path: Path, monkeypatch):
    target = tmp_path / "Subdir" / "UGR_Courses"
    assert not target.exists()

    with patch("subprocess.Popen") as mock_popen, patch("os.startfile", create=True) as mock_startfile:
        res = open_folder(target)
        assert res is True
        assert target.exists()
        assert mock_popen.called or mock_startfile.called


def test_open_url():
    with patch("webbrowser.open") as mock_wb:
        mock_wb.return_value = True
        res = open_url("https://correo.ugr.es")
        assert res is True
        mock_wb.assert_called_once_with("https://correo.ugr.es")


def test_prompt_login_gui_success(tmp_path: Path, monkeypatch):
    cfg = PradoConfig(courses_root=tmp_path / "Courses", username="")
    monkeypatch.setattr("prado.ui.dialogs.save_config", lambda c: None)

    mock_prompts = iter(["testuser@correo.ugr.es", "secret_pass"])
    monkeypatch.setattr("prado.ui.dialogs.prompt_gui_input", lambda **kw: next(mock_prompts))

    mock_cred_store = MagicMock()

    res = prompt_login_gui(cfg=cfg, cred_store=mock_cred_store)
    assert res is True
    assert cfg.username == "testuser@correo.ugr.es"
    mock_cred_store.set_sso_credentials.assert_called_once_with("testuser@correo.ugr.es", "secret_pass")


def test_prompt_login_gui_cancel(tmp_path: Path, monkeypatch):
    cfg = PradoConfig(courses_root=tmp_path / "Courses", username="")

    monkeypatch.setattr("prado.ui.dialogs.prompt_gui_input", lambda **kw: None)

    mock_cred_store = MagicMock()

    res = prompt_login_gui(cfg=cfg, cred_store=mock_cred_store)
    assert res is False
    assert cfg.username == ""
    mock_cred_store.set_sso_credentials.assert_not_called()
