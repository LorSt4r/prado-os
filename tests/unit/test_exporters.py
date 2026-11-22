"""
Unit tests for PradoOS DASHBOARD.md and CHANGELOG.md exporters.
"""

from __future__ import annotations

import datetime
from pathlib import Path
import pytest

from prado.core.downloader import (
    AdoptedFile,
    ConflictFile,
    DeadlineItem,
    DownloadedFile,
    ForumPost,
    SyncSummary,
)
from prado.exporters.changelog import (
    ChangelogExporter,
    escape_markdown_filename,
    export_changelog,
    format_file_size,
    prepend_changelog_md,
    truncate_text,
)
from prado.exporters.dashboard import (
    DashboardExporter,
    DeadlineUrgency,
    classify_deadline_type,
    escape_markdown_table_cell,
    export_dashboard,
    format_time_left,
    generate_dashboard_md,
)
from prado.state import CourseRecord


# =============================================================================
# Dashboard Exporter Unit Tests
# =============================================================================

def test_dashboard_header_metadata(tmp_path):
    exporter = DashboardExporter(courses_root=tmp_path, academic_year="2026/2027")
    content = exporter.render()
    assert "# 🎓 Academic Dashboard — PradoOS (2026/2027)" in content
    assert "**Last Sync:**" in content
    assert "CET" in content


def test_dashboard_zero_deadlines_empty_state(tmp_path):
    exporter = DashboardExporter(courses_root=tmp_path)
    summary = SyncSummary(deadlines=[])
    content = exporter.render(summary=summary)
    assert "No upcoming deadlines scheduled." in content


def test_dashboard_deadlines_sorting(tmp_path):
    exporter = DashboardExporter(courses_root=tmp_path)
    now = datetime.datetime(2026, 10, 27, 10, 0, 0)
    d1 = DeadlineItem(
        id="101",
        title="Final Exam",
        course="ED",
        due_date=datetime.datetime(2026, 11, 15, 9, 0, 0),
        url="https://prado.ugr.es/mod/assign/101",
    )
    d2 = DeadlineItem(
        id="102",
        title="Early Quiz",
        course="MC",
        due_date=datetime.datetime(2026, 10, 30, 9, 0, 0),
        url="https://prado.ugr.es/mod/assign/102",
    )
    d3 = DeadlineItem(
        id="103",
        title="Midterm",
        course="SO",
        due_date=datetime.datetime(2026, 11, 5, 12, 0, 0),
        url="https://prado.ugr.es/mod/assign/103",
    )

    summary = SyncSummary(deadlines=[d1, d2, d3])
    content = exporter.render(summary=summary, now=now)

    pos_early = content.find("Early Quiz")
    pos_mid = content.find("Midterm")
    pos_final = content.find("Final Exam")

    assert pos_early < pos_mid < pos_final


def test_dashboard_urgency_badge_tiers():
    now = datetime.datetime(2026, 10, 27, 12, 0, 0)

    # 36 hours left -> Urgent
    due_36h = now + datetime.timedelta(hours=36)
    urg_1, badge_1, dur_1 = format_time_left(due_36h, now=now)
    assert urg_1 == DeadlineUrgency.URGENT
    assert badge_1 == "🚨 Urgent"
    assert "1d 12h" in dur_1

    # 120 hours left (5 days) -> Soon
    due_120h = now + datetime.timedelta(hours=120)
    urg_2, badge_2, dur_2 = format_time_left(due_120h, now=now)
    assert urg_2 == DeadlineUrgency.SOON
    assert badge_2 == "⏳ Soon"

    # 240 hours left (10 days) -> Scheduled
    due_240h = now + datetime.timedelta(hours=240)
    urg_3, badge_3, dur_3 = format_time_left(due_240h, now=now)
    assert urg_3 == DeadlineUrgency.NORMAL
    assert badge_3 == "📅 Scheduled"

    # 24 hours ago -> Overdue
    due_past = now - datetime.timedelta(hours=24)
    urg_4, badge_4, dur_4 = format_time_left(due_past, now=now)
    assert urg_4 == DeadlineUrgency.OVERDUE
    assert badge_4 == "⚠️ Overdue"


def test_dashboard_escape_pipes_in_markdown():
    raw_title = "Exam: Topic 1 | Topic 2 | Topic 3"
    escaped = escape_markdown_table_cell(raw_title)
    assert r"\|" in escaped
    assert "|" not in escaped.replace(r"\|", "")


def test_dashboard_enrolled_courses_table(tmp_path):
    exporter = DashboardExporter(courses_root=tmp_path)
    c1 = CourseRecord(course_id=2961122, fullname="Estructura de Datos", shortname="ED")
    c2 = CourseRecord(course_id=2961123, fullname="Sistemas Operativos", shortname="SO")

    summary = SyncSummary(
        deadlines=[
            DeadlineItem("1", "P1", "ED", datetime.datetime(2026, 11, 1), ""),
            DeadlineItem("2", "P2", "ED", datetime.datetime(2026, 11, 5), ""),
        ]
    )

    content = exporter.render(summary=summary, courses=[c1, c2])
    assert "## 📚 Enrolled Courses" in content
    assert "2961122" in content
    assert "Estructura de Datos" in content
    assert "2961123" in content
    assert "Sistemas Operativos" in content


def test_dashboard_recent_sync_summary(tmp_path):
    exporter = DashboardExporter(courses_root=tmp_path)
    summary = SyncSummary(
        downloaded_files=[
            DownloadedFile(path=Path("f1.pdf"), url="http://x", sha256="abc", size_bytes=100)
        ],
        updated_files=[
            DownloadedFile(path=Path("f2.pdf"), url="http://y", sha256="def", size_bytes=200)
        ],
        conflict_files=[
            ConflictFile(
                original_path=Path("f3.pdf"),
                forked_path=Path("f3_server.pdf"),
                server_sha256="111",
                local_sha256="222",
            )
        ],
        adopted_files=[AdoptedFile(path=Path("f4.pdf"), sha256="333", size_bytes=50)],
        forum_announcements=[
            ForumPost(forum_id="1", subject="Notice", author="Prof", content="Hello")
        ],
    )

    content = exporter.render(summary=summary)
    assert "- **Downloaded files:** 1" in content
    assert "- **Updated files:** 1" in content
    assert "- **Adopted files:** 1" in content
    assert "- **Conflicts detected:** 1" in content
    assert "- **Forum announcements:** 1" in content


def test_dashboard_atomic_export(tmp_path):
    dest = export_dashboard(courses_root=tmp_path)
    assert dest.exists()
    assert dest.name == "DASHBOARD.md"
    tmp_file = tmp_path / ".DASHBOARD.md.tmp"
    assert not tmp_file.exists()


# =============================================================================
# Changelog Exporter Unit Tests
# =============================================================================

def test_changelog_run_timestamp_header(tmp_path):
    exporter = ChangelogExporter(courses_root=tmp_path)
    run_dt = datetime.datetime(2026, 10, 27, 18, 30, 0)
    summary = SyncSummary()
    entry = exporter.render_run_entry(summary, run_time=run_dt)
    assert "## 🔄 [2026-10-27 18:30 CET] Sync Run" in entry


def test_changelog_zero_changes_message(tmp_path):
    exporter = ChangelogExporter(courses_root=tmp_path)
    summary = SyncSummary()
    entry = exporter.render_run_entry(summary)
    assert "- All course directories verified up to date." in entry


def test_changelog_file_size_formatting():
    assert format_file_size(850 * 1024) == "850 KB"
    assert format_file_size(15 * 1024 * 1024) == "15.0 MB"
    assert format_file_size(1400 * 1024) == "1.4 MB"


def test_changelog_escape_brackets_in_filenames():
    escaped = escape_markdown_filename("relacion_[1].pdf")
    assert escaped == r"relacion_\[1\].pdf"


def test_changelog_short_sha256_hash(tmp_path):
    exporter = ChangelogExporter(courses_root=tmp_path)
    summary = SyncSummary(
        downloaded_files=[
            DownloadedFile(
                path=Path("guia_p2.pdf"),
                url="http://x",
                sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                size_bytes=1468006,
                course_id="SO",
            )
        ]
    )
    entry = exporter.render_run_entry(summary)
    assert "`[e3b0c442]`" in entry
    assert "**[SO]**" in entry
    assert "(1.4 MB)" in entry


def test_changelog_overwrite_protection_warning(tmp_path):
    exporter = ChangelogExporter(courses_root=tmp_path)
    summary = SyncSummary(
        conflict_files=[
            ConflictFile(
                original_path=Path("lab1.ipynb"),
                forked_path=Path("lab1_server_ts.ipynb"),
                server_sha256="aaa",
                local_sha256="bbb",
            )
        ]
    )
    entry = exporter.render_run_entry(summary)
    assert "⚠️ OVERWRITE PROTECTION: Preserved local `lab1.ipynb`, saved server update as `lab1_server_ts.ipynb`" in entry


def test_changelog_forum_post_truncation(tmp_path):
    exporter = ChangelogExporter(courses_root=tmp_path)
    long_text = "Word " * 100  # 500 characters
    summary = SyncSummary(
        forum_announcements=[
            ForumPost(
                forum_id="MC",
                subject="Aclaración sobre 1ª Prueba",
                author="Prof. Serafín Moral",
                content=long_text,
            )
        ]
    )
    entry = exporter.render_run_entry(summary)
    assert "### 📢 Forum Announcements" in entry
    assert "Aclaración sobre 1ª Prueba" in entry
    assert "Prof. Serafín Moral" in entry
    assert "..." in entry


def test_changelog_reverse_chronological_prepending(tmp_path):
    t1 = datetime.datetime(2026, 10, 20, 10, 15, 0)
    t2 = datetime.datetime(2026, 10, 27, 18, 30, 0)

    summary1 = SyncSummary()
    summary2 = SyncSummary(
        downloaded_files=[
            DownloadedFile(path=Path("slide1.pdf"), url="u", sha256="12345678", size_bytes=1024)
        ]
    )

    prepend_changelog_md(courses_root=tmp_path, summary=summary1, run_time=t1)
    dest = prepend_changelog_md(courses_root=tmp_path, summary=summary2, run_time=t2)

    content = dest.read_text(encoding="utf-8")
    pos_t2 = content.find("2026-10-27 18:30 CET")
    pos_t1 = content.find("2026-10-20 10:15 CET")

    assert pos_t2 != -1
    assert pos_t1 != -1
    assert pos_t2 < pos_t1  # Newest run appears first


def test_changelog_truncation_limit_50_runs(tmp_path):
    exporter = ChangelogExporter(courses_root=tmp_path)
    cl_file = tmp_path / "CHANGELOG.md"

    # Pre-populate 60 runs
    fake_runs = [f"## 🔄 [2026-01-{i+1:02d} 10:00 CET] Sync Run\n- Run {i+1}" for i in range(60)]
    cl_file.write_text("\n\n---\n\n".join(fake_runs), encoding="utf-8")

    # Prepend a new run
    new_summary = SyncSummary()
    exporter.export(new_summary, dest_path=cl_file)

    content = cl_file.read_text(encoding="utf-8")
    run_headers = [line for line in content.splitlines() if line.startswith("## 🔄 [")]
    assert len(run_headers) == 50


def test_changelog_atomic_export(tmp_path):
    summary = SyncSummary()
    dest = export_changelog(courses_root=tmp_path, summary=summary)
    assert dest.exists()
    assert dest.name == "CHANGELOG.md"
    assert not (tmp_path / ".CHANGELOG.md.tmp").exists()


def test_dashboard_html_and_single_language_italian(tmp_path, monkeypatch):
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setattr(
        "prado.mail.client.load_mail_cache",
        lambda *a, **kw: {
            "messages": [
                {
                    "uid": "1",
                    "is_unread": True,
                    "is_academic": True,
                    "date_str": "2026-11-22",
                    "sender": "Prof. <script>alert(1)</script>",
                    "subject": "Esame parziale",
                }
            ]
        },
    )

    course_dir = tmp_path / "Algebra III"
    course_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "deadlines.ics").write_text("BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n", encoding="utf-8")

    now = datetime.datetime(2026, 11, 10, 10, 0, 0)
    summary = SyncSummary(
        deadlines=[
            DeadlineItem(
                id="1",
                title="Examen <script>xss</script>",
                course="Algebra III",
                due_date=now + datetime.timedelta(hours=12),
                url="javascript:alert(1)",
            ),
            DeadlineItem(
                id="2",
                title="Entrega P1",
                course="Algebra III",
                due_date=now + datetime.timedelta(days=4),
                url="https://prado.ugr.es/mod/assign/view.php?id=2",
            ),
        ],
        downloaded_files=[
            DownloadedFile(path=Path("Algebra III/Tema1.pdf"), url="https://prado.ugr.es/1.pdf", sha256="aa", size_bytes=100)
        ],
    )
    courses = [CourseRecord(course_id=101, fullname="Algebra III", shortname="ALG3")]

    md_path = export_dashboard(
        courses_root=tmp_path,
        summary=summary,
        courses=courses,
        language="it",
        now=now,
    )
    html_path = tmp_path / "DASHBOARD.html"

    assert md_path.exists()
    assert html_path.exists()
    assert not (tmp_path / ".DASHBOARD.md.tmp").exists()
    assert not (tmp_path / ".DASHBOARD.html.tmp").exists()

    md_text = md_path.read_text(encoding="utf-8")
    assert "Dashboard Accademica" in md_text
    assert "Prossime Scadenze ed Esami" in md_text
    assert "Corsi Iscritti" in md_text
    assert "Riepilogo Ultima Sincronizzazione" in md_text
    assert "Ultime Email Accademiche" in md_text
    assert "DASHBOARD.html" in md_text
    assert "deadlines.ics" in md_text
    # Ensure zero English/Spanish leakage when language="it"
    assert "Upcoming Deadlines" not in md_text
    assert "Últimos Correos Académicos" not in md_text
    assert "Recent Sync Summary" not in md_text

    html_text = html_path.read_text(encoding="utf-8")
    assert '<html lang="it">' in html_text
    assert "Dashboard Visiva (DASHBOARD.html)" in html_text
    assert 'href="deadlines.ics"' in html_text
    assert 'href="Algebra%20III/"' in html_text
    assert "https://prado.ugr.es/mod/assign/view.php?id=2" in html_text
    assert "<script>" not in html_text
    assert "javascript:alert(1)" not in html_text


def test_dashboard_coherent_es_en_fr(tmp_path, monkeypatch):
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(tmp_path / "cfg"))
    from prado.exporters.dashboard import generate_dashboard_html

    now = datetime.datetime(2026, 11, 10, 10, 0, 0)
    summary = SyncSummary()
    expected = {
        "es": ("Panel Académico — PradoOS", "Cómo usar esta carpeta"),
        "en": ("Academic Dashboard — PradoOS", "How to use this folder"),
        "fr": ("Tableau de Bord Académique — PradoOS", "Comment utiliser ce dossier"),
    }
    for lang, (md_heading, html_guide) in expected.items():
        md_text = generate_dashboard_md(courses_root=tmp_path, summary=summary, language=lang, now=now)
        html_text = generate_dashboard_html(courses_root=tmp_path, summary=summary, language=lang, now=now)
        assert md_heading in md_text
        assert "DASHBOARD.html" in md_text
        assert f'<html lang="{lang}">' in html_text
        assert html_guide in html_text
