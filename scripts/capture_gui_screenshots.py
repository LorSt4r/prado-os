#!/usr/bin/env python3
"""
Generates high-resolution Retina (2x) screenshots of the PradoOS Desktop Control Center
across all 5 views (Dashboard, Courses & Subgroups, UGR Mail & Auto-Forwarding,
Calendar & Doctor, and Onboarding Wizard) into `assets/screens/`.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

from prado.config import PradoConfig, get_config_file, get_mail_cache_file, save_config
from prado.auth.credentials import CredentialStore
from prado.mail import save_mail_cache
from prado.state import CourseRecord, FileRecord, StateDatabase
from prado.ui.server import PradoControlCenterAPI, PradoUIServer


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    screens_dir = repo_root / "assets" / "screens"
    screens_dir.mkdir(parents=True, exist_ok=True)

    chrome_bin = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome_bin.exists():
        print("Google Chrome not found at /Applications/Google Chrome.app")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cfg_dir = tmp_path / "prado_cfg"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        os.environ["PRADO_CONFIG_DIR"] = str(cfg_dir)

        courses_root_sim = Path.home() / "Documents" / "Asignaturas_UGR"
        created_sim_dir = not courses_root_sim.exists()
        courses_root_sim.mkdir(parents=True, exist_ok=True)

        # Seed realistic deadlines.ics
        ics_content = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "BEGIN:VEVENT\r\n"
            "SUMMARY:[Visión por Computador] Entrega Práctica 2 (Deep Learning)\r\n"
            "DTSTART:20261115T225900Z\r\n"
            "CATEGORIES:Visión por Computador\r\n"
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
            "BEGIN:VEVENT\r\n"
            "SUMMARY:[Estructura de Datos] Entrega Práctica Final (Gestión de Matrículas)\r\n"
            "DTSTART:20261214T225900Z\r\n"
            "CATEGORIES:Estructura de Datos\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )
        (courses_root_sim / "deadlines.ics").write_text(ics_content, encoding="utf-8")

        state_db = StateDatabase()
        sample_courses = [
            (2961122, "Estructura de Datos (Grupo C)", "ED_C", "2º Ingeniería Informática (ETSIIT)", "2026-11-07T18:10:00Z"),
            (2961148, "Visión por Computador (Grupo A)", "VC_A", "Optativa Mención Computación", "2026-11-07T18:10:00Z"),
            (2961199, "Teoría de la Información y la Codificación (Grupo A)", "TIC_A", "Optativa Mención Computación", "2026-11-07T18:10:00Z"),
            (2961123, "Sistemas Operativos (Grupo E)", "SO_E", "2º Ingeniería Informática (ETSIIT)", "2026-11-07T18:10:00Z"),
            (2961131, "Modelos de Computación (Grupo B)", "MC_B", "2º Ingeniería Informática (ETSIIT)", "2026-11-07T18:10:00Z"),
        ]
        for cid, fname, sname, cat, synced in sample_courses:
            state_db.upsert_course(
                CourseRecord(
                    course_id=cid,
                    fullname=fname,
                    shortname=sname,
                    category=cat,
                    is_active=1,
                    last_synced_at=synced,
                )
            )

        sample_files = [
            ("Visión_por_Computador/Practicas/P2/P2_DeepLearning.ipynb", 2961148, 1001, 524288, 1, 0),
            ("Estructura_de_Datos/Practicas/Practica_Final/guion_matriculas_stl.pdf", 2961122, 1002, 348160, 0, 0),
            ("Teoría_de_la_Información/Practicas/P3/P3_Huffman_Quijote.ipynb", 2961199, 1003, 618496, 1, 1),
            ("Sistemas_Operativos/Modulo_2/Tema2_Llamadas_al_Sistema_POSIX.pdf", 2961123, 1004, 892928, 0, 0),
            ("Modelos_de_Computacion/Teoria/Tema3_Gramaticas_Independientes_Contexto.pdf", 2961131, 1005, 412672, 0, 0),
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

        save_mail_cache(
            {
                "last_synced": "2026-11-07T18:10:00Z",
                "forwarded_uids": ["901", "902"],
                "messages": [
                    {
                        "uid": "901",
                        "subject": "[PRADO] Visión por Computador: Rúbrica y entrega Práctica 2 (PyTorch)",
                        "sender": "Pablo Mesejo Santiago",
                        "sender_email": "pmesejo@decsai.ugr.es",
                        "date_str": "07 Nov 2026, 16:40",
                        "is_unread": True,
                        "is_academic": True,
                        "snippet": "Hola a todos, os adjunto la rúbrica detallada de evaluación de la Práctica 2 de Deep Learning...",
                        "body_text": (
                            "Hola a todos,\n\n"
                            "Os recuerdo que la entrega de la Práctica 2 (Redes Convolucionales, Data Augmentation y "
                            "Fine-Tuning con ResNet en PyTorch) está abierta en PRADO hasta el domingo 15 de noviembre a las 23:59.\n\n"
                            "Adjunto en este correo la rúbrica oficial de evaluación y las recomendaciones para Google Colab Pro.\n\n"
                            "Un cordial saludo,\nPablo Mesejo Santiago\nDepartamento de Ciencias de la Computación e IA (DECSAI)"
                        ),
                        "attachments": [
                            {"index": 0, "filename": "Rubrica_Evaluacion_P2_VC.pdf", "content_type": "application/pdf", "size_bytes": 148480},
                            {"index": 1, "filename": "Plantilla_Colab_P2.ipynb", "content_type": "application/x-ipynb+json", "size_bytes": 68608},
                        ],
                    },
                    {
                        "uid": "902",
                        "subject": "[ED Grupo C2] Convocatoria 2º Examen de Prácticas (TDA STL Vector y Set)",
                        "sender": "Antonio Manjavacas Lucas",
                        "sender_email": "manjavacas@ugr.es",
                        "date_str": "06 Nov 2026, 11:15",
                        "is_unread": False,
                        "is_academic": True,
                        "snippet": "El próximo viernes 20 de noviembre tendrá lugar la segunda prueba evaluable en el Aula 3.7...",
                        "body_text": "El próximo viernes 20 de noviembre a las 11:30 en el Aula 3.7 realizaremos el 2º Examen de Prácticas.",
                        "attachments": [],
                    },
                    {
                        "uid": "903",
                        "subject": "[TIC Grupo A] Recordatorio 1ª Evaluación Tipo Test (Temas 1 a 3 — Aula 1.1)",
                        "sender": "Manuel Pegalajar Cuéllar",
                        "sender_email": "manupc@decsai.ugr.es",
                        "date_str": "05 Nov 2026, 09:50",
                        "is_unread": False,
                        "is_academic": True,
                        "snippet": "Se confirma que la prueba tipo test de los Temas 1-3 se celebrará el miércoles 18 de noviembre...",
                        "body_text": "Se confirma que la prueba tipo test de los Temas 1-3 se celebrará el miércoles 18 de noviembre a las 09:30 en el Aula 1.1.",
                        "attachments": [],
                    },
                ],
            },
            get_mail_cache_file(),
        )

        cfg = PradoConfig(
            courses_root=courses_root_sim,
            username="lorenzovasile@correo.ugr.es",
            language="es",
            credential_store="vault_file",
        )
        cfg.sync.preset = "smart"
        cfg.sync.subgroups = {"ED_C": "C2", "VC_A": "A3", "SO_E": "E3", "TIC_A": "A1", "MC_B": "B1"}
        cfg.notifications.enabled = True
        cfg.mail.enabled = True
        cfg.mail.forward_enabled = True
        cfg.mail.forward_to = "lorenzovasile@gmail.com"
        cfg.mail.forward_mode = "academic"
        cfg.mail.filter_senders = ["@decsai.ugr.es", "manjavacas@ugr.es", "pmesejo@ugr.es"]
        cfg.mail.filter_keywords = ["práctica", "examen", "entrega", "nota", "convocatoria"]
        save_config(cfg, get_config_file())

        cred = CredentialStore()
        cred.set_sso_credentials("lorenzovasile@correo.ugr.es", "demo_password_ugr")

        api = PradoControlCenterAPI(cfg=cfg)
        api.last_sync_time = "18:15"
        api._append_log("🔑 Conectando a https://pradogrado2627.ugr.es como lorenzovasile@correo.ugr.es...")
        api._append_log("✓ Sesión SAML validada mediante MFA_TOKEN (Dispositivo verificado por 30 días).")
        api._append_log("📚 5 asignaturas activas detectadas en PRADO UGR (Subgrupos C2, A3, A1, E3, B1).")
        api._append_log("🛡️ 2 archivos modificados localmente (.ipynb) protegidos contra sobrescritura (SHA-256).")
        api._append_log("📬 Correo UGR (@correo.ugr.es): 3 mensajes revisados (BODY.PEEK[]), 2 auto-reenviados.")
        api._append_log("✅ Sincronización completada (DASHBOARD.md y deadlines.ics actualizados).")

        server = PradoUIServer(api=api)
        base_url = server.start()

        targets = [
            ("gui_01_dashboard.png", f"{base_url}&view=dashboard&logs=1"),
            ("gui_02_courses.png", f"{base_url}&view=courses"),
            ("gui_03_mail.png", f"{base_url}&view=mail&open_msg=901"),
            ("gui_04_calendar_doctor.png", f"{base_url}&view=calendar&run_doctor=1"),
            ("gui_05_onboarding.png", f"{base_url}&view=onboarding"),
        ]

        try:
            for filename, target_url in targets:
                out_path = screens_dir / filename
                cmd = [
                    str(chrome_bin),
                    "--headless=new",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    "--window-size=1240,840",
                    "--force-device-scale-factor=2",
                    "--virtual-time-budget=2500",
                    f"--screenshot={out_path}",
                    target_url,
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"  ✓ Captured {out_path.name} ({out_path.stat().st_size // 1024} KB)")
        finally:
            server.stop()
            ics_f = courses_root_sim / "deadlines.ics"
            if ics_f.exists() and created_sim_dir:
                ics_f.unlink(missing_ok=True)
            if created_sim_dir:
                try:
                    courses_root_sim.rmdir()
                except Exception:
                    pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
