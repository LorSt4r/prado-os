"""
Unit tests for Mid-Semester Adoption scanner.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import pytest

from prado.core.adoption import AdoptionScanner, LocalFileInfo
from prado.state import StateDatabase


class TestAdoptionScanner:
    def test_prescan_indexes_existing_files(self, tmp_path):
        db_path = tmp_path / "state.db"
        state_db = StateDatabase(db_path)
        courses_dir = tmp_path / "courses"
        courses_dir.mkdir()

        # Create sample files
        f1 = courses_dir / "ED_C" / "Teoria" / "Tema_1.pdf"
        f1.parent.mkdir(parents=True, exist_ok=True)
        c1 = b"%PDF-1.4 Tema 1 Content"
        f1.write_bytes(c1)
        h1 = hashlib.sha256(c1).hexdigest()

        f2 = courses_dir / "ED_C" / "Practicas" / "Guion_1.pdf"
        f2.parent.mkdir(parents=True, exist_ok=True)
        c2 = b"%PDF-1.4 Guion 1 Content"
        f2.write_bytes(c2)
        h2 = hashlib.sha256(c2).hexdigest()

        scanner = AdoptionScanner(courses_root=courses_dir, state_db=state_db)
        count = scanner.scan_local_files()

        assert count == 2
        assert h1 in scanner.hash_index
        assert h2 in scanner.hash_index
        assert scanner.hash_index[h1].rel_path == "ED_C/Teoria/Tema_1.pdf"

    def test_ignore_hidden_and_zero_byte_files(self, tmp_path):
        db_path = tmp_path / "state.db"
        state_db = StateDatabase(db_path)
        courses_dir = tmp_path / "courses"
        courses_dir.mkdir()

        # Regular file
        f_reg = courses_dir / "valid.pdf"
        f_reg.write_bytes(b"valid content")

        # Zero-byte file
        f_zero = courses_dir / "empty.pdf"
        f_zero.touch()

        # Hidden file (.DS_Store)
        f_hidden = courses_dir / ".DS_Store"
        f_hidden.write_bytes(b"macos metadata")

        # File in hidden directory
        git_dir = courses_dir / ".git" / "objects"
        git_dir.mkdir(parents=True, exist_ok=True)
        f_git = git_dir / "commit_obj"
        f_git.write_bytes(b"git data")

        scanner = AdoptionScanner(courses_root=courses_dir, state_db=state_db)
        count = scanner.scan_local_files()

        assert count == 1
        assert len(scanner.hash_index) == 1
        reg_hash = hashlib.sha256(b"valid content").hexdigest()
        assert reg_hash in scanner.hash_index

    def test_match_and_adopt_preserves_disk_mtime(self, tmp_path):
        db_path = tmp_path / "state.db"
        state_db = StateDatabase(db_path)
        courses_dir = tmp_path / "courses"
        courses_dir.mkdir()

        pdf_path = courses_dir / "ED_C" / "Teoria" / "Tema_1.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        content = b"%PDF-1.4 Already downloaded weeks ago"
        pdf_path.write_bytes(content)
        initial_mtime = pdf_path.stat().st_mtime
        server_hash = hashlib.sha256(content).hexdigest()

        scanner = AdoptionScanner(courses_root=courses_dir, state_db=state_db)
        scanner.scan_local_files()

        adopted = scanner.match_and_adopt(
            rel_path="ED_C/Teoria/Tema_1.pdf",
            server_hash=server_hash,
            course_id=15819,
        )

        assert adopted is not None
        assert adopted.sha256 == server_hash
        # Verify 0 disk writes: mtime must be unchanged!
        assert pdf_path.stat().st_mtime == initial_mtime

        # Verify state database registration
        rec = state_db.get_file("ED_C/Teoria/Tema_1.pdf")
        assert rec is not None
        assert rec.is_adopted == 1
        assert rec.original_hash == server_hash
        assert rec.student_modified == 0

    def test_non_matching_hash_returns_none(self, tmp_path):
        db_path = tmp_path / "state.db"
        state_db = StateDatabase(db_path)
        courses_dir = tmp_path / "courses"
        courses_dir.mkdir()

        f = courses_dir / "file.pdf"
        f.write_bytes(b"local content")

        scanner = AdoptionScanner(courses_root=courses_dir, state_db=state_db)
        scanner.scan_local_files()

        different_server_hash = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        res = scanner.match_and_adopt("file.pdf", different_server_hash)
        assert res is None

    def test_scan_prunes_heavy_dirs_caps_files_size_and_skips_onedrive_placeholders(self, tmp_path, monkeypatch):
        from types import SimpleNamespace

        db_path = tmp_path / "state.db"
        state_db = StateDatabase(db_path)
        courses_dir = tmp_path / "courses"
        courses_dir.mkdir()

        # Heavy ignored dir should be pruned without indexing
        nm = courses_dir / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_bytes(b"console.log(1);")

        # Valid files
        (courses_dir / "a.pdf").write_bytes(b"pdf-a")
        (courses_dir / "b.pdf").write_bytes(b"pdf-b")
        (courses_dir / "big.pdf").write_bytes(b"0123456789ABCDEF")  # 16 bytes -> skipped with max_file_size_bytes=10
        cloud_only = courses_dir / "onedrive_cloud.pdf"
        cloud_only.write_bytes(b"cloud")

        orig_stat = Path.stat

        def fake_stat(self_path: Path, *args, **kwargs):
            st = orig_stat(self_path, *args, **kwargs)
            if self_path.name == "onedrive_cloud.pdf":
                return SimpleNamespace(
                    st_size=st.st_size,
                    st_mtime=st.st_mtime,
                    st_mode=st.st_mode,
                    st_file_attributes=0x00400000,  # FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
                )
            return st

        monkeypatch.setattr(Path, "stat", fake_stat)

        scanner = AdoptionScanner(courses_root=courses_dir, state_db=state_db)
        count = scanner.scan_local_files(max_files=50, max_seconds=5.0, max_file_size_bytes=10)
        assert count == 2
        assert sorted(scanner.path_index.keys()) == ["a.pdf", "b.pdf"]

        # max_files=1 stops cleanly after indexing 1 file
        scanner2 = AdoptionScanner(courses_root=courses_dir, state_db=state_db)
        count_capped = scanner2.scan_local_files(max_files=1, max_seconds=5.0, max_file_size_bytes=10)
        assert count_capped == 1
