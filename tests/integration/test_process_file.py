# tests/integration/test_process_file.py

from pathlib import Path

from app.models.formatter_model import FormatterModel
from tests.conftest import StubMaterialRepository


def test_process_file_uses_material_mapping_for_brus(nc_file_factory):
    formatter = FormatterModel(
        StubMaterialRepository([["1.4301BRUS-4.0", "1.4301 brus"]])
    )
    nc_file = nc_file_factory("(MA/1.4301BRUS-4.0)")

    changed = formatter.process_file(nc_file)

    assert changed is True
    assert nc_file.read_text(encoding="utf-8").splitlines()[3] == "(MA/1.4301 brus)"


def test_process_file_keeps_already_canonical_material(nc_file_factory):
    formatter = FormatterModel(
        StubMaterialRepository([["1.4301BRUS-4.0", "1.4301 brus"]])
    )
    nc_file = nc_file_factory("(MA/1.4301 brus)")

    changed = formatter.process_file(nc_file)

    assert changed is False
    assert nc_file.read_text(encoding="utf-8").splitlines()[3] == "(MA/1.4301 brus)"


def test_process_file_uses_exact_mapping_before_generic_number_fallback(
    nc_file_factory,
):
    formatter = FormatterModel(
        StubMaterialRepository([["1.0037S235JRG2", "1.0037 S235JRG2"]])
    )
    nc_file = nc_file_factory("(MA/1.0037S235JRG2)")

    changed = formatter.process_file(nc_file)

    assert changed is True
    assert nc_file.read_text(encoding="utf-8").splitlines()[3] == "(MA/1.0037 S235JRG2)"


def test_process_file_keeps_canonical_material_with_digits_in_suffix(nc_file_factory):
    formatter = FormatterModel(
        StubMaterialRepository([["1.0037S235JRG2", "1.0037 S235JRG2"]])
    )
    nc_file = nc_file_factory("(MA/1.0037 S235JRG2)")

    changed = formatter.process_file(nc_file)

    assert changed is False
    assert nc_file.read_text(encoding="utf-8").splitlines()[3] == "(MA/1.0037 S235JRG2)"


def test_process_file_handles_short_file(tmp_path: Path):
    formatter = FormatterModel()

    nc_file = tmp_path / "short.NC"
    print(nc_file.exists())  # False
    nc_file.write_text("line1\nline2\nline3\nline4", encoding="utf-8")

    changed = formatter.process_file(nc_file)

    assert changed is False


def test_process_file_without_material_line(nc_file_factory):
    formatter = FormatterModel()

    nc_file = nc_file_factory("(NO_MATERIAL)")

    changed = formatter.process_file(nc_file)

    assert changed is False


def test_process_file_is_idempotent(nc_file_factory):
    formatter = FormatterModel()

    nc_file = nc_file_factory("(MA/1.4301BRUS-4.0)")

    formatter.process_file(nc_file)
    first = nc_file.read_text(encoding="utf-8")

    formatter.process_file(nc_file)
    second = nc_file.read_text(encoding="utf-8")

    assert first == second


def test_material_mapping_is_case_insensitive(nc_file_factory):
    formatter = FormatterModel(
        StubMaterialRepository([["1.4301BRUS-4.0", "1.4301 brus"]])
    )

    nc_file = nc_file_factory("(MA/1.4301brus-4.0)")

    changed = formatter.process_file(nc_file)

    assert changed is True
    assert nc_file.read_text(encoding="utf-8").splitlines()[3] == "(MA/1.4301 brus)"
