import pytest
import re
from pathlib import Path
from nc_formatter import access_line_4, fix_material_format, write_line_4

# Regex pattern použitý při kontrole
pattern = re.compile(r"\(MA/\d\.\d{4}(?: ?[a-zA-Zčěščřžýáíéůúťň]+)?\)?")

# Testovací obsah NC souboru
NC_FILE_CONTENT = """(PR/4037-92)
(MC/ENSIS3015AJ)
(MN/ 244)
(MA/3.3535-4.0)
(PZ/   80.00X   80.00)
(WK/    1.00T 2500.00X 1250.00)
"""

# Očekávaná opravená hodnota
EXPECTED_FIXED_LINE = "(MA/3.3535)"


@pytest.fixture
def test_file(tmp_path: Path) -> Path:
    """Vytvoří dočasný NC soubor pro testy"""
    file = tmp_path / "test.NC"
    file.write_text(NC_FILE_CONTENT, encoding="utf-8")
    return file


def test_access_line_4(test_file):
    """Testuje, že získáme 4. řádek správně"""
    line = access_line_4(test_file)
    assert line == "(MA/3.3535-4.0)"


def test_fix_material_format():
    """Testuje opravu formátu"""
    fixed = fix_material_format("(MA/3.3535-4.0)")
    assert fixed == "(MA/3.3535)"


@pytest.mark.parametrize(
    "input_line, expected",
    [
        ("(MA/1.2345-4.0)", "(MA/1.2345)"),  # opravit
        ("(MA/1.2345 pozink)", "(MA/1.2345 pozink)"),  # OK
        ("(MA/1.2345 brus)", "(MA/1.2345 brus)"),  # OK
        ("(MA/1.2345ALUNOX)", "(MA/1.2345ALUNOX)"),  # OK
        ("(MA/1.2345 OtherStuff)", "(MA/1.2345 OtherStuff)"),  # OK
        ("(MA/1.2345 OtherStuff", "(MA/1.2345 OtherStuff)"),  #  zavorka
        ("MA/1.2345)", "(MA/1.2345)"),  #  závorky
        ("(MA/1.2345@#$%)", "(MA/1.2345)"),  # opravit nesmysl
    ],
)
def test_fix_material_format_parametrized(input_line, expected):
    assert fix_material_format(input_line) == expected


def test_write_line_4(test_file):
    """Testuje přepsání 4. řádku opravenou hodnotou"""
    write_line_4(test_file, EXPECTED_FIXED_LINE)
    new_line = access_line_4(test_file)
    assert new_line == EXPECTED_FIXED_LINE
    assert pattern.fullmatch(new_line)
