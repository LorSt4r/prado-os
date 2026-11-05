"""
Unit and Adversarial Tests for the PradoOS Institutional Mail Module (`prado mail`).

Verifies:
- Official UGR mail defaults (`correo.ugr.es:993` IMAP4_SSL and `correo.ugr.es:465` SMTP_SSL)
- Non-destructive background fetching (`readonly=True` + `BODY.PEEK[]`) preserving Unread status
- Explicit `STORE +FLAGS (\\Seen)` only when a user opens an email in the TUI
- Full unfiltered Webmail-style default view (`view_mode = "all"`) + interactive manual filters (`[F]`)
- Auto-forwarding rules (`[R]`) and UID deduplication in `mail_cache.json`
- Native GUI folder picker invocation every time an attachment is saved
- `DASHBOARD.md` academic email section integration
"""

from __future__ import annotations

from email.message import EmailMessage
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from prado.auth.credentials import CredentialStore
from prado.cli import main
from prado.config import MailConfig, PradoConfig, load_config, save_config
from prado.exporters.dashboard import generate_dashboard_md
from prado.mail.client import (
    UgrMailClient,
    html_to_plain_text,
    is_academic_message,
    load_mail_cache,
    matches_mail_filter,
    parse_raw_email,
)
from prado.mail.tui import run_mail_tui


def _build_rfc822_bytes(
    subject: str,
    sender: str,
    body_text: str = "",
    body_html: str = "",
    attachment: Tuple[str, bytes] | None = None,
) -> bytes:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = "lorenzovasile@correo.ugr.es"
    msg["Date"] = "Wed, 04 Nov 2026 18:30:00 +0100"

    if body_html and not body_text:
        msg.set_content(body_html, subtype="html")
    else:
        msg.set_content(body_text or "Contenido de prueba.")
        if body_html:
            msg.add_alternative(body_html, subtype="html")

    if attachment is not None:
        fname, payload = attachment
        msg.add_attachment(
            payload,
            maintype="application",
            subtype="pdf",
            filename=fname,
        )
    return msg.as_bytes()


class FakeImapConnection:
    def __init__(self, messages: Dict[str, Tuple[bytes, bytes]]):
        self.messages = messages  # uid -> (flags_bytes, raw_rfc822_bytes)
        self.logged_in_as: Tuple[str, str] | None = None
        self.selected_readonly: List[bool] = []
        self.fetch_commands: List[Tuple[str, str]] = []
        self.store_commands: List[Tuple[str, str, str]] = []

    def login(self, user: str, password: str):
        self.logged_in_as = (user, password)
        return "OK", [b"Logged in"]

    def select(self, folder: str = "INBOX", readonly: bool = False):
        self.selected_readonly.append(readonly)
        return "OK", [b"3"]

    def uid(self, command: str, *args):
        cmd = command.upper()
        if cmd == "SEARCH":
            uids_bytes = " ".join(self.messages.keys()).encode("ascii")
            return "OK", [uids_bytes]
        if cmd == "FETCH":
            uid_str = str(args[0])
            query = str(args[1])
            self.fetch_commands.append((uid_str, query))
            if uid_str not in self.messages:
                return "NO", []
            flags, raw = self.messages[uid_str]
            header = f"{uid_str} (UID {uid_str} FLAGS ({flags.decode('ascii')}) BODY[] {{{len(raw)}}})".encode("ascii")
            return "OK", [(header, raw), b")"]
        if cmd == "STORE":
            uid_str, op, flag_str = str(args[0]), str(args[1]), str(args[2])
            self.store_commands.append((uid_str, op, flag_str))
            if uid_str in self.messages:
                old_flags, raw = self.messages[uid_str]
                if b"\\Seen" not in old_flags:
                    self.messages[uid_str] = (old_flags + b" \\Seen", raw)
            return "OK", [b"Success"]
        return "BAD", []

    def logout(self):
        return "BYE", [b"Logout"]


class FakeSmtpServer:
    def __init__(self):
        self.sent_messages: List[EmailMessage] = []
        self.logged_in_as: Tuple[str, str] | None = None

    def login(self, user: str, password: str):
        self.logged_in_as = (user, password)

    def send_message(self, msg: EmailMessage):
        self.sent_messages.append(msg)

    def quit(self):
        pass


class TestUgrMailUnitAndTui:
    def test_official_ugr_mail_config_defaults(self):
        cfg = PradoConfig()
        assert cfg.mail.imap_host == "correo.ugr.es"
        assert cfg.mail.imap_port == 143
        assert cfg.mail.smtp_host == "correo.ugr.es"
        assert cfg.mail.smtp_port == 465
        assert cfg.mail.forward_enabled is False

    def test_html_to_plain_text_and_academic_classifier(self):
        raw_html = "<html><head><style>body{}</style></head><body><p>Hola <b>Lorenzo</b>,<br>Aula 3.7</p></body></html>"
        assert "Hola Lorenzo,\nAula 3.7" in html_to_plain_text(raw_html)

        assert is_academic_message("Antonio Manjavacas <manjavacas@ugr.es>", "1er Examen de Prácticas ED") is True
        assert is_academic_message("Serafín Moral <seramoral@decsai.ugr.es>", "Nota Prueba 1") is True
        assert is_academic_message("Listas UGR <listas.ugr.es>", "Concierto cultural en el Hospital Real") is False

    def test_fetch_inbox_uses_body_peek_and_never_marks_seen(
        self, mock_config_dir, mock_courses_dir, in_memory_keyring
    ):
        cred_store = CredentialStore()
        cred_store.set_sso_credentials("lorenzovasile@correo.ugr.es", "secret123")
        cfg = PradoConfig(username="lorenzovasile@correo.ugr.es", courses_root=mock_courses_dir)

        raw_unread = _build_rfc822_bytes(
            subject="Aviso Examen ED",
            sender="Antonio Manjavacas <manjavacas@ugr.es>",
            body_text="El examen será en el Aula 3.7.",
        )
        raw_read = _build_rfc822_bytes(
            subject="Boletín Cultural",
            sender="Cultura <listas.ugr.es>",
            body_text="Actividades de la semana.",
        )
        fake_imap = FakeImapConnection({
            "101": (b"\\Seen", raw_read),
            "102": (b"", raw_unread),
        })
        hosts_called: List[Tuple[str, int]] = []

        def imap_factory(host: str, port: int):
            hosts_called.append((host, port))
            return fake_imap

        client = UgrMailClient(config=cfg, credential_store=cred_store, imap_factory=imap_factory)
        msgs = client.fetch_inbox()

        assert hosts_called == [("correo.ugr.es", 143)]
        assert fake_imap.selected_readonly == [True]
        assert all("BODY.PEEK[]" in q for _, q in fake_imap.fetch_commands)
        assert fake_imap.store_commands == []  # Never marks as read during fetch!
        assert len(msgs) == 2
        assert msgs[0].uid == "102"
        assert msgs[0].is_unread is True
        assert msgs[0].is_academic is True
        assert msgs[1].uid == "101"
        assert msgs[1].is_unread is False

        # Now explicitly open UID 102 via read_message(mark_seen=True)
        opened = client.read_message("102", mark_seen=True)
        assert ("102", "+FLAGS", "(\\Seen)") in fake_imap.store_commands
        assert opened.is_unread is False

    def test_sync_and_forward_deduplicates_uids_and_updates_dashboard(
        self, mock_config_dir, mock_courses_dir, in_memory_keyring
    ):
        cred_store = CredentialStore()
        cred_store.set_sso_credentials("lorenzovasile@correo.ugr.es", "secret123")

        cfg = PradoConfig(
            username="lorenzovasile@correo.ugr.es",
            courses_root=mock_courses_dir,
            mail=MailConfig(
                forward_enabled=True,
                forward_to="lorenzo.personal@gmail.com",
                forward_mode="custom",
                filter_senders=["manjavacas@ugr.es"],
                filter_keywords=["Proyecto Final"],
            ),
        )
        save_config(cfg)

        msg1 = _build_rfc822_bytes(
            subject="Horario Examen Prácticas",
            sender="Antonio Manjavacas <manjavacas@ugr.es>",
            body_text="Viernes 11:30 en Aula 3.7",
        )
        msg2 = _build_rfc822_bytes(
            subject="Publicación de cartelera cultural",
            sender="Canal UGR <canal@listas.ugr.es>",
            body_text="Evento no académico",
        )
        fake_imap = FakeImapConnection({
            "201": (b"", msg1),
            "202": (b"", msg2),
        })
        fake_smtp = FakeSmtpServer()
        smtp_endpoints: List[Tuple[str, int]] = []

        client = UgrMailClient(
            config=cfg,
            credential_store=cred_store,
            imap_factory=lambda h, p: fake_imap,
            smtp_factory=lambda h, p: (smtp_endpoints.append((h, p)) or fake_smtp),
        )

        # First sync: forwards UID 201 (matches manjavacas@ugr.es), skips UID 202
        res1 = client.sync_and_forward()
        assert res1["forwarded"] == 1
        assert smtp_endpoints == [("correo.ugr.es", 465)]
        assert len(fake_smtp.sent_messages) == 1
        assert fake_smtp.sent_messages[0]["To"] == "lorenzo.personal@gmail.com"
        assert "[UGR Mail] Horario Examen Prácticas" in fake_smtp.sent_messages[0]["Subject"]
        # Original email on UGR server is STILL unread!
        assert b"\\Seen" not in fake_imap.messages["201"][0]

        # Second sync: UID 201 is already in forwarded_uids -> not forwarded a second time!
        res2 = client.sync_and_forward()
        assert res2["forwarded"] == 0
        assert len(fake_smtp.sent_messages) == 1

        # Verify DASHBOARD.md includes the academic email table
        dash_md = generate_dashboard_md(courses_root=mock_courses_dir)
        assert "📬 Últimos Correos Académicos" in dash_md
        assert "Horario Examen Prácticas" in dash_md

    def test_tui_reader_shows_all_inbox_filters_and_saves_attachments_via_gui(
        self, mock_config_dir, mock_courses_dir, in_memory_keyring
    ):
        cred_store = CredentialStore()
        cred_store.set_sso_credentials("lorenzovasile@correo.ugr.es", "secret123")
        cfg = PradoConfig(username="lorenzovasile@correo.ugr.es", courses_root=mock_courses_dir)
        save_config(cfg)

        pdf_bytes = b"%PDF-1.4 Guia Practica 2"
        msg_with_att = _build_rfc822_bytes(
            subject="Guion Práctica 2 STL",
            sender="Antonio Manjavacas <manjavacas@ugr.es>",
            body_text="Adjunto el PDF de la práctica.",
            attachment=("Guion_P2.pdf", pdf_bytes),
        )
        msg_general = _build_rfc822_bytes(
            subject="Aviso Biblioteca UGR",
            sender="Biblioteca <biblio@ugr.es>",
            body_text="Horario de apertura.",
        )
        fake_imap = FakeImapConnection({
            "301": (b"", msg_general),
            "302": (b"", msg_with_att),
        })
        client = UgrMailClient(
            config=cfg,
            credential_store=cred_store,
            imap_factory=lambda h, p: fake_imap,
        )

        gui_picker_calls: List[str] = []
        dest_folder = mock_courses_dir / "SelectedViaFinderGUI"

        def fake_folder_picker(prompt: str):
            gui_picker_calls.append(prompt)
            return dest_folder

        # Simulate user interaction in TUI:
        # 1. Open TUI (sees both 302 and 301 in 'all' Webmail mode)
        # 2. Press '1' to read email #1 (UID 302 with attachment)
        # 3. Press 'a' to save attachment -> triggers GUI folder picker!
        # 4. Press '0' to return to inbox
        # 5. Press 'f' to open Filter settings, '5' to add 'manjavacas@ugr.es', '4' to switch to Custom Filter view
        # 6. Press '0' to exit TUI
        user_inputs = iter(["1", "a", "0", "f", "5", "manjavacas@ugr.es", "4", "0"])
        printed: List[str] = []

        rc = run_mail_tui(
            client=client,
            input_fn=lambda p: next(user_inputs),
            print_fn=lambda s: printed.append(s),
            folder_picker_fn=fake_folder_picker,
        )
        assert rc == 0
        # Verify attachment was saved to the directory chosen in the GUI picker
        saved_pdf = dest_folder / "Guion_P2.pdf"
        assert len(gui_picker_calls) == 1
        assert saved_pdf.exists()
        assert saved_pdf.read_bytes() == pdf_bytes
        # Verify opening message #1 marked UID 302 as \Seen on the server, while UID 301 remained unread
        assert b"\\Seen" in fake_imap.messages["302"][0]
        assert b"\\Seen" not in fake_imap.messages["301"][0]
        # Verify filter was saved in config.yaml
        assert "manjavacas@ugr.es" in load_config().mail.filter_senders

    def test_cli_mail_forward_config_json(self, mock_config_dir, mock_courses_dir, capsys):
        save_config(PradoConfig(username="lorenzovasile@correo.ugr.es", courses_root=mock_courses_dir))
        code = main([
            "mail",
            "forward",
            "--to",
            "mio@gmail.com",
            "--mode",
            "custom",
            "--senders",
            "manjavacas@ugr.es,pmesejo@ugr.es",
            "--keywords",
            "Examen,Nota",
            "--json",
        ])
        assert code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["forward_enabled"] is True
        assert out["forward_to"] == "mio@gmail.com"
        assert out["filter_senders"] == ["manjavacas@ugr.es", "pmesejo@ugr.es"]
        assert out["filter_keywords"] == ["Examen", "Nota"]
