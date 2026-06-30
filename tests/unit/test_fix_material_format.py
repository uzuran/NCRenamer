# tests/unit/test_fix_material_format.py

import pytest

from hypothesis import given, strategies as st
from app.models.formatter_model import FormatterModel


@pytest.mark.parametrize("input_val,expected", [
    ("(MA/1.4301BRUS-4.0)", "(MA/1.4301)"),
    ("(MA/1.0037S235JR)", "(MA/1.0037 S235JR)"),
    ("test", "test"),
    ("(MA/test-1.0)", "(MA/test)"),
    
])
def test_fix_material_format_variants(formatter_factory, input_val, expected):
    formatter = formatter_factory()

    result = formatter.fix_material_format(input_val)

    assert result == expected


@given(st.text())
def test_fix_material_format_never_crashes(text):
    formatter = FormatterModel()

    result = formatter.fix_material_format(text)
    assert isinstance(result, str)