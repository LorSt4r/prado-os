"""Unit tests for the cross-platform Desktop Login Autostart manager."""

from __future__ import annotations

from pathlib import Path
import plistlib
import sys

from prado.ui import autostart


def test_get_autostart_command_source_vs_frozen(monkeypatch, tmp_path: Path):
    monkeypatch.delattr(sys, "frozen", raising=False)
    cmd_source = autostart.get_autostart_command()
    assert cmd_source == [sys.executable, "-m", "prado", "app", "--tray-only"]

    fake_bin = tmp_path / "PradoOS.app" / "Contents" / "MacOS" / "PradoOS"
    fake_bin.parent.mkdir(parents=True, exist_ok=True)
    fake_bin.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_bin))
    cmd_frozen = autostart.get_autostart_command()
    assert cmd_frozen == [str(fake_bin.resolve()), "--tray-only"]


def test_macos_autostart_plist_lifecycle(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    fake_bin = tmp_path / "PradoOS"
    fake_bin.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", str(fake_bin))

    assert autostart.is_autostart_enabled(home_dir=tmp_path) is False

    assert autostart.set_autostart_enabled(True, home_dir=tmp_path) is True
    assert autostart.is_autostart_enabled(home_dir=tmp_path) is True

    plist_path = tmp_path / "Library" / "LaunchAgents" / f"{autostart.TRAY_LAUNCHD_LABEL}.plist"
    assert plist_path.exists()
    with open(plist_path, "rb") as f:
        data = plistlib.load(f)

    assert data["Label"] == autostart.TRAY_LAUNCHD_LABEL
    assert data["ProgramArguments"] == [str(fake_bin.resolve()), "--tray-only"]
    assert data["RunAtLoad"] is True
    assert data["KeepAlive"] is False

    assert autostart.set_autostart_enabled(False, home_dir=tmp_path) is False
    assert autostart.is_autostart_enabled(home_dir=tmp_path) is False
    assert not plist_path.exists()


def test_linux_autostart_desktop_lifecycle(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert autostart.is_autostart_enabled(home_dir=tmp_path) is False
    assert autostart.set_autostart_enabled(True, home_dir=tmp_path) is True
    assert autostart.is_autostart_enabled(home_dir=tmp_path) is True

    desktop_file = tmp_path / ".config" / "autostart" / "pradoos.desktop"
    assert desktop_file.exists()
    text = desktop_file.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in text
    assert "-m prado app --tray-only" in text
    assert "X-GNOME-Autostart-enabled=true" in text

    assert autostart.set_autostart_enabled(False, home_dir=tmp_path) is False
    assert autostart.is_autostart_enabled(home_dir=tmp_path) is False
    assert not desktop_file.exists()
