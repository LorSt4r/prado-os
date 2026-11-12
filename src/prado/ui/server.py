"""
PradoOS Control Center Local API Server (`127.0.0.1` Loopback Engine).

Exposes a thread-safe REST API over `127.0.0.1:<ephemeral_port>` protected by an
ephemeral session token (`X-Prado-Token`) for the PradoOS Desktop Control Center UI
(`pywebview` native window or local browser fallback).
"""

from __future__ import annotations

import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import socket
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from prado import __version__
from prado.auth.credentials import CredentialStore
from prado.auth.mfa import MfaResolver
from prado.auth.saml import UgrSamlDriver
from prado.auth.session import MoodleSessionManager
from prado.cli import _obtain_authenticated_session, _sync_single_course, normalize_ugr_username
from prado.config import (
    PradoConfig,
    get_config_file,
    get_default_academic_year_code,
    get_default_moodle_url,
    get_mail_cache_file,
    load_config,
    prompt_folder_picker_gui,
    save_config,
)
from prado.core.adoption import AdoptionScanner
from prado.core.discovery import CourseDiscovery, CourseFilter
from prado.core.downloader import SafeDownloader, SyncSummary
from prado.core.overwrite import OverwriteGuard
from prado.core.router import CourseRouter
from prado.exceptions import (
    AuthenticationRequiredError,
    InvalidCredentialsError,
    MfaRequiredError,
    PradoError,
)
from prado.exporters.calendar import export_calendar
from prado.exporters.changelog import export_changelog
from prado.exporters.dashboard import export_dashboard
from prado.i18n import SUPPORTED_LANGUAGES, normalize_language, t
from prado.mail.client import UgrMailClient, load_mail_cache
from prado.notifications.desktop import DesktopNotifier
from prado.scheduler.daemon import DaemonManager
from prado.scheduler.doctor import DoctorEngine, ProbeStatus
from prado.state import CourseRecord, StateDatabase
from prado.ui.dialogs import open_folder, open_url


def _get_portal_presets() -> Dict[str, str]:
    code = get_default_academic_year_code()
    return {
        "grado": f"https://pradogrado{code}.ugr.es",
        "posgrado": f"https://pradoposgrado{code}.ugr.es",
        "ceprud": f"https://pradoceprud{code}.ugr.es",
    }


PORTAL_PRESETS: Dict[str, str] = _get_portal_presets()


def parse_deadlines_from_ics(ics_path: Path) -> List[Dict[str, Any]]:
    """
    Lightweight parser for existing `deadlines.ics` in `courses_root` so upcoming
    deadlines are immediately visible in the Control Center even before a new sync.
    """
    if not ics_path.exists():
        return []
    try:
        raw = ics_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    # Unfold RFC-5545 folded lines
    unfolded = re.sub(r"\r?\n[ \t]", "", raw)
    events: List[Dict[str, Any]] = []
    for block in unfolded.split("BEGIN:VEVENT")[1:]:
        end_idx = block.find("END:VEVENT")
        if end_idx != -1:
            block = block[:end_idx]

        summary_m = re.search(r"^SUMMARY:(.*)$", block, re.MULTILINE)
        dtstart_m = re.search(r"^DTSTART(?:;[^:]*)?:([0-9T]+Z?)$", block, re.MULTILINE)
        desc_m = re.search(r"^DESCRIPTION:(.*)$", block, re.MULTILINE)
        cat_m = re.search(r"^CATEGORIES:(.*)$", block, re.MULTILINE)

        if not summary_m or not dtstart_m:
            continue

        title = summary_m.group(1).strip().replace(r"\,", ",").replace(r"\;", ";").replace(r"\n", " ")
        dt_str = dtstart_m.group(1).strip()
        due_dt: Optional[datetime.datetime] = None
        for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
            try:
                due_dt = datetime.datetime.strptime(dt_str, fmt)
                break
            except ValueError:
                continue

        if due_dt is None:
            continue

        course_name = cat_m.group(1).strip() if cat_m else ""
        if not course_name and title.startswith("[") and "]" in title:
            course_name = title[1 : title.find("]")]
            title = title[title.find("]") + 1 :].strip()

        now_date = datetime.datetime.now(datetime.timezone.utc).date()
        due_date_val = due_dt.date()
        days_left = (due_date_val - now_date).days

        kind = "EXAM" if any(k in title.lower() for k in ("examen", "test", "prueba", "parcial", "control")) else "ASSIGNMENT"
        events.append({
            "course": course_name or "PRADO UGR",
            "title": title,
            "due_iso": due_dt.strftime("%Y-%m-%d %H:%M"),
            "timestamp": due_dt.timestamp(),
            "days_left": days_left,
            "kind": kind,
            "description": (desc_m.group(1).strip().replace(r"\n", "\n").replace(r"\,", ",") if desc_m else ""),
        })

    events.sort(key=lambda x: x["timestamp"])
    return events


class PradoControlCenterAPI:
    """
    Core controller orchestrating all PradoOS engines for the Desktop Control Center UI.
    Thread-safe, stateful, and testable both directly and via the loopback HTTP server.
    """

    def __init__(
        self,
        cfg: Optional[PradoConfig] = None,
        on_status_change: Optional[Callable[[str, Optional[str]], None]] = None,
    ) -> None:
        self.cfg: PradoConfig = cfg or load_config()
        self.on_status_change = on_status_change

        # Sync state & real-time progress tracking
        self._sync_lock = threading.Lock()
        self.status: str = "idle"  # "idle" | "syncing" | "mfa_required" | "error"
        self.progress_pct: int = 0
        self.current_step: str = ""
        self.logs: List[str] = []
        self.last_sync_time: Optional[str] = None
        self.last_error: Optional[str] = None
        self.last_summary: Dict[str, Any] = {}
        self.live_deadlines: List[Dict[str, Any]] = []

        # Interactive 2FA / MFA coordination between UI and background SAML worker
        self.mfa_pending: bool = False
        self.mfa_prompt_message: str = ""
        self._mfa_event = threading.Event()
        self._mfa_code_value: Optional[str] = None

        # Cached daemon & credential presence checks to keep /api/state fast (< 2ms) and avoid Keychain polling
        self._daemon_cache: Optional[Dict[str, Any]] = None
        self._daemon_cache_ts: float = 0.0
        self._credentials_cache: Optional[Tuple[str, bool]] = None

        # In-memory cache of recently opened full emails (with attachment payloads)
        self._loaded_messages: Dict[str, Any] = {}
        self.gcalendar_enabled: bool = False
        self.gcalendar_id: str = "auto"

        self.notifier = DesktopNotifier(app_name="PradoOS")

    # -------------------------------------------------------------------------
    # Internal Logging & Status Notification
    # -------------------------------------------------------------------------
    def _append_log(self, message: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}"
        self.logs.append(line)
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]

    def _set_status(self, new_status: str, step: Optional[str] = None, pct: Optional[int] = None) -> None:
        self.status = new_status
        if step is not None:
            self.current_step = step
        if pct is not None:
            self.progress_pct = max(0, min(100, int(pct)))
        if callable(self.on_status_change):
            try:
                self.on_status_change(self.status, self.last_sync_time)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # MFA Coordination Callback (Invoked by MfaResolver in Worker Thread)
    # -------------------------------------------------------------------------
    def _wait_for_mfa_code(self) -> Optional[str]:
        """
        Called by MfaResolver when UGR SAML requires a 6-digit email verification code
        and neither IMAP nor Apple Mail auto-resolved it.
        Signals the UI to open the inline 6-digit MFA modal and waits up to 180s.
        """
        lang = self.cfg.language or "es"
        prompt_map = {
            "es": "Introduce el código de 6 dígitos enviado a tu correo @correo.ugr.es:",
            "en": "Enter the 6-digit verification code sent to your @correo.ugr.es email:",
            "it": "Inserisci il codice a 6 cifre inviato alla tua email @correo.ugr.es:",
            "fr": "Entrez le code à 6 chiffres envoyé à votre courriel @correo.ugr.es :",
        }
        self.mfa_prompt_message = prompt_map.get(lang, prompt_map["es"])
        self._mfa_code_value = None
        self._mfa_event.clear()
        self.mfa_pending = True
        prev_status = self.status
        self._set_status("mfa_required", step=self.mfa_prompt_message)
        self._append_log("🔐 Verificación en 2 pasos (MFA) requerida por PRADO UGR. Esperando código de 6 dígitos...")

        signaled = self._mfa_event.wait(timeout=180.0)
        self.mfa_pending = False
        code = self._mfa_code_value
        self._mfa_code_value = None

        if signaled and code and re.match(r"^[0-9]{6}$", code.strip()):
            self._set_status(prev_status if prev_status != "mfa_required" else "syncing")
            self._append_log("✓ Código MFA recibido. Validando dispositivo por 30 días...")
            return code.strip()

        return None

    def submit_mfa_code(self, code: str) -> Dict[str, Any]:
        """Submits the 6-digit MFA code entered by the student in the Control Center UI."""
        clean = re.sub(r"\D", "", str(code or ""))
        if len(clean) != 6:
            lang = normalize_language(self.cfg.language)
            err_map = {
                "es": "El código MFA debe tener exactamente 6 dígitos numéricos.",
                "en": "The MFA code must be exactly 6 numeric digits.",
                "it": "Il codice MFA deve contenere esattamente 6 cifre numeriche.",
                "fr": "Le code MFA doit contenir exactement 6 chiffres.",
            }
            return {"status": "error", "error": err_map.get(lang, err_map["es"])}
        self._mfa_code_value = clean
        self._mfa_event.set()
        return {"status": "success", "code_submitted": True}

    def cancel_mfa(self) -> Dict[str, Any]:
        """Cancels a pending 2FA code wait cleanly and returns status to idle."""
        self._mfa_code_value = None
        self.mfa_pending = False
        self._mfa_event.set()
        if self.status == "mfa_required":
            self._set_status("idle", step="", pct=0)
        return {"status": "cancelled"}

    # -------------------------------------------------------------------------
    # 1. Full Application State (`GET /api/state`)
    # -------------------------------------------------------------------------
    def get_full_state(self) -> Dict[str, Any]:
        if get_config_file().exists():
            try:
                self.cfg = load_config()
            except Exception:
                pass

        cred_store = CredentialStore()
        has_credentials = False
        if self.cfg.username:
            if self._credentials_cache is not None and self._credentials_cache[0] == self.cfg.username:
                has_credentials = self._credentials_cache[1]
            else:
                try:
                    u, p = cred_store.get_sso_credentials(self.cfg.username)
                    has_credentials = bool(u and p)
                except Exception:
                    has_credentials = False
                self._credentials_cache = (self.cfg.username, has_credentials)
        else:
            self._credentials_cache = None

        sess_mgr = MoodleSessionManager(base_url=self.cfg.moodle_url)
        has_session_cookies = sess_mgr.load_session()

        is_onboarded = bool(get_config_file().exists() and self.cfg.username and has_credentials)

        # Read courses & recent files from SQLite StateDatabase
        courses_list: List[Dict[str, Any]] = []
        recent_files: List[Dict[str, Any]] = []
        stats = {
            "total_courses": 0,
            "active_courses": 0,
            "total_files": 0,
            "protected_files": 0,
            "adopted_files": 0,
        }
        try:
            state_db = StateDatabase()
            all_courses = state_db.list_all_courses()
            for c in all_courses:
                subg = ""
                for k, v in (self.cfg.sync.subgroups or {}).items():
                    if k.lower() in (c.fullname.lower(), (c.shortname or "").lower(), str(c.course_id)):
                        subg = v
                        break
                courses_list.append({
                    "course_id": c.course_id,
                    "fullname": c.fullname,
                    "shortname": c.shortname or "",
                    "idnumber": c.idnumber or "",
                    "category": c.category or "",
                    "is_active": bool(c.is_active),
                    "last_synced_at": c.last_synced_at or "",
                    "subgroup": subg,
                })

            conn = state_db._get_connection()
            try:
                cur_stats = conn.execute(
                    "SELECT COUNT(*) AS total, "
                    "SUM(CASE WHEN student_modified = 1 OR is_modified = 1 THEN 1 ELSE 0 END) AS protected, "
                    "SUM(CASE WHEN is_adopted = 1 THEN 1 ELSE 0 END) AS adopted "
                    "FROM files"
                ).fetchone()
                if cur_stats:
                    stats["total_files"] = int(cur_stats["total"] or 0)
                    stats["protected_files"] = int(cur_stats["protected"] or 0)
                    stats["adopted_files"] = int(cur_stats["adopted"] or 0)

                rows = conn.execute(
                    "SELECT path, course_id, file_size, last_synced_at, is_adopted, student_modified "
                    "FROM files ORDER BY last_synced_at DESC LIMIT 30"
                ).fetchall()
                for r in rows:
                    recent_files.append({
                        "path": r["path"],
                        "name": Path(r["path"]).name,
                        "course_id": r["course_id"],
                        "file_size": int(r["file_size"] or 0),
                        "last_synced_at": r["last_synced_at"] or "",
                        "is_adopted": bool(r["is_adopted"]),
                        "student_modified": bool(r["student_modified"]),
                    })
            finally:
                conn.close()

            stats["total_courses"] = len(courses_list)
            stats["active_courses"] = sum(1 for c in courses_list if c["is_active"])
        except Exception:
            pass

        # Deadlines from live sync or parsed from deadlines.ics
        deadlines = self.live_deadlines
        if not deadlines:
            ics_file = self.cfg.courses_root / "deadlines.ics"
            deadlines = parse_deadlines_from_ics(ics_file)

        # Cached daemon status (refresh every 15s)
        now_ts = time.time()
        if self._daemon_cache is None or (now_ts - self._daemon_cache_ts) > 15.0:
            try:
                self._daemon_cache = DaemonManager().status().to_dict()
                self._daemon_cache_ts = now_ts
            except Exception as exc:
                self._daemon_cache = {"installed": False, "active": False, "error": str(exc)}

        # Determine active portal key
        moodle_url_low = (self.cfg.moodle_url or "").lower()
        if "posgrado" in moodle_url_low:
            portal_key = "posgrado"
        elif "ceprud" in moodle_url_low:
            portal_key = "ceprud"
        else:
            portal_key = "grado"

        return {
            "version": __version__,
            "language": self.cfg.language or "es",
            "supported_languages": list(SUPPORTED_LANGUAGES),
            "is_onboarded": is_onboarded,
            "auth": {
                "username": self.cfg.username or "",
                "has_credentials": has_credentials,
                "has_session_cookies": has_session_cookies,
                "moodle_url": self.cfg.moodle_url,
                "portal": portal_key,
            },
            "config": {
                "courses_root": str(self.cfg.courses_root),
                "preset": self.cfg.sync.preset or "mirror",
                "semester": self.cfg.sync.semester,
                "auto_sync": bool(getattr(self.cfg.sync, "auto_sync", False)),
                "auto_sync_interval_minutes": int(getattr(self.cfg.sync, "auto_sync_interval_minutes", 60)),
                "subgroups": self.cfg.sync.subgroups or {},
                "notifications_enabled": bool(self.cfg.notifications.enabled),
                "notifications_sound": bool(self.cfg.notifications.sound),
                "mail": {
                    "enabled": bool(self.cfg.mail.enabled),
                    "forward_enabled": bool(self.cfg.mail.forward_enabled),
                    "forward_to": self.cfg.mail.forward_to or "",
                    "forward_mode": self.cfg.mail.forward_mode or "academic",
                    "filter_senders": list(self.cfg.mail.filter_senders or []),
                    "filter_keywords": list(self.cfg.mail.filter_keywords or []),
                },
                "gcalendar": {
                    "enabled": bool(self.gcalendar_enabled),
                    "calendar_id": self.gcalendar_id or "auto",
                },
            },
            "sync": {
                "status": self.status,
                "progress_pct": self.progress_pct,
                "current_step": self.current_step,
                "logs": self.logs[-60:],
                "last_sync_time": self.last_sync_time,
                "last_error": self.last_error,
                "last_summary": self.last_summary,
                "mfa_pending": self.mfa_pending,
                "mfa_prompt": self.mfa_prompt_message,
            },
            "stats": stats,
            "courses": courses_list,
            "deadlines": deadlines,
            "recent_files": recent_files,
            "daemon": self._daemon_cache,
        }

    # -------------------------------------------------------------------------
    # 2. Onboarding & Authentication (`POST /api/onboard`, `/api/auth/login`)
    # -------------------------------------------------------------------------
    def save_onboarding_and_login(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        lang = normalize_language(payload.get("language", self.cfg.language or "es"))
        self.cfg.language = lang

        portal = str(payload.get("portal", "grado")).strip().lower()
        if portal in PORTAL_PRESETS:
            self.cfg.moodle_url = PORTAL_PRESETS[portal]
        elif payload.get("moodle_url"):
            self.cfg.moodle_url = str(payload["moodle_url"]).strip().rstrip("/")

        if payload.get("courses_root"):
            self.cfg.courses_root = Path(str(payload["courses_root"])).expanduser().resolve()

        preset = str(payload.get("preset", self.cfg.sync.preset or "mirror")).strip().lower()
        if preset in ("mirror", "smart"):
            self.cfg.sync.preset = preset

        if "notifications_enabled" in payload:
            self.cfg.notifications.enabled = bool(payload["notifications_enabled"])
        if "auto_sync" in payload:
            self.cfg.sync.auto_sync = bool(payload["auto_sync"])
        if "auto_sync_interval_minutes" in payload:
            try:
                mins = int(payload["auto_sync_interval_minutes"])
                if 15 <= mins <= 1440:
                    self.cfg.sync.auto_sync_interval_minutes = mins
            except (TypeError, ValueError):
                pass

        raw_user = str(payload.get("username", self.cfg.username or "")).strip()
        raw_pass = str(payload.get("password", "")).strip()

        if not raw_user:
            err_user = {
                "es": "Introduce tu correo institucional UGR (@correo.ugr.es).",
                "en": "Enter your institutional UGR email (@correo.ugr.es).",
                "it": "Inserisci la tua email istituzionale UGR (@correo.ugr.es).",
                "fr": "Saisissez votre courriel institutionnel UGR (@correo.ugr.es).",
            }
            return {"status": "error", "field": "username", "error": err_user.get(lang, err_user["es"])}

        norm_user = normalize_ugr_username(raw_user, self.cfg.moodle_url) or raw_user
        self.cfg.username = norm_user

        cred_store = CredentialStore()
        if raw_pass:
            cred_store.set_sso_credentials(norm_user, raw_pass)
        else:
            # Verify stored password exists
            try:
                cred_store.get_sso_credentials(norm_user)
            except Exception:
                err_pass = {
                    "es": "Introduce tu contraseña de Acceso Identificado UGR.",
                    "en": "Enter your UGR SSO password.",
                    "it": "Inserisci la tua password di Acceso Identificado UGR.",
                    "fr": "Saisissez votre mot de passe Acceso Identificado UGR.",
                }
                return {"status": "error", "field": "password", "error": err_pass.get(lang, err_pass["es"])}

        try:
            self.cfg.courses_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return {"status": "error", "field": "courses_root", "error": str(exc)}
        save_config(self.cfg)
        self._credentials_cache = (norm_user, True)

        # If trigger_sync is requested (default after onboarding), launch background login + sync
        if payload.get("start_sync", True):
            self.start_sync()
        else:
            self._set_status(self.status)
        return {"status": "success", "username": norm_user, "courses_root": str(self.cfg.courses_root)}

    def update_language(self, lang_code: str) -> Dict[str, Any]:
        self.cfg.language = normalize_language(lang_code)
        save_config(self.cfg)
        self._set_status(self.status)
        return {"status": "success", "language": self.cfg.language}

    def logout(self) -> Dict[str, Any]:
        cred_store = CredentialStore()
        if self.cfg.username:
            cred_store.delete_sso_credentials(self.cfg.username)
        self.cfg.username = ""
        self._credentials_cache = None
        save_config(self.cfg)
        sess_mgr = MoodleSessionManager(base_url=self.cfg.moodle_url)
        sess_mgr.clear_session()
        self._set_status("idle", step="", pct=0)
        self._append_log("🔒 Sesión cerrada y credenciales eliminadas del llavero.")
        return {"status": "success"}

    # -------------------------------------------------------------------------
    # 3. Real-Time Course-by-Course Synchronization (`POST /api/sync/start`)
    # -------------------------------------------------------------------------
    def start_sync(self, course_filter: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        if not self._sync_lock.acquire(blocking=False):
            return {"status": "already_running"}

        t_worker = threading.Thread(
            target=self._sync_worker_detailed,
            kwargs={"course_filter": course_filter, "force": force},
            daemon=True,
        )
        t_worker.start()
        return {"status": "started"}

    def _sync_worker_detailed(self, course_filter: Optional[str] = None, force: bool = False) -> None:
        try:
            self.cfg = load_config()
            self.last_error = None
            self._set_status("syncing", step=t("sync_starting", self.cfg.language), pct=5)
            self._append_log("🚀 Iniciando sincronización con PRADO UGR...")

            state_db = StateDatabase()
            self.cfg.courses_root.mkdir(parents=True, exist_ok=True)

            # Step 1: Adoption scan (protect local files)
            self._set_status("syncing", step="Escaneando carpeta local y protegiendo archivos modificados...", pct=12)
            adoption_scanner = AdoptionScanner(self.cfg.courses_root, state_db)
            adoption_scanner.scan_local_files()

            # Step 2: SAML Authentication (with live inline MFA callback + GUI fallback)
            self._set_status("syncing", step="Autenticando sesión SSO con la Universidad de Granada...", pct=20)
            self._append_log(f"🔑 Conectando a {self.cfg.moodle_url} como {self.cfg.username}...")
            session = _obtain_authenticated_session(
                cfg=self.cfg,
                interactive=False,
                json_mode=False,
                gui_mode=True,
                code_callback=self._wait_for_mfa_code,
            )
            self._append_log("✓ Sesión SAML validada correctamente.")

            # Step 3: Course Discovery
            self._set_status("syncing", step="Descubriendo asignaturas matriculadas en PRADO...", pct=30)
            discovery = CourseDiscovery(session=session, base_url=self.cfg.moodle_url)
            c_filter = CourseFilter(
                semester=self.cfg.sync.semester,
                active_only=True,
                subgroup_map=self.cfg.sync.subgroups,
            )
            courses = discovery.discover_courses(course_filter=c_filter)
            if course_filter:
                target_str = str(course_filter).strip().lower()
                courses = [
                    c
                    for c in courses
                    if str(c.id) == target_str
                    or c.slug.lower() == target_str
                    or c.folder_name.lower() == target_str
                    or target_str in c.fullname.lower()
                ]

            self._append_log(f"📚 {len(courses)} asignatura(s) activa(s) detectada(s).")

            router = CourseRouter(self.cfg.sync)
            downloader = SafeDownloader(session=session)
            overwrite_guard = OverwriteGuard(state_db)
            summary = SyncSummary()
            planned_actions: List[Dict[str, Any]] = []

            total_c = max(1, len(courses))
            for idx, c in enumerate(courses, start=1):
                pct = 30 + int((idx - 1) / total_c * 52)
                self._set_status("syncing", step=f"({idx}/{len(courses)}) {c.fullname}", pct=pct)
                self._append_log(f"🔄 [{idx}/{len(courses)}] Sincronizando: {c.fullname}...")

                state_db.upsert_course(
                    CourseRecord(
                        course_id=c.id,
                        fullname=c.fullname,
                        shortname=c.shortname,
                        idnumber=c.idnumber,
                        category=c.coursecategory,
                        is_active=1 if c.is_active else 0,
                        last_synced_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    )
                )
                prev_dl = len(summary.downloaded_files)
                _sync_single_course(
                    course=c,
                    session=session,
                    cfg=self.cfg,
                    state_db=state_db,
                    router=router,
                    downloader=downloader,
                    adoption_scanner=adoption_scanner,
                    overwrite_guard=overwrite_guard,
                    summary=summary,
                    dry_run=False,
                    force=force,
                    planned_actions=planned_actions,
                )
                new_dl = len(summary.downloaded_files) - prev_dl
                if new_dl > 0:
                    self._append_log(f"   ✓ {new_dl} nuevo(s) archivo(s) descargado(s) en {c.shortname or c.fullname}.")

            # Step 4: Exporters (Dashboard, Changelog, ICS Calendar)
            self._set_status("syncing", step="Actualizando DASHBOARD.md y calendario deadlines.ics...", pct=86)
            export_dashboard(courses_root=self.cfg.courses_root, summary=summary, state_db=state_db)
            export_changelog(courses_root=self.cfg.courses_root, summary=summary)
            ics_path = export_calendar(courses_root=self.cfg.courses_root, deadlines=summary.deadlines)
            self.live_deadlines = parse_deadlines_from_ics(ics_path)

            # Step 5: Optional Mail Sync & Auto-Forwarding
            mail_info = None
            if self.cfg.mail.enabled:
                self._set_status("syncing", step="Comprobando buzón institucional @correo.ugr.es...", pct=92)
                try:
                    mail_client = UgrMailClient(config=self.cfg)
                    mail_res = mail_client.sync_and_forward(dry_run=False)
                    mail_info = {
                        "fetched": mail_res.get("fetched", 0),
                        "unread": mail_res.get("unread", 0),
                        "forwarded": mail_res.get("forwarded", 0),
                    }
                    self._append_log(
                        f"📬 Correo UGR: {mail_info['fetched']} revisados ({mail_info['unread']} no leídos), "
                        f"{mail_info['forwarded']} auto-reenviados."
                    )
                except Exception as mail_exc:
                    self._append_log(f"⚠ Correo UGR omitido: {mail_exc}")

            # Step 6: Optional Google Calendar Sync
            if self.gcalendar_enabled:
                self._set_status("syncing", step="Sincronizando entregas con Google Calendar...", pct=96)
                try:
                    from prado.exporters.gcalendar import GoogleCalendarSync

                    gcal = GoogleCalendarSync(calendar_id=self.gcalendar_id or "auto")
                    gcal_res = gcal.sync_deadlines(summary.deadlines, dry_run=False)
                    self._append_log(f"📅 Google Calendar: {gcal_res.get('created', 0)} eventos creados.")
                except Exception as gcal_exc:
                    self._append_log(f"⚠ Google Calendar: {gcal_exc}")

            self.last_sync_time = datetime.datetime.now().strftime("%H:%M")
            self.last_summary = {
                "courses_synced": len(courses),
                "downloaded": len(summary.downloaded_files),
                "adopted": len(summary.adopted_files),
                "conflicts": len(summary.conflict_files),
                "deadlines": len(summary.deadlines),
                "mail": mail_info,
            }
            self._append_log(
                f"✅ Sincronización completada ({len(courses)} asignaturas, "
                f"{len(summary.downloaded_files)} descargados, {len(summary.deadlines)} entregas)."
            )
            self._set_status("idle", step=t("sync_completed", self.cfg.language), pct=100)

            if self.cfg.notifications.enabled:
                self.notifier.notify(
                    title="PradoOS",
                    message=t("tray_sync_success_notification", self.cfg.language),
                    sound=self.cfg.notifications.sound,
                )
        except Exception as exc:
            self.last_error = str(exc)
            self._append_log(f"❌ Error en sincronización: {exc}")
            self._set_status("error", step=f"Error: {exc}", pct=0)
            if self.cfg.notifications.enabled:
                self.notifier.notify(
                    title="PradoOS",
                    message=t("tray_sync_error_notification", self.cfg.language, error=str(exc)),
                    urgency="critical",
                )
        finally:
            self._sync_lock.release()

    # -------------------------------------------------------------------------
    # 4. Courses & Folder Management (`GET /api/courses/discover`, `POST /api/courses/settings`)
    # -------------------------------------------------------------------------
    def discover_courses_live(self) -> Dict[str, Any]:
        try:
            self.cfg = load_config()
            session = _obtain_authenticated_session(
                cfg=self.cfg,
                interactive=False,
                json_mode=False,
                gui_mode=True,
                code_callback=self._wait_for_mfa_code,
            )
            discovery = CourseDiscovery(session=session, base_url=self.cfg.moodle_url)
            courses = discovery.discover_courses(course_filter=CourseFilter(active_only=False))
            state_db = StateDatabase()
            for c in courses:
                existing = state_db.get_course(c.id)
                is_act = existing.is_active if existing is not None else (1 if c.is_active else 0)
                state_db.upsert_course(
                    CourseRecord(
                        course_id=c.id,
                        fullname=c.fullname,
                        shortname=c.shortname,
                        idnumber=c.idnumber,
                        category=c.coursecategory,
                        is_active=is_act,
                        last_synced_at=existing.last_synced_at if existing else None,
                    )
                )
            self._append_log(f"🔍 Descubiertas {len(courses)} asignaturas en PRADO.")
            return {"status": "success", "discovered": len(courses)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def update_course_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if payload.get("courses_root"):
            self.cfg.courses_root = Path(str(payload["courses_root"])).expanduser().resolve()
            self.cfg.courses_root.mkdir(parents=True, exist_ok=True)

        if payload.get("preset") in ("mirror", "smart"):
            self.cfg.sync.preset = str(payload["preset"])

        if "semester" in payload:
            sem = payload["semester"]
            self.cfg.sync.semester = int(sem) if sem in (1, 2, "1", "2") else None

        if isinstance(payload.get("subgroups"), dict):
            clean_sub: Dict[str, str] = {}
            for k, v in payload["subgroups"].items():
                if str(k).strip() and str(v).strip():
                    clean_sub[str(k).strip()] = str(v).strip()
            self.cfg.sync.subgroups = clean_sub

        if isinstance(payload.get("active_courses"), dict):
            state_db = StateDatabase()
            for cid_str, is_act in payload["active_courses"].items():
                try:
                    state_db.set_course_active(int(cid_str), bool(is_act))
                except Exception:
                    pass

        save_config(self.cfg)
        self._append_log("💾 Configuración de asignaturas y carpetas guardada.")
        return {"status": "success", "courses_root": str(self.cfg.courses_root), "preset": self.cfg.sync.preset}

    def pick_folder_native(self, prompt: Optional[str] = None) -> Dict[str, Any]:
        chosen = prompt_folder_picker_gui(prompt or "Selecciona la carpeta para tus apuntes de PRADO UGR")
        if chosen:
            return {"status": "success", "path": str(chosen)}
        return {"status": "cancelled"}

    def open_local_path(self, rel_or_abs: Optional[str] = None) -> Dict[str, Any]:
        if not rel_or_abs:
            target = self.cfg.courses_root
        else:
            candidate = Path(rel_or_abs).expanduser()
            if not candidate.is_absolute():
                candidate = self.cfg.courses_root / candidate
            target = candidate.resolve()
            if target.is_file():
                target = target.parent
        ok = open_folder(target)
        return {"status": "success" if ok else "error", "path": str(target)}

    # -------------------------------------------------------------------------
    # 5. Institutional Mail (`@correo.ugr.es`) & Selective Auto-Forwarding
    # -------------------------------------------------------------------------
    def fetch_mail_inbox(
        self,
        filter_mode: str = "all",
        query: str = "",
        refresh: bool = False,
    ) -> Dict[str, Any]:
        try:
            if get_config_file().exists():
                self.cfg = load_config()
            cache = load_mail_cache(get_mail_cache_file())
            messages = cache.get("messages", [])

            if refresh or not messages:
                client = UgrMailClient(config=self.cfg)
                res = client.sync_and_forward(dry_run=False)
                messages = res.get("messages", [])

            filtered: List[Dict[str, Any]] = []
            q_low = (query or "").strip().lower()
            for m in messages:
                if not isinstance(m, dict):
                    continue
                if filter_mode == "unread" and not m.get("is_unread"):
                    continue
                if filter_mode == "academic" and not m.get("is_academic"):
                    continue
                if q_low:
                    haystack = f"{m.get('subject', '')} {m.get('sender', '')} {m.get('sender_email', '')}".lower()
                    if q_low not in haystack:
                        continue
                filtered.append(m)

            return {
                "status": "success",
                "messages": filtered,
                "total": len(messages),
                "unread": sum(1 for m in messages if isinstance(m, dict) and m.get("is_unread")),
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc), "messages": []}

    def read_mail_message(self, uid: str, mark_seen: bool = True) -> Dict[str, Any]:
        try:
            if get_config_file().exists():
                self.cfg = load_config()
            client = UgrMailClient(config=self.cfg)
            msg = client.read_message(uid=str(uid), mark_seen=mark_seen)
            self._loaded_messages[str(uid)] = msg
            return {"status": "success", "message": msg.to_dict()}
        except Exception as exc:
            # Fallback to cached message snippet if offline
            cache = load_mail_cache(get_mail_cache_file())
            for m in cache.get("messages", []):
                if isinstance(m, dict) and str(m.get("uid")) == str(uid):
                    return {"status": "success", "message": m, "cached_fallback": True}
            return {"status": "error", "error": str(exc)}

    def save_mail_attachment(self, uid: str, attachment_index: int, dest_dir: Optional[str] = None) -> Dict[str, Any]:
        try:
            msg = self._loaded_messages.get(str(uid))
            if msg is None:
                client = UgrMailClient(config=self.cfg)
                msg = client.read_message(uid=str(uid), mark_seen=False)
                self._loaded_messages[str(uid)] = msg

            att = next((a for a in msg.attachments if a.index == int(attachment_index)), None)
            if att is None and 0 <= int(attachment_index) < len(msg.attachments):
                att = msg.attachments[int(attachment_index)]

            if att is None or att.payload is None:
                return {"status": "error", "error": "Adjunto no encontrado o sin contenido."}

            if dest_dir:
                folder = Path(dest_dir).expanduser().resolve()
            else:
                chosen = prompt_folder_picker_gui(f"Guardar adjunto: {att.filename}")
                if not chosen:
                    return {"status": "cancelled"}
                folder = chosen

            folder.mkdir(parents=True, exist_ok=True)
            safe_name = Path(att.filename).name or f"adjunto_{uid}_{attachment_index}"
            out_file = folder / safe_name
            out_file.write_bytes(att.payload)
            open_folder(folder)
            return {"status": "success", "saved_path": str(out_file)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def update_mail_forwarding(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if "enabled" in payload:
            self.cfg.mail.enabled = bool(payload["enabled"])
        if "forward_enabled" in payload:
            self.cfg.mail.forward_enabled = bool(payload["forward_enabled"])
        if "forward_to" in payload:
            self.cfg.mail.forward_to = str(payload["forward_to"] or "").strip()
        if payload.get("forward_mode") in ("academic", "custom", "all"):
            self.cfg.mail.forward_mode = str(payload["forward_mode"])
        if "filter_senders" in payload:
            raw_s = payload["filter_senders"]
            if isinstance(raw_s, str):
                self.cfg.mail.filter_senders = [x.strip() for x in raw_s.split(",") if x.strip()]
            elif isinstance(raw_s, list):
                self.cfg.mail.filter_senders = [str(x).strip() for x in raw_s if str(x).strip()]
        if "filter_keywords" in payload:
            raw_k = payload["filter_keywords"]
            if isinstance(raw_k, str):
                self.cfg.mail.filter_keywords = [x.strip() for x in raw_k.split(",") if x.strip()]
            elif isinstance(raw_k, list):
                self.cfg.mail.filter_keywords = [str(x).strip() for x in raw_k if str(x).strip()]

        save_config(self.cfg)
        self._append_log("📬 Reglas de Correo UGR y Auto-Reenvío actualizadas.")
        return {"status": "success", "mail": self.get_full_state()["config"]["mail"]}

    # -------------------------------------------------------------------------
    # 6. Calendar, Daemon, Notifications & Doctor
    # -------------------------------------------------------------------------
    def run_calendar_action(self, action: str, calendar_id: Optional[str] = None) -> Dict[str, Any]:
        if calendar_id:
            self.gcalendar_id = str(calendar_id).strip()

        if action == "open_ics":
            ics_path = self.cfg.courses_root / "deadlines.ics"
            if not ics_path.exists():
                export_calendar(courses_root=self.cfg.courses_root, deadlines=[])
            open_folder(ics_path)
            return {"status": "success", "path": str(ics_path)}

        if action == "open_web":
            open_url("https://calendar.google.com")
            return {"status": "success"}

        if action == "gcalendar":
            try:
                from prado.core.downloader import DeadlineItem
                from prado.exporters.gcalendar import GoogleCalendarSync

                self.gcalendar_enabled = True

                # Convert parsed deadlines into DeadlineItem objects
                ics_events = parse_deadlines_from_ics(self.cfg.courses_root / "deadlines.ics")
                items: List[DeadlineItem] = []
                for idx, ev in enumerate(ics_events, start=1):
                    dt = datetime.datetime.fromtimestamp(ev["timestamp"], tz=datetime.timezone.utc)
                    items.append(
                        DeadlineItem(
                            course_id=idx,
                            course_name=ev["course"],
                            activity_id=idx,
                            title=ev["title"],
                            due_date=dt,
                            url=self.cfg.moodle_url,
                            description=ev.get("description", ""),
                        )
                    )
                gcal = GoogleCalendarSync(calendar_id=self.gcalendar_id or "auto")
                res = gcal.sync_deadlines(items, dry_run=False)
                return {"status": "success", "gcalendar": res}
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

        return {"status": "error", "error": f"Unknown calendar action: {action}"}

    def toggle_daemon(self, enable: bool, interval_hours: int = 4) -> Dict[str, Any]:
        mgr = DaemonManager()
        try:
            if enable:
                mgr.install(interval_seconds=max(900, int(interval_hours) * 3600))
                self._append_log(f"⏰ Servicio automático activado (cada {interval_hours}h).")
            else:
                mgr.uninstall()
                self._append_log("⏰ Servicio automático en segundo plano desactivado.")
            st = mgr.status().to_dict()
            self._daemon_cache = st
            self._daemon_cache_ts = time.time()
            return {"status": "success", "daemon": st}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def toggle_notifications(self, enabled: bool, sound: Optional[bool] = None, test: bool = False) -> Dict[str, Any]:
        self.cfg.notifications.enabled = bool(enabled)
        if sound is not None:
            self.cfg.notifications.sound = bool(sound)
        save_config(self.cfg)

        if test:
            self.notifier.notify(
                title="PradoOS",
                message=t("tray_sync_success_notification", self.cfg.language),
                sound=self.cfg.notifications.sound,
            )
        return {
            "status": "success",
            "enabled": self.cfg.notifications.enabled,
            "sound": self.cfg.notifications.sound,
        }

    def run_doctor_diagnostics(self) -> Dict[str, Any]:
        engine = DoctorEngine()
        report = engine.run_all()
        data = report.to_dict()
        data["status"] = "success"
        data["verdict"] = "SYSTEM_OPERATIONAL" if report.overall_status != ProbeStatus.FAIL else "ISSUES_DETECTED"
        return data


class PradoUIServer:
    """
    Threaded HTTP loopback server (`127.0.0.1:<port>`) serving the PradoOS Control Center SPA
    and dispatching `/api/*` requests to `PradoControlCenterAPI`.
    """

    def __init__(
        self,
        api: Optional[PradoControlCenterAPI] = None,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self.api = api or PradoControlCenterAPI()
        self.host = host
        self.requested_port = port
        self.port: int = 0
        self.token: str = secrets.token_urlsafe(24)
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/?token={self.token}"

    def start(self) -> str:
        if self._httpd is not None:
            return self.url

        from prado.ui.frontend import render_control_center_html

        server_ref = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                # Silence noisy HTTP access logs in stdout
                pass

            def _check_auth(self, parsed_url: Any) -> bool:
                header_tok = self.headers.get("X-Prado-Token", "")
                if header_tok and secrets.compare_digest(header_tok, server_ref.token):
                    return True
                qs = parse_qs(parsed_url.query)
                q_tok = (qs.get("token") or [""])[0]
                if q_tok and secrets.compare_digest(q_tok, server_ref.token):
                    return True
                return False

            def _send_json(self, payload: Dict[str, Any], status_code: int = 200) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _read_json_body(self) -> Dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or "0")
                if length <= 0:
                    return {}
                raw = self.rfile.read(length)
                try:
                    data = json.loads(raw.decode("utf-8"))
                    return data if isinstance(data, dict) else {}
                except Exception:
                    return {}

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                path = parsed.path

                if path in ("/", "/index.html"):
                    html_str = render_control_center_html(token=server_ref.token)
                    body = html_str.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return

                if not self._check_auth(parsed):
                    self._send_json({"status": "error", "error": "Unauthorized token"}, status_code=403)
                    return

                qs = parse_qs(parsed.query)
                if path == "/api/state":
                    self._send_json(server_ref.api.get_full_state())
                elif path == "/api/courses/discover":
                    self._send_json(server_ref.api.discover_courses_live())
                elif path in ("/api/mail/messages", "/api/mail/inbox"):
                    f_mode = (qs.get("filter") or ["all"])[0]
                    q_str = (qs.get("q") or [""])[0]
                    refresh = (qs.get("refresh") or ["0"])[0] in ("1", "true")
                    self._send_json(server_ref.api.fetch_mail_inbox(filter_mode=f_mode, query=q_str, refresh=refresh))
                elif path.startswith("/api/mail/message/"):
                    uid = path.split("/api/mail/message/", 1)[1]
                    self._send_json(server_ref.api.read_mail_message(uid=uid, mark_seen=True))
                elif path == "/api/doctor":
                    self._send_json(server_ref.api.run_doctor_diagnostics())
                else:
                    self._send_json({"status": "error", "error": f"Not found: {path}"}, status_code=404)

            def do_POST(self) -> None:
                parsed = urlparse(self.path)
                if not self._check_auth(parsed):
                    self._send_json({"status": "error", "error": "Unauthorized token"}, status_code=403)
                    return

                path = parsed.path
                body = self._read_json_body()

                if path == "/api/onboard":
                    self._send_json(server_ref.api.save_onboarding_and_login(body))
                elif path == "/api/language":
                    self._send_json(server_ref.api.update_language(str(body.get("language", "es"))))
                elif path == "/api/auth/mfa":
                    self._send_json(server_ref.api.submit_mfa_code(str(body.get("code", ""))))
                elif path == "/api/auth/mfa/cancel":
                    self._send_json(server_ref.api.cancel_mfa())
                elif path == "/api/auth/logout":
                    self._send_json(server_ref.api.logout())
                elif path == "/api/sync/start":
                    self._send_json(
                        server_ref.api.start_sync(
                            course_filter=body.get("course"),
                            force=bool(body.get("force", False)),
                        )
                    )
                elif path == "/api/courses/settings":
                    self._send_json(server_ref.api.update_course_settings(body))
                elif path == "/api/folder/pick":
                    self._send_json(server_ref.api.pick_folder_native(body.get("prompt")))
                elif path == "/api/folder/open":
                    self._send_json(server_ref.api.open_local_path(body.get("path")))
                elif path == "/api/mail/attachment":
                    self._send_json(
                        server_ref.api.save_mail_attachment(
                            uid=str(body.get("uid", "")),
                            attachment_index=int(body.get("index", 0)),
                            dest_dir=body.get("dest_dir"),
                        )
                    )
                elif path == "/api/mail/forwarding":
                    self._send_json(server_ref.api.update_mail_forwarding(body))
                elif path == "/api/calendar/action":
                    self._send_json(
                        server_ref.api.run_calendar_action(
                            action=str(body.get("action", "open_ics")),
                            calendar_id=body.get("calendar_id"),
                        )
                    )
                elif path == "/api/daemon/toggle":
                    self._send_json(
                        server_ref.api.toggle_daemon(
                            enable=bool(body.get("enable", True)),
                            interval_hours=int(body.get("interval_hours", 4)),
                        )
                    )
                elif path == "/api/notifications/toggle":
                    self._send_json(
                        server_ref.api.toggle_notifications(
                            enabled=bool(body.get("enabled", True)),
                            sound=body.get("sound"),
                            test=bool(body.get("test", False)),
                        )
                    )
                else:
                    self._send_json({"status": "error", "error": f"Not found: {path}"}, status_code=404)

        self._httpd = ThreadingHTTPServer((self.host, self.requested_port), Handler)
        self.port = int(self._httpd.server_address[1])
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self.url

    def stop(self) -> None:
        if self._httpd is not None:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:
                pass
            self._httpd = None
