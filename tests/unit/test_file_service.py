"""Tests for FileService - file reading with encoding fallback."""

import pytest

from app.burn_table.services.file_service import FileService


@pytest.fixture
def svc():
    return FileService()


class TestReadNc:
    def test_reads_utf8_file(self, svc, tmp_path):
        f = tmp_path / "prog.NC"
        f.write_text("(PR/6670-18)\n(MA/1.0037)\n", encoding="utf-8")
        content = svc.read_nc(f)
        assert "(PR/6670-18)" in content

    def test_raises_when_file_missing(self, svc, tmp_path):
        with pytest.raises(FileNotFoundError):
            svc.read_nc(tmp_path / "missing.NC")

    def test_reads_windows1250_file(self, svc, tmp_path):
        f = tmp_path / "prog.NC"
        # Write text that has windows-1250 characters
        f.write_bytes("(PR/6670-18)\n".encode("windows-1250"))
        content = svc.read_nc(f)
        assert "6670-18" in content


class TestReadSch:
    def test_reads_xml_file(self, svc, tmp_path):
        f = tmp_path / "sched.SCH"
        xml = '<?xml version="1.0"?><root><parts_name>6670-18</parts_name></root>'
        f.write_text(xml, encoding="utf-8")
        assert "6670-18" in svc.read_sch(f)

    def test_raises_when_file_missing(self, svc, tmp_path):
        with pytest.raises(FileNotFoundError):
            svc.read_sch(tmp_path / "missing.SCH")


class TestExists:
    def test_existing_file_returns_true(self, svc, tmp_path):
        f = tmp_path / "file.xls"
        f.write_text("")
        assert svc.exists(f) is True

    def test_missing_file_returns_false(self, svc, tmp_path):
        assert svc.exists(tmp_path / "ghost.xls") is False

    def test_directory_returns_false(self, svc, tmp_path):
        assert svc.exists(tmp_path) is False


class TestEnsureParent:
    def test_creates_nested_directories(self, svc, tmp_path):
        target = tmp_path / "a" / "b" / "c" / "file.xls"
        svc.ensure_parent(target)
        assert target.parent.is_dir()

    def test_existing_parent_is_noop(self, svc, tmp_path):
        target = tmp_path / "file.xls"
        svc.ensure_parent(target)  # parent already exists
        assert tmp_path.is_dir()
