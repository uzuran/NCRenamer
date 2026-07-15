"""Unit tests for PartStorageRepository — CRUD, search, persistence."""

import json
from pathlib import Path

import pytest

from app.models.part_storage_repository import PartStorageRepository


@pytest.fixture
def repo(tmp_path: Path) -> PartStorageRepository:
    return PartStorageRepository(path=tmp_path / "part_storage.json")


# ── add_part ──────────────────────────────────────────────────────────────────


class TestAddPart:
    def test_returns_id_string(self, repo):
        part_id = repo.add_part("ABC-001", "Regal A3")
        assert isinstance(part_id, str) and part_id

    def test_empty_part_number_returns_none(self, repo):
        assert repo.add_part("", "Regal A3") is None

    def test_whitespace_part_number_returns_none(self, repo):
        assert repo.add_part("   ", "Regal A3") is None

    def test_empty_location_returns_none(self, repo):
        assert repo.add_part("ABC-001", "") is None

    def test_whitespace_location_returns_none(self, repo):
        assert repo.add_part("ABC-001", "   ") is None

    def test_part_appears_in_load(self, repo):
        repo.add_part("ABC-001", "Regal A3")
        parts = repo.load_parts()
        assert len(parts) == 1
        assert parts[0]["part_number"] == "ABC-001"
        assert parts[0]["location"] == "Regal A3"

    def test_default_date_added_is_set(self, repo):
        repo.add_part("ABC-001", "Regal A3")
        item = repo.load_parts()[0]
        assert "date_added" in item
        assert item["date_added"]  # non-empty ISO date

    def test_custom_date_stored(self, repo):
        repo.add_part("ABC-001", "Regal A3", date_added="2026-01-15")
        assert repo.load_parts()[0]["date_added"] == "2026-01-15"

    def test_notes_stored(self, repo):
        repo.add_part("ABC-001", "Regal A3", notes="Leftover from job 8891")
        assert repo.load_parts()[0]["notes"] == "Leftover from job 8891"

    def test_notes_stripped(self, repo):
        repo.add_part("ABC-001", "Regal A3", notes="  trimmed  ")
        assert repo.load_parts()[0]["notes"] == "trimmed"

    def test_part_number_stripped(self, repo):
        repo.add_part("  ABC-001  ", "Regal A3")
        assert repo.load_parts()[0]["part_number"] == "ABC-001"

    def test_location_stripped(self, repo):
        repo.add_part("ABC-001", "  Regal A3  ")
        assert repo.load_parts()[0]["location"] == "Regal A3"

    def test_multiple_parts_accumulate(self, repo):
        repo.add_part("AAA-001", "Regal A1")
        repo.add_part("BBB-002", "Regal B2")
        assert len(repo.load_parts()) == 2

    def test_duplicate_part_numbers_allowed(self, repo):
        repo.add_part("ABC-001", "Regal A3")
        repo.add_part("ABC-001", "Regal B1")
        assert len(repo.load_parts()) == 2


# ── load_parts ────────────────────────────────────────────────────────────────


class TestLoadParts:
    def test_empty_on_fresh_repo(self, repo):
        assert repo.load_parts() == []

    def test_skips_items_without_id(self, tmp_path):
        path = tmp_path / "part_storage.json"
        path.write_text(
            json.dumps([{"part_number": "X", "location": "A"}]), encoding="utf-8"
        )
        r = PartStorageRepository(path=path)
        assert r.load_parts() == []

    def test_skips_items_without_part_number(self, tmp_path):
        path = tmp_path / "part_storage.json"
        path.write_text(
            json.dumps([{"id": "abc", "location": "A"}]), encoding="utf-8"
        )
        r = PartStorageRepository(path=path)
        assert r.load_parts() == []

    def test_returns_empty_on_corrupt_json(self, tmp_path):
        path = tmp_path / "part_storage.json"
        path.write_text("not valid json {{", encoding="utf-8")
        r = PartStorageRepository(path=path)
        assert r.load_parts() == []


# ── update_part ───────────────────────────────────────────────────────────────


class TestUpdatePart:
    def test_updates_existing_part(self, repo):
        part_id = repo.add_part("ABC-001", "Regal A3")
        assert repo.update_part(part_id, "ABC-002", "Regal B1") is True
        item = repo.load_parts()[0]
        assert item["part_number"] == "ABC-002"
        assert item["location"] == "Regal B1"

    def test_returns_false_for_unknown_id(self, repo):
        assert repo.update_part("nonexistent", "X", "Y") is False

    def test_returns_false_for_empty_part_number(self, repo):
        part_id = repo.add_part("ABC-001", "Regal A3")
        assert repo.update_part(part_id, "", "Regal A3") is False

    def test_returns_false_for_empty_location(self, repo):
        part_id = repo.add_part("ABC-001", "Regal A3")
        assert repo.update_part(part_id, "ABC-001", "") is False

    def test_notes_updated(self, repo):
        part_id = repo.add_part("ABC-001", "Regal A3", notes="old note")
        repo.update_part(part_id, "ABC-001", "Regal A3", notes="new note")
        assert repo.load_parts()[0]["notes"] == "new note"

    def test_original_date_preserved(self, repo):
        part_id = repo.add_part("ABC-001", "Regal A3", date_added="2025-01-01")
        repo.update_part(part_id, "ABC-002", "Regal B2")
        assert repo.load_parts()[0]["date_added"] == "2025-01-01"


# ── delete_part ───────────────────────────────────────────────────────────────


class TestDeletePart:
    def test_removes_existing_part(self, repo):
        part_id = repo.add_part("ABC-001", "Regal A3")
        assert repo.delete_part(part_id) is True
        assert repo.load_parts() == []

    def test_returns_false_for_unknown_id(self, repo):
        assert repo.delete_part("nonexistent") is False

    def test_other_parts_unaffected(self, repo):
        repo.add_part("KEEP-001", "Regal K1")
        del_id = repo.add_part("DEL-002", "Regal D2")
        repo.delete_part(del_id)
        parts = repo.load_parts()
        assert len(parts) == 1
        assert parts[0]["part_number"] == "KEEP-001"


# ── search_by_part_number ─────────────────────────────────────────────────────


class TestSearchByPartNumber:
    def test_exact_match(self, repo):
        repo.add_part("ABC-001", "Regal A1")
        results = repo.search_by_part_number("ABC-001")
        assert len(results) == 1

    def test_partial_match(self, repo):
        repo.add_part("ABC-001", "Regal A1")
        repo.add_part("ABC-002", "Regal A2")
        repo.add_part("XYZ-999", "Regal X9")
        results = repo.search_by_part_number("ABC")
        assert len(results) == 2

    def test_case_insensitive(self, repo):
        repo.add_part("abc-001", "Regal A1")
        results = repo.search_by_part_number("ABC")
        assert len(results) == 1

    def test_empty_query_returns_all(self, repo):
        repo.add_part("AAA-001", "Regal A1")
        repo.add_part("BBB-002", "Regal B2")
        assert len(repo.search_by_part_number("")) == 2

    def test_no_match_returns_empty(self, repo):
        repo.add_part("ABC-001", "Regal A1")
        assert repo.search_by_part_number("ZZZ") == []

    def test_partial_suffix_match(self, repo):
        repo.add_part("ABC-001", "Regal A1")
        results = repo.search_by_part_number("001")
        assert len(results) == 1


# ── persistence ───────────────────────────────────────────────────────────────


class TestPersistence:
    def test_data_survives_new_instance(self, tmp_path):
        path = tmp_path / "part_storage.json"
        r1 = PartStorageRepository(path=path)
        r1.add_part("ABC-001", "Regal A3", notes="persistent")

        r2 = PartStorageRepository(path=path)
        parts = r2.load_parts()
        assert len(parts) == 1
        assert parts[0]["part_number"] == "ABC-001"
        assert parts[0]["notes"] == "persistent"

    def test_file_created_automatically(self, tmp_path):
        path = tmp_path / "subdir" / "part_storage.json"
        PartStorageRepository(path=path)
        assert path.exists()
