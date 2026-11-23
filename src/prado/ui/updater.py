"""
Zero-telemetry 1-click Desktop Auto-Updater for PradoOS.

Checks GitHub Releases (`LorSt4r/prado-os/releases/latest`) strictly read-only,
validates download origins against official GitHub HTTPS hosts, downloads the
OS-matching release artifact, and on Windows launches `PradoOS-Setup.exe /SILENT`
for seamless in-place upgrades.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
import urllib.parse

import requests

from prado import __version__
from prado.ui.dialogs import open_folder, open_url

GITHUB_RELEASES_LATEST_URL = "https://api.github.com/repos/LorSt4r/prado-os/releases/latest"
GITHUB_RELEASES_PAGE_URL = "https://github.com/LorSt4r/prado-os/releases/latest"
ALLOWED_DOWNLOAD_HOSTS = (
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
)

_SEMVER_RE = re.compile(
    r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[._-]?(alpha|a|beta|b|rc)[._-]?(\d*))?\s*$",
    re.IGNORECASE,
)


def get_installed_version(build_info_path: Optional[Path] = None) -> str:
    """
    Returns the running release version string (without leading 'v').
    Prefers embedded `prado_build.json` in frozen PyInstaller bundles so beta
    releases (e.g. `0.2.0-beta.4`) compare accurately against GitHub tags.
    """
    candidates: List[Path] = []
    if build_info_path is not None:
        candidates.append(Path(build_info_path))
    elif getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "prado_build.json")
        try:
            exe_dir = Path(sys.executable).resolve().parent
            candidates.append(exe_dir / "prado_build.json")
            candidates.append(exe_dir / "_internal" / "prado_build.json")
        except Exception:
            pass

    for cand in candidates:
        try:
            if cand.is_file():
                raw = json.loads(cand.read_text(encoding="utf-8"))
                tag = str(raw.get("release_tag") or raw.get("version") or "").strip().lstrip("vV")
                if tag:
                    return tag
        except Exception:
            continue

    return str(__version__).strip().lstrip("vV")


def parse_version(raw: str) -> Tuple[int, int, int, int, int]:
    """
    Parses SemVer/PEP 440 versions and prereleases into a comparable tuple:
    (major, minor, patch, stage, prerelease_num) where stage is:
    alpha=0, beta=1, rc=2, final=3.
    """
    cleaned = str(raw or "").strip()
    m = _SEMVER_RE.match(cleaned)
    if not m:
        nums = [int(n) for n in re.findall(r"\d+", cleaned)[:3]]
        while len(nums) < 3:
            nums.append(0)
        return (nums[0], nums[1], nums[2], 3, 0)

    major = int(m.group(1) or 0)
    minor = int(m.group(2) or 0)
    patch = int(m.group(3) or 0)
    pre_label = (m.group(4) or "").lower()
    if not pre_label:
        return (major, minor, patch, 3, 0)

    stage_map = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "rc": 2}
    stage = stage_map.get(pre_label, 1)
    pre_num = int(m.group(5) or 0)
    return (major, minor, patch, stage, pre_num)


def is_newer_version(latest: str, current: str) -> bool:
    """Returns True strictly when `latest` is a higher version than `current`."""
    return parse_version(latest) > parse_version(current)


def validate_download_url(url: str) -> bool:
    """Allows HTTPS release URLs hosted strictly on official GitHub domains/repo."""
    try:
        parsed = urllib.parse.urlparse(str(url or "").strip())
    except Exception:
        return False
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_DOWNLOAD_HOSTS:
        return False
    if host == "github.com" and not (parsed.path or "").startswith("/LorSt4r/prado-os/"):
        return False
    return True


def select_asset_for_platform(
    assets: List[Dict[str, Any]],
    platform_name: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """Selects the optimal release asset for Windows, macOS, or Linux."""
    plat = (platform_name or sys.platform).lower()
    valid: List[Tuple[str, str, str]] = []
    for asset in assets or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "").strip()
        dl_url = str(asset.get("browser_download_url") or "").strip()
        if not name or not dl_url or not validate_download_url(dl_url):
            continue
        valid.append((name, name.lower(), dl_url))

    if plat in ("win32", "cygwin", "nt"):
        for orig, low, url in valid:
            if low == "pradoos-setup.exe" or low.endswith("-setup.exe"):
                return {"name": orig, "download_url": url, "kind": "windows_installer"}
        for orig, low, url in valid:
            if low.endswith(".zip") and "win" in low:
                return {"name": orig, "download_url": url, "kind": "archive"}
        return None

    if plat == "darwin":
        for orig, low, url in valid:
            if low.endswith(".zip") and ("mac" in low or "darwin" in low):
                return {"name": orig, "download_url": url, "kind": "archive"}
        return None

    for orig, low, url in valid:
        if (low.endswith(".tar.gz") or low.endswith(".tgz")) and "linux" in low:
            return {"name": orig, "download_url": url, "kind": "archive"}
    return None


def check_for_updates(
    current_version: Optional[str] = None,
    timeout: float = 5.0,
    platform_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Queries GitHub Releases API for a newer PradoOS version. Never raises."""
    cur = (current_version or get_installed_version()).strip().lstrip("vV")
    base: Dict[str, Any] = {
        "status": "error",
        "available": False,
        "current_version": cur,
        "latest_version": cur,
        "release_url": GITHUB_RELEASES_PAGE_URL,
        "asset_name": "",
        "download_url": "",
        "asset_kind": "",
        "notes": "",
        "error": None,
    }
    try:
        resp = requests.get(
            GITHUB_RELEASES_LATEST_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"PradoOS/{cur}",
            },
            timeout=timeout,
        )
        if resp.status_code != 200:
            base["error"] = f"HTTP {resp.status_code}"
            return base

        data = resp.json()
        raw_tag = str(data.get("tag_name") or "").strip()
        latest = raw_tag.lstrip("vV") or cur
        rel_url = str(data.get("html_url") or GITHUB_RELEASES_PAGE_URL).strip()
        if not validate_download_url(rel_url):
            rel_url = GITHUB_RELEASES_PAGE_URL
        asset = select_asset_for_platform(data.get("assets") or [], platform_name=platform_name)

        return {
            "status": "ok",
            "available": is_newer_version(raw_tag or latest, cur),
            "current_version": cur,
            "latest_version": latest,
            "release_url": rel_url,
            "asset_name": asset["name"] if asset else "",
            "download_url": asset["download_url"] if asset else "",
            "asset_kind": asset["kind"] if asset else "",
            "notes": str(data.get("body") or "")[:400],
            "error": None,
        }
    except Exception as exc:
        base["error"] = str(exc)
        return base


def _resolve_downloads_dir(explicit: Optional[Path] = None) -> Path:
    if explicit is not None:
        explicit.mkdir(parents=True, exist_ok=True)
        return explicit
    dl_dir = Path.home() / "Downloads"
    try:
        if dl_dir.is_dir() and os.access(dl_dir, os.W_OK):
            return dl_dir
    except Exception:
        pass
    tmp = Path(tempfile.gettempdir())
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp


def download_and_apply_update(
    update_info: Dict[str, Any],
    on_progress: Optional[Callable[[int], None]] = None,
    on_before_exit: Optional[Callable[[], None]] = None,
    platform_name: Optional[str] = None,
    is_frozen: Optional[bool] = None,
    downloads_dir: Optional[Path] = None,
    temp_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Downloads the official update asset and either runs the silent Windows
    installer (`PradoOS-Setup.exe /SP- /SILENT /NORESTART`) or reveals the
    downloaded macOS/Linux bundle in the file manager.
    """
    plat = (platform_name or sys.platform).lower()
    frozen = bool(getattr(sys, "frozen", False)) if is_frozen is None else bool(is_frozen)
    is_win = plat in ("win32", "cygwin", "nt")

    download_url = str(update_info.get("download_url") or "").strip()
    release_url = str(update_info.get("release_url") or GITHUB_RELEASES_PAGE_URL).strip()
    if not release_url.startswith("https://"):
        release_url = GITHUB_RELEASES_PAGE_URL
    asset_kind = str(update_info.get("asset_kind") or "").strip()
    asset_name = Path(str(update_info.get("asset_name") or "PradoOS-update")).name

    if not frozen or not download_url or not validate_download_url(download_url):
        open_url(release_url)
        return {"status": "opened_browser", "url": release_url}

    tmp_base = Path(temp_dir) if temp_dir is not None else Path(tempfile.gettempdir())
    if is_win and asset_kind == "windows_installer":
        safe_ver = re.sub(r"[^A-Za-z0-9._-]+", "", str(update_info.get("latest_version") or "latest")) or "latest"
        dest_dir = tmp_base
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"PradoOS-Setup-{safe_ver}.exe"
    else:
        dest_dir = _resolve_downloads_dir(downloads_dir)
        dest_path = dest_dir / asset_name

    part_path = dest_path.with_name(f".{dest_path.name}.part")
    try:
        with requests.get(download_url, stream=True, timeout=30, allow_redirects=True) as resp:
            resp.raise_for_status()
            final_url = str(getattr(resp, "url", download_url) or download_url)
            if not validate_download_url(final_url):
                return {"status": "error", "error": "Untrusted redirect URL"}

            total_bytes = int(resp.headers.get("Content-Length") or 0)
            written = 0
            first_bytes = b""
            with open(part_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    if len(first_bytes) < 2:
                        first_bytes = (first_bytes + chunk)[:2]
                    fh.write(chunk)
                    written += len(chunk)
                    if callable(on_progress) and total_bytes > 0:
                        pct = min(99, max(1, int(written * 100 / total_bytes)))
                        on_progress(pct)

        if is_win and asset_kind == "windows_installer" and not first_bytes.startswith(b"MZ"):
            if part_path.exists():
                part_path.unlink()
            return {"status": "error", "error": "Invalid Windows installer payload"}

        os.replace(part_path, dest_path)
        if callable(on_progress):
            on_progress(100)
    except Exception as exc:
        if part_path.exists():
            try:
                part_path.unlink()
            except OSError:
                pass
        return {"status": "error", "error": str(exc)}

    if is_win and asset_kind == "windows_installer":
        flags = (
            getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        )
        subprocess.Popen(
            [str(dest_path), "/SP-", "/SILENT", "/NORESTART"],
            creationflags=flags,
            close_fds=True,
        )
        if callable(on_before_exit):
            timer = threading.Timer(0.6, on_before_exit)
            timer.daemon = True
            timer.start()
        return {"status": "launching_installer", "path": str(dest_path)}

    if plat == "darwin":
        try:
            subprocess.Popen(["open", "-R", str(dest_path)], close_fds=True)
        except Exception:
            open_folder(dest_path.parent)
    else:
        open_folder(dest_path.parent)
    return {"status": "downloaded", "path": str(dest_path)}
