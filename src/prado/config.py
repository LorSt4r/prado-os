"""
Configuration management and secure OS path resolution for PradoOS.

Strictly enforces isolation between user configuration/credentials/state (mode 0700/0600)
and the synced course directories.
"""

from __future__ import annotations

import datetime
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from prado.exceptions import ConfigError


def get_default_academic_year_code(dt: Optional[datetime.datetime] = None) -> str:
    """
    Returns the two-digit pair code for the current academic year (e.g. '2627' for 2026/2027).
    Academic years start in September (month 9).
    """
    if dt is None:
        dt = datetime.datetime.now()
    year = dt.year
    if dt.month >= 9:
        start_yy = f"{year % 100:02d}"
        end_yy = f"{(year + 1) % 100:02d}"
    else:
        start_yy = f"{(year - 1) % 100:02d}"
        end_yy = f"{year % 100:02d}"
    return f"{start_yy}{end_yy}"


def get_default_moodle_url() -> str:
    """Returns the default undergraduate Moodle URL for the current academic year."""
    code = get_default_academic_year_code()
    return f"https://pradogrado{code}.ugr.es"


def get_config_dir() -> Path:
    """
    Returns the OS-appropriate configuration directory for PradoOS:
    - POSIX (macOS, Linux): ~/.config/prado (or $XDG_CONFIG_HOME/prado)
    - Windows: %APPDATA%/prado
    Can be overridden via PRADO_CONFIG_DIR environment variable for testing.
    """
    override = os.environ.get("PRADO_CONFIG_DIR")
    if override:
        path = Path(override)
    elif os.name == "nt":
        app_data = os.environ.get("APPDATA")
        if app_data:
            path = Path(app_data) / "prado"
        else:
            path = Path.home() / "AppData" / "Roaming" / "prado"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            path = Path(xdg_config) / "prado"
        else:
            path = Path.home() / ".config" / "prado"

    ensure_secure_dir(path)
    return path


def get_config_file() -> Path:
    """Returns the absolute path to config.yaml."""
    return get_config_dir() / "config.yaml"


def get_session_file() -> Path:
    """Returns the absolute path to session.json."""
    return get_config_dir() / "session.json"


def get_state_db_path() -> Path:
    """Returns the absolute path to state.db (SQLite database)."""
    return get_config_dir() / "state.db"


def get_credentials_vault_file() -> Path:
    """Returns the absolute path to the encrypted credentials vault fallback."""
    return get_config_dir() / "credentials.vault"


def get_localized_desktop_dir() -> Path:
    """
    Resolves the true OS-localized Desktop directory across Windows, macOS, and Linux
    (e.g. Desktop, Escritorio, Scrivania, OneDrive Desktop), falling back to Path.home().
    """
    home = Path.home()
    if os.name == "nt":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(260)
            # CSIDL_DESKTOPDIRECTORY = 0x0010
            res = ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf)
            if res == 0 and buf.value:
                win_desk = Path(buf.value)
                if win_desk.exists():
                    return win_desk
        except Exception:
            pass
    else:
        # Check XDG user-dirs.dirs on Linux
        xdg_dirs = home / ".config" / "user-dirs.dirs"
        if xdg_dirs.exists():
            try:
                import re
                text = xdg_dirs.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r'^XDG_DESKTOP_DIR="([^"]+)"', text, re.MULTILINE)
                if m:
                    raw_dir = m.group(1).replace("$HOME", str(home))
                    xdg_desk = Path(raw_dir)
                    if xdg_desk.exists():
                        return xdg_desk
            except Exception:
                pass

    for candidate_name in ("Desktop", "Escritorio", "Scrivania"):
        candidate = home / candidate_name
        if candidate.exists() and candidate.is_dir():
            return candidate

    return home


def prompt_folder_picker_gui(prompt: str = "Selecciona dónde guardar la carpeta de PRADO") -> Optional[Path]:
    """
    Opens a native OS graphical directory picker dialog (Finder on macOS,
    FolderBrowserDialog on Windows Explorer, Zenity/KDialog/Tkinter on Linux).
    Returns the selected Path, or None if cancelled or unavailable.
    """
    import subprocess
    import sys

    if sys.platform == "darwin":
        safe_prompt = prompt.replace('"', '\\"')
        script = f'POSIX path of (choose folder with prompt "{safe_prompt}")'
        try:
            proc = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return Path(proc.stdout.strip())
        except Exception:
            pass
        return None

    if os.name == "nt":
        safe_prompt = prompt.replace("'", "''")
        ps_cmd = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
            f"$f.Description = '{safe_prompt}'; "
            "$f.ShowNewFolderButton = $true; "
            "if ($f.ShowDialog() -eq 'OK') { [Console]::Out.WriteLine($f.SelectedPath) }"
        )
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-STA", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return Path(proc.stdout.strip().splitlines()[-1].strip())
        except Exception:
            pass
        return None

    # Linux Desktop: try zenity, kdialog, then tkinter
    import shutil
    if shutil.which("zenity"):
        try:
            proc = subprocess.run(
                ["zenity", "--file-selection", "--directory", f"--title={prompt}"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return Path(proc.stdout.strip())
        except Exception:
            pass

    if shutil.which("kdialog"):
        try:
            proc = subprocess.run(
                ["kdialog", "--getexistingdirectory", str(get_localized_desktop_dir()), "--title", prompt],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return Path(proc.stdout.strip())
        except Exception:
            pass

    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        selected = filedialog.askdirectory(title=prompt, initialdir=str(get_localized_desktop_dir()))
        root.destroy()
        if selected:
            return Path(selected)
    except Exception:
        pass

    return None


def ensure_secure_dir(directory: Path) -> Path:
    """
    Ensures directory exists with restricted permissions:
    mode 0700 (rwx------) on POSIX.
    """
    directory.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(directory, 0o700)
        except OSError:
            pass
    return directory


def write_secure_file(path: Path, content: str | bytes, mode: int = 0o600) -> None:
    """
    Atomically writes content to path and enforces restricted file permissions (mode 0600 on POSIX).
    Uses a temporary file in the same directory before atomic replacement.
    """
    parent = path.parent
    ensure_secure_dir(parent)

    import uuid
    token = uuid.uuid4().hex[:8]
    tmp_path = parent / f".tmp_{os.getpid()}_{token}_{path.name}"
    try:
        if isinstance(content, str):
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(tmp_path, "wb") as f:
                f.write(content)

        if os.name != "nt":
            try:
                os.chmod(tmp_path, mode)
            except OSError:
                pass

        import time
        for attempt in range(30):
            try:
                os.replace(tmp_path, path)
                break
            except PermissionError:
                if os.name == "nt" and attempt < 29:
                    time.sleep(0.01 * (attempt + 1))
                else:
                    raise
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


@dataclass
class MfaConfig:
    enable_device_trust: bool = True
    imap_enabled: bool = False
    imap_host: str = "imap.ugr.es"
    imap_port: int = 993
    imap_ssl: bool = True
    imap_username: Optional[str] = None
    imap_folder: str = "INBOX"
    imap_timeout: int = 60
    imap_poll_interval: int = 3
    apple_mail_enabled: bool = True
    apple_mail_account: str = "auto"


@dataclass
class SyncConfig:
    preset: str = "smart"  # 'smart' or 'mirror'
    semester: Optional[int] = None
    dry_run: bool = False
    subgroups: Dict[str, str] = field(default_factory=dict)


@dataclass
class PradoConfig:
    version: str = "1.0"
    language: str = "es"  # 'es' (default Spanish) or 'en' (English)
    moodle_url: str = field(default_factory=get_default_moodle_url)
    sso_type: str = "ugr_saml"
    username: Optional[str] = None
    credential_store: str = "auto"  # 'auto', 'keyring', 'vault_file', 'env'
    courses_root: Path = field(default_factory=lambda: Path.home() / "Documents" / "UGR_Courses")
    mfa: MfaConfig = field(default_factory=MfaConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["courses_root"] = str(self.courses_root)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PradoConfig:
        if not isinstance(data, dict):
            raise ConfigError("Config data must be a dictionary")

        mfa_data = data.get("mfa", {})
        if isinstance(mfa_data, dict):
            mfa_cfg = MfaConfig(**mfa_data)
        else:
            mfa_cfg = MfaConfig()

        sync_data = data.get("sync", {})
        if isinstance(sync_data, dict):
            sync_cfg = SyncConfig(**sync_data)
        else:
            sync_cfg = SyncConfig()

        courses_root_val = data.get("courses_root")
        if courses_root_val:
            courses_root = Path(courses_root_val).expanduser()
        else:
            courses_root = Path.home() / "Documents" / "UGR_Courses"

        lang = str(data.get("language", "es")).strip().lower()
        if lang not in ("es", "en"):
            lang = "es"

        return cls(
            version=str(data.get("version", "1.0")),
            language=lang,
            moodle_url=str(data.get("moodle_url") or get_default_moodle_url()),
            sso_type=str(data.get("sso_type", "ugr_saml")),
            username=data.get("username"),
            credential_store=str(data.get("credential_store", "auto")),
            courses_root=courses_root,
            mfa=mfa_cfg,
            sync=sync_cfg,
        )


def load_config(path: Optional[Path] = None) -> PradoConfig:
    """
    Loads PradoConfig from the specified file or the default config path (~/.config/prado/config.yaml).
    If the file does not exist, returns the default configuration.
    """
    config_file = path or get_config_file()
    if not config_file.exists():
        return PradoConfig()

    import time
    for attempt in range(20):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
            if not content:
                return PradoConfig()
            return PradoConfig.from_dict(content)
        except PermissionError as e:
            if os.name == "nt" and attempt < 19:
                time.sleep(0.01 * (attempt + 1))
                continue
            raise ConfigError(f"Failed to load configuration from {config_file}: {e}") from e
        except yaml.YAMLError as e:
            raise ConfigError(f"Malformed YAML in {config_file}: {e}") from e
        except Exception as e:
            raise ConfigError(f"Failed to load configuration from {config_file}: {e}") from e
    return PradoConfig()


def save_config(config: PradoConfig, path: Optional[Path] = None) -> None:
    """
    Serializes and securely writes PradoConfig to YAML with mode 0600.
    """
    config_file = path or get_config_file()
    content = yaml.dump(config.to_dict(), default_flow_style=False, sort_keys=False)
    write_secure_file(config_file, content, mode=0o600)
