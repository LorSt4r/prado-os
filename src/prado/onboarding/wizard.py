"""
2-Phase Progressive Disclosure Onboarding Wizard (`prado onboard`) for PradoOS.

Phase 1 (<60 seconds):
  1. Platform & Institutional Credentials (stored in OS Keyring / 0600 Vault)
  2. Destination Folder (`courses_root`) & Folder Routing Preset (`smart` vs `mirror`)
  3. Configuration Persistence & First Sync / Dry-Run Preview

Phase 2 (Optional Power-Ups):
  1. Lab / Seminar Subgroup Filtering (`C2`, `E3`, `A1`, etc.)
  2. Zero-Touch 2FA Email Auto-Fetch via IMAP SSL (`imap.ugr.es`)
  3. Background Sync Daemon Installation (`launchd`, `systemd`, `schtasks`)
"""

from __future__ import annotations

import getpass
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional

from prado.auth.credentials import CredentialStore
from prado.config import (
    MfaConfig,
    PradoConfig,
    SyncConfig,
    get_config_dir,
    get_config_file,
    get_default_academic_year_code,
    get_default_moodle_url,
    get_localized_desktop_dir,
    load_config,
    prompt_folder_picker_gui,
    save_config,
)
from prado.onboarding.star import maybe_prompt_star_after_sync
from prado.scheduler.daemon import DaemonManager


def resolve_platform_url(platform_choice: str, year_code: Optional[str] = None) -> str:
    """
    Maps a platform preset ('grado', 'posgrado', 'ceprud') or full URL to a Moodle base URL.
    """
    code = year_code or get_default_academic_year_code()
    clean = (platform_choice or "").strip()
    lower = clean.lower()

    if lower in ("", "1", "grado", "pradogrado", "undergraduate"):
        return f"https://pradogrado{code}.ugr.es"
    if lower in ("2", "posgrado", "pradoposgrado", "postgraduate", "master"):
        return f"https://pradoposgrado{code}.ugr.es"
    if lower in ("3", "ceprud", "prado", "general"):
        return "https://prado.ugr.es"
    if clean.startswith("http://") or clean.startswith("https://"):
        return clean.rstrip("/")
    return f"https://{clean.rstrip('/')}"


def reveal_folder_in_file_manager(folder: Path) -> bool:
    """Opens the synced courses folder in Finder (macOS), Explorer (Windows), or xdg-open (Linux)."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(
                ["open", str(folder)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        if os.name == "nt":
            subprocess.Popen(
                ["explorer", str(folder)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        subprocess.Popen(
            ["xdg-open", str(folder)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


class OnboardingWizard:
    """
    Orchestrates Phase 1 and Phase 2 onboarding in both interactive TTY mode
    and non-interactive / agent-driven mode.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        credential_store: Optional[CredentialStore] = None,
        input_fn: Callable[[str], str] = input,
        password_fn: Callable[[str], str] = getpass.getpass,
        print_fn: Callable[[str], None] = print,
    ) -> None:
        self.config_path = config_path or get_config_file()
        self.credential_store = credential_store or CredentialStore()
        self.input_fn = input_fn
        self.password_fn = password_fn
        self.print_fn = print_fn

    def run_phase1(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        moodle_url: Optional[str] = None,
        courses_root: Optional[Path | str] = None,
        preset: Optional[str] = None,
        semester: Optional[int] = None,
        language: Optional[str] = None,
        interactive: bool = True,
        reveal_folder: bool = False,
    ) -> PradoConfig:
        """
        Executes Phase 1 core onboarding:
        - Prompts for language ('es' default or 'en') first in interactive mode.
        - Collects or applies username, password, Moodle URL, destination directory (with native GUI folder picker support), and routing preset.
        - Stores SSO credentials in the OS credential store / vault.
        - Creates the destination folder on disk.
        - Saves config.yaml with mode 0600 permissions.
        """
        existing = load_config(self.config_path)
        resolved_lang = (language or existing.language or "es").strip().lower()
        if resolved_lang not in ("es", "en", "it", "fr"):
            resolved_lang = "es"

        if interactive and not username:
            self.print_fn("\n🎓 PradoOS — Configuración Inicial / Initial Setup / Configurazione / Configuration")
            self.print_fn("=" * 68)

            lang_ans = self.input_fn(
                "🌐 0. Idioma / Language [1 = Español (default), 2 = English, 3 = Italiano, 4 = Français] [1]: "
            ).strip().lower()
            if lang_ans in ("2", "en", "english", "eng"):
                resolved_lang = "en"
            elif lang_ans in ("3", "it", "italiano", "ita"):
                resolved_lang = "it"
            elif lang_ans in ("4", "fr", "français", "francais", "fra"):
                resolved_lang = "fr"
            else:
                resolved_lang = "es"

            is_en = resolved_lang == "en"
            is_it = resolved_lang == "it"
            is_fr = resolved_lang == "fr"
            default_url = moodle_url or existing.moodle_url or get_default_moodle_url()

            if is_en:
                plat_ans = self.input_fn(
                    f"1. Platform [1=Grado ({default_url}), 2=Posgrado, 3=CEPRUD, or custom URL] (default 1): "
                ).strip()
            elif is_it:
                plat_ans = self.input_fn(
                    f"1. Piattaforma [1=Grado ({default_url}), 2=Posgrado, 3=CEPRUD, o URL personalizzato] (default 1): "
                ).strip()
            elif is_fr:
                plat_ans = self.input_fn(
                    f"1. Plateforme [1=Grado ({default_url}), 2=Posgrado, 3=CEPRUD, ou URL personnalisée] (défaut 1) : "
                ).strip()
            else:
                plat_ans = self.input_fn(
                    f"1. Plataforma [1=Grado ({default_url}), 2=Posgrado, 3=CEPRUD, o URL personalizada] (por defecto 1): "
                ).strip()
            resolved_url = resolve_platform_url(plat_ans) if plat_ans else default_url

            default_user = existing.username or ""
            if is_en:
                user_prompt = (
                    f"2. Institutional Email / Username [{default_user}]: "
                    if default_user
                    else "2. Institutional Email / Username (e.g. student@correo.ugr.es): "
                )
            elif is_it:
                user_prompt = (
                    f"2. Email Istituzionale / Nome Utente [{default_user}]: "
                    if default_user
                    else "2. Email Istituzionale / Nome Utente (es. student@correo.ugr.es): "
                )
            elif is_fr:
                user_prompt = (
                    f"2. Courriel Institutionnel / Identifiant [{default_user}] : "
                    if default_user
                    else "2. Courriel Institutionnel / Identifiant (ex. student@correo.ugr.es) : "
                )
            else:
                user_prompt = (
                    f"2. Correo Institucional UGR / Usuario [{default_user}]: "
                    if default_user
                    else "2. Correo Institucional UGR / Usuario (ej. alumno@correo.ugr.es): "
                )
            entered_user = self.input_fn(user_prompt).strip() or default_user
            if entered_user:
                if entered_user.lower().endswith("@go.ugr.es"):
                    local_part = entered_user.split("@", 1)[0]
                    if local_part.lower().startswith("e.") and len(local_part) > 2:
                        local_part = local_part[2:]
                    entered_user = f"{local_part}@correo.ugr.es"
                    if is_en:
                        self.print_fn(f"   (Note: UGR SSO requires @correo.ugr.es -> using '{entered_user}')")
                    else:
                        self.print_fn(f"   (Nota: El SSO de la UGR requiere @correo.ugr.es -> usando '{entered_user}')")
                elif "@" not in entered_user and ".ugr.es" in resolved_url.lower():
                    entered_user = f"{entered_user}@correo.ugr.es"
                    if is_en:
                        self.print_fn(f"   (Normalized username to '{entered_user}')")
                    else:
                        self.print_fn(f"   (Usuario normalizado automáticamente a '{entered_user}')")
            username = entered_user

            if password is None:
                if is_en:
                    self.print_fn("   💡 (Note: For security reasons, password characters are NOT displayed while typing. Just type it and press Enter.)")
                    entered_pass = self.password_fn("3. Institutional Password (hidden): ")
                elif is_it:
                    self.print_fn("   💡 (Nota: Per motivi di sicurezza, la password NON è visibile durante la digitazione. Digitala normalmente e premi Invio.)")
                    entered_pass = self.password_fn("3. Password Istituzionale (nascosta): ")
                elif is_fr:
                    self.print_fn("   💡 (Note : Pour des raisons de sécurité, le mot de passe est MASQUÉ lors de la saisie. Tapez-le et appuyez sur Entrée.)")
                    entered_pass = self.password_fn("3. Mot de Passe Institutionnel (masqué) : ")
                else:
                    self.print_fn("   💡 (Nota: Por motivos de seguridad, la contraseña NO es visible mientras escribes. Escríbela normalmente y pulsa Enter.)")
                    entered_pass = self.password_fn("3. Contraseña Institucional (oculta): ")
                password = entered_pass

            # Resolve default localized Desktop/Home folder and base folder name
            desktop_dir = get_localized_desktop_dir()
            default_folder_name = "PRADO_UGR"
            default_root_path = Path(courses_root) if courses_root else (desktop_dir / default_folder_name)

            if is_en:
                self.print_fn(f"\n4. Destination Folder for your Courses (default on Desktop/Home: {default_root_path}):")
                self.print_fn("   • Press [Enter] to use the default location and choose a folder name")
                self.print_fn("   • Type 'G' and press Enter to select a folder via Graphical Window (Finder / File Explorer)")
                self.print_fn("   • Or type a custom folder name / full path directly")
                entered_root = self.input_fn(f"   Location or 'G' for GUI [{desktop_dir}]: ").strip()
            elif is_it:
                self.print_fn(f"\n4. Cartella di destinazione per i tuoi insegnamenti (default su Scrivania/Home: {default_root_path}):")
                self.print_fn("   • Premi [Invio] per usare la Scrivania/Home e scegliere il nome della cartella")
                self.print_fn("   • Digita 'G' e premi Invio per aprire la finestra grafica (Finder / Esplora Risorse)")
                self.print_fn("   • O inserisci direttamente un percorso completo personalizzato")
                entered_root = self.input_fn(f"   Posizione o 'G' per finestra grafica [{desktop_dir}]: ").strip()
            elif is_fr:
                self.print_fn(f"\n4. Dossier de destination pour vos cours (par défaut sur Bureau/Accueil : {default_root_path}) :")
                self.print_fn("   • Appuyez sur [Entrée] pour utiliser l'emplacement par défaut")
                self.print_fn("   • Tapez 'G' et appuyez sur Entrée pour ouvrir l'explorateur graphique (Finder / Explorateur de fichiers)")
                self.print_fn("   • Ou saisissez directement un chemin complet")
                entered_root = self.input_fn(f"   Emplacement ou 'G' pour sélecteur graphique [{desktop_dir}] : ").strip()
            else:
                self.print_fn(f"\n4. Ubicación donde guardar tus asignaturas (por defecto en Escritorio/Inicio: {default_root_path}):")
                self.print_fn("   • Pulsa [Enter] para usar tu Escritorio/Inicio y elegir el nombre de la carpeta base")
                self.print_fn("   • Escribe 'G' y pulsa Enter para abrir la ventana gráfica (Finder / Explorador de Archivos)")
                self.print_fn("   • O escribe directamente una ruta completa")
                entered_root = self.input_fn(f"   Ubicación o 'G' para ventana gráfica [{desktop_dir}]: ").strip()

            if entered_root.lower() in ("g", "gui", "finder", "explorer"):
                if is_en:
                    gui_prompt = "Select where to place your PRADO courses folder"
                elif is_it:
                    gui_prompt = "Seleziona dove salvare la cartella dei tuoi corsi PRADO"
                elif is_fr:
                    gui_prompt = "Sélectionnez où enregistrer vos dossiers de cours PRADO"
                else:
                    gui_prompt = "Selecciona dónde guardar la carpeta de tus asignaturas de PRADO"
                picked = prompt_folder_picker_gui(prompt=gui_prompt)
                base_parent = picked if picked is not None else desktop_dir
                if is_en:
                    name_prompt = f"   Base folder name inside '{base_parent}' [{default_folder_name}]: "
                elif is_it:
                    name_prompt = f"   Nome della cartella principale in '{base_parent}' [{default_folder_name}]: "
                elif is_fr:
                    name_prompt = f"   Nom du dossier principal dans '{base_parent}' [{default_folder_name}] : "
                else:
                    name_prompt = f"   Nombre de la carpeta base dentro de '{base_parent}' [{default_folder_name}]: "
                chosen_name = self.input_fn(name_prompt).strip() or default_folder_name
                resolved_root = base_parent if chosen_name in (".", "") else (base_parent / chosen_name)
            elif not entered_root:
                if is_en:
                    name_prompt = f"   Base folder name on '{desktop_dir}' [{default_folder_name}]: "
                elif is_it:
                    name_prompt = f"   Nome della cartella principale in '{desktop_dir}' [{default_folder_name}]: "
                elif is_fr:
                    name_prompt = f"   Nom du dossier principal dans '{desktop_dir}' [{default_folder_name}] : "
                else:
                    name_prompt = f"   Nombre de la carpeta base en '{desktop_dir}' [{default_folder_name}]: "
                chosen_name = self.input_fn(name_prompt).strip() or default_folder_name
                resolved_root = (desktop_dir / chosen_name).expanduser()
            else:
                candidate_path = Path(entered_root).expanduser()
                if candidate_path.is_absolute() or "/" in entered_root or "\\" in entered_root:
                    resolved_root = candidate_path
                else:
                    resolved_root = desktop_dir / entered_root

            default_preset = preset or "mirror"
            if is_en:
                self.print_fn(
                    "\n5. Folder Structure Mode:\n"
                    "   • 'mirror' (Default): Exact PRADO layout & official PRADO course names.\n"
                    "   • 'smart' (AI Mode only): Groups files into Teoria/ & Practicas/ with course acronyms (only recommended if configured with an AI Agent)."
                )
                entered_preset = self.input_fn(f"   Mode [mirror/smart] [{default_preset}]: ").strip().lower()
            elif is_it:
                self.print_fn(
                    "\n5. Organizzazione delle Cartelle:\n"
                    "   • 'mirror' (Default): Struttura originale di PRADO e nomi ufficiali dei tuoi insegnamenti.\n"
                    "   • 'smart' (Solo con IA): Raggruppa in Teoria/ e Pratiche/ con acronimi (ideale se affiancato da un assistente IA)."
                )
                entered_preset = self.input_fn(f"   Modalità [mirror/smart] [{default_preset}]: ").strip().lower()
            elif is_fr:
                self.print_fn(
                    "\n5. Organisation des Dossiers :\n"
                    "   • 'mirror' (Par défaut) : Structure originale de PRADO et noms officiels des cours.\n"
                    "   • 'smart' (Mode IA) : Regroupe en Théorie/ et Travaux Pratiques/ (recommandé avec un assistant IA)."
                )
                entered_preset = self.input_fn(f"   Mode [mirror/smart] [{default_preset}] : ").strip().lower()
            else:
                self.print_fn(
                    "\n5. Organización de Carpetas:\n"
                    "   • 'mirror' (Por defecto): Estructura original de PRADO y nombres oficiales de tus asignaturas.\n"
                    "   • 'smart' (Solo con IA): Agrupa en Teoria/ y Practicas/ con siglas (solo tiene sentido si usas la configuración con IA que ordena los archivos nuevos)."
                )
                entered_preset = self.input_fn(f"   Modo [mirror/smart] [{default_preset}]: ").strip().lower()
            resolved_preset = entered_preset if entered_preset in ("smart", "mirror") else default_preset

            if semester is None:
                if is_en:
                    sem_prompt = "6. Semester Filter [1 = 1st Semester, 2 = 2nd Semester, Enter = All Active]: "
                elif is_it:
                    sem_prompt = "6. Filtro Semestre [1 = 1º Semestre, 2 = 2º Semestre, Invio = Tutti gli attivi]: "
                elif is_fr:
                    sem_prompt = "6. Filtre de Semestre [1 = 1er Semestre, 2 = 2e Semestre, Entrée = Tous les cours actifs] : "
                else:
                    sem_prompt = "6. Filtro de Cuatrimestre [1 = 1º Cuatrimestre, 2 = 2º Cuatrimestre, Enter = Todos los activos]: "
                sem_ans = self.input_fn(sem_prompt).strip()
                if sem_ans in ("1", "2"):
                    semester = int(sem_ans)
                else:
                    semester = existing.sync.semester

            if is_en:
                self.print_fn(
                    "\n🛡️  Overwrite Protection ACTIVE: If you edit any downloaded file (notes, code, notebooks) and the professor uploads a new version on PRADO, your local changes are NEVER overwritten (the server version is saved alongside)."
                )
            else:
                self.print_fn(
                    "\n🛡️  Protección Anti-Sobrescritura ACTIVA: Si modificas cualquier archivo descargado (apuntes, código, notebooks) y el profesor sube una versión nueva en PRADO, tu trabajo NUNCA se borrará (la nueva versión se guardará al lado sin pisar la tuya)."
                )
        else:
            resolved_url = resolve_platform_url(moodle_url) if moodle_url else (existing.moodle_url or get_default_moodle_url())
            username = username or existing.username
            resolved_root = Path(courses_root).expanduser() if courses_root else existing.courses_root
            resolved_preset = (preset or existing.sync.preset or "smart").lower()
            if resolved_preset not in ("smart", "mirror"):
                resolved_preset = "smart"
            if semester is None:
                semester = existing.sync.semester

        # Persist credentials if both username and password are provided
        if username and password:
            self.credential_store.set_sso_credentials(username, password)

        # Ensure destination directory exists
        resolved_root.mkdir(parents=True, exist_ok=True)

        cfg = PradoConfig(
            version=existing.version,
            language=resolved_lang,
            moodle_url=resolved_url,
            sso_type=existing.sso_type,
            username=username,
            credential_store=existing.credential_store,
            courses_root=resolved_root,
            mfa=existing.mfa,
            sync=SyncConfig(
                preset=resolved_preset,
                semester=semester,
                dry_run=existing.sync.dry_run,
                subgroups=dict(existing.sync.subgroups),
            ),
            mail=existing.mail,
        )
        save_config(cfg, self.config_path)

        if reveal_folder:
            reveal_folder_in_file_manager(resolved_root)

        return cfg

    def run_phase2(
        self,
        subgroups: Optional[Dict[str, str]] = None,
        imap_enabled: Optional[bool] = None,
        imap_host: Optional[str] = None,
        imap_username: Optional[str] = None,
        imap_password: Optional[str] = None,
        install_daemon: bool = False,
        daemon_interval: int = 14400,
        interactive: bool = True,
    ) -> PradoConfig:
        """
        Executes Phase 2 Optional Power-Up configuration:
        - Configures lab/seminar subgroup filtering (e.g. ED_C -> C2).
        - Configures automatic 2FA email extraction via IMAP SSL.
        - Optionally installs background sync scheduler daemon.
        """
        cfg = load_config(self.config_path)
        is_en = cfg.language == "en"
        is_it = cfg.language == "it"
        is_fr = cfg.language == "fr"

        if interactive and subgroups is None and imap_enabled is None:
            if is_en:
                self.print_fn("\n⚡ PradoOS Phase 2 — Optional Power-Ups")
                self.print_fn("=" * 68)
                sub_ans = self.input_fn(
                    "1. Lab Subgroups (e.g. 'ED_C=C2,SO_E=E3' or Enter to keep all): "
                ).strip()
            else:
                self.print_fn("\n⚡ PradoOS Fase 2 — Opciones Avanzadas")
                self.print_fn("=" * 68)
                sub_ans = self.input_fn(
                    "1. Subgrupos de prácticas (ej. 'ED_C=C2,SO_E=E3' o Enter para descargar todos): "
                ).strip()
            if sub_ans:
                parsed_subs: Dict[str, str] = {}
                for pair in sub_ans.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        if k.strip() and v.strip():
                            parsed_subs[k.strip()] = v.strip()
                subgroups = parsed_subs

            imap_prompt = (
                "2. Enable automatic 2FA email code fetching via IMAP? [y/N]: "
                if is_en
                else "2. ¿Activar lectura automática del código 2FA por correo vía IMAP? [s/N]: "
            )
            imap_ans = self.input_fn(imap_prompt).strip().lower()
            if imap_ans in ("y", "yes", "s", "si", "sí"):
                imap_enabled = True
                default_host = cfg.mfa.imap_host or "imap.ugr.es"
                imap_host = self.input_fn(f"   IMAP Host [{default_host}]: ").strip() or default_host
                default_imap_user = cfg.mfa.imap_username or cfg.username or ""
                imap_username = (
                    self.input_fn(f"   IMAP Username [{default_imap_user}]: ").strip()
                    or default_imap_user
                )
                if imap_password is None:
                    pwd_msg = (
                        "   IMAP Password (Enter to reuse SSO password): "
                        if is_en
                        else "   Contraseña IMAP (Enter para reutilizar la contraseña UGR): "
                    )
                    imap_password = self.password_fn(pwd_msg)

            if is_en:
                daemon_prompt = "3. Install automatic background sync every 4 hours? [y/N]: "
            elif is_it:
                daemon_prompt = "3. Installare la sincronizzazione automatica ogni 4 ore? [s/N]: "
            elif is_fr:
                daemon_prompt = "3. Activer la synchronisation automatique toutes les 4 heures ? [o/N] : "
            else:
                daemon_prompt = "3. ¿Activar sincronización automática en segundo plano cada 4 horas? [s/N]: "
            daemon_ans = self.input_fn(daemon_prompt).strip().lower()
            if daemon_ans in ("y", "yes", "s", "si", "sí", "o", "oui"):
                install_daemon = True

        if subgroups is not None:
            cfg.sync.subgroups.update(subgroups)

        if imap_enabled is not None:
            cfg.mfa.imap_enabled = bool(imap_enabled)
        if imap_host:
            cfg.mfa.imap_host = imap_host
        if imap_username:
            cfg.mfa.imap_username = imap_username
        if imap_username and imap_password:
            self.credential_store.set_imap_credentials(imap_username, imap_password)

        save_config(cfg, self.config_path)

        if install_daemon:
            mgr = DaemonManager()
            mgr.install(interval_seconds=daemon_interval)

        return cfg

    def run_full_onboarding(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        moodle_url: Optional[str] = None,
        courses_root: Optional[Path | str] = None,
        preset: Optional[str] = None,
        semester: Optional[int] = None,
        language: Optional[str] = None,
        subgroups: Optional[Dict[str, str]] = None,
        imap_enabled: Optional[bool] = None,
        imap_host: Optional[str] = None,
        imap_username: Optional[str] = None,
        imap_password: Optional[str] = None,
        install_daemon: bool = False,
        interactive: bool = True,
        json_mode: bool = False,
        prompt_star: bool = False,
    ) -> Dict[str, Any]:
        """
        Runs Phase 1 and (optionally) Phase 2 onboarding, returning a structured summary dict.
        Note: GitHub star prompt is deferred to the 2nd completed automatic download/sync by default.
        """
        cfg = self.run_phase1(
            username=username,
            password=password,
            moodle_url=moodle_url,
            courses_root=courses_root,
            preset=preset,
            semester=semester,
            language=language,
            interactive=interactive and not json_mode,
        )

        has_phase2_args = any(
            x is not None for x in (subgroups, imap_enabled, imap_host, imap_username, imap_password)
        ) or install_daemon

        if has_phase2_args:
            cfg = self.run_phase2(
                subgroups=subgroups,
                imap_enabled=imap_enabled,
                imap_host=imap_host,
                imap_username=imap_username,
                imap_password=imap_password,
                install_daemon=install_daemon,
                interactive=False,
            )
        elif interactive and not json_mode:
            p2_prompt = (
                "\nWould you like to configure Phase 2 Power-Ups (subgroups / background daemon) now? [y/N]: "
                if cfg.language == "en"
                else "\n¿Quieres configurar opciones avanzadas (subgrupos de prácticas / sincronización automática cada 4h) ahora? [s/N]: "
            )
            try:
                want_p2 = self.input_fn(p2_prompt).strip().lower()
            except (StopIteration, EOFError):
                want_p2 = "n"
            if want_p2 in ("y", "yes", "s", "si", "sí"):
                cfg = self.run_phase2(interactive=True)

            mail_prompt = (
                "\n📬 Would you also like to activate the UGR Mail reader / auto-forwarding to your personal email? [y/N]: "
                if cfg.language == "en"
                else "\n📬 ¿Quieres activar también el lector/reenvío automático de correo UGR (@correo.ugr.es) a tu correo personal? [s/N]: "
            )
            try:
                want_mail = self.input_fn(mail_prompt).strip().lower()
            except (StopIteration, EOFError):
                want_mail = "n"
            if want_mail in ("y", "yes", "s", "si", "sí"):
                from prado.mail.tui import configure_forwarding_interactive
                cfg = configure_forwarding_interactive(
                    cfg=cfg,
                    input_fn=self.input_fn,
                    print_fn=self.print_fn,
                )

        star_info: Optional[Dict[str, Any]] = None
        if prompt_star:
            star_info = maybe_prompt_star_after_sync(
                interactive=interactive,
                json_mode=json_mode,
                config_dir=self.config_path.parent,
                input_fn=self.input_fn,
                print_fn=self.print_fn,
                language=cfg.language,
            )

        return {
            "status": "success",
            "config_file": str(self.config_path),
            "language": cfg.language,
            "username": cfg.username,
            "moodle_url": cfg.moodle_url,
            "courses_root": str(cfg.courses_root),
            "preset": cfg.sync.preset,
            "semester": cfg.sync.semester,
            "subgroups": cfg.sync.subgroups,
            "imap_enabled": cfg.mfa.imap_enabled,
            "star": star_info,
        }
