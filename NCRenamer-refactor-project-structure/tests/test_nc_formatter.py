"""test_nc_formatter.py"""

import re
from pathlib import Path
import pandas as pd
from pandas import DataFrame
import pytest
from nc_formatter import NcFormatter

NC_FILE_CONTENT = """(PR/4037-92)
(MC/ENSIS3015AJ)
(MN/ 244)
(MA/3.3535-4.0)
(PZ/   80.00X   80.00)
(WK/    1.00T 2500.00X 1250.00)
"""

EXPECTED_FIXED_LINE = "3.3535"
PATTERN = re.compile(r"MA/(\d\.\d{4})(?: ?[a-zA]+)?")

data_path = Path(__file__).resolve().parent.parent / "CNCs" / "materials_new.csv"
df: DataFrame = pd.read_csv(data_path, sep="\t", header=None, usecols=[0, 1])
df[0] = df[0].apply(lambda x: f"(MA/{x})")
TEST_DATA = list(zip(df[0], df[1]))


@pytest.fixture
def test_file(tmp_path: Path) -> Path:
    """Fixture to create a temporary NC file for testing."""
    file = tmp_path / "test.NC"
    file.write_text(NC_FILE_CONTENT, encoding="utf-8")
    return file


class TestNcFormatter:
    """Test suite for the NcFormatter class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup method to initialize the NcFormatter instance."""
        self.nc_formatter = NcFormatter()

    def test_access_line_4(self, test_file):
        """Test accessing line 4 of the NC file."""
        line = self.nc_formatter.access_line_4(test_file)
        assert line == "(MA/3.3535-4.0)"

    def test_fix_material_format(self):
        """Test fixing the material format in line 4."""
        fixed = self.nc_formatter.fix_material_format("(MA/3.3535-4.0)")
        assert fixed == "(MA/3.3535)"

    @pytest.mark.parametrize("input_line, expected", TEST_DATA)
    def test_fix_material_format_parametrized(self, input_line, expected):
        """Test fixing material format with parametrized input."""
        result = self.nc_formatter.fix_material_format(input_line)
        assert result == expected

    def test_write_line_4(self, test_file):
        """Test writing a fixed line 4 to the NC file."""
        self.nc_formatter.write_line_4(test_file, EXPECTED_FIXED_LINE)
        new_line = self.nc_formatter.access_line_4(test_file)
        assert new_line == EXPECTED_FIXED_LINE
        assert PATTERN.fullmatch(new_line)
