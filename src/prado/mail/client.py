"""
UGR Institutional Mail Client (IMAP4_SSL + SMTP) & Filter/Forwarding Engine.

All identifiers, comments, and docstrings are strictly in English.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import datetime
import email
from email.header import decode_header
from email.message import EmailMessage, Message
from email.utils import parsedate_to_datetime
import html
import imaplib
import json
from pathlib import Path
import re
import smtplib
import ssl
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from prado.auth.credentials import CredentialStore
from prado.config import (
    MailConfig,
    PradoConfig,
    get_mail_cache_file,
    load_config,
    write_secure_file,
)
from prado.exceptions import AuthenticationRequiredError, InvalidCredentialsError, PradoError


@dataclass
class MailAttachment:
    """Metadata and optional payload for an email attachment."""

    index: int
    filename: str
    content_type: str
    size_bytes: int
    payload: Optional[bytes] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "filename": self.filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
        }


@dataclass
class MailMessage:
    """Structured representation of an institutional email message."""

    uid: str
    subject: str
    sender: str
    sender_email: str
    recipient: str
    date_str: str
    timestamp: str
    is_unread: bool
    is_academic: bool
    snippet: str = ""
    body_text: str = ""
    attachments: List[MailAttachment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "subject": self.subject,
            "sender": self.sender,
            "sender_email": self.sender_email,
            "recipient": self.recipient,
            "date_str": self.date_str,
            "timestamp": self.timestamp,
            "is_unread": self.is_unread,
            "is_academic": self.is_academic,
            "snippet": self.snippet,
            "body_text": self.body_text,
            "attachments": [a.to_dict() for a in self.attachments],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MailMessage:
        atts = [
            MailAttachment(
                index=int(a.get("index", idx)),
                filename=str(a.get("filename", f"attachment_{idx}")),
                content_type=str(a.get("content_type", "application/octet-stream")),
                size_bytes=int(a.get("size_bytes", 0)),
            )
            for idx, a in enumerate(data.get("attachments", []))
        ]
        return cls(
            uid=str(data.get("uid", "")),
            subject=str(data.get("subject", "(No Subject)")),
            sender=str(data.get("sender", "")),
            sender_email=str(data.get("sender_email", "")),
            recipient=str(data.get("recipient", "")),
            date_str=str(data.get("date_str", "")),
            timestamp=str(data.get("timestamp", "")),
            is_unread=bool(data.get("is_unread", False)),
            is_academic=bool(data.get("is_academic", False)),
            snippet=str(data.get("snippet", "")),
            body_text=str(data.get("body_text", "")),
            attachments=atts,
        )


def decode_mime_words(raw_val: Optional[str]) -> str:
    """Decodes RFC 2047 MIME encoded header words into a clean Unicode string."""
    if not raw_val:
        return ""
    parts: List[str] = []
    try:
        for chunk, enc in decode_header(raw_val):
            if isinstance(chunk, bytes):
                charset = enc or "utf-8"
                if charset.lower() in ("unknown-8bit", "default"):
                    charset = "utf-8"
                try:
                    parts.append(chunk.decode(charset, errors="replace"))
                except LookupError:
                    parts.append(chunk.decode("utf-8", errors="replace"))
            else:
                parts.append(str(chunk))
    except Exception:
        return str(raw_val).strip()
    return " ".join("".join(parts).split())


def extract_email_address(sender_header: str) -> str:
    """Extracts the bare email address in lowercase from a From header."""
    if not sender_header:
        return ""
    m = re.search(r"<([^>]+)>", sender_header)
    if m:
        return m.group(1).strip().lower()
    m2 = re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", sender_header)
    if m2:
        return m2.group(0).strip().lower()
    return sender_header.strip().lower()


def html_to_plain_text(html_content: str) -> str:
    """Converts HTML email bodies into clean, readable terminal plain text."""
    if not html_content:
        return ""
    text = re.sub(r"(?is)<(script|style|head).*?>.*?</\1>", "", html_content)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|li|h[1-6]|blockquote)>", "\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "  • ", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    text = html.unescape(text)
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned_lines: List[str] = []
    blank_streak = 0
    for line in lines:
        if not line.strip():
            blank_streak += 1
            if blank_streak <= 2:
                cleaned_lines.append("")
        else:
            blank_streak = 0
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def is_academic_message(sender: str, subject: str) -> bool:
    """
    Determines whether an email is an academic/course/professor message vs bulk institutional spam.
    """
    sender_low = (sender or "").lower()
    subj_low = (subject or "").lower()

    bulk_noise = (
        "listas.ugr.es",
        "boletin@",
        "canal.ugr.es",
        "rectorado@ugr.es",
        "vicerrectorado",
        "newsletter",
        "no-reply@google",
    )
    if any(n in sender_low for n in bulk_noise):
        # Allow through only if subject explicitly mentions a course/exam/grade keyword
        academic_Rescue = ("prado", "examen", "práctica", "practica", "calificaci", "nota", "tutoría", "tutoria")
        if not any(k in subj_low for k in academic_Rescue):
            return False

    academic_domains = (
        "@ugr.es",
        "@decsai.ugr.es",
        "@etsiit.ugr.es",
        "@ugr.es>",
        "prado",
        "@go.ugr.es",
        "@correo.ugr.es",
    )
    if any(d in sender_low for d in academic_domains):
        return True

    academic_keywords = (
        "prado",
        "asignatura",
        "práctica",
        "practica",
        "examen",
        "entrega",
        "calificación",
        "calificacion",
        "tutoría",
        "tutoria",
        "subgrupo",
        "convocatoria",
    )
    return any(k in subj_low for k in academic_keywords)


def matches_mail_filter(
    msg: MailMessage,
    mode: str = "all",
    filter_senders: Optional[Sequence[str]] = None,
    filter_keywords: Optional[Sequence[str]] = None,
) -> bool:
    """
    Evaluates whether a MailMessage matches the given filter criteria:
    - 'all': matches all messages
    - 'unread': matches only unread messages
    - 'academic': matches academic/professor messages
    - 'custom': matches if sender matches any item in filter_senders OR subject/sender/snippet matches filter_keywords
    """
    norm_mode = (mode or "all").strip().lower()
    if norm_mode == "all":
        return True
    if norm_mode == "unread":
        return msg.is_unread
    if norm_mode == "academic":
        return msg.is_academic

    # 'custom' mode
    senders = [s.strip().lower() for s in (filter_senders or []) if s and s.strip()]
    keywords = [k.strip().lower() for k in (filter_keywords or []) if k and k.strip()]

    if not senders and not keywords:
        return False

    haystack_sender = f"{msg.sender} {msg.sender_email}".lower()
    haystack_text = f"{msg.subject} {msg.sender} {msg.snippet} {msg.body_text}".lower()

    for s in senders:
        if s in haystack_sender:
            return True
    for k in keywords:
        if k in haystack_text:
            return True
    return False


def sanitize_attachment_filename(filename: str) -> str:
    """Sanitizes an attachment filename to prevent path traversal or invalid OS characters."""
    base = Path(filename or "attachment.bin").name
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", base).strip(" .")
    return cleaned or "attachment.bin"


def parse_raw_email(
    uid: str,
    raw_bytes: bytes,
    flags_bytes: bytes = b"",
    include_attachment_payloads: bool = False,
) -> MailMessage:
    """Parses raw RFC822 message bytes into a structured MailMessage."""
    msg: Message = email.message_from_bytes(raw_bytes)
    subject = decode_mime_words(msg.get("Subject")) or "(Sin asunto)"
    sender = decode_mime_words(msg.get("From")) or "(Desconocido)"
    sender_email = extract_email_address(sender)
    recipient = decode_mime_words(msg.get("To")) or ""
    raw_date = msg.get("Date") or ""

    dt_obj: Optional[datetime.datetime] = None
    if raw_date:
        try:
            dt_obj = parsedate_to_datetime(raw_date)
        except Exception:
            dt_obj = None

    if dt_obj is not None:
        try:
            local_dt = dt_obj.astimezone()
        except Exception:
            local_dt = dt_obj
        date_str = local_dt.strftime("%Y-%m-%d %H:%M")
        timestamp = local_dt.isoformat()
    else:
        date_str = raw_date[:22].strip()
        timestamp = ""

    is_unread = b"\\Seen" not in (flags_bytes or b"")

    plain_parts: List[str] = []
    html_parts: List[str] = []
    attachments: List[MailAttachment] = []
    att_idx = 1

    if msg.is_multipart():
        for part in msg.walk():
            content_type = (part.get_content_type() or "text/plain").lower()
            content_disp = str(part.get("Content-Disposition") or "")
            raw_filename = part.get_filename()
            decoded_filename = decode_mime_words(raw_filename) if raw_filename else ""

            if decoded_filename or "attachment" in content_disp.lower():
                payload_bytes = part.get_payload(decode=True) or b""
                safe_name = sanitize_attachment_filename(decoded_filename or f"adjunto_{att_idx}")
                attachments.append(
                    MailAttachment(
                        index=att_idx,
                        filename=safe_name,
                        content_type=content_type,
                        size_bytes=len(payload_bytes),
                        payload=payload_bytes if include_attachment_payloads else None,
                    )
                )
                att_idx += 1
                continue

            if content_type == "text/plain":
                payload_bytes = part.get_payload(decode=True)
                if payload_bytes is not None:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        plain_parts.append(payload_bytes.decode(charset, errors="replace"))
                    except LookupError:
                        plain_parts.append(payload_bytes.decode("utf-8", errors="replace"))
            elif content_type == "text/html":
                payload_bytes = part.get_payload(decode=True)
                if payload_bytes is not None:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        html_parts.append(payload_bytes.decode(charset, errors="replace"))
                    except LookupError:
                        html_parts.append(payload_bytes.decode("utf-8", errors="replace"))
    else:
        content_type = (msg.get_content_type() or "text/plain").lower()
        payload_bytes = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        try:
            decoded_body = payload_bytes.decode(charset, errors="replace")
        except LookupError:
            decoded_body = payload_bytes.decode("utf-8", errors="replace")
        if content_type == "text/html":
            html_parts.append(decoded_body)
        else:
            plain_parts.append(decoded_body)

    if plain_parts:
        body_text = "\n\n".join(p.strip() for p in plain_parts if p.strip())
    elif html_parts:
        body_text = html_to_plain_text("\n\n".join(html_parts))
    else:
        body_text = ""

    snippet = " ".join(body_text.split())[:160]
    academic = is_academic_message(sender=sender, subject=subject)

    return MailMessage(
        uid=str(uid),
        subject=subject,
        sender=sender,
        sender_email=sender_email,
        recipient=recipient,
        date_str=date_str,
        timestamp=timestamp,
        is_unread=is_unread,
        is_academic=academic,
        snippet=snippet,
        body_text=body_text,
        attachments=attachments,
    )


def load_mail_cache(cache_path: Optional[Path] = None) -> Dict[str, Any]:
    """Loads cached mail state (`messages` and `forwarded_uids`) from `mail_cache.json`."""
    target = cache_path or get_mail_cache_file()
    if not target.exists():
        return {"last_synced": None, "forwarded_uids": [], "messages": []}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"last_synced": None, "forwarded_uids": [], "messages": []}
        return {
            "last_synced": data.get("last_synced"),
            "forwarded_uids": list(data.get("forwarded_uids", [])),
            "messages": list(data.get("messages", [])),
        }
    except Exception:
        return {"last_synced": None, "forwarded_uids": [], "messages": []}


def save_mail_cache(cache_data: Dict[str, Any], cache_path: Optional[Path] = None) -> Path:
    """Atomically writes `mail_cache.json` with mode 0600 permissions."""
    target = cache_path or get_mail_cache_file()
    content = json.dumps(cache_data, indent=2, ensure_ascii=False)
    write_secure_file(target, content, mode=0o600)
    return target


class UgrMailClient:
    """
    Client for UGR institutional mail (`@correo.ugr.es`) over IMAP4_SSL and SMTP.
    Reuses credentials stored in PradoOS `CredentialStore`.
    """

    def __init__(
        self,
        config: Optional[PradoConfig] = None,
        credential_store: Optional[CredentialStore] = None,
        imap_factory: Optional[Callable[[str, int], Any]] = None,
        smtp_factory: Optional[Callable[[str, int], Any]] = None,
    ):
        self.config = config or load_config()
        self.credential_store = credential_store or CredentialStore()
        self.imap_factory = imap_factory
        self.smtp_factory = smtp_factory

    def _resolve_credentials(self) -> Tuple[str, str]:
        """Returns normalized `(email_address, password)` from `CredentialStore`."""
        try:
            username, password = self.credential_store.get_sso_credentials(self.config.username)
        except InvalidCredentialsError as exc:
            raise AuthenticationRequiredError(
                "No stored UGR credentials found. Run 'prado onboard' or 'prado auth login' first."
            ) from exc

        clean_user = username.strip()
        if clean_user.lower().endswith("@go.ugr.es"):
            local = clean_user.split("@", 1)[0]
            if local.lower().startswith("e.") and len(local) > 2:
                local = local[2:]
            clean_user = f"{local}@correo.ugr.es"
        elif "@" not in clean_user:
            clean_user = f"{clean_user}@correo.ugr.es"

        return clean_user, password

    def _connect_imap(self) -> Any:
        """
        Connects and authenticates to UGR IMAP server (`correo.ugr.es`).
        Prioritizes port 143 (`IMAP4` + `STARTTLS`, the exact official UGR / Apple Mail config)
        with automatic fallback to port 993 (`IMAP4_SSL`).
        """
        username, password = self._resolve_credentials()
        primary_host = self.config.mail.imap_host or "correo.ugr.es"
        primary_port = self.config.mail.imap_port or 143

        if self.imap_factory is not None:
            conn = self.imap_factory(primary_host, primary_port)
            conn.login(username, password)
            return conn

        # Build deduplicated candidate (host, port, mode) list:
        raw_candidates: List[Tuple[str, int, str]] = [
            (primary_host, primary_port, "starttls" if primary_port == 143 else "ssl"),
            ("correo.ugr.es", 143, "starttls"),
            ("correo.ugr.es", 993, "ssl"),
        ]
        if username.lower().endswith("@ugr.es"):
            raw_candidates.append(("imap.ugr.es", 993, "ssl"))

        candidates: List[Tuple[str, int, str]] = []
        for item in raw_candidates:
            if item not in candidates:
                candidates.append(item)

        last_err: Optional[Exception] = None
        for host, port, mode in candidates:
            try:
                ctx = ssl.create_default_context()
                if mode == "starttls":
                    conn = imaplib.IMAP4(host, port, timeout=15)
                    conn.starttls(ssl_context=ctx)
                else:
                    conn = imaplib.IMAP4_SSL(host, port, ssl_context=ctx, timeout=15)
                conn.login(username, password)
                return conn
            except imaplib.IMAP4.error as auth_err:
                raise InvalidCredentialsError(
                    f"IMAP authentication failed for '{username}' on {host}:{port}: {auth_err}"
                ) from auth_err
            except Exception as exc:
                last_err = exc
                continue

        raise PradoError(f"Could not connect to UGR IMAP server ({primary_host}): {last_err}")

    def fetch_inbox(self, limit: Optional[int] = None) -> List[MailMessage]:
        """
        Fetches the latest `limit` messages from INBOX in read-only mode using `BODY.PEEK[]`.
        NEVER modifies the Unread (`\\Seen`) flag on the UGR mail server.
        Returns messages sorted newest first.
        """
        max_items = limit or self.config.mail.max_fetch or 25
        conn = self._connect_imap()
        try:
            conn.select("INBOX", readonly=True)
            status, data = conn.uid("SEARCH", None, "ALL")
            if status != "OK" or not data or not data[0]:
                return []

            all_uids = [u.decode("ascii", errors="ignore") for u in data[0].split() if u]
            recent_uids = list(reversed(all_uids[-max_items:]))

            messages: List[MailMessage] = []
            for uid in recent_uids:
                f_status, f_data = conn.uid("FETCH", uid, "(FLAGS BODY.PEEK[])")
                if f_status != "OK" or not f_data:
                    continue
                raw_bytes = b""
                flags_bytes = b""
                for item in f_data:
                    if isinstance(item, tuple) and len(item) >= 2:
                        flags_bytes = item[0] or b""
                        raw_bytes = item[1] or b""
                        break
                if raw_bytes:
                    messages.append(
                        parse_raw_email(
                            uid=uid,
                            raw_bytes=raw_bytes,
                            flags_bytes=flags_bytes,
                            include_attachment_payloads=False,
                        )
                    )
            return messages
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def read_message(self, uid: str, mark_seen: bool = True) -> MailMessage:
        """
        Fetches a single message by UID including attachment payloads.
        When `mark_seen=True` (used when the student explicitly opens the message in the TUI),
        marks the email as Read (`\\Seen`) on the UGR server.
        """
        conn = self._connect_imap()
        try:
            conn.select("INBOX", readonly=not mark_seen)
            f_status, f_data = conn.uid("FETCH", str(uid), "(FLAGS BODY.PEEK[])")
            if f_status != "OK" or not f_data:
                raise PradoError(f"Message UID {uid} not found in INBOX.")

            raw_bytes = b""
            flags_bytes = b""
            for item in f_data:
                if isinstance(item, tuple) and len(item) >= 2:
                    flags_bytes = item[0] or b""
                    raw_bytes = item[1] or b""
                    break

            if not raw_bytes:
                raise PradoError(f"Empty message payload for UID {uid}.")

            if mark_seen:
                try:
                    conn.uid("STORE", str(uid), "+FLAGS", "(\\Seen)")
                    flags_bytes = flags_bytes + b" \\Seen"
                except Exception:
                    pass

            return parse_raw_email(
                uid=str(uid),
                raw_bytes=raw_bytes,
                flags_bytes=flags_bytes,
                include_attachment_payloads=True,
            )
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def forward_message(self, msg: MailMessage, forward_to: str) -> bool:
        """
        Forwards `msg` (including any attachments) to `forward_to` using UGR's official SMTP server
        authenticated with the student's `@correo.ugr.es` credentials.
        """
        target_email = (forward_to or "").strip()
        if not target_email or "@" not in target_email:
            raise PradoError(f"Invalid forwarding destination address: '{forward_to}'")

        username, password = self._resolve_credentials()

        # If message had attachments without loaded payloads, fetch full message non-destructively
        if msg.attachments and any(a.payload is None for a in msg.attachments):
            try:
                msg = self.read_message(msg.uid, mark_seen=False)
            except Exception:
                pass

        out = EmailMessage()
        out["Subject"] = f"[UGR Mail] {msg.subject}"
        out["From"] = username
        out["To"] = target_email
        if msg.sender_email:
            out["Reply-To"] = msg.sender_email

        header_banner = (
            "────────────────────────────────────────────────────────────\n"
            "📬 Correo Institucional UGR reenviado automáticamente por PradoOS\n"
            f"• De (From) : {msg.sender}\n"
            f"• Fecha     : {msg.date_str}\n"
            f"• Asunto    : {msg.subject}\n"
            "────────────────────────────────────────────────────────────\n\n"
        )
        out.set_content(header_banner + (msg.body_text or "(Mensaje sin texto)"))

        for att in msg.attachments:
            if att.payload is not None:
                maintype, _, subtype = att.content_type.partition("/")
                out.add_attachment(
                    att.payload,
                    maintype=maintype or "application",
                    subtype=subtype or "octet-stream",
                    filename=att.filename,
                )

        smtp_hosts = [self.config.mail.smtp_host or "correo.ugr.es"]
        for fb in ("correo.ugr.es", "smtp.ugr.es", "mail.ugr.es"):
            if fb not in smtp_hosts:
                smtp_hosts.append(fb)

        last_err: Optional[Exception] = None
        for host in smtp_hosts:
            try:
                if self.smtp_factory is not None:
                    server = self.smtp_factory(host, self.config.mail.smtp_port)
                    server.login(username, password)
                    server.send_message(out)
                    server.quit()
                    return True

                ctx = ssl.create_default_context()
                port = self.config.mail.smtp_port or 465
                if port == 465:
                    with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as server:
                        server.login(username, password)
                        server.send_message(out)
                else:
                    with smtplib.SMTP(host, port, timeout=20) as server:
                        server.ehlo()
                        server.starttls(context=ctx)
                        server.ehlo()
                        server.login(username, password)
                        server.send_message(out)
                return True
            except Exception as exc:
                last_err = exc
                continue

        raise PradoError(f"Failed to forward email UID {msg.uid} via UGR SMTP: {last_err}")

    def sync_and_forward(
        self,
        limit: Optional[int] = None,
        dry_run: bool = False,
        cache_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Non-destructively fetches recent emails (`BODY.PEEK[]`), updates `mail_cache.json`,
        and forwards any newly seen emails matching the student's forwarding rules.
        """
        cache = load_mail_cache(cache_path)
        known_uids_existed = bool(cache.get("last_synced"))
        forwarded_uids = set(str(u) for u in cache.get("forwarded_uids", []))
        previously_seen_uids = set(str(m.get("uid")) for m in cache.get("messages", []) if isinstance(m, dict))

        messages = self.fetch_inbox(limit=limit)
        forwarded_now: List[Dict[str, str]] = []
        forward_errors: List[str] = []

        mail_cfg: MailConfig = self.config.mail
        if mail_cfg.forward_enabled and mail_cfg.forward_to:
            # On the very first sync ever, mark existing older inbox UIDs as baseline
            # and only forward unread or newly arrived messages that match the rule
            for msg in reversed(messages):
                if msg.uid in forwarded_uids:
                    continue
                if not known_uids_existed and not msg.is_unread and msg.uid not in previously_seen_uids:
                    forwarded_uids.add(msg.uid)
                    continue

                if matches_mail_filter(
                    msg,
                    mode=mail_cfg.forward_mode,
                    filter_senders=mail_cfg.filter_senders,
                    filter_keywords=mail_cfg.filter_keywords,
                ):
                    if dry_run:
                        forwarded_now.append({"uid": msg.uid, "subject": msg.subject, "to": mail_cfg.forward_to})
                    else:
                        try:
                            self.forward_message(msg, mail_cfg.forward_to)
                            forwarded_uids.add(msg.uid)
                            forwarded_now.append({"uid": msg.uid, "subject": msg.subject, "to": mail_cfg.forward_to})
                        except Exception as exc:
                            forward_errors.append(f"UID {msg.uid}: {exc}")

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        updated_cache = {
            "last_synced": now_iso,
            "forwarded_uids": sorted(forwarded_uids),
            "messages": [m.to_dict() for m in messages],
        }
        if not dry_run:
            save_mail_cache(updated_cache, cache_path)

        return {
            "status": "success",
            "fetched": len(messages),
            "unread": sum(1 for m in messages if m.is_unread),
            "academic": sum(1 for m in messages if m.is_academic),
            "forwarded": len(forwarded_now),
            "forwarded_items": forwarded_now,
            "forward_errors": forward_errors,
            "messages": [m.to_dict() for m in messages],
        }
