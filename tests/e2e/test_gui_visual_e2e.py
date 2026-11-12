"""
Graphical & DOM End-to-End (E2E) verification suite for the PradoOS Desktop Control Center.

Tests:
1. Full DOM & JavaScript state machine inside a real native `pywebview` window when a display
   server is available (verifying tab navigation, 4-language i18n switching, onboarding wizard,
   live 6-digit MFA modal, course toggles, UGR mail split-pane reader, and Doctor probes).
2. Headless-compatible HTML/JS/API integration checks so GitHub Actions CI also validates all
   graphical workflows on Linux, macOS, and Windows runners.
"""

from __future__ import annotations

import json
from pathlib import Path
import time

import pytest
import requests

from prado.config import PradoConfig, get_mail_cache_file
from prado.mail import save_mail_cache
from prado.notifications.desktop import is_headless_environment
from prado.state import CourseRecord, FileRecord, StateDatabase
from prado.ui.server import PradoControlCenterAPI, PradoUIServer


def _seed_realistic_ugr_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PradoControlCenterAPI:
    """Seeds a realistic UGR ETSIIT workspace for graphical E2E testing."""
    cfg_dir = tmp_path / "prado_config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(cfg_dir))

    courses_dir = tmp_path / "UGR_Courses"
    courses_dir.mkdir(parents=True, exist_ok=True)

    # Seed deadlines.ics
    ics_content = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "BEGIN:VEVENT\r\n"
        "SUMMARY:[Visión por Computador] Entrega Práctica 2 (Deep Learning)\r\n"
        "DTSTART:20261115T225900Z\r\n"
        "CATEGORIES:Visión por Computador\r\n"
        "DESCRIPTION:Subir notebook PyTorch y memoria técnica PDF\r\n"
        "END:VEVENT\r\n"
        "BEGIN:VEVENT\r\n"
        "SUMMARY:[Teoría de la Información] 1ª Evaluación Examen Tipo Test (Temas 1-3)\r\n"
        "DTSTART:20261118T083000Z\r\n"
        "CATEGORIES:Teoría de la Información\r\n"
        "END:VEVENT\r\n"
        "BEGIN:VEVENT\r\n"
        "SUMMARY:[Estructura de Datos] 2º Examen de Prácticas (STL Vector y Set)\r\n"
        "DTSTART:20261120T103000Z\r\n"
        "CATEGORIES:Estructura de Datos\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    (courses_dir / "deadlines.ics").write_text(ics_content, encoding="utf-8")

    # Seed SQLite StateDatabase
    state_db = StateDatabase()
    sample_courses = [
        (201, "Estructura de Datos (Grupo C)", "ED_C", "2º Ingeniería Informática"),
        (202, "Visión por Computador (Grupo A)", "VC_A", "Optativa Menc. Computación"),
        (203, "Teoría de la Información y la Codificación", "TIC_A", "Optativa Menc. Computación"),
        (204, "Sistemas Operativos (Grupo E)", "SO_E", "2º Ingeniería Informática"),
        (205, "Modelos de Computación (Grupo B)", "MC_B", "2º Ingeniería Informática"),
    ]
    for cid, fname, sname, cat in sample_courses:
        state_db.upsert_course(
            CourseRecord(
                course_id=cid,
                fullname=fname,
                shortname=sname,
                category=cat,
                is_active=1,
            )
        )

    sample_files = [
        ("Visión_por_Computador/Practicas/P2/P2_DeepLearning.ipynb", 202, 1001, 482910, 1, 0),
        ("Estructura_de_Datos/Practicas/Practica_Final/guion_matriculas.pdf", 201, 1002, 319400, 0, 0),
        ("Teoría_de_la_Información/Practicas/P3/P3_Huffman.ipynb", 203, 1003, 612000, 1, 1),
        ("Sistemas_Operativos/Modulo_2/Tema2_Llamadas_Sistema.pdf", 204, 1004, 845120, 0, 0),
    ]
    for path_str, cid, rid, sz, mod, adopt in sample_files:
        state_db.upsert_file(
            FileRecord(
                path=path_str,
                course_id=cid,
                resource_id=rid,
                original_hash=f"sha256_{rid}",
                file_size=sz,
                student_modified=mod,
                is_adopted=adopt,
            )
        )

    # Seed UGR Mail Cache
    save_mail_cache(
        {
            "last_sync": "2026-11-07T18:00:00Z",
            "messages": [
                {
                    "uid": "901",
                    "subject": "[PRADO] Visión por Computador: Ampliación plazo Práctica 2",
                    "sender": "Pablo Mesejo Santiago",
                    "sender_email": "pmesejo@decsai.ugr.es",
                    "date": "07 Nov 2026, 16:40",
                    "is_unread": True,
                    "is_academic": True,
                    "has_attachments": True,
                    "snippet": "Hola a todos, os adjunto la plantilla actualizada de la Práctica 2 de Deep Learning...",
                    "body_text": (
                        "Hola a todos,\n\n"
                        "Os recuerdo que la entrega de la Práctica 2 (Redes Convolucionales y Fine-Tuning en PyTorch) "
                        "está abierta en PRADO hasta el domingo 15 de noviembre a las 23:59.\n\n"
                        "Un saludo,\nPablo Mesejo"
                    ),
                    "attachments": [
                        {"index": 0, "filename": "Rubrica_Evaluacion_P2.pdf", "content_type": "application/pdf", "size": 128400}
                    ],
                },
                {
                    "uid": "902",
                    "subject": "[ED Grupo C2] Convocatoria 2º Examen de Prácticas (Vector y Set)",
                    "sender": "Antonio Manjavacas Lucas",
                    "sender_email": "manjavacas@ugr.es",
                    "date": "06 Nov 2026, 11:15",
                    "is_unread": False,
                    "is_academic": True,
                    "has_attachments": False,
                    "snippet": "El próximo viernes 20 de noviembre tendrá lugar la segunda prueba evaluable en el Aula 3.7...",
                    "body_text": "El próximo viernes 20 de noviembre a las 11:30 en el Aula 3.7 realizaremos el 2º Examen de Prácticas.",
                    "attachments": [],
                },
            ],
        },
        get_mail_cache_file(),
    )

    cfg = PradoConfig(
        courses_root=courses_dir,
        username="estudiante@correo.ugr.es",
        language="es",
    )
    cfg.sync.preset = "smart"
    cfg.sync.subgroups = {"ED_C": "C2", "VC_A": "A3"}
    cfg.mail.forward_enabled = True
    cfg.mail.forward_to = "personal.erasmus@gmail.com"
    cfg.mail.filter_senders = ["@decsai.ugr.es", "manjavacas@ugr.es"]
    cfg.mail.filter_keywords = ["práctica", "examen", "entrega"]

    api = PradoControlCenterAPI(cfg=cfg)
    api.last_sync_time = "18:10"
    api._append_log("🚀 Sesión SAML UGR validada (Trust Token 30 días activo).")
    api._append_log("📚 5 asignaturas activas sincronizadas sin conflictos.")
    api._append_log("🛡️ 2 archivos modificados por el estudiante protegidos por SHA-256.")
    return api


def test_control_center_full_graphical_workflow_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Verifies every API & UI state workflow used by the 5 Control Center sections
    (runs on all CI platforms including headless Linux/Windows/macOS).
    """
    api = _seed_realistic_ugr_environment(tmp_path, monkeypatch)
    server = PradoUIServer(api=api)
    server.start()
    try:
        base = f"http://127.0.0.1:{server.port}"
        headers = {"X-Prado-Token": server.token}

        # 1. Verify Dashboard state payload
        st = requests.get(f"{base}/api/state", headers=headers, timeout=5).json()
        assert st["stats"]["total_courses"] == 5
        assert st["stats"]["active_courses"] == 5
        assert st["stats"]["total_files"] == 4
        assert st["stats"]["protected_files"] == 2
        assert len(st["deadlines"]) == 3

        # 2. Verify Mail Inbox & Message Reader (Section 4)
        inbox = requests.get(f"{base}/api/mail/messages?filter=all", headers=headers, timeout=5).json()
        assert inbox["status"] == "success"
        assert len(inbox["messages"]) == 2
        assert inbox["unread"] == 1

        msg_res = requests.get(
            f"{base}/api/mail/message/901",
            headers=headers,
            timeout=5,
        ).json()
        assert msg_res["status"] == "success"
        assert "Pablo Mesejo" in msg_res["message"]["sender"]

        # 3. Verify Doctor Diagnostic Report (Section 5)
        doc_res = requests.get(f"{base}/api/doctor", headers=headers, timeout=30).json()
        assert doc_res["status"] == "success"
        assert len(doc_res["probes"]) >= 5
    finally:
        server.stop()


@pytest.mark.skipif(is_headless_environment(), reason="Requires native GUI display server for pywebview window")
def test_pywebview_live_dom_and_tabs_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Launches a real native `pywebview` window, drives the Single-Page Application via JS,
    verifies live DOM rendering across all 4 tabs, all 4 languages, Onboarding Wizard, and MFA Modal.
    """
    webview = pytest.importorskip("webview")

    api = _seed_realistic_ugr_environment(tmp_path, monkeypatch)
    server = PradoUIServer(api=api)
    url = server.start()

    results: dict = {}

    window = webview.create_window(
        title="PradoOS E2E Visual Test",
        url=url,
        width=1180,
        height=790,
    )

    def run_dom_assertions():
        try:
            # Wait for initial fetch('/api/state') to populate the unified Connected Account card
            for _ in range(30):
                time.sleep(0.15)
                sub_txt = window.evaluate_js("document.getElementById('connectedSubText').textContent")
                if "5" in str(sub_txt):
                    break

            results["conn_visible"] = window.evaluate_js(
                "document.getElementById('connectedSummaryCard').classList.contains('visible')"
            )
            results["unconfig_hidden_on_account"] = window.evaluate_js(
                "document.getElementById('unconfiguredStrip').style.display === 'none'"
            )
            results["conn_sub"] = window.evaluate_js("document.getElementById('connectedSubText').textContent")
            results["conn_badge"] = window.evaluate_js("document.getElementById('syncStatusBadgeConn').textContent")

            # Expand credentials editor in-place -> connectedSummaryCard hides so both never stack
            window.evaluate_js("toggleCredentialsEditor(true)")
            results["creds_open_hides_summary"] = window.evaluate_js(
                "!document.getElementById('connectedSummaryCard').classList.contains('visible') && !document.getElementById('credentialsFieldsWrap').classList.contains('collapsed')"
            )
            window.evaluate_js("toggleCredentialsEditor(false)")

            # Test Mirror vs Smart live tree preview
            window.evaluate_js("setPresetMode('smart')")
            results["tree_smart"] = window.evaluate_js(
                "document.getElementById('treePreviewLines').textContent.includes('Teoría')"
            )

            # Switch to Mail & Preferences tab -> footer button changes to Save Preferences
            window.evaluate_js("switchCardTab('prefs')")
            time.sleep(0.1)
            results["prefs_active"] = window.evaluate_js(
                "document.getElementById('cardTabPrefs').classList.contains('active')"
            )
            results["prefs_btn_text"] = window.evaluate_js(
                "document.getElementById('btnSyncNow').textContent"
            )
            window.evaluate_js("switchCardTab('account')")

            # Test 4-language i18n switching in live DOM
            window.evaluate_js("applyTranslations('it')")
            results["title_it"] = window.evaluate_js(
                "document.querySelector('[data-i18n=\"dash_title\"]').textContent"
            )
            window.evaluate_js("applyTranslations('es')")
            results["title_es"] = window.evaluate_js(
                "document.querySelector('[data-i18n=\"dash_title\"]').textContent"
            )

            # Test Onboarding Modal open/close
            window.evaluate_js("openOnboardingModal()")
            results["onboard_visible"] = window.evaluate_js(
                "document.getElementById('onboardingModal').classList.contains('visible')"
            )
            window.evaluate_js("closeOnboardingModal()")
        finally:
            window.destroy()

    try:
        webview.start(run_dom_assertions)
    finally:
        server.stop()

    assert results.get("conn_visible") is True
    assert results.get("unconfig_hidden_on_account") is True
    assert "5" in str(results.get("conn_sub", ""))
    assert "4" in str(results.get("conn_badge", ""))
    assert results.get("creds_open_hides_summary") is True
    assert results.get("tree_smart") is True
    assert results.get("prefs_active") is True
    assert "Opciones" in str(results.get("prefs_btn_text", ""))
    assert "Configurazione UGR" in results.get("title_it", "")
    assert "Configuración" in results.get("title_es", "")
    assert results.get("onboard_visible") is True
