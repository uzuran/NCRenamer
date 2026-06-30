# tests/unit/test_formatter_model.py
"""Unit tests for every public method of FormatterModel."""

import re
from pathlib import Path

import pytest

from app.models.formatter_model import FormatterModel
from tests.conftest import StubMaterialRepository


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def make_formatter(materials: list[list[str]] | None = None) -> FormatterModel:
    repo = StubMaterialRepository(materials) if materials is not None else None
    return FormatterModel(repo)  # type: ignore[arg-type]


def write_nc(tmp_path: Path, lines: list[str]) -> Path:
    """Write an NC file whose lines are joined with newlines."""
    path = tmp_path / "test.NC"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# access_line_4
# --------------------------------------------------------------------------- #

class TestAccessLine4:
    def test_returns_fourth_line(self, tmp_path):
        path = write_nc(tmp_path, ["L1", "L2", "L3", "(MA/1.4301)", "L5"])
        assert FormatterModel().access_line_4(path) == "(MA/1.4301)"

    def test_strips_trailing_newline(self, tmp_path):
        path = tmp_path / "test.NC"
        path.write_text("L1\nL2\nL3\n(MA/1.4301)\nL5\n", encoding="utf-8")
        result = FormatterModel().access_line_4(path)
        assert "\n" not in result

    def test_returns_none_for_file_with_fewer_than_four_lines(self, tmp_path):
        path = write_nc(tmp_path, ["L1", "L2", "L3"])
        assert FormatterModel().access_line_4(path) is None

    def test_returns_none_for_exactly_three_lines(self, tmp_path):
        path = tmp_path / "test.NC"
        path.write_text("L1\nL2\nL3", encoding="utf-8")
        assert FormatterModel().access_line_4(path) is None

    def test_returns_line_when_file_has_exactly_four_lines(self, tmp_path):
        path = write_nc(tmp_path, ["L1", "L2", "L3", "(MA/1.0037)"])
        assert FormatterModel().access_line_4(path) == "(MA/1.0037)"


# --------------------------------------------------------------------------- #
# extract_material_value
# --------------------------------------------------------------------------- #

class TestExtractMaterialValue:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("(MA/1.4301)", "1.4301"),
            ("(MA/1.4301 brus)", "1.4301 brus"),
            ("(MA/3.3535 listkovy)", "3.3535 listkovy"),
            ("1.4301", "1.4301"),
            ("  (MA/1.4301)  ", "1.4301"),
            ("MA/1.4301", "1.4301"),
        ],
    )
    def test_extracts_payload(self, text, expected):
        assert FormatterModel().extract_material_value(text) == expected

    def test_plain_number_returned_unchanged(self):
        assert FormatterModel().extract_material_value("1.0037") == "1.0037"

    def test_empty_string_returned_unchanged(self):
        assert FormatterModel().extract_material_value("") == ""


# --------------------------------------------------------------------------- #
# normalize_material_key
# --------------------------------------------------------------------------- #

class TestNormalizeMaterialKey:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("(MA/1.4301)", "1.4301"),
            ("(MA/1.4301 brus)", "1.4301BRUS"),
            ("(MA/1.0037 S235JRG2)", "1.0037S235JRG2"),
            ("1.4301brus", "1.4301BRUS"),
        ],
    )
    def test_removes_spaces_and_uppercases(self, text, expected):
        assert FormatterModel().normalize_material_key(text) == expected


# --------------------------------------------------------------------------- #
# lookup_material_mapping
# --------------------------------------------------------------------------- #

class TestLookupMaterialMapping:
    def test_returns_correct_when_match_found(self):
        fm = make_formatter([["1.4301BRUS-4.0", "1.4301 brus"]])
        assert fm.lookup_material_mapping("(MA/1.4301BRUS-4.0)") == "1.4301 brus"

    def test_returns_none_when_no_match(self):
        fm = make_formatter([["1.4301BRUS-4.0", "1.4301 brus"]])
        assert fm.lookup_material_mapping("(MA/1.0037)") is None

    def test_returns_none_without_repository(self):
        fm = FormatterModel(material_repository=None)
        assert fm.lookup_material_mapping("(MA/1.4301BRUS-4.0)") is None

    def test_lookup_is_case_insensitive(self):
        fm = make_formatter([["1.4301BRUS-4.0", "1.4301 brus"]])
        assert fm.lookup_material_mapping("(MA/1.4301brus-4.0)") == "1.4301 brus"

    def test_lookup_ignores_spaces_in_key(self):
        fm = make_formatter([["1.0037 S235JRG2", "1.0037 S235JRG2"]])
        assert fm.lookup_material_mapping("(MA/1.0037S235JRG2)") == "1.0037 S235JRG2"


# --------------------------------------------------------------------------- #
# infer_material_with_missing_space
# --------------------------------------------------------------------------- #

class TestInferMaterialWithMissingSpace:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("(MA/1.0037S235JR)", "1.0037 S235JR"),
            ("(MA/1.4301Brus)", "1.4301 Brus"),
            ("(MA/3.3535Special)", "3.3535 Special"),
        ],
    )
    def test_inserts_space_between_number_and_alpha_suffix(self, text, expected):
        assert FormatterModel().infer_material_with_missing_space(text) == expected

    def test_returns_none_when_already_spaced(self):
        assert FormatterModel().infer_material_with_missing_space("(MA/1.4301 brus)") is None

    def test_returns_none_for_number_only(self):
        assert FormatterModel().infer_material_with_missing_space("(MA/1.4301)") is None

    def test_returns_none_for_non_material_text(self):
        assert FormatterModel().infer_material_with_missing_space("garbage") is None


# --------------------------------------------------------------------------- #
# write_line_4
# --------------------------------------------------------------------------- #

class TestWriteLine4:
    def test_replaces_fourth_line(self, tmp_path):
        path = write_nc(tmp_path, ["L1", "L2", "L3", "(MA/OLD)", "L5"])
        FormatterModel().write_line_4(path, "(MA/1.4301)")
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[3] == "(MA/1.4301)"

    def test_preserves_other_lines(self, tmp_path):
        path = write_nc(tmp_path, ["L1", "L2", "L3", "(MA/OLD)", "L5"])
        FormatterModel().write_line_4(path, "(MA/1.4301)")
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "L1"
        assert lines[4] == "L5"

    def test_does_nothing_for_file_with_fewer_than_four_lines(self, tmp_path):
        path = write_nc(tmp_path, ["L1", "L2", "L3"])
        original = path.read_text(encoding="utf-8")
        FormatterModel().write_line_4(path, "(MA/1.4301)")
        assert path.read_text(encoding="utf-8") == original


# --------------------------------------------------------------------------- #
# PATTERN regex
# --------------------------------------------------------------------------- #

class TestPattern:
    VALID = [
        "(MA/1.4301)",
        "(MA/1.0037)",
        "(MA/3.3535)",
        "(MA/1.4301 brus)",
        "(MA/1.0037 S235JRG2)",
        "(MA/3.3535 listkovy)",
    ]
    INVALID = [
        "MA/1.4301",           # missing outer parens
        "(MA/1.4301BRUS-4.0)", # suffix with no space separator
        "(MA/test)",           # no numeric code
        "(MA/1.430)",          # wrong number format (3 digits)
        "",
        "(MA/)",
    ]

    @pytest.mark.parametrize("value", VALID)
    def test_pattern_matches_valid_material(self, value):
        assert FormatterModel.PATTERN.fullmatch(value) is not None, (
            f"Expected pattern to match: {value!r}"
        )

    @pytest.mark.parametrize("value", INVALID)
    def test_pattern_rejects_invalid_material(self, value):
        assert FormatterModel.PATTERN.fullmatch(value) is None, (
            f"Expected pattern NOT to match: {value!r}"
        )
