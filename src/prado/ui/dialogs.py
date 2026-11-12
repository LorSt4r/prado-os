"""
Native OS dialogs and filesystem / browser integration for PradoOS.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Optional
import webbrowser

from prado.auth.credentials import CredentialStore, prompt_gui_input
from prado.config import PradoConfig, save_config
from prado.i18n import t
from prado.notifications.desktop import DesktopNotifier


def open_folder(path: Path | str) -> bool:
    """
    Opens a folder in the native OS file explorer (Finder on macOS, Explorer on Windows, xdg-open on Linux).
    Creates the directory if it does not exist yet.
    """
    target = Path(path).expanduser().resolve()
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
            return True
        elif sys.platform in ("win32", "cygwin") or os.name == "nt":
            if hasattr(os, "startfile"):
                os.startfile(str(target))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["explorer", str(target)])
            return True
        else:
            xdg_bin = shutil.which("xdg-open")
            if xdg_bin:
                subprocess.Popen([xdg_bin, str(target)])
                return True
    except Exception:
        pass
    return False


def open_url(url: str) -> bool:
    """Opens a URL in the student's default web browser."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", url])
            return True
        elif sys.platform in ("win32", "cygwin") or os.name == "nt":
            if hasattr(os, "startfile"):
                os.startfile(url)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["cmd", "/c", "start", "", url])
            return True
        xdg_bin = shutil.which("xdg-open")
        if xdg_bin:
            subprocess.Popen([xdg_bin, url])
            return True
        return webbrowser.open(url)
    except Exception:
        return False


def prompt_login_gui(cfg: PradoConfig, cred_store: Optional[CredentialStore] = None) -> bool:
    """
    Displays native OS dialogs to collect UGR credentials and saves them securely in Keyring / Vault.
    Returns True if credentials were saved, False if cancelled.
    """
    if cred_store is None:
        cred_store = CredentialStore()

    lang = cfg.language or "es"

    email_prompt = {
        "es": "Introduce tu correo institucional UGR (@correo.ugr.es):",
        "en": "Enter your institutional UGR email (@correo.ugr.es):",
        "it": "Inserisci la tua email istituzionale UGR (@correo.ugr.es):",
        "fr": "Entrez votre courriel institutionnel UGR (@correo.ugr.es) :",
    }.get(lang, "Introduce tu correo institucional UGR (@correo.ugr.es):")

    pwd_prompt = {
        "es": "Introduce tu contraseña de Acceso Identificado UGR / PRADO:",
        "en": "Enter your UGR Acceso Identificado / PRADO password:",
        "it": "Inserisci la password di Acceso Identificado UGR / PRADO:",
        "fr": "Entrez votre mot de passe Acceso Identificado UGR / PRADO :",
    }.get(lang, "Introduce tu contraseña de Acceso Identificado UGR / PRADO:")

    title = "PradoOS — UGR SSO"

    username = prompt_gui_input(
        prompt=email_prompt,
        title=title,
        default=cfg.username or "",
        hidden=False,
    )
    if not username:
        return False

    username = username.strip()
    if "@" not in username:
        username = f"{username}@correo.ugr.es"

    password = prompt_gui_input(
        prompt=pwd_prompt,
        title=title,
        hidden=True,
    )
    if not password:
        return False

    # Persist in secure OS Keyring / encrypted vault
    cred_store.set_sso_credentials(username, password)

    # Update active configuration
    cfg.username = username
    save_config(cfg)

    # Show confirmation notification
    notifier = DesktopNotifier(app_name="PradoOS")
    notifier.notify(
        title="PradoOS",
        message=t("tray_credentials_saved", lang),
    )
    return True
