"""
DASHBOARD.md & DASHBOARD.html Exporters for PradoOS.

Generates both:
1. DASHBOARD.md (concise Markdown overview for agents, editors, and CLI users)
2. DASHBOARD.html (self-contained, 100%-localized offline visual dashboard
   with direct links to course folders, upcoming deadlines, and deadlines.ics)
"""

from __future__ import annotations

import datetime
from enum import Enum
import html as html_lib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse

from prado.core.downloader import DeadlineItem, SyncSummary
from prado.i18n import normalize_language
from prado.state import CourseRecord, StateDatabase


class DeadlineUrgency(str, Enum):
    OVERDUE = "overdue"
    URGENT = "urgent"
    SOON = "soon"
    NORMAL = "normal"


_DASHBOARD_I18N: Dict[str, Dict[str, str]] = {
    "es": {
        "title": "Panel Académico — PradoOS",
        "subtitle": "Universidad de Granada · Sincronización local automática y segura",
        "last_sync": "Última sincronización:",
        "md_html_tip": "💡 Consejo: haz doble clic en `DASHBOARD.html` para abrir este panel visualmente en tu navegador y en `deadlines.ics` para añadir tus entregas al calendario.",
        "guide_title": "Cómo usar esta carpeta",
        "guide_dash_title": "Panel Visual (DASHBOARD.html)",
        "guide_dash_desc": "Ábrelo con doble clic en cualquier navegador para ver asignaturas, archivos descargados, próximas entregas y enlaces directos a PRADO.",
        "guide_ics_title": "Calendario de Entregas (deadlines.ics)",
        "guide_ics_desc": "Haz doble clic en deadlines.ics (o pulsa el botón) para importar automáticamente tus prácticas y exámenes con recordatorios en Outlook, Apple Calendar o Google Calendar.",
        "guide_ics_btn": "📅 Añadir entregas al Calendario (deadlines.ics)",
        "kpi_courses": "Asignaturas activas",
        "kpi_files": "Archivos sincronizados",
        "kpi_deadlines": "Próximas entregas",
        "kpi_sync": "Descargados última sinc.",
        "upcoming_deadlines": "Próximas Entregas y Exámenes",
        "no_deadlines": "No hay entregas ni exámenes pendientes próximos.",
        "col_status": "Estado",
        "col_due": "Fecha límite",
        "col_left": "Tiempo restante",
        "col_course": "Asignatura",
        "col_activity": "Actividad / Examen",
        "col_type": "Tipo",
        "col_link": "Enlace",
        "open_prado": "Abrir en PRADO",
        "type_exam": "Examen",
        "type_assignment": "Entrega",
        "urg_overdue": "⚠️ Vencida",
        "urg_urgent": "🚨 Urgente",
        "urg_soon": "⏳ Pronto",
        "urg_normal": "📅 Programada",
        "ago_suffix": "hace {dur}",
        "enrolled_courses": "Asignaturas Matriculadas",
        "no_courses": "Aún no se han sincronizado asignaturas.",
        "col_code": "Código",
        "col_course_name": "Asignatura",
        "col_files": "Archivos",
        "col_pending": "Pendientes",
        "open_folder_link": "Abrir carpeta →",
        "recent_sync": "Resumen de la Última Sincronización",
        "downloaded_files": "Archivos descargados",
        "updated_files": "Archivos actualizados",
        "adopted_files": "Archivos locales protegidos",
        "conflicts_detected": "Conflictos preservados",
        "forum_announcements": "Avisos en foros",
        "recent_emails": "Últimos Correos Académicos (@correo.ugr.es)",
        "col_mail_status": "Estado",
        "col_mail_date": "Fecha",
        "col_mail_sender": "Remitente",
        "col_mail_subject": "Asunto",
        "mail_new": "● Nuevo",
        "mail_read": "Leído",
        "footer_note": "PradoOS mantiene esta carpeta sincronizada automáticamente en segundo plano sin sobrescribir nunca tus apuntes editados localmente.",
    },
    "en": {
        "title": "Academic Dashboard — PradoOS",
        "subtitle": "University of Granada · Automatic, non-destructive local course sync",
        "last_sync": "Last Sync:",
        "md_html_tip": "💡 Tip: double-click `DASHBOARD.html` to view this dashboard in your browser and `deadlines.ics` to import deadlines into your calendar app.",
        "guide_title": "How to use this folder",
        "guide_dash_title": "Visual Dashboard (DASHBOARD.html)",
        "guide_dash_desc": "Double-click it to open a clean browser overview of your courses, synced files, upcoming deadlines, and direct PRADO links.",
        "guide_ics_title": "Deadlines Calendar (deadlines.ics)",
        "guide_ics_desc": "Double-click deadlines.ics (or click below) to import assignments and exams with reminders into Outlook, Apple Calendar, or Google Calendar.",
        "guide_ics_btn": "📅 Import Deadlines to Calendar (deadlines.ics)",
        "kpi_courses": "Active courses",
        "kpi_files": "Synced files",
        "kpi_deadlines": "Upcoming deadlines",
        "kpi_sync": "Downloaded last sync",
        "upcoming_deadlines": "Upcoming Deadlines & Exams",
        "no_deadlines": "No upcoming deadlines scheduled.",
        "col_status": "Status",
        "col_due": "Due Date",
        "col_left": "Time Left",
        "col_course": "Course",
        "col_activity": "Activity / Exam",
        "col_type": "Type",
        "col_link": "Link",
        "open_prado": "Open in PRADO",
        "type_exam": "Exam",
        "type_assignment": "Assignment",
        "urg_overdue": "⚠️ Overdue",
        "urg_urgent": "🚨 Urgent",
        "urg_soon": "⏳ Soon",
        "urg_normal": "📅 Scheduled",
        "ago_suffix": "{dur} ago",
        "enrolled_courses": "Enrolled Courses",
        "no_courses": "No courses synced yet.",
        "col_code": "Code",
        "col_course_name": "Course Name",
        "col_files": "Files",
        "col_pending": "Pending",
        "open_folder_link": "Open folder →",
        "recent_sync": "Recent Sync Summary",
        "downloaded_files": "Downloaded files",
        "updated_files": "Updated files",
        "adopted_files": "Adopted local files",
        "conflicts_detected": "Protected conflicts",
        "forum_announcements": "Forum announcements",
        "recent_emails": "Recent Academic Emails (@correo.ugr.es)",
        "col_mail_status": "Status",
        "col_mail_date": "Date",
        "col_mail_sender": "Sender",
        "col_mail_subject": "Subject",
        "mail_new": "● New",
        "mail_read": "Read",
        "footer_note": "PradoOS keeps this folder synced automatically in the background and never overwrites files you edit locally.",
    },
    "it": {
        "title": "Dashboard Accademica — PradoOS",
        "subtitle": "Universidad de Granada · Sincronizzazione locale automatica e sicura",
        "last_sync": "Ultimo aggiornamento:",
        "md_html_tip": "💡 Consiglio: fai doppio clic su `DASHBOARD.html` per aprire questo pannello nel browser e su `deadlines.ics` per aggiungere le scadenze al tuo calendario.",
        "guide_title": "Come usare questa cartella",
        "guide_dash_title": "Dashboard Visiva (DASHBOARD.html)",
        "guide_dash_desc": "Fai doppio clic per aprirla nel browser e vedere a colpo d'occhio tutti i corsi, i file scaricati, le prossime scadenze e i link diretti a PRADO.",
        "guide_ics_title": "Calendario Scadenze (deadlines.ics)",
        "guide_ics_desc": "Fai doppio clic su deadlines.ics (o clicca qui sotto) per importare consegne ed esami con promemoria in Outlook, Apple Calendar o Google Calendar.",
        "guide_ics_btn": "📅 Importa scadenze nel Calendario (deadlines.ics)",
        "kpi_courses": "Corsi attivi",
        "kpi_files": "File sincronizzati",
        "kpi_deadlines": "Prossime scadenze",
        "kpi_sync": "Nuovi nell'ultima sinc.",
        "upcoming_deadlines": "Prossime Scadenze ed Esami",
        "no_deadlines": "Nessuna consegna o esame imminente in programma.",
        "col_status": "Stato",
        "col_due": "Scadenza",
        "col_left": "Tempo rimasto",
        "col_course": "Corso",
        "col_activity": "Attività / Esame",
        "col_type": "Tipo",
        "col_link": "Link",
        "open_prado": "Apri su PRADO",
        "type_exam": "Esame",
        "type_assignment": "Consegna",
        "urg_overdue": "⚠️ Scaduta",
        "urg_urgent": "🚨 Urgente",
        "urg_soon": "⏳ A breve",
        "urg_normal": "📅 In programma",
        "ago_suffix": "{dur} fa",
        "enrolled_courses": "Corsi Iscritti",
        "no_courses": "Nessun corso ancora sincronizzato.",
        "col_code": "Codice",
        "col_course_name": "Nome del Corso",
        "col_files": "File",
        "col_pending": "In sospeso",
        "open_folder_link": "Apri cartella →",
        "recent_sync": "Riepilogo Ultima Sincronizzazione",
        "downloaded_files": "File scaricati",
        "updated_files": "File aggiornati",
        "adopted_files": "File locali protetti",
        "conflicts_detected": "Conflitti preservati",
        "forum_announcements": "Avvisi dai forum",
        "recent_emails": "Ultime Email Accademiche (@correo.ugr.es)",
        "col_mail_status": "Stato",
        "col_mail_date": "Data",
        "col_mail_sender": "Mittente",
        "col_mail_subject": "Oggetto",
        "mail_new": "● Nuova",
        "mail_read": "Letta",
        "footer_note": "PradoOS mantiene aggiornata questa cartella in background e non sovrascrive mai gli appunti o i file modificati da te.",
    },
    "fr": {
        "title": "Tableau de Bord Académique — PradoOS",
        "subtitle": "Université de Granada · Synchronisation locale automatique et sûre",
        "last_sync": "Dernière synchronisation :",
        "md_html_tip": "💡 Astuce : double-cliquez sur `DASHBOARD.html` pour l'ouvrir dans votre navigateur et sur `deadlines.ics` pour importer les échéances dans votre calendrier.",
        "guide_title": "Comment utiliser ce dossier",
        "guide_dash_title": "Tableau de Bord Visuel (DASHBOARD.html)",
        "guide_dash_desc": "Double-cliquez pour afficher dans votre navigateur vos cours, fichiers téléchargés, échéances à venir et liens directs vers PRADO.",
        "guide_ics_title": "Calendrier des Échéances (deadlines.ics)",
        "guide_ics_desc": "Double-cliquez sur deadlines.ics (ou cliquez ci-dessous) pour importer devoirs et examens avec rappels dans Outlook, Apple Calendar ou Google Calendar.",
        "guide_ics_btn": "📅 Ajouter au Calendrier (deadlines.ics)",
        "kpi_courses": "Cours actifs",
        "kpi_files": "Fichiers synchronisés",
        "kpi_deadlines": "Prochaines échéances",
        "kpi_sync": "Téléchargés (dernière sync)",
        "upcoming_deadlines": "Prochaines Échéances et Examens",
        "no_deadlines": "Aucune échéance ou examen prévu prochainement.",
        "col_status": "Statut",
        "col_due": "Échéance",
        "col_left": "Temps restant",
        "col_course": "Cours",
        "col_activity": "Activité / Examen",
        "col_type": "Type",
        "col_link": "Lien",
        "open_prado": "Ouvrir dans PRADO",
        "type_exam": "Examen",
        "type_assignment": "Devoir",
        "urg_overdue": "⚠️ Expirée",
        "urg_urgent": "🚨 Urgent",
        "urg_soon": "⏳ Bientôt",
        "urg_normal": "📅 Planifiée",
        "ago_suffix": "il y a {dur}",
        "enrolled_courses": "Cours Inscrits",
        "no_courses": "Aucun cours synchronisé pour le moment.",
        "col_code": "Code",
        "col_course_name": "Nom du Cours",
        "col_files": "Fichiers",
        "col_pending": "À rendre",
        "open_folder_link": "Ouvrir dossier →",
        "recent_sync": "Résumé de la Dernière Synchronisation",
        "downloaded_files": "Fichiers téléchargés",
        "updated_files": "Fichiers mis à jour",
        "adopted_files": "Fichiers locaux protégés",
        "conflicts_detected": "Conflits préservés",
        "forum_announcements": "Annonces du forum",
        "recent_emails": "Derniers Courriels Académiques (@correo.ugr.es)",
        "col_mail_status": "Statut",
        "col_mail_date": "Date",
        "col_mail_sender": "Expéditeur",
        "col_mail_subject": "Objet",
        "mail_new": "● Nouveau",
        "mail_read": "Lu",
        "footer_note": "PradoOS synchronise ce dossier en arrière-plan et n'écrase jamais vos fichiers modifiés localement.",
    },
}


def _dtext(lang: Optional[str], key: str) -> str:
    norm = normalize_language(lang) if lang else "en"
    return _DASHBOARD_I18N.get(norm, _DASHBOARD_I18N["en"]).get(key, key)


def _safe_http_url(url: str) -> str:
    cleaned = (url or "").strip()
    if cleaned.lower().startswith(("http://", "https://")):
        return cleaned
    return ""


def escape_markdown_table_cell(text: str) -> str:
    """Escapes pipe characters (|) and cleans whitespace for Markdown tables."""
    if not text:
        return ""
    cleaned = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    return cleaned.replace("|", r"\|")


def classify_deadline_type(title: str) -> str:
    """
    Returns 'Exam' if title contains exam keywords (exam, prueba, parcial, test, quiz),
    otherwise 'Assignment'.
    """
    lower = title.lower()
    exam_keywords = ["exam", "prueba", "parcial", "test", "quiz", "control"]
    if any(k in lower for k in exam_keywords):
        return "Exam"
    return "Assignment"


def format_time_left(
    due_date: datetime.datetime,
    now: Optional[datetime.datetime] = None,
    language: Optional[str] = None,
) -> Tuple[DeadlineUrgency, str, str]:
    """
    Computes time remaining until deadline.
    Returns: (urgency_enum, badge_str, human_duration_str)
    """
    if now is None:
        if due_date.tzinfo is not None:
            now = datetime.datetime.now(due_date.tzinfo)
        else:
            now = datetime.datetime.now()
    else:
        if due_date.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=due_date.tzinfo)
        elif due_date.tzinfo is None and now.tzinfo is not None:
            due_date = due_date.replace(tzinfo=now.tzinfo)

    if due_date < now:
        delta = now - due_date
        days = delta.days
        hours = delta.seconds // 3600
        raw_dur = f"{days}d {hours}h" if days > 0 else f"{hours}h"
        if language is None:
            return DeadlineUrgency.OVERDUE, "⚠️ Overdue", f"{raw_dur} ago"
        return (
            DeadlineUrgency.OVERDUE,
            _dtext(language, "urg_overdue"),
            _dtext(language, "ago_suffix").format(dur=raw_dur),
        )

    delta = due_date - now
    total_hours = delta.total_seconds() / 3600.0
    days = delta.days
    hours = delta.seconds // 3600
    dur = f"{days}d {hours:02d}h"

    if total_hours < 48.0:
        badge = "🚨 Urgent" if language is None else _dtext(language, "urg_urgent")
        return DeadlineUrgency.URGENT, badge, dur
    elif total_hours < 168.0:
        badge = "⏳ Soon" if language is None else _dtext(language, "urg_soon")
        return DeadlineUrgency.SOON, badge, dur
    else:
        badge = "📅 Scheduled" if language is None else _dtext(language, "urg_normal")
        return DeadlineUrgency.NORMAL, badge, dur


class DashboardExporter:
    """Generates and writes DASHBOARD.md and DASHBOARD.html atomically."""

    def __init__(
        self,
        courses_root: Path,
        state_db: Optional[StateDatabase] = None,
        academic_year: Optional[str] = None,
        language: Optional[str] = None,
    ):
        self.courses_root = Path(courses_root)
        self.state_db = state_db
        self.academic_year = academic_year or "2026/2027"
        self.language: Optional[str] = normalize_language(language) if language else None

    def _collect_data(
        self,
        summary: Optional[SyncSummary] = None,
        courses: Optional[List[CourseRecord]] = None,
    ) -> Tuple[List[DeadlineItem], List[CourseRecord], Dict[str, int], List[Dict[str, Any]]]:
        raw_deadlines = summary.deadlines if summary else []
        deadlines = [d for d in raw_deadlines if d.due_date is not None]

        def _sort_key(d: DeadlineItem) -> datetime.datetime:
            dt = d.due_date
            if dt.tzinfo is not None:
                return dt.astimezone(datetime.timezone.utc)
            return dt.replace(tzinfo=datetime.timezone.utc)

        sorted_deadlines = sorted(deadlines, key=_sort_key)

        course_list: List[CourseRecord] = []
        if courses is not None:
            course_list = courses
        elif self.state_db is not None:
            course_list = self.state_db.list_active_courses()

        pending_counts: Dict[str, int] = {}
        for d in sorted_deadlines:
            cid = str(d.course).lower()
            pending_counts[cid] = pending_counts.get(cid, 0) + 1

        academic_msgs: List[Dict[str, Any]] = []
        try:
            from prado.mail.client import load_mail_cache

            mail_cache = load_mail_cache()
            cached_msgs = mail_cache.get("messages", [])
            academic_msgs = [
                m for m in cached_msgs
                if isinstance(m, dict) and m.get("is_academic", True)
            ][:8]
        except Exception:
            academic_msgs = []

        return sorted_deadlines, course_list, pending_counts, academic_msgs

    def _count_course_files(self, course: CourseRecord) -> int:
        if self.state_db is None:
            return 0
        try:
            return len(self.state_db.list_files(course.course_id))
        except Exception:
            return 0

    def _count_course_pending(self, course: CourseRecord, pending_counts: Dict[str, int]) -> int:
        pending = pending_counts.get(str(course.course_id).lower(), 0)
        if not pending and course.shortname:
            pending = pending_counts.get(course.shortname.lower(), 0)
        if not pending and course.idnumber:
            pending = pending_counts.get(course.idnumber.lower(), 0)
        if not pending and course.fullname:
            pending = pending_counts.get(course.fullname.lower(), 0)
        return pending

    def _resolve_course_rel_folder(self, course: CourseRecord) -> Optional[str]:
        """Resolves a safe single-segment subdirectory under courses_root for HTML links."""
        if not self.courses_root.exists():
            return None

        candidates: List[str] = []
        if self.state_db is not None:
            try:
                files = self.state_db.list_files(course.course_id)
                for f in files:
                    if getattr(f, "path", None):
                        parts = Path(str(f.path)).parts
                        if parts and parts[0]:
                            candidates.append(parts[0])
                            break
            except Exception:
                pass

        try:
            from prado.core.discovery import derive_course_slug, sanitize_folder_name

            if course.fullname:
                candidates.append(sanitize_folder_name(course.fullname))
                candidates.append(
                    derive_course_slug(course.fullname, course.shortname or "", course.idnumber or "")
                )
        except Exception:
            if course.fullname:
                candidates.append(course.fullname)

        if course.shortname:
            candidates.append(course.shortname)

        for cand in candidates:
            clean = (cand or "").strip()
            if not clean or clean in (".", "..") or clean.startswith(".") or "/" in clean or "\\" in clean:
                continue
            target = self.courses_root / clean
            if target.is_dir():
                return clean
        return None

    def render(
        self,
        summary: Optional[SyncSummary] = None,
        courses: Optional[List[CourseRecord]] = None,
        now: Optional[datetime.datetime] = None,
    ) -> str:
        """Renders DASHBOARD.md. Uses legacy headings if self.language is None, else 100% localized."""
        current_time = now or datetime.datetime.now()
        ts_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        lang = self.language
        sorted_deadlines, course_list, pending_counts, academic_msgs = self._collect_data(
            summary=summary, courses=courses
        )

        if lang is None:
            lines = [
                f"# 🎓 Academic Dashboard — PradoOS ({self.academic_year})",
                "",
                f"**Last Sync:** {ts_str} CET",
                "",
                "## 📅 Upcoming Deadlines",
                "",
            ]
            if not sorted_deadlines:
                lines.append("No upcoming deadlines scheduled.")
            else:
                lines.append("| Status | Due Date | Time Left | Course | Activity / Exam | Type | Link |")
                lines.append("|---|---|:---:|:---:|---|:---:|:---:|")
                for item in sorted_deadlines:
                    _, badge, time_left = format_time_left(item.due_date, now=current_time, language=None)
                    due_str = item.due_date.strftime("%Y-%m-%d %H:%M")
                    item_type = classify_deadline_type(item.title)
                    safe_title = escape_markdown_table_cell(item.title)
                    course_label = escape_markdown_table_cell(item.course)
                    safe_url = item.url.replace("|", "%7C").replace("\r", "").replace("\n", "") if item.url else ""
                    link_str = f"[Open]({safe_url})" if safe_url else "N/A"
                    lines.append(
                        f"| {badge} | {due_str} | {time_left} | {course_label} | {safe_title} | {item_type} | {link_str} |"
                    )
            lines.append("")

            if course_list:
                lines.append("## 📚 Enrolled Courses")
                lines.append("")
                lines.append("| Code | Course Name | Files | Pending |")
                lines.append("|---|---|:---:|:---:|")
                for c in course_list:
                    cid_str = c.idnumber or str(c.course_id)
                    name = escape_markdown_table_cell(c.fullname)
                    file_count = self._count_course_files(c)
                    pending = self._count_course_pending(c, pending_counts)
                    lines.append(f"| {cid_str} | {name} | {file_count} | {pending} |")
                lines.append("")

            if summary is not None:
                lines.append("## 🔄 Recent Sync Summary")
                lines.append("")
                lines.append(f"- **Downloaded files:** {len(summary.downloaded_files)}")
                lines.append(f"- **Updated files:** {len(summary.updated_files)}")
                lines.append(f"- **Adopted files:** {len(summary.adopted_files)}")
                lines.append(f"- **Conflicts detected:** {len(summary.conflict_files)}")
                lines.append(f"- **Forum announcements:** {len(summary.forum_announcements)}")
                lines.append("")

            if academic_msgs:
                lines.append("## 📬 Últimos Correos Académicos (`@correo.ugr.es`)")
                lines.append("")
                lines.append("| Estado | Fecha | Remitente | Asunto |")
                lines.append("|:---:|---|---|---|")
                for m in academic_msgs:
                    st_badge = "● Nuevo" if m.get("is_unread") else "Leído"
                    dt_cell = escape_markdown_table_cell(str(m.get("date_str") or m.get("date") or ""))
                    from_cell = escape_markdown_table_cell(str(m.get("sender", "")))
                    subj_cell = escape_markdown_table_cell(str(m.get("subject", "")))
                    lines.append(f"| {st_badge} | {dt_cell} | {from_cell} | {subj_cell} |")
                lines.append("")

            return "\n".join(lines).strip() + "\n"

        # Localized coherent single-language Markdown
        lines = [
            f"# 🎓 {_dtext(lang, 'title')} ({self.academic_year})",
            "",
            f"**{_dtext(lang, 'last_sync')}** {ts_str} CET",
            "",
            f"> {_dtext(lang, 'md_html_tip')}",
            "",
            f"## 📅 {_dtext(lang, 'upcoming_deadlines')}",
            "",
        ]
        if not sorted_deadlines:
            lines.append(_dtext(lang, "no_deadlines"))
        else:
            lines.append(
                f"| {_dtext(lang, 'col_status')} | {_dtext(lang, 'col_due')} | {_dtext(lang, 'col_left')} | "
                f"{_dtext(lang, 'col_course')} | {_dtext(lang, 'col_activity')} | {_dtext(lang, 'col_type')} | {_dtext(lang, 'col_link')} |"
            )
            lines.append("|---|---|:---:|:---:|---|:---:|:---:|")
            for item in sorted_deadlines:
                _, badge, time_left = format_time_left(item.due_date, now=current_time, language=lang)
                due_str = item.due_date.strftime("%Y-%m-%d %H:%M")
                raw_type = classify_deadline_type(item.title)
                item_type = _dtext(lang, "type_exam" if raw_type == "Exam" else "type_assignment")
                safe_title = escape_markdown_table_cell(item.title)
                course_label = escape_markdown_table_cell(item.course)
                safe_url = _safe_http_url(item.url or "").replace("|", "%7C")
                link_str = f"[{_dtext(lang, 'open_prado')}]({safe_url})" if safe_url else "—"
                lines.append(
                    f"| {badge} | {due_str} | {time_left} | {course_label} | {safe_title} | {item_type} | {link_str} |"
                )
        lines.append("")

        if course_list:
            lines.append(f"## 📚 {_dtext(lang, 'enrolled_courses')}")
            lines.append("")
            lines.append(
                f"| {_dtext(lang, 'col_code')} | {_dtext(lang, 'col_course_name')} | "
                f"{_dtext(lang, 'col_files')} | {_dtext(lang, 'col_pending')} |"
            )
            lines.append("|---|---|:---:|:---:|")
            for c in course_list:
                cid_str = c.idnumber or str(c.course_id)
                name = escape_markdown_table_cell(c.fullname)
                file_count = self._count_course_files(c)
                pending = self._count_course_pending(c, pending_counts)
                lines.append(f"| {cid_str} | {name} | {file_count} | {pending} |")
            lines.append("")

        if summary is not None:
            lines.append(f"## 🔄 {_dtext(lang, 'recent_sync')}")
            lines.append("")
            lines.append(f"- **{_dtext(lang, 'downloaded_files')}:** {len(summary.downloaded_files)}")
            lines.append(f"- **{_dtext(lang, 'updated_files')}:** {len(summary.updated_files)}")
            lines.append(f"- **{_dtext(lang, 'adopted_files')}:** {len(summary.adopted_files)}")
            lines.append(f"- **{_dtext(lang, 'conflicts_detected')}:** {len(summary.conflict_files)}")
            lines.append(f"- **{_dtext(lang, 'forum_announcements')}:** {len(summary.forum_announcements)}")
            lines.append("")

        if academic_msgs:
            lines.append(f"## 📬 {_dtext(lang, 'recent_emails')}")
            lines.append("")
            lines.append(
                f"| {_dtext(lang, 'col_mail_status')} | {_dtext(lang, 'col_mail_date')} | "
                f"{_dtext(lang, 'col_mail_sender')} | {_dtext(lang, 'col_mail_subject')} |"
            )
            lines.append("|:---:|---|---|---|")
            for m in academic_msgs:
                st_badge = _dtext(lang, "mail_new" if m.get("is_unread") else "mail_read")
                dt_cell = escape_markdown_table_cell(str(m.get("date_str") or m.get("date") or ""))
                from_cell = escape_markdown_table_cell(str(m.get("sender", "")))
                subj_cell = escape_markdown_table_cell(str(m.get("subject", "")))
                lines.append(f"| {st_badge} | {dt_cell} | {from_cell} | {subj_cell} |")
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def render_html(
        self,
        summary: Optional[SyncSummary] = None,
        courses: Optional[List[CourseRecord]] = None,
        now: Optional[datetime.datetime] = None,
    ) -> str:
        """Renders a self-contained, 100%-localized offline visual HTML dashboard."""
        lang = self.language or "es"
        current_time = now or datetime.datetime.now()
        ts_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        sorted_deadlines, course_list, pending_counts, academic_msgs = self._collect_data(
            summary=summary, courses=courses
        )

        total_files = sum(self._count_course_files(c) for c in course_list)
        if not total_files and summary is not None:
            total_files = len(summary.downloaded_files) + len(summary.adopted_files)
        last_dl = len(summary.downloaded_files) if summary is not None else 0

        # Deadlines HTML rows
        if not sorted_deadlines:
            deadlines_html = f'<p class="empty-state">{html_lib.escape(_dtext(lang, "no_deadlines"))}</p>'
        else:
            dl_rows: List[str] = []
            for item in sorted_deadlines:
                urg, badge, time_left = format_time_left(item.due_date, now=current_time, language=lang)
                due_str = item.due_date.strftime("%Y-%m-%d %H:%M")
                raw_type = classify_deadline_type(item.title)
                item_type = _dtext(lang, "type_exam" if raw_type == "Exam" else "type_assignment")
                safe_url = _safe_http_url(item.url or "")
                if safe_url:
                    link_cell = (
                        f'<a class="ext-link" href="{html_lib.escape(safe_url, quote=True)}" '
                        f'target="_blank" rel="noopener noreferrer">'
                        f'{html_lib.escape(_dtext(lang, "open_prado"))} ↗</a>'
                    )
                else:
                    link_cell = '<span class="muted">—</span>'
                dl_rows.append(
                    "<tr>"
                    f'<td><span class="pill pill-{html_lib.escape(urg.value)}">{html_lib.escape(badge)}</span></td>'
                    f'<td class="mono">{html_lib.escape(due_str)}</td>'
                    f'<td class="mono">{html_lib.escape(time_left)}</td>'
                    f'<td><strong>{html_lib.escape(item.course)}</strong></td>'
                    f"<td>{html_lib.escape(item.title)}</td>"
                    f'<td><span class="type-tag">{html_lib.escape(item_type)}</span></td>'
                    f"<td>{link_cell}</td>"
                    "</tr>"
                )
            deadlines_html = (
                '<div class="table-wrap"><table><thead><tr>'
                f"<th>{html_lib.escape(_dtext(lang, 'col_status'))}</th>"
                f"<th>{html_lib.escape(_dtext(lang, 'col_due'))}</th>"
                f"<th>{html_lib.escape(_dtext(lang, 'col_left'))}</th>"
                f"<th>{html_lib.escape(_dtext(lang, 'col_course'))}</th>"
                f"<th>{html_lib.escape(_dtext(lang, 'col_activity'))}</th>"
                f"<th>{html_lib.escape(_dtext(lang, 'col_type'))}</th>"
                f"<th>{html_lib.escape(_dtext(lang, 'col_link'))}</th>"
                "</tr></thead><tbody>"
                + "".join(dl_rows)
                + "</tbody></table></div>"
            )

        # Enrolled courses card grid
        if not course_list:
            courses_html = f'<p class="empty-state">{html_lib.escape(_dtext(lang, "no_courses"))}</p>'
        else:
            cards: List[str] = []
            for c in course_list:
                cid_str = c.idnumber or str(c.course_id)
                fcount = self._count_course_files(c)
                pcount = self._count_course_pending(c, pending_counts)
                rel_dir = self._resolve_course_rel_folder(c)
                folder_link = ""
                if rel_dir:
                    href = urllib.parse.quote(rel_dir) + "/"
                    folder_link = (
                        f'<a class="course-link" href="{html_lib.escape(href, quote=True)}">'
                        f"{html_lib.escape(_dtext(lang, 'open_folder_link'))}</a>"
                    )
                pending_cls = "has-pending" if pcount > 0 else ""
                cards.append(
                    '<div class="course-card">'
                    f'<div class="course-code">{html_lib.escape(cid_str)}</div>'
                    f'<div class="course-name">{html_lib.escape(c.fullname)}</div>'
                    '<div class="course-meta">'
                    f'<span>{fcount} {html_lib.escape(_dtext(lang, "col_files").lower())}</span>'
                    f'<span class="{pending_cls}">{pcount} {html_lib.escape(_dtext(lang, "col_pending").lower())}</span>'
                    "</div>"
                    f"{folder_link}"
                    "</div>"
                )
            courses_html = f'<div class="course-grid">{"".join(cards)}</div>'

        # Optional sync summary section
        sync_section_html = ""
        if summary is not None:
            sync_badges = [
                (_dtext(lang, "downloaded_files"), len(summary.downloaded_files)),
                (_dtext(lang, "updated_files"), len(summary.updated_files)),
                (_dtext(lang, "adopted_files"), len(summary.adopted_files)),
                (_dtext(lang, "conflicts_detected"), len(summary.conflict_files)),
                (_dtext(lang, "forum_announcements"), len(summary.forum_announcements)),
            ]
            items_html = "".join(
                f'<div class="sync-stat"><span>{html_lib.escape(lbl)}</span><strong>{val}</strong></div>'
                for lbl, val in sync_badges
            )
            sync_section_html = (
                f'<section class="card"><h2>🔄 {html_lib.escape(_dtext(lang, "recent_sync"))}</h2>'
                f'<div class="sync-grid">{items_html}</div></section>'
            )

        # Optional recent emails section
        emails_section_html = ""
        if academic_msgs:
            mail_rows: List[str] = []
            for m in academic_msgs:
                unread = bool(m.get("is_unread"))
                st_label = _dtext(lang, "mail_new" if unread else "mail_read")
                st_cls = "pill-urgent" if unread else "pill-normal"
                dt_txt = str(m.get("date_str") or m.get("date") or "")
                mail_rows.append(
                    "<tr>"
                    f'<td><span class="pill {st_cls}">{html_lib.escape(st_label)}</span></td>'
                    f'<td class="mono">{html_lib.escape(dt_txt)}</td>'
                    f'<td>{html_lib.escape(str(m.get("sender", "")))}</td>'
                    f'<td>{html_lib.escape(str(m.get("subject", "")))}</td>'
                    "</tr>"
                )
            emails_section_html = (
                f'<section class="card"><h2>📬 {html_lib.escape(_dtext(lang, "recent_emails"))}</h2>'
                '<div class="table-wrap"><table><thead><tr>'
                f"<th>{html_lib.escape(_dtext(lang, 'col_mail_status'))}</th>"
                f"<th>{html_lib.escape(_dtext(lang, 'col_mail_date'))}</th>"
                f"<th>{html_lib.escape(_dtext(lang, 'col_mail_sender'))}</th>"
                f"<th>{html_lib.escape(_dtext(lang, 'col_mail_subject'))}</th>"
                "</tr></thead><tbody>"
                + "".join(mail_rows)
                + "</tbody></table></div></section>"
            )

        ics_exists = (self.courses_root / "deadlines.ics").exists()
        ics_action_html = (
            f'<a class="btn-ics" href="deadlines.ics">{html_lib.escape(_dtext(lang, "guide_ics_btn"))}</a>'
            if ics_exists
            else ""
        )

        return f"""<!DOCTYPE html>
<html lang="{html_lib.escape(lang, quote=True)}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_lib.escape(_dtext(lang, 'title'))}</title>
<style>
  :root {{
    --bg: #f8fafc;
    --card: #ffffff;
    --surface: #f1f5f9;
    --border: #dbe2ea;
    --text: #0f172a;
    --muted: #475569;
    --accent: #c8102e;
    --accent-soft: rgba(200, 16, 46, 0.10);
    --green: #047857;
    --green-soft: rgba(5, 150, 105, 0.12);
    --amber: #b45309;
    --amber-soft: rgba(217, 119, 6, 0.14);
    --red: #dc2626;
    --red-soft: rgba(220, 38, 38, 0.12);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0f1117;
      --card: #171a23;
      --surface: #1e2330;
      --border: #2b3140;
      --text: #f1f4f9;
      --muted: #9aa3b2;
      --accent: #e11d48;
      --accent-soft: rgba(225, 29, 72, 0.15);
      --green: #34d399;
      --green-soft: rgba(16, 185, 129, 0.15);
      --amber: #fbbf24;
      --amber-soft: rgba(245, 158, 11, 0.16);
      --red: #f87171;
      --red-soft: rgba(239, 68, 68, 0.16);
    }}
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 28px 18px 48px;
  }}
  .wrap {{ max-width: 1080px; margin: 0 auto; display: flex; flex-direction: column; gap: 18px; }}
  .hero {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 20px 24px;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
  }}
  .hero h1 {{ font-size: 22px; font-weight: 800; letter-spacing: -0.02em; }}
  .hero-sub {{ color: var(--muted); font-size: 13px; margin-top: 3px; }}
  .sync-pill {{
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 7px 12px;
    border-radius: 999px;
    font-size: 12.5px;
    color: var(--muted);
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
  }}
  .kpi {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 16px;
  }}
  .kpi-val {{ font-size: 24px; font-weight: 800; color: var(--accent); }}
  .kpi-lbl {{ font-size: 12.5px; color: var(--muted); margin-top: 2px; }}
  .guide-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
    gap: 12px;
  }}
  .guide-box {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}
  .guide-box h3 {{ font-size: 14px; font-weight: 700; }}
  .guide-box p {{ font-size: 13px; color: var(--muted); }}
  .btn-ics {{
    display: inline-flex;
    align-items: center;
    align-self: flex-start;
    margin-top: 2px;
    background: var(--accent);
    color: #ffffff;
    text-decoration: none;
    font-size: 12.5px;
    font-weight: 600;
    padding: 7px 12px;
    border-radius: 8px;
  }}
  .btn-ics:hover {{ opacity: 0.92; }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 20px;
  }}
  .card h2 {{ font-size: 16px; font-weight: 700; margin-bottom: 12px; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
  th {{ font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }}
  tr:last-child td {{ border-bottom: none; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; white-space: nowrap; }}
  .pill {{
    display: inline-block;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 700;
    white-space: nowrap;
  }}
  .pill-overdue, .pill-urgent {{ background: var(--red-soft); color: var(--red); }}
  .pill-soon {{ background: var(--amber-soft); color: var(--amber); }}
  .pill-normal {{ background: var(--surface); color: var(--muted); }}
  .type-tag {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 2px 7px;
    font-size: 11.5px;
  }}
  .ext-link {{ color: var(--accent); font-weight: 600; text-decoration: none; white-space: nowrap; }}
  .ext-link:hover {{ text-decoration: underline; }}
  .course-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 12px;
  }}
  .course-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 13px 15px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .course-code {{ font-size: 11.5px; color: var(--muted); font-weight: 600; }}
  .course-name {{ font-size: 14px; font-weight: 700; }}
  .course-meta {{ display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); margin-top: 2px; }}
  .course-meta .has-pending {{ color: var(--amber); font-weight: 700; }}
  .course-link {{ margin-top: 4px; font-size: 12.5px; font-weight: 600; color: var(--accent); text-decoration: none; }}
  .course-link:hover {{ text-decoration: underline; }}
  .sync-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(175px, 1fr)); gap: 10px; }}
  .sync-stat {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
  }}
  .empty-state {{ color: var(--muted); font-size: 13.5px; padding: 6px 0; }}
  .muted {{ color: var(--muted); }}
  .footer-note {{ text-align: center; font-size: 12px; color: var(--muted); margin-top: 4px; }}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div>
      <h1>🎓 {html_lib.escape(_dtext(lang, 'title'))} ({html_lib.escape(self.academic_year)})</h1>
      <div class="hero-sub">{html_lib.escape(_dtext(lang, 'subtitle'))}</div>
    </div>
    <div class="sync-pill"><strong>{html_lib.escape(_dtext(lang, 'last_sync'))}</strong> {html_lib.escape(ts_str)} CET</div>
  </header>

  <section class="kpi-grid">
    <div class="kpi"><div class="kpi-val">{len(course_list)}</div><div class="kpi-lbl">{html_lib.escape(_dtext(lang, 'kpi_courses'))}</div></div>
    <div class="kpi"><div class="kpi-val">{total_files}</div><div class="kpi-lbl">{html_lib.escape(_dtext(lang, 'kpi_files'))}</div></div>
    <div class="kpi"><div class="kpi-val">{len(sorted_deadlines)}</div><div class="kpi-lbl">{html_lib.escape(_dtext(lang, 'kpi_deadlines'))}</div></div>
    <div class="kpi"><div class="kpi-val">{last_dl}</div><div class="kpi-lbl">{html_lib.escape(_dtext(lang, 'kpi_sync'))}</div></div>
  </section>

  <section class="card">
    <h2>🧭 {html_lib.escape(_dtext(lang, 'guide_title'))}</h2>
    <div class="guide-grid">
      <div class="guide-box">
        <h3>📊 {html_lib.escape(_dtext(lang, 'guide_dash_title'))}</h3>
        <p>{html_lib.escape(_dtext(lang, 'guide_dash_desc'))}</p>
      </div>
      <div class="guide-box">
        <h3>📅 {html_lib.escape(_dtext(lang, 'guide_ics_title'))}</h3>
        <p>{html_lib.escape(_dtext(lang, 'guide_ics_desc'))}</p>
        {ics_action_html}
      </div>
    </div>
  </section>

  <section class="card">
    <h2>📅 {html_lib.escape(_dtext(lang, 'upcoming_deadlines'))}</h2>
    {deadlines_html}
  </section>

  <section class="card">
    <h2>📚 {html_lib.escape(_dtext(lang, 'enrolled_courses'))}</h2>
    {courses_html}
  </section>

  {sync_section_html}
  {emails_section_html}

  <p class="footer-note">{html_lib.escape(_dtext(lang, 'footer_note'))}</p>
</div>
</body>
</html>
"""

    @staticmethod
    def _atomic_write(target: Path, content: str) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp_target = target.parent / f".{target.name}.tmp"
        tmp_target.write_text(content, encoding="utf-8")
        os.replace(tmp_target, target)
        return target

    def export_html(
        self,
        summary: Optional[SyncSummary] = None,
        courses: Optional[List[CourseRecord]] = None,
        dest_path: Optional[Path] = None,
        now: Optional[datetime.datetime] = None,
    ) -> Path:
        """Renders and atomically writes DASHBOARD.html to disk."""
        target = Path(dest_path) if dest_path else self.courses_root / "DASHBOARD.html"
        content = self.render_html(summary=summary, courses=courses, now=now)
        return self._atomic_write(target, content)

    def export(
        self,
        summary: Optional[SyncSummary] = None,
        courses: Optional[List[CourseRecord]] = None,
        dest_path: Optional[Path] = None,
        now: Optional[datetime.datetime] = None,
    ) -> Path:
        """Renders and atomically writes DASHBOARD.md (and DASHBOARD.html alongside) to disk."""
        target = Path(dest_path) if dest_path else self.courses_root / "DASHBOARD.md"
        content = self.render(summary=summary, courses=courses, now=now)
        md_path = self._atomic_write(target, content)
        if dest_path is None:
            self.export_html(summary=summary, courses=courses, now=now)
        return md_path


def generate_dashboard_md(
    courses_root: Path,
    summary: Optional[SyncSummary] = None,
    courses: Optional[List[CourseRecord]] = None,
    state_db: Optional[StateDatabase] = None,
    academic_year: Optional[str] = None,
    now: Optional[datetime.datetime] = None,
    language: Optional[str] = None,
) -> str:
    """Generates DASHBOARD.md content string."""
    exporter = DashboardExporter(
        courses_root, state_db=state_db, academic_year=academic_year, language=language
    )
    return exporter.render(summary=summary, courses=courses, now=now)


def generate_dashboard_html(
    courses_root: Path,
    summary: Optional[SyncSummary] = None,
    courses: Optional[List[CourseRecord]] = None,
    state_db: Optional[StateDatabase] = None,
    academic_year: Optional[str] = None,
    now: Optional[datetime.datetime] = None,
    language: Optional[str] = None,
) -> str:
    """Generates DASHBOARD.html content string."""
    exporter = DashboardExporter(
        courses_root, state_db=state_db, academic_year=academic_year, language=language or "es"
    )
    return exporter.render_html(summary=summary, courses=courses, now=now)


def export_dashboard(
    courses_root: Path,
    summary: Optional[SyncSummary] = None,
    courses: Optional[List[CourseRecord]] = None,
    state_db: Optional[StateDatabase] = None,
    dest_path: Optional[Path] = None,
    academic_year: Optional[str] = None,
    now: Optional[datetime.datetime] = None,
    language: Optional[str] = None,
) -> Path:
    """Renders and atomically saves DASHBOARD.md (and DASHBOARD.html) to disk."""
    exporter = DashboardExporter(
        courses_root, state_db=state_db, academic_year=academic_year, language=language
    )
    return exporter.export(summary=summary, courses=courses, dest_path=dest_path, now=now)


def export_dashboard_html(
    courses_root: Path,
    summary: Optional[SyncSummary] = None,
    courses: Optional[List[CourseRecord]] = None,
    state_db: Optional[StateDatabase] = None,
    dest_path: Optional[Path] = None,
    academic_year: Optional[str] = None,
    now: Optional[datetime.datetime] = None,
    language: Optional[str] = None,
) -> Path:
    """Renders and atomically saves DASHBOARD.html to disk."""
    exporter = DashboardExporter(
        courses_root, state_db=state_db, academic_year=academic_year, language=language or "es"
    )
    return exporter.export_html(summary=summary, courses=courses, dest_path=dest_path, now=now)
