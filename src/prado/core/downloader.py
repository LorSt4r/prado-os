"""
Streaming, chunked, atomic downloader with live SHA-256 calculation for PradoOS.

Streams file downloads in 64KB chunks into secure temporary files
(.prado_tmp_{pid}_{token}_{name}.part) in the destination directory, calculates
hashes concurrently, and atomically moves to target destination.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import datetime
from enum import Enum
import hashlib
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Dict, List, Optional
import urllib.parse
import uuid

import requests

from prado.exceptions import NetworkError, PradoError


MIME_TO_EXTENSION: Dict[str, str] = {
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
    "application/x-ipynb+json": ".ipynb",
    "application/json": ".json",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/x-tar": ".tar",
    "application/gzip": ".tar.gz",
    "text/plain": ".txt",
    "text/x-c": ".c",
    "text/x-c++": ".cpp",
    "text/x-python": ".py",
}

DYNAMIC_URL_EXTENSIONS = {
    "",
    ".php",
    ".html",
    ".htm",
    ".aspx",
    ".jsp",
    ".do",
    ".cgi",
    ".action",
    ".cfm",
    ".ashx",
}


def is_dynamic_or_empty_extension(ext: str) -> bool:
    """Returns True if the extension represents a dynamic server endpoint or is empty."""
    if not ext:
        return True
    return ext.lower() in DYNAMIC_URL_EXTENSIONS


def resolve_destination_path(
    dest_path: Path,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    final_url: Optional[str] = None,
) -> Path:
    """
    Resolves the final filesystem destination path for a download.

    When the URL lacks a clean extension (e.g. Moodle endpoints like
    '/mod/resource/view.php?id=123'), this inspects Content-Disposition
    and Content-Type (using MIME_TO_EXTENSION) to determine the true
    file extension and prevent saving non-PDF files (ZIP, DOCX, IPYNB, etc.)
    with mismatched or missing extensions.
    """
    from prado.core.overwrite import split_filename_and_extension
    from prado.core.router import sanitize_path_segment

    headers = headers or {}
    dest_stem, dest_ext = split_filename_and_extension(dest_path.name)

    # 1. Determine if URL lacks a clean extension
    parsed_orig = urllib.parse.urlparse(url)
    _, orig_url_ext = split_filename_and_extension(os.path.basename(parsed_orig.path))
    url_lacks_clean_ext = is_dynamic_or_empty_extension(orig_url_ext)

    # If the URL already has a clean extension and dest_path has a non-dynamic extension, keep dest_path
    if not url_lacks_clean_ext and not is_dynamic_or_empty_extension(dest_ext):
        return dest_path

    # 2. Extract candidate extension and filename from Content-Disposition
    cd_header = headers.get("Content-Disposition") or headers.get("content-disposition")
    cd_filename = parse_content_disposition(cd_header)
    cd_ext = None
    if cd_filename:
        _, cd_ext = split_filename_and_extension(cd_filename)

    # 3. Extract candidate extension from Content-Type / MIME_TO_EXTENSION
    ct_header = headers.get("Content-Type") or headers.get("content-type") or ""
    mime = ct_header.split(";")[0].strip().lower()
    mime_ext = MIME_TO_EXTENSION.get(mime)
    if not mime_ext and mime:
        import mimetypes
        guessed = mimetypes.guess_extension(mime)
        if guessed and guessed.lower() not in (".bin", ".exe", ".sh"):
            mime_ext = guessed

    # 4. Extract candidate extension from final redirected URL (if available)
    redirect_ext = None
    if final_url and isinstance(final_url, str):
        parsed_final = urllib.parse.urlparse(final_url)
        _, final_path_ext = split_filename_and_extension(os.path.basename(parsed_final.path))
        if not is_dynamic_or_empty_extension(final_path_ext):
            redirect_ext = final_path_ext

    # 5. Determine resolved extension by precedence: Content-Disposition -> MIME -> Redirect URL
    resolved_ext = None
    if cd_ext and not is_dynamic_or_empty_extension(cd_ext):
        resolved_ext = cd_ext
    elif mime_ext and not is_dynamic_or_empty_extension(mime_ext):
        resolved_ext = mime_ext
    elif redirect_ext:
        resolved_ext = redirect_ext

    if not resolved_ext:
        return dest_path

    # 6. Apply resolved extension to destination path
    generic_stems = {"download", "file", "view", "resource", "index", ""}
    if dest_stem.lower() in generic_stems and cd_filename:
        return dest_path.parent / sanitize_path_segment(cd_filename)

    if is_dynamic_or_empty_extension(dest_ext) or (url_lacks_clean_ext and dest_ext.lower() != resolved_ext.lower()):
        if dest_stem.lower().endswith(resolved_ext.lower()):
            return dest_path.parent / dest_stem
        return dest_path.parent / f"{dest_stem}{resolved_ext}"

    return dest_path


class DownloadStatus(str, Enum):
    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    REPLACED = "replaced"
    CONFLICT_SAVED = "conflict_saved"
    ADOPTED = "adopted"
    FAILED = "failed"


@dataclass
class DownloadResult:
    dest_path: Path
    url: str
    sha256: str
    size_bytes: int
    status: DownloadStatus
    error: Optional[str] = None
    elapsed_seconds: float = 0.0
    forked_path: Optional[Path] = None


@dataclass
class DownloadedFile:
    path: Path
    url: str
    sha256: str
    size_bytes: int
    course_id: Optional[str] = None


@dataclass
class ConflictFile:
    original_path: Path
    forked_path: Path
    server_sha256: str
    local_sha256: str


@dataclass
class AdoptedFile:
    path: Path
    sha256: str
    size_bytes: int


@dataclass
class DeadlineItem:
    id: str
    title: str
    course: str
    due_date: datetime.datetime
    url: str


@dataclass
class ForumPost:
    forum_id: str
    subject: str
    author: str
    content: str
    url: Optional[str] = None


@dataclass
class SyncSummary:
    """Summary DTO representing the outcome of a sync operation."""
    downloaded_files: List[DownloadedFile] = field(default_factory=list)
    updated_files: List[DownloadedFile] = field(default_factory=list)
    conflict_files: List[ConflictFile] = field(default_factory=list)
    adopted_files: List[AdoptedFile] = field(default_factory=list)
    deadlines: List[DeadlineItem] = field(default_factory=list)
    forum_announcements: List[ForumPost] = field(default_factory=list)


def parse_content_disposition(header: Optional[str]) -> Optional[str]:
    """
    Parses Content-Disposition header supporting:
    - RFC 5987 / 6266 UTF-8 encoded: filename*=UTF-8''Presentaci%C3%B3n.pdf
    - Quoted: filename="example.pdf"
    - Unquoted: filename=example.pdf
    """
    if not header:
        return None

    # 1. RFC 5987 / 6266 UTF-8 encoded filename
    m_utf8 = re.search(r"filename\*=UTF-8''([^;\s]+)", header, re.IGNORECASE)
    if m_utf8:
        raw_val = m_utf8.group(1).strip("\"'")
        return urllib.parse.unquote(raw_val)

    # 2. Quoted filename
    m_quoted = re.search(r'filename="([^"]+)"', header, re.IGNORECASE)
    if m_quoted:
        return m_quoted.group(1)

    # 3. Unquoted filename
    m_unquoted = re.search(r"filename=([^\s;]+)", header, re.IGNORECASE)
    if m_unquoted:
        return m_unquoted.group(1).strip("\"'")

    return None


def _extract_embedded_pluginfile_url(html: str, base_url: str) -> Optional[str]:
    """
    Extracts an embedded `pluginfile.php` resource URL from Moodle resource wrapper HTML
    (`<div class="resourceworkaround">`, `<object data=...>`, `<iframe src=...>`, `<embed src=...>`).
    """
    if not html:
        return None
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        wa = soup.find(class_="resourceworkaround")
        if wa:
            link = wa.find("a", href=True)
            if link and "pluginfile.php" in link["href"]:
                return urllib.parse.urljoin(base_url, link["href"])
        for tag_name, attr in (("object", "data"), ("iframe", "src"), ("embed", "src"), ("a", "href")):
            for tag in soup.find_all(tag_name):
                val = tag.get(attr)
                if isinstance(val, str) and "pluginfile.php" in val:
                    return urllib.parse.urljoin(base_url, val)
    except Exception:
        pass

    m = re.search(r"""(?:href|src|data)\s*=\s*["']([^"']*pluginfile\.php[^"']*)["']""", html, re.IGNORECASE)
    if m:
        return urllib.parse.urljoin(base_url, m.group(1))
    return None


def _is_html_content_type(resp: Any) -> bool:
    headers = getattr(resp, "headers", None)
    if not headers or not hasattr(headers, "get"):
        return False
    raw_ct = headers.get("Content-Type") or headers.get("content-type")
    if not isinstance(raw_ct, str):
        return False
    ct = raw_ct.split(";")[0].strip().lower()
    return ct in ("text/html", "application/xhtml+xml")


def _read_html_response_text(resp: Any) -> str:
    txt = getattr(resp, "text", None)
    if isinstance(txt, str):
        return txt
    try:
        chunks = b"".join(c for c in resp.iter_content(chunk_size=65536) if c)
        return chunks.decode("utf-8", errors="replace")
    except Exception:
        return ""


class SafeDownloader:
    """
    Safe chunked downloader. Streams in 64KB chunks into .prado_tmp_{pid}_{token}_{name}.part,
    calculates SHA-256 live, and atomically replaces target on completion.
    """
    CHUNK_SIZE: int = 65536  # 64 KB
    DEFAULT_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    BACKOFF_FACTOR: float = 0.5

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()

    def resolve_destination(
        self,
        dest_path: Path,
        url: str,
        response: Optional[requests.Response] = None,
    ) -> Path:
        """
        Resolves destination path using response headers (Content-Disposition, Content-Type)
        and redirect URL when the original URL lacks a clean extension.
        """
        headers: Dict[str, str] = {}
        final_url: Optional[str] = None
        if response is not None:
            if hasattr(response, "headers") and response.headers is not None:
                try:
                    headers = dict(response.headers)
                except (TypeError, ValueError):
                    headers = {}
            if hasattr(response, "url") and isinstance(response.url, str):
                final_url = response.url
        return resolve_destination_path(dest_path=dest_path, url=url, headers=headers, final_url=final_url)

    def download_file(
        self,
        url: str,
        dest_path: Path,
        expected_hash: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> DownloadResult:
        """
        Streams URL content to dest_path atomically.
        """
        start_time = time.time()
        retries = 0
        last_exception: Optional[Exception] = None
        tmp_file: Optional[Path] = None

        while retries <= self.MAX_RETRIES:
            try:
                hasher = hashlib.sha256()
                bytes_written = 0

                resp = self.session.get(
                    url,
                    stream=True,
                    timeout=self.DEFAULT_TIMEOUT,
                    allow_redirects=True,
                )

                if resp.status_code == 404:
                    return DownloadResult(
                        dest_path=dest_path,
                        url=url,
                        sha256="",
                        size_bytes=0,
                        status=DownloadStatus.FAILED,
                        error=f"HTTP 404 Not Found from {url}",
                        elapsed_seconds=time.time() - start_time,
                    )

                resp.raise_for_status()

                # Guard against Moodle resource wrapper HTML being saved with a binary extension (.pdf, .zip)
                if _is_html_content_type(resp) and dest_path.suffix.lower() not in (".html", ".htm"):
                    html_text = _read_html_response_text(resp)
                    if hasattr(resp, "close"):
                        try:
                            resp.close()
                        except Exception:
                            pass
                    resp_url = getattr(resp, "url", None)
                    base_ref = resp_url if isinstance(resp_url, str) and resp_url else url
                    embedded_url = _extract_embedded_pluginfile_url(html_text, base_ref)
                    if not embedded_url:
                        return DownloadResult(
                            dest_path=dest_path,
                            url=url,
                            sha256="",
                            size_bytes=0,
                            status=DownloadStatus.FAILED,
                            error=f"Received HTML wrapper instead of binary file from {url}",
                            elapsed_seconds=time.time() - start_time,
                        )
                    resp = self.session.get(
                        embedded_url,
                        stream=True,
                        timeout=self.DEFAULT_TIMEOUT,
                        allow_redirects=True,
                    )
                    if resp.status_code == 404:
                        return DownloadResult(
                            dest_path=dest_path,
                            url=embedded_url,
                            sha256="",
                            size_bytes=0,
                            status=DownloadStatus.FAILED,
                            error=f"HTTP 404 Not Found from {embedded_url}",
                            elapsed_seconds=time.time() - start_time,
                        )
                    resp.raise_for_status()
                    if _is_html_content_type(resp):
                        if hasattr(resp, "close"):
                            try:
                                resp.close()
                            except Exception:
                                pass
                        return DownloadResult(
                            dest_path=dest_path,
                            url=embedded_url,
                            sha256="",
                            size_bytes=0,
                            status=DownloadStatus.FAILED,
                            error=f"Received HTML wrapper instead of binary file from {embedded_url}",
                            elapsed_seconds=time.time() - start_time,
                        )

                # Wire Content-Disposition and MIME_TO_EXTENSION resolution
                target_dest = self.resolve_destination(dest_path=dest_path, url=url, response=resp)
                dest_dir = target_dest.parent
                dest_dir.mkdir(parents=True, exist_ok=True)

                token = uuid.uuid4().hex[:8]
                tmp_file = dest_dir / f".prado_tmp_{os.getpid()}_{token}_{target_dest.name}.part"

                content_length_hdr = resp.headers.get("Content-Length")
                expected_size = int(content_length_hdr) if content_length_hdr and content_length_hdr.isdigit() else None

                with open(tmp_file, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=self.CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            hasher.update(chunk)
                            bytes_written += len(chunk)
                            if progress_callback and expected_size:
                                progress_callback(bytes_written, expected_size)

                computed_hash = hasher.hexdigest()

                # Validate expected hash if provided
                if expected_hash and computed_hash.lower() != expected_hash.lower():
                    raise PradoError(
                        f"Checksum mismatch for {target_dest.name}: expected {expected_hash}, got {computed_hash}"
                    )

                # Atomic swap into target destination (with Windows NTFS lock retry)
                for attempt in range(30):
                    try:
                        os.replace(tmp_file, target_dest)
                        break
                    except PermissionError:
                        if attempt == 29:
                            raise
                        time.sleep(0.01 * (attempt + 1))

                return DownloadResult(
                    dest_path=target_dest,
                    url=url,
                    sha256=computed_hash,
                    size_bytes=bytes_written,
                    status=DownloadStatus.DOWNLOADED,
                    elapsed_seconds=time.time() - start_time,
                )

            except (requests.RequestException, IOError, PradoError) as e:
                last_exception = e
                retries += 1
                if tmp_file is not None and tmp_file.exists():
                    try:
                        tmp_file.unlink()
                    except OSError:
                        pass
                if retries <= self.MAX_RETRIES:
                    time.sleep(self.BACKOFF_FACTOR * (2 ** (retries - 1)))
                else:
                    break

        return DownloadResult(
            dest_path=dest_path,
            url=url,
            sha256="",
            size_bytes=0,
            status=DownloadStatus.FAILED,
            error=str(last_exception),
            elapsed_seconds=time.time() - start_time,
        )


__all__ = [
    "AdoptedFile",
    "ConflictFile",
    "DYNAMIC_URL_EXTENSIONS",
    "DeadlineItem",
    "DownloadedFile",
    "DownloadResult",
    "DownloadStatus",
    "ForumPost",
    "MIME_TO_EXTENSION",
    "SafeDownloader",
    "SyncSummary",
    "is_dynamic_or_empty_extension",
    "parse_content_disposition",
    "resolve_destination_path",
]
