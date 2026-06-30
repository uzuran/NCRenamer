# tests/unit/test_fix_material_format.py
"""Parametrised tests for FormatterModel.fix_material_format."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.models.formatter_model import FormatterModel


@pytest.mark.parametrize(
    "input_val, expected",
    [
        # CSV mapping is absent → generic number-only fallback applies
        ("(MA/1.4301BRUS-4.0)", "(MA/1.4301)"),
        # Missing space between number and alphabetic suffix → inferred
        ("(MA/1.0037S235JR)", "(MA/1.0037 S235JR)"),
        # Completely unrecognised text → returned unchanged
        ("test", "test"),
        # Non-numeric material with a dash suffix: no X.XXXX present,
        # fix_material_format cannot extract anything → returned unchanged.
        ("(MA/test-1.0)", "(MA/test-1.0)"),
    ],
)
def test_fix_material_format_variants(formatter_factory, input_val, expected):
    formatter = formatter_factory()
    assert formatter.fix_material_format(input_val) == expected


@given(st.text())
def test_fix_material_format_never_crashes(text):
    """fix_material_format must always return a str, never raise."""
    result = FormatterModel().fix_material_format(text)
    assert isinstance(result, str)
