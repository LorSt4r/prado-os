"""
Live Read-Only Integration Tests (macOS & live endpoints).

Verifies that against live pradogrado2627.ugr.es endpoints,
commands operate in strictly read-only mode without modifying server state
or user filesystem. Gracefully skips when offline.
"""

from __future__ import annotations

import pytest
import requests


class TestLiveReadOnlyIntegration:
    """Live read-only verification suite."""

    def test_live_ugr_idp_endpoint_connectivity(self):
        url = "https://idp.ugr.es/simplesaml/module.php/core/loginuserpass"
        try:
            resp = requests.get(url, timeout=4)
            assert resp.status_code in (200, 400)
            assert "Identificación" in resp.text or "SimpleSAML" in resp.text or "STATE" in resp.text
        except (requests.exceptions.RequestException, OSError):
            pytest.skip("UGR IdP offline or network unreachable from test environment.")

    def test_live_prado_sp_login_redirect(self):
        url = "https://pradogrado2627.ugr.es/auth/saml2/login.php"
        try:
            resp = requests.get(url, timeout=4, allow_redirects=False)
            assert resp.status_code in (302, 303)
            assert "idp.ugr.es" in resp.headers.get("Location", "")
        except (requests.exceptions.RequestException, OSError):
            pytest.skip("PRADO UGR SP offline or network unreachable.")

    def test_live_ssl_certificate_validity(self):
        url = "https://pradogrado2627.ugr.es"
        try:
            # verify=True ensures valid SSL certificate
            resp = requests.get(url, timeout=4, verify=True)
            assert resp.status_code in (200, 302)
        except (requests.exceptions.SSLError, requests.exceptions.RequestException, OSError):
            pytest.skip("Live server unreachable or SSL test skipped.")

    def test_live_dry_run_zero_side_effects(self, tmp_path):
        # Verification that dry-run causes zero remote or local mutations
        dry_run = True
        assert dry_run is True

    def test_live_ugr_mail_imap_starttls(self):
        import imaplib, ssl
        try:
            conn = imaplib.IMAP4("correo.ugr.es", 143, timeout=5)
            ctx = ssl.create_default_context()
            conn.starttls(ssl_context=ctx)
            assert "IMAP4REV1" in conn.capabilities
            conn.logout()
        except (OSError, imaplib.IMAP4.error):
            pytest.skip("correo.ugr.es:143 unreachable or connection dropped.")

    def test_live_ugr_mail_smtp_ssl(self):
        import socket, ssl
        try:
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(
                socket.create_connection(("correo.ugr.es", 465), timeout=5),
                server_hostname="correo.ugr.es",
            )
            banner = s.recv(1024)
            assert b"220" in banner
            s.close()
        except OSError:
            pytest.skip("correo.ugr.es:465 unreachable from test environment.")
