"""
Tests for desktop notifications opt-in CLI (`prado notify`) and config isolation.
"""

import json

import pytest

from prado.cli import main
from prado.config import PradoConfig, load_config, save_config


def test_prado_notify_status_default_disabled(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    save_config(PradoConfig(), cfg_file)
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path))

    # Test JSON mode
    ret = main(["notify", "status", "--json"])
    assert ret == 0

    cfg = load_config(cfg_file)
    assert cfg.notifications.enabled is False


def test_prado_notify_toggle_on_and_off(tmp_path, monkeypatch, capsys):
    cfg_file = tmp_path / "config.yaml"
    save_config(PradoConfig(), cfg_file)
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path))

    # Turn on
    ret = main(["notify", "on", "--json"])
    assert ret == 0
    cfg = load_config(cfg_file)
    assert cfg.notifications.enabled is True

    # Turn off
    ret = main(["notify", "off", "--json"])
    assert ret == 0
    cfg = load_config(cfg_file)
    assert cfg.notifications.enabled is False


def test_prado_notify_test_headless(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    save_config(PradoConfig(), cfg_file)
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("PRADO_HEADLESS", "1")

    ret = main(["notify", "test", "--json"])
    assert ret == 0
