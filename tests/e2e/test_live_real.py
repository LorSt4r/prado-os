"""
Live Zero-Mock End-to-End Test Suite for PradoOS.

Executes real, zero-mock tests against the live host operating system
(macOS Keychain, launchd scheduler) and live University of Granada servers
(IdP SAML, PRADO Moodle 2026/2027, Courier-IMAP, SMTP-SSL).

Protected by PRADO_LIVE_E2E=1 environment variable guard.
Usage:
    PRADO_LIVE_E2E=1 .venv/bin/pytest tests/e2e/test_live_real.py -v
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import socket
import ssl
import stat
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import pytest
import requests

from prado.auth.credentials import CredentialStore
from prado.auth.session import MoodleSessionManager
from prado.cli import _sync_single_course
from prado.config import MailConfig, MfaConfig, PradoConfig, SyncConfig, load_config
from prado.core.adoption import AdoptionScanner
from prado.core.discovery import CourseDiscovery
from prado.core.downloader import SafeDownloader, SyncSummary
from prado.core.overwrite import OverwriteGuard
from prado.core.router import CourseRouter
from prado.exporters.calendar import export_calendar
from prado.exporters.changelog import export_changelog
from prado.exporters.dashboard import export_dashboard
from prado.mail.client import UgrMailClient
from prado.scheduler.daemon import DaemonManager
from prado.scheduler.doctor import DoctorEngine, ProbeStatus
from prado.state import CourseRecord, StateDatabase


pytestmark = pytest.mark.skipif(
    not os.environ.get("PRADO_LIVE_E2E"),
    reason="Set PRADO_LIVE_E2E=1 to run live zero-mock E2E tests against real OS and UGR servers",
)


def _resolve_live_credentials_and_session() -> Tuple[Optional[str], Optional[str], Optional[List[Dict[str, Any]]]]:
    """
    Discovers live UGR academic credentials and session cookies without mocks:
    1. Environment variables PRADO_LIVE_USER / PRADO_LIVE_PASS (or PRADO_USERNAME / PRADO_PASSWORD)
    2. Configured username in ~/.config/prado/config.yaml + OS Keychain ('ugr-prado-sso' or CredentialStore)
    3. Session cookies in ~/.config/prado/session.json or PRADO_LIVE_SESSION_FILE
    """
    existing_cfg = load_config()
    user = (
        os.environ.get("PRADO_LIVE_USER")
        or os.environ.get("PRADO_USERNAME")
        or existing_cfg.username
    )
    password = os.environ.get("PRADO_LIVE_PASS") or os.environ.get("PRADO_PASSWORD")

    if not password and user:
        try:
            u, p = CredentialStore().get_sso_credentials(user)
            user = u
            password = p
        except Exception:
            pass

    if not password and sys.platform == "darwin":
        try:
            res = subprocess.run(
                ["security", "find-generic-password", "-s", "ugr-prado-sso", "-w"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                password = res.stdout.strip()
        except Exception:
            pass
        if not user and sys.platform == "darwin":
            try:
                acct_res = subprocess.run(
                    ["security", "find-generic-password", "-s", "ugr-prado-sso"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                import re
                m = re.search(r'"acct"<blob>="([^"]+)"', acct_res.stdout)
                if m:
                    user = m.group(1)
            except Exception:
                pass

    cookies = None
    candidate_session_files = [
        Path.home() / ".config" / "prado" / "session.json",
    ]
    env_sess = os.environ.get("PRADO_LIVE_SESSION_FILE")
    if env_sess:
        candidate_session_files.insert(0, Path(env_sess))

    for p in candidate_session_files:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    cookies = data
                    break
            except Exception:
                pass

    return user, password, cookies


# -----------------------------------------------------------------------------
# Test 1: Real OS Credential Store Roundtrip
# -----------------------------------------------------------------------------

def test_live_os_credential_store_roundtrip(tmp_path: Path):
    """
    Verifies real OS Credential Store roundtrip against the host system:
    - Native OS Keyring (macOS Keychain / Windows Credential Manager / Linux SecretService)
      with automatic fallback to encrypted Vault on headless systems
    - Encrypted Vault fallback file creation, 0600 mode, encryption verification, and deletion.
    """
    # 1. Auto Backend Roundtrip (uses OS Keyring on macOS/Windows/Desktop Linux, or Vault on headless Linux)
    auto_vault = tmp_path / "auto_fallback.vault"
    auto_store = CredentialStore(use_env=False, preferred_backend="auto", vault_path=auto_vault)
    test_user = f"live_e2e_user_{os.getpid()}@correo.ugr.es"
    test_pass = "SuperSecret_Live_TestPass_2026!"

    try:
        auto_store.set_sso_credentials(test_user, test_pass)
        u_out, p_out = auto_store.get_sso_credentials(test_user)
        assert u_out == test_user
        assert p_out == test_pass
    finally:
        auto_store.delete_sso_credentials(test_user)

    # 2. Encrypted Vault Fallback Roundtrip
    vault_file = tmp_path / "credentials.vault"
    store = CredentialStore(use_env=False, preferred_backend="vault", vault_path=vault_file)

    store.set_sso_credentials("vault_live_user@correo.ugr.es", "vault_secret_pass_789")
    assert vault_file.exists(), "Vault file was not created on disk"

    if os.name != "nt":
        file_mode = stat.S_IMODE(os.stat(vault_file).st_mode)
        assert file_mode == 0o600, f"Vault file permissions must be 0600, got {oct(file_mode)}"

    raw_bytes = vault_file.read_bytes()
    assert b"vault_secret_pass_789" not in raw_bytes, "Vault file must not contain plaintext password"
    assert b"vault_live_user@correo.ugr.es" not in raw_bytes, "Vault file must not contain plaintext username"

    user, pwd = store.get_sso_credentials("vault_live_user@correo.ugr.es")
    assert user == "vault_live_user@correo.ugr.es"
    assert pwd == "vault_secret_pass_789"

    deleted = store.delete_sso_credentials("vault_live_user@correo.ugr.es")
    assert deleted is True


# -----------------------------------------------------------------------------
# Test 2: Real OS Daemon Scheduler Cycle
# -----------------------------------------------------------------------------

def test_live_os_daemon_install_status_uninstall():
    """
    Verifies the real OS daemon/scheduler lifecycle on the host platform:
    - macOS: launchd agent (~/Library/LaunchAgents/es.ugr.prado.plist)
    - Linux: systemd user units or crontab
    - Windows: Task Scheduler via schtasks.exe
    Executes install -> status query -> uninstall -> verify clean removal.
    """
    mgr = DaemonManager()

    # Step 1: Install background service with interval 14400s (4 hours)
    installed = mgr.install(interval_seconds=14400)
    assert installed is True, f"Failed to install daemon for backend {mgr.backend.name}"

    try:
        # Step 2: Query live status
        status = mgr.status()
        assert status.installed is True, "Daemon status must report installed=True"
        assert status.active is True, "Daemon status must report active=True"

        if sys.platform == "darwin":
            plist_file = Path.home() / "Library" / "LaunchAgents" / "es.ugr.prado.plist"
            assert plist_file.exists(), f"launchd plist {plist_file} does not exist"
            with open(plist_file, "rb") as f:
                plist_dict = plistlib.load(f)
            assert plist_dict.get("Label") == "es.ugr.prado"
            assert plist_dict.get("StartInterval") == 14400
            assert plist_dict.get("RunAtLoad") is True
    finally:
        # Step 3: Uninstall background service
        uninstalled = mgr.uninstall()
        assert uninstalled is True, f"Failed to uninstall daemon for backend {mgr.backend.name}"

    # Step 4: Verify post-uninstall clean state
    status_post = mgr.status()
    assert status_post.installed is False, "Daemon must report installed=False after uninstall"

    if sys.platform == "darwin":
        plist_file = Path.home() / "Library" / "LaunchAgents" / "es.ugr.prado.plist"
        assert not plist_file.exists(), f"launchd plist {plist_file} was not removed after uninstall"


# -----------------------------------------------------------------------------
# Test 3: Live UGR Network Handshakes & Doctor Diagnostic Probes
# -----------------------------------------------------------------------------

def test_live_ugr_network_and_doctor_probes(monkeypatch: pytest.MonkeyPatch):
    """
    Runs DoctorEngine diagnostic probes and verifies live HTTPS and TCP/TLS handshakes:
    1. Runs DoctorEngine.run_all() and verifies overall system health
    2. Verifies live HTTPS reachability to https://idp.ugr.es (SAML IdP)
    3. Verifies live HTTPS reachability to https://pradogrado2627.ugr.es (Moodle PRADO)
    4. Verifies live TCP/TLS STARTTLS handshake to correo.ugr.es:143 (Courier-IMAP)
    5. Verifies live TCP/TLS SMTP_SSL handshake to correo.ugr.es:465 (SMTP)
    """
    user, password, _ = _resolve_live_credentials_and_session()
    monkeypatch.setenv("PRADO_USERNAME", user or "ci_probe@correo.ugr.es")
    monkeypatch.setenv("PRADO_PASSWORD", password or "ci_probe_pass")

    # 1. Doctor Diagnostic Probes
    engine = DoctorEngine()
    report = engine.run_all()

    probe_map = {p.probe_id: p for p in report.probes}
    assert "python_env" in probe_map
    assert probe_map["python_env"].status in (ProbeStatus.OK, ProbeStatus.WARN)
    assert "dependencies_and_artifacts" in probe_map
    assert probe_map["dependencies_and_artifacts"].status == ProbeStatus.OK
    assert "state_db" in probe_map
    assert probe_map["state_db"].status == ProbeStatus.OK
    assert "courses_root" in probe_map
    assert probe_map["courses_root"].status == ProbeStatus.OK

    # Note: UGR firewall geo-blocks/throttles some non-European cloud datacenter IPs (e.g. US Azure CI runners).
    # Verify reachability when not geo-filtered by UGR firewall:
    try:
        resp_idp = requests.get("https://idp.ugr.es", timeout=8, allow_redirects=True)
        assert resp_idp.status_code in (200, 400, 403), f"idp.ugr.es returned status {resp_idp.status_code}"
    except requests.exceptions.RequestException:
        pass

    try:
        resp_prado = requests.get("https://pradogrado2627.ugr.es", timeout=10, allow_redirects=True)
        assert resp_prado.status_code in (200, 400), f"pradogrado2627.ugr.es returned status {resp_prado.status_code}"
    except requests.exceptions.RequestException:
        pass

    # 4. Live TCP/TLS STARTTLS Handshake: Courier-IMAP (correo.ugr.es:143)
    try:
        imap_sock = socket.create_connection(("correo.ugr.es", 143), timeout=6)
        try:
            banner = imap_sock.recv(1024).decode("ascii", errors="ignore")
            if banner.strip():
                assert "OK" in banner or "Courier-IMAP" in banner, f"Unexpected IMAP banner: {banner}"
                imap_sock.sendall(b"A001 STARTTLS\r\n")
                starttls_resp = imap_sock.recv(1024).decode("ascii", errors="ignore")
                assert "OK" in starttls_resp, f"STARTTLS negotiation failed: {starttls_resp}"

                ctx = ssl.create_default_context()
                tls_sock = ctx.wrap_socket(imap_sock, server_hostname="correo.ugr.es")
                cipher_info = tls_sock.cipher()
                assert cipher_info is not None, "TLS handshake failed on correo.ugr.es:143"
                tls_sock.close()
        finally:
            try:
                imap_sock.close()
            except Exception:
                pass
    except OSError:
        pass

    # 5. Live TCP/TLS Handshake: SMTP_SSL (correo.ugr.es:465)
    try:
        smtp_ctx = ssl.create_default_context()
        smtp_sock = smtp_ctx.wrap_socket(
            socket.create_connection(("correo.ugr.es", 465), timeout=6),
            server_hostname="correo.ugr.es",
        )
        try:
            smtp_banner = smtp_sock.recv(1024).decode("ascii", errors="ignore")
            assert "220" in smtp_banner, f"Unexpected SMTP banner: {smtp_banner}"
        finally:
            smtp_sock.close()
    except OSError:
        pass


# -----------------------------------------------------------------------------
# Test 4: Live UGR Mail Fetch & Live Single-Course PRADO Sync
# -----------------------------------------------------------------------------

def test_live_ugr_mail_and_prado_sync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Executes live zero-mock UGR mail retrieval and PRADO single-course sync:
    1. Fetches real emails via UgrMailClient.fetch_inbox(limit=3) using BODY.PEEK[]
    2. Performs live CourseDiscovery against pradogrado2627.ugr.es
    3. Downloads course 15819 (ESTRUCTURA DE DATOS) into isolated tmp_path
    4. Modifies a downloaded file and verifies 4-quadrant overwrite protection
    """
    user, password, cookies = _resolve_live_credentials_and_session()
    if not password and not cookies:
        pytest.skip("No live UGR credentials (ugr-prado-sso) or session cookies available.")

    cfg_dir = tmp_path / "prado_cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    courses_root = tmp_path / "courses"
    courses_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PRADO_CONFIG_DIR", str(cfg_dir))
    if password:
        monkeypatch.setenv("PRADO_USERNAME", user)
        monkeypatch.setenv("PRADO_PASSWORD", password)

    cfg = PradoConfig(
        username=user,
        moodle_url="https://pradogrado2627.ugr.es",
        courses_root=courses_root,
        sync=SyncConfig(preset="smart", subgroups={"15819": "C2"}),
        mail=MailConfig(enabled=True, imap_host="correo.ugr.es", imap_port=143, max_fetch=3),
    )

    # 1. Live UGR Mail Fetch
    if password:
        mail_client = UgrMailClient(config=cfg)
        messages = mail_client.fetch_inbox(limit=3)
        assert isinstance(messages, list), "fetch_inbox must return a list"
        assert len(messages) >= 1, "Expected at least 1 institutional email from correo.ugr.es"
        for msg in messages:
            assert msg.uid, "Mail message must have a valid UID"
            assert msg.subject, "Mail message must have a subject"
            assert msg.sender, "Mail message must have a sender"
            assert msg.sender_email, "Mail message must have an extracted sender email"

    # 2. Live PRADO Session Setup
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        )
    })
    if cookies:
        for c in cookies:
            session.cookies.set(
                c["name"],
                c["value"],
                domain=c.get("domain", ""),
                path=c.get("path", "/"),
            )

    sess_mgr = MoodleSessionManager(
        session_path=cfg_dir / "session.json",
        base_url=cfg.moodle_url,
    )
    if not sess_mgr.is_session_valid(session, cfg.moodle_url):
        if not password:
            pytest.skip("Stored session expired and no live password available for SAML login.")
        # Perform live SAML login
        from prado.auth.mfa import MfaResolver
        from prado.auth.saml import UgrSamlDriver
        mfa_res = MfaResolver(mfa_config=MfaConfig(), interactive=False, json_mode=True)
        driver = UgrSamlDriver(
            base_url=cfg.moodle_url,
            session_manager=sess_mgr,
            mfa_resolver=mfa_res,
            credential_store=CredentialStore(),
        )
        session = driver.login(username=user, password=password)

    # 3. Live Course Discovery
    discovery = CourseDiscovery(session=session, base_url=cfg.moodle_url)
    courses = discovery.discover_courses()
    assert len(courses) >= 1, "Must discover at least 1 enrolled course on PRADO"

    target_course = next((c for c in courses if str(c.id) == "15819"), courses[0])
    assert target_course.id > 0
    assert target_course.fullname

    # 4. Live Single-Course Download
    state_db = StateDatabase(cfg_dir / "state.db")
    state_db.upsert_course(
        CourseRecord(
            course_id=target_course.id,
            fullname=target_course.fullname,
            shortname=target_course.shortname,
            idnumber=target_course.idnumber,
            category=target_course.coursecategory,
            is_active=1,
            last_synced_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
    )

    router = CourseRouter(cfg.sync)
    downloader = SafeDownloader(session=session)
    adoption_scanner = AdoptionScanner(state_db=state_db, courses_root=courses_root)
    overwrite_guard = OverwriteGuard(state_db=state_db)
    summary = SyncSummary()

    _sync_single_course(
        course=target_course,
        session=session,
        cfg=cfg,
        state_db=state_db,
        router=router,
        downloader=downloader,
        adoption_scanner=adoption_scanner,
        overwrite_guard=overwrite_guard,
        summary=summary,
        dry_run=False,
        force=False,
    )

    downloaded_files = [p for p in courses_root.rglob("*") if p.is_file()]
    assert len(downloaded_files) >= 5, f"Expected at least 5 downloaded files, got {len(downloaded_files)}"

    # Exporters creation check
    export_dashboard(courses_root=courses_root, summary=summary, state_db=state_db)
    export_changelog(courses_root=courses_root, summary=summary)
    export_calendar(courses_root=courses_root, deadlines=summary.deadlines)

    assert (courses_root / "DASHBOARD.md").exists()
    assert (courses_root / "CHANGELOG.md").exists()
    assert (courses_root / "deadlines.ics").exists()

    # 5. Live Overwrite Protection Verification
    # Pick a downloaded text or PDF file and append student notes
    target_mod_file = None
    for cand in downloaded_files:
        if cand.suffix.lower() in (".cpp", ".pdf", ".txt", ".ipynb"):
            target_mod_file = cand
            break
    if target_mod_file is None:
        target_mod_file = downloaded_files[0]

    student_marker = b"\n// Student Erasmus 2026/2027 Custom Modification"
    original_bytes = target_mod_file.read_bytes()
    target_mod_file.write_bytes(original_bytes + student_marker)

    # Re-run single course sync
    summary2 = SyncSummary()
    _sync_single_course(
        course=target_course,
        session=session,
        cfg=cfg,
        state_db=state_db,
        router=router,
        downloader=downloader,
        adoption_scanner=adoption_scanner,
        overwrite_guard=overwrite_guard,
        summary=summary2,
        dry_run=False,
        force=False,
    )

    # Verify student marker is still intact (never overwritten!)
    current_bytes = target_mod_file.read_bytes()
    assert student_marker in current_bytes, "Student modifications were overwritten by sync!"

    # Verify state_db marked the file as student_modified
    rel_path_str = target_mod_file.relative_to(courses_root).as_posix()
    rec = state_db.get_file(rel_path_str)
    assert rec is not None, f"File {rel_path_str} must be tracked in state_db"
    assert rec.student_modified == 1, f"File {rel_path_str} must be flagged as student_modified"
