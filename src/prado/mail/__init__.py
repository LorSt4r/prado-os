"""
Institutional Email Module (`@correo.ugr.es`) for PradoOS.

Provides:
- Non-destructive IMAP4_SSL inbox fetching (`BODY.PEEK[]`) reusing `CredentialStore`
- Explicit read-state marking (`\\Seen`) only when opened in the TUI reader
- Manual & smart academic filtering (by sender or subject/body keywords)
- Auto-forwarding rules via UGR SMTP (`smtp.ugr.es` / `mail.ugr.es`)
- Interactive TUI mail reader with native GUI folder picker for attachments
"""

from prado.mail.client import (
    MailAttachment,
    MailMessage,
    UgrMailClient,
    html_to_plain_text,
    is_academic_message,
    load_mail_cache,
    matches_mail_filter,
    save_mail_cache,
)

__all__ = [
    "MailAttachment",
    "MailMessage",
    "UgrMailClient",
    "html_to_plain_text",
    "is_academic_message",
    "load_mail_cache",
    "matches_mail_filter",
    "save_mail_cache",
]
