"""
Unit tests for PradoOS Desktop 1-Click Auto-Updater and in-place Windows upgrade packaging.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests

from prado import __version__
from prado.config import PradoConfig
from prado.ui.frontend import render_control_center_html
from prado.ui.server import PradoControlCenterAPI, PradoUIServer
from prado.ui.updater import (
    check_for_updates,
    download_and_apply_update,
    get_installed_version,
    is_newer_version,
    parse_version,
    select_asset_for_platform,
    validate_download_url,
)


def test_version_parsing_and_prerelease_ordering():
    assert parse_version("v0.2.0-beta.2") < parse_version("v0.2.0-beta.3")
    assert parse_version("v0.2.0-beta.3") < parse_version("v0.2.0-beta.4")
    assert parse_version("v0.2.0-beta.4") == parse_version("0.2.0b4")
    assert parse_version("0.2.0-beta.4") < parse_version("0.2.0-rc.1")
    assert parse_version("0.2.0-rc.1") < parse_version("0.2.0")
    assert parse_version("0.2.0") < parse_version("0.2.1")

    assert is_newer_version("v0.2.0-beta.4", "0.2.0-beta.3") is True
    assert is_newer_version("v0.2.0", "0.2.0-beta.4") is True
    assert is_newer_version("v0.2.0-beta.3", "0.2.0-beta.3") is False
    assert is_newer_version("v0.2.0-beta.2", "0.2.0") is False


def test_get_installed_version_prefers_embedded_build_json(tmp_path: Path):
    build_json = tmp_path / "prado_build.json"
    build_json.write_text(json.dumps({"release_tag": "v0.2.0-beta.4"}), encoding="utf-8")
    assert get_installed_version(build_info_path=build_json) == "0.2.0-beta.4"

    missing = tmp_path / "missing.json"
    assert get_installed_version(build_info_path=missing) == __version__


def test_validate_download_url_and_platform_asset_selection():
    assert validate_download_url(
        "https://github.com/LorSt4r/prado-os/releases/download/v0.2.0-beta.4/PradoOS-Setup.exe"
    ) is True
    assert validate_download_url(
        "https://objects.githubusercontent.com/github-production-release-asset/123/PradoOS-Setup.exe"
    ) is True
    assert validate_download_url(
        "http://github.com/LorSt4r/prado-os/releases/download/v0.2.0/PradoOS-Setup.exe"
    ) is False
    assert validate_download_url(
        "https://github.com/evil-org/other-repo/releases/download/v1.0/PradoOS-Setup.exe"
    ) is False
    assert validate_download_url("https://evil.example.com/PradoOS-Setup.exe") is False

    assets = [
        {
            "name": "PradoOS-windows.zip",
            "browser_download_url": "https://github.com/LorSt4r/prado-os/releases/download/v0.2.0-beta.4/PradoOS-windows.zip",
        },
        {
            "name": "PradoOS-Setup.exe",
            "browser_download_url": "https://github.com/LorSt4r/prado-os/releases/download/v0.2.0-beta.4/PradoOS-Setup.exe",
        },
        {
            "name": "PradoOS-macos.zip",
            "browser_download_url": "https://github.com/LorSt4r/prado-os/releases/download/v0.2.0-beta.4/PradoOS-macos.zip",
        },
        {
            "name": "PradoOS-linux.tar.gz",
            "browser_download_url": "https://github.com/LorSt4r/prado-os/releases/download/v0.2.0-beta.4/PradoOS-linux.tar.gz",
        },
    ]
    win_asset = select_asset_for_platform(assets, platform_name="win32")
    assert win_asset is not None and win_asset["name"] == "PradoOS-Setup.exe"
    assert win_asset["kind"] == "windows_installer"

    mac_asset = select_asset_for_platform(assets, platform_name="darwin")
    assert mac_asset is not None and mac_asset["name"] == "PradoOS-macos.zip"

    linux_asset = select_asset_for_platform(assets, platform_name="linux")
    assert linux_asset is not None and linux_asset["name"] == "PradoOS-linux.tar.gz"


def test_check_for_updates_available_up_to_date_and_offline(monkeypatch):
    def _fake_ok(*args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "tag_name": "v0.2.0-beta.4",
            "html_url": "https://github.com/LorSt4r/prado-os/releases/tag/v0.2.0-beta.4",
            "body": "1-click updates",
            "assets": [
                {
                    "name": "PradoOS-Setup.exe",
                    "browser_download_url": "https://github.com/LorSt4r/prado-os/releases/download/v0.2.0-beta.4/PradoOS-Setup.exe",
                }
            ],
        }
        return resp

    monkeypatch.setattr("prado.ui.updater.requests.get", _fake_ok)
    avail = check_for_updates(current_version="0.2.0-beta.3", platform_name="win32")
    assert avail["status"] == "ok"
    assert avail["available"] is True
    assert avail["latest_version"] == "0.2.0-beta.4"
    assert avail["asset_name"] == "PradoOS-Setup.exe"

    same = check_for_updates(current_version="0.2.0-beta.4", platform_name="win32")
    assert same["status"] == "ok"
    assert same["available"] is False

    def _fake_offline(*args, **kwargs):
        raise requests.ConnectionError("network offline")

    monkeypatch.setattr("prado.ui.updater.requests.get", _fake_offline)
    err = check_for_updates(current_version="0.2.0-beta.3", platform_name="win32")
    assert err["status"] == "error"
    assert err["available"] is False
    assert "network offline" in str(err["error"])


def test_download_and_apply_update_windows_silent_installer_and_non_mz_rejection(tmp_path: Path, monkeypatch):
    def _make_stream_resp(payload: bytes, url: str):
        class _Resp:
            def __init__(self):
                self.url = url
                self.headers = {"Content-Length": str(len(payload))}

            def raise_for_status(self):
                return None

            def iter_content(self, chunk_size=65536):
                yield payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Resp()

    dl_url = "https://github.com/LorSt4r/prado-os/releases/download/v0.2.0-beta.4/PradoOS-Setup.exe"
    info = {
        "latest_version": "0.2.0-beta.4",
        "release_url": "https://github.com/LorSt4r/prado-os/releases/tag/v0.2.0-beta.4",
        "download_url": dl_url,
        "asset_name": "PradoOS-Setup.exe",
        "asset_kind": "windows_installer",
    }

    # 1. Reject non-MZ payload (e.g. HTML error page)
    monkeypatch.setattr("prado.ui.updater.requests.get", lambda *a, **kw: _make_stream_resp(b"<html>404</html>", dl_url))
    bad = download_and_apply_update(info, platform_name="win32", is_frozen=True, temp_dir=tmp_path)
    assert bad["status"] == "error"
    assert "Invalid Windows installer payload" in str(bad["error"])

    # 2. Valid MZ payload launches Inno Setup silently and schedules clean app exit
    popen_calls = []
    monkeypatch.setattr("prado.ui.updater.requests.get", lambda *a, **kw: _make_stream_resp(b"MZ" + b"\x00" * 128, dl_url))
    monkeypatch.setattr("prado.ui.updater.subprocess.Popen", lambda cmd, **kw: popen_calls.append((cmd, kw)) or MagicMock())

    timers = []
    class _FakeTimer:
        def __init__(self, delay, fn):
            self.delay = delay
            self.fn = fn
            self.daemon = False

        def start(self):
            timers.append(self)

    monkeypatch.setattr("prado.ui.updater.threading.Timer", _FakeTimer)
    exit_calls = []
    prog_events = []

    res = download_and_apply_update(
        info,
        on_progress=prog_events.append,
        on_before_exit=lambda: exit_calls.append("exit"),
        platform_name="win32",
        is_frozen=True,
        temp_dir=tmp_path,
    )
    assert res["status"] == "launching_installer"
    expected_exe = tmp_path / "PradoOS-Setup-0.2.0-beta.4.exe"
    assert expected_exe.exists()
    assert prog_events[-1] == 100
    assert popen_calls[0][0] == [str(expected_exe), "/SP-", "/SILENT", "/NORESTART"]
    assert len(timers) == 1
    timers[0].fn()
    assert exit_calls == ["exit"]

    # 3. Source / non-frozen run falls back cleanly to browser release URL
    opened_urls = []
    monkeypatch.setattr("prado.ui.updater.open_url", lambda u: opened_urls.append(u) or True)
    src_res = download_and_apply_update(info, platform_name="win32", is_frozen=False, temp_dir=tmp_path)
    assert src_res["status"] == "opened_browser"
    assert opened_urls == [info["release_url"]]


def test_download_and_apply_update_macos_archive_reveals_in_finder(tmp_path: Path, monkeypatch):
    dl_url = "https://github.com/LorSt4r/prado-os/releases/download/v0.2.0-beta.4/PradoOS-macos.zip"

    class _Resp:
        url = dl_url
        headers = {"Content-Length": "4"}
        def raise_for_status(self):
            return None
        def iter_content(self, chunk_size=65536):
            yield b"PK\x03\x04"
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr("prado.ui.updater.requests.get", lambda *a, **kw: _Resp())
    popen_calls = []
    monkeypatch.setattr("prado.ui.updater.subprocess.Popen", lambda cmd, **kw: popen_calls.append(cmd) or MagicMock())

    res = download_and_apply_update(
        {
            "latest_version": "0.2.0-beta.4",
            "release_url": "https://github.com/LorSt4r/prado-os/releases/tag/v0.2.0-beta.4",
            "download_url": dl_url,
            "asset_name": "PradoOS-macos.zip",
            "asset_kind": "archive",
        },
        platform_name="darwin",
        is_frozen=True,
        downloads_dir=tmp_path,
    )
    assert res["status"] == "downloaded"
    expected_zip = tmp_path / "PradoOS-macos.zip"
    assert expected_zip.exists()
    assert popen_calls == [["open", "-R", str(expected_zip)]]


def test_control_center_update_endpoints_and_frontend_banner(tmp_path: Path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(cfg_dir))

    monkeypatch.setattr(
        "prado.ui.server.check_for_updates",
        lambda current_version=None: {
            "status": "ok",
            "available": True,
            "current_version": "0.2.0-beta.3",
            "latest_version": "0.2.0-beta.4",
            "release_url": "https://github.com/LorSt4r/prado-os/releases/tag/v0.2.0-beta.4",
            "asset_name": "PradoOS-Setup.exe",
            "download_url": "https://github.com/LorSt4r/prado-os/releases/download/v0.2.0-beta.4/PradoOS-Setup.exe",
            "asset_kind": "windows_installer",
            "notes": "Auto-updater",
            "error": None,
        },
    )
    monkeypatch.setattr(
        "prado.ui.server.download_and_apply_update",
        lambda info, on_progress=None, on_before_exit=None: {
            "status": "launching_installer",
            "path": str(tmp_path / "PradoOS-Setup.exe"),
        },
    )

    api = PradoControlCenterAPI(cfg=PradoConfig(courses_root=tmp_path / "Courses", language="it"))
    server = PradoUIServer(api=api)
    server.start()
    try:
        headers = {"X-Prado-Token": server.token, "Content-Type": "application/json"}
        r_chk = requests.post(f"http://127.0.0.1:{server.port}/api/update/check", headers=headers, data="{}", timeout=3)
        assert r_chk.status_code == 200
        assert r_chk.json()["available"] is True
        assert r_chk.json()["latest_version"] == "0.2.0-beta.4"

        r_st = requests.get(f"http://127.0.0.1:{server.port}/api/state", headers=headers, timeout=3)
        assert r_st.status_code == 200
        assert r_st.json()["update"]["available"] is True

        r_inst = requests.post(f"http://127.0.0.1:{server.port}/api/update/install", headers=headers, data="{}", timeout=3)
        assert r_inst.status_code == 200
        assert r_inst.json()["status"] in ("started", "already_downloading", "launching_installer")

        for _ in range(25):
            st_now = requests.get(f"http://127.0.0.1:{server.port}/api/state", headers=headers, timeout=3).json()
            if st_now["update"]["status"] == "launching_installer":
                break
            time.sleep(0.05)
        assert st_now["update"]["status"] == "launching_installer"
    finally:
        server.stop()

    html = render_control_center_html("tok-upd")
    assert "updateBanner" in html
    assert "btnInstallUpdate" in html
    assert "installAvailableUpdate" in html
    assert "checkForUpdatesManual" in html


def test_packaging_in_place_upgrade_and_installer_script(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    iss_text = (repo_root / "packaging" / "windows_installer.iss").read_text(encoding="utf-8")
    assert r"AppMutex=Local\PradoOS_Desktop_SingleInstance" in iss_text
    assert "CloseApplications=force" in iss_text
    assert "skipifnotsilent" in iss_text
    assert "PrepareToInstall" in iss_text

    script_path = repo_root / "scripts" / "build_desktop.py"
    spec = importlib.util.spec_from_file_location("build_desktop_upd", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    args = mod.collect_pyinstaller_args(repo_root=tmp_path, target_platform="win32", has_module=lambda _: False)
    assert "--hidden-import=prado.ui.updater" in args
