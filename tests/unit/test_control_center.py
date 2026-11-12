"""
Unit and HTTP integration tests for the PradoOS Desktop Control Center
(`PradoControlCenterAPI`, `PradoUIServer`, and `frontend.py`).
"""

from __future__ import annotations

from pathlib import Path
import threading
import time
from unittest.mock import MagicMock

import pytest
import requests

from prado.config import PradoConfig
from prado.state import CourseRecord, FileRecord, StateDatabase
from prado.ui.server import PradoControlCenterAPI, PradoUIServer, parse_deadlines_from_ics


def test_parse_deadlines_from_ics(tmp_path: Path):
    ics_content = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "BEGIN:VEVENT\r\n"
        "SUMMARY:[Visión por Computador] Entrega Práctica 2\r\n"
        "DTSTART:20261115T225900Z\r\n"
        "CATEGORIES:Visión por Computador\r\n"
        "DESCRIPTION:Subir notebook y memoria PDF\r\n"
        "END:VEVENT\r\n"
        "BEGIN:VEVENT\r\n"
        "SUMMARY:[TIC] 1ª Evaluación Examen Tipo Test\r\n"
        "DTSTART:20261118T083000Z\r\n"
        "CATEGORIES:Teoría de la Información\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    ics_file = tmp_path / "deadlines.ics"
    ics_file.write_text(ics_content, encoding="utf-8")

    events = parse_deadlines_from_ics(ics_file)
    assert len(events) == 2
    assert events[0]["course"] == "Visión por Computador"
    assert events[0]["kind"] == "ASSIGNMENT"
    assert events[1]["course"] == "Teoría de la Información"
    assert events[1]["kind"] == "EXAM"


def test_control_center_state_and_settings(tmp_path: Path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(cfg_dir))

    courses_dir = tmp_path / "UGR_Courses"
    cfg = PradoConfig(courses_root=courses_dir, username="estudiante@correo.ugr.es", language="es")

    state_db = StateDatabase()
    state_db.upsert_course(
        CourseRecord(
            course_id=101,
            fullname="Estructura de Datos",
            shortname="ED_C",
            category="Ingeniería Informática",
            is_active=1,
        )
    )
    state_db.upsert_file(
        FileRecord(
            path="Estructura_de_Datos/Guia_P2.pdf",
            course_id=101,
            resource_id=501,
            original_hash="abc123",
            file_size=20480,
            student_modified=1,
        )
    )

    api = PradoControlCenterAPI(cfg=cfg)
    st = api.get_full_state()

    assert st["stats"]["total_courses"] == 1
    assert st["stats"]["active_courses"] == 1
    assert st["stats"]["total_files"] == 1
    assert st["stats"]["protected_files"] == 1
    assert len(st["recent_files"]) == 1
    assert st["recent_files"][0]["student_modified"] is True

    # Update course settings and subgroups
    res = api.update_course_settings({
        "preset": "smart",
        "subgroups": {"ED_C": "C2"},
        "active_courses": {"101": False},
    })
    assert res["status"] == "success"
    assert res["preset"] == "smart"

    st2 = api.get_full_state()
    assert st2["config"]["preset"] == "smart"
    assert st2["courses"][0]["subgroup"] == "C2"
    assert st2["courses"][0]["is_active"] is False


def test_control_center_live_mfa_coordination(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))
    api = PradoControlCenterAPI(cfg=PradoConfig(courses_root=tmp_path / "Courses"))

    resolved_holder = []

    def worker():
        code = api._wait_for_mfa_code()
        resolved_holder.append(code)

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    # Wait until mfa_pending is active
    for _ in range(30):
        if api.mfa_pending:
            break
        time.sleep(0.02)

    assert api.mfa_pending is True
    assert api.status == "mfa_required"

    # Invalid code rejected
    bad_res = api.submit_mfa_code("123")
    assert bad_res["status"] == "error"

    # Valid 6-digit code unblocks worker thread immediately
    ok_res = api.submit_mfa_code("482910")
    assert ok_res["status"] == "success"

    t.join(timeout=2.0)
    assert resolved_holder == ["482910"]
    assert api.mfa_pending is False


def test_control_center_mail_forwarding_settings(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))
    api = PradoControlCenterAPI(cfg=PradoConfig(courses_root=tmp_path / "Courses"))

    res = api.update_mail_forwarding({
        "forward_enabled": True,
        "forward_to": "personal@gmail.com",
        "forward_mode": "custom",
        "filter_senders": "@decsai.ugr.es, manjavacas@ugr.es",
        "filter_keywords": "práctica, examen",
    })
    assert res["status"] == "success"
    assert res["mail"]["forward_enabled"] is True
    assert res["mail"]["forward_to"] == "personal@gmail.com"
    assert res["mail"]["forward_mode"] == "custom"
    assert "@decsai.ugr.es" in res["mail"]["filter_senders"]
    assert "examen" in res["mail"]["filter_keywords"]


def test_ui_server_loopback_http_and_token_security(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))
    api = PradoControlCenterAPI(cfg=PradoConfig(courses_root=tmp_path / "Courses"))
    server = PradoUIServer(api=api)

    url = server.start()
    try:
        assert server.port > 0
        base = f"http://127.0.0.1:{server.port}"

        # 1. GET / serves Control Center HTML
        r_html = requests.get(f"{base}/", timeout=5)
        assert r_html.status_code == 200
        assert "PradoOS" in r_html.text
        assert "onboardingModal" in r_html.text
        assert "mfaModal" in r_html.text
        assert "badge-neutral" in r_html.text
        assert "err-username" in r_html.text
        assert "err-password" in r_html.text
        assert 'autocomplete="one-time-code"' in r_html.text
        assert "segMirror" in r_html.text
        assert "segSmart" in r_html.text
        assert "treePreviewBox" in r_html.text
        assert "btnMfaCancel" in r_html.text
        assert "connectedSummaryCard" in r_html.text
        assert "toggleAutostartImmediate" in r_html.text
        assert "toggleNotificationsImmediate" in r_html.text

        # 2. GET /api/state without token -> 403 Forbidden
        r_unauth = requests.get(f"{base}/api/state", timeout=5)
        assert r_unauth.status_code == 403

        # 3. GET /api/state with X-Prado-Token -> 200 OK
        headers = {"X-Prado-Token": server.token}
        r_state = requests.get(f"{base}/api/state", headers=headers, timeout=5)
        assert r_state.status_code == 200
        data = r_state.json()
        assert "sync" in data
        assert "courses" in data
        assert "deadlines" in data

        # 4. POST /api/language updates language
        r_lang = requests.post(f"{base}/api/language", json={"language": "it"}, headers=headers, timeout=5)
        assert r_lang.status_code == 200
        assert r_lang.json()["language"] == "it"

        # 4b. POST /api/onboard missing username returns structured field error
        r_err = requests.post(
            f"{base}/api/onboard",
            json={"language": "en", "username": "", "password": ""},
            headers=headers,
            timeout=5,
        )
        assert r_err.status_code == 200
        assert r_err.json()["status"] == "error"
        assert r_err.json()["field"] == "username"
        assert "UGR email" in r_err.json()["error"]

        # 5. POST /api/onboard saves credentials and configuration (with start_sync=False)
        r_onboard = requests.post(
            f"{base}/api/onboard",
            json={
                "language": "es",
                "portal": "grado",
                "username": "alumno",
                "password": "secret_password_123",
                "courses_root": str(tmp_path / "Mis_Asignaturas"),
                "preset": "smart",
                "auto_sync": True,
                "auto_sync_interval_minutes": 30,
                "start_sync": False,
            },
            headers=headers,
            timeout=5,
        )
        assert r_onboard.status_code == 200
        ob_data = r_onboard.json()
        assert ob_data["status"] == "success"
        assert ob_data["username"] == "alumno@correo.ugr.es"

        r_st_after = requests.get(f"{base}/api/state", headers=headers, timeout=5)
        assert r_st_after.json()["config"]["auto_sync"] is True
        assert r_st_after.json()["config"]["auto_sync_interval_minutes"] == 30

        # 5b. POST /api/auth/mfa/cancel resets mfa state cleanly
        api.mfa_pending = True
        api.status = "mfa_required"
        r_mfa_cancel = requests.post(f"{base}/api/auth/mfa/cancel", json={}, headers=headers, timeout=5)
        assert r_mfa_cancel.status_code == 200
        assert r_mfa_cancel.json()["status"] == "cancelled"
        assert api.mfa_pending is False
        assert api.status == "idle"

        # 6. GET /api/doctor returns diagnostic probe list
        r_doc = requests.get(f"{base}/api/doctor", headers=headers, timeout=30)
        assert r_doc.status_code == 200
        doc_data = r_doc.json()
        assert doc_data["status"] == "success"
        assert len(doc_data["probes"]) >= 5
    finally:
        server.stop()


def test_control_center_caches_credential_lookup_across_state_polls(tmp_path: Path, monkeypatch):
    from unittest.mock import MagicMock

    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))
    cfg = PradoConfig(username="student@correo.ugr.es", courses_root=tmp_path / "Courses")
    (tmp_path / "cfg").mkdir(parents=True, exist_ok=True)
    from prado.config import save_config
    save_config(cfg)

    mock_store = MagicMock()
    mock_store.get_sso_credentials.return_value = ("student@correo.ugr.es", "pw123")
    monkeypatch.setattr("prado.ui.server.CredentialStore", lambda *a, **kw: mock_store)

    api = PradoControlCenterAPI(cfg=cfg)
    st1 = api.get_full_state()
    st2 = api.get_full_state()
    st3 = api.get_full_state()

    assert st1["auth"]["has_credentials"] is True
    assert st2["auth"]["has_credentials"] is True
    assert st3["auth"]["has_credentials"] is True
    assert mock_store.get_sso_credentials.call_count == 1

    api.logout()
    st_after = api.get_full_state()
    assert st_after["auth"]["has_credentials"] is False


def test_control_center_autostart_endpoints(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))
    (tmp_path / "cfg").mkdir(parents=True, exist_ok=True)
    cfg = PradoConfig(username="student@correo.ugr.es", courses_root=tmp_path / "Courses")

    autostart_state = {"enabled": False}
    monkeypatch.setattr("prado.ui.server.is_autostart_enabled", lambda: autostart_state["enabled"])

    def _fake_set(enabled: bool) -> bool:
        autostart_state["enabled"] = bool(enabled)
        return autostart_state["enabled"]

    monkeypatch.setattr("prado.ui.server.set_autostart_enabled", _fake_set)

    api = PradoControlCenterAPI(cfg=cfg)
    server = PradoUIServer(api=api)
    server.start()
    try:
        headers = {"X-Prado-Token": server.token}
        base = f"http://127.0.0.1:{server.port}"

        st0 = requests.get(f"{base}/api/state", headers=headers, timeout=5).json()
        assert st0["config"]["autostart"] is False

        r_tog = requests.post(
            f"{base}/api/autostart/toggle",
            json={"enabled": True},
            headers=headers,
            timeout=5,
        )
        assert r_tog.status_code == 200
        assert r_tog.json() == {"status": "success", "autostart": True}
        assert autostart_state["enabled"] is True

        st1 = requests.get(f"{base}/api/state", headers=headers, timeout=5).json()
        assert st1["config"]["autostart"] is True

        r_onb = requests.post(
            f"{base}/api/onboard",
            json={
                "language": "en",
                "portal": "grado",
                "username": "alumno",
                "password": "secret_password_123",
                "courses_root": str(tmp_path / "Courses"),
                "autostart": False,
                "start_sync": False,
            },
            headers=headers,
            timeout=5,
        )
        assert r_onb.status_code == 200
        assert r_onb.json()["status"] == "success"
        assert autostart_state["enabled"] is False
    finally:
        server.stop()


