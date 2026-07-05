# tests/conftest.py
from __future__ import annotations

import pytest

from app.models.formatter_model import FormatterModel
from app.models.material_repository import MaterialRepository

# --------------------------------------------------------------------------- #
# Stub classes (re-usable across unit-test modules)
# --------------------------------------------------------------------------- #


class StubMaterialRepository:
    """In-memory replacement for MaterialRepository used in unit tests."""

    def __init__(self, materials: list[list[str]] | None = None) -> None:
        self._materials: list[list[str]] = [list(row) for row in (materials or [])]

    def load_materials(self) -> list[list[str]]:
        return [list(row) for row in self._materials]

    def add_material(self, incorrect: str, correct: str) -> bool:
        if any(row[0] == incorrect for row in self._materials):
            return False
        self._materials.append([incorrect, correct])
        return True

    def update_material(
        self, incorrect: str, new_incorrect: str, new_correct: str
    ) -> bool:
        incorrect = incorrect.strip()
        new_incorrect = new_incorrect.strip()
        new_correct = new_correct.strip()
        for row in self._materials:
            if row[0].strip() == incorrect:
                row[0] = new_incorrect
                row[1] = new_correct
                return True
        return False

    def delete_material(self, incorrect: str) -> bool:
        original_len = len(self._materials)
        self._materials = [
            row for row in self._materials if row[0].strip() != incorrect.strip()
        ]
        return len(self._materials) < original_len


class StubFormatterModel:
    """
    Configurable stand-in for FormatterModel.

    Set *changed*, *line_4*, and *material* at construction time to control
    what each method returns without touching the filesystem.
    """

    def __init__(
        self,
        changed: bool = False,
        line_4: str | None = "(MA/1.4301)",
        material: str = "1.4301",
    ) -> None:
        self._changed = changed
        self._line_4 = line_4
        self._material = material

    def process_file(self, file_path) -> bool:
        return self._changed

    def access_line_4(self, file_path) -> str | None:
        return self._line_4

    def extract_material_value(self, text: str) -> str:
        return self._material


# --------------------------------------------------------------------------- #
# Fixtures shared across test modules
# --------------------------------------------------------------------------- #


@pytest.fixture
def formatter_factory():
    """Return a factory that creates a FormatterModel with an optional repo."""

    def _create(repo=None):
        return FormatterModel(repo)

    return _create


@pytest.fixture
def nc_file_factory(tmp_path):
    """
    Return a factory that writes a 5-line NC file whose 4th line is *line_4*.

    Each call produces ``tmp_path/sample.NC``; safe to call once per test.
    """

    def _create(line_4: str):
        nc_file = tmp_path / "sample.NC"
        nc_file.write_text(
            "line1\nline2\nline3\n" + line_4 + "\nline5\n",
            encoding="utf-8",
        )
        return nc_file

    return _create


@pytest.fixture
def empty_material_repo(tmp_path):
    """MaterialRepository backed by an empty temp CSV."""
    csv_file = tmp_path / "materials.csv"
    csv_file.write_text("", encoding="utf-8")
    return MaterialRepository(csv_path=csv_file)


@pytest.fixture
def stub_repo():
    """Empty StubMaterialRepository."""
    return StubMaterialRepository()


@pytest.fixture
def stub_formatter():
    """Default StubFormatterModel (no change, canonical 1.4301 line)."""
    return StubFormatterModel()
