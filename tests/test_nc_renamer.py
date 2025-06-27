import re

class TestNcRenamer:
    def setup_method(self):
        # Use your real existing file path
        self.file_path = "4037-92.NC"

        # Expected value.
        self.expected_value = "3.3535"

    # Read basic correct format on line 4
    def test_if_basic_correct_format_exists(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Check if file has a fewer than 4 lines.
        assert len(lines) >= 4, "File has fewer than 4 lines"

        # Line 4
        line_4 = lines[3].strip()
        print()

        # Extract the first number after "MA/" or anywhere
        match = re.search(r"(\d+\.\d+)", line_4)
        assert match, f"No number found in line 4: '{line_4}'"

        actual_value = match.group(1)
        assert actual_value == self.expected_value, f"Expected '{self.expected_value}', got '{actual_value}'"
