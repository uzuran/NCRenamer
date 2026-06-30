"""Module for formatting and validating NC files."""

import re
import sys
from pathlib import Path
from rich.console import Console

from app.models.material_repository import MaterialRepository


class FormatterModel:
    """
    Provides functionality to validate, extract, and fix specific
    lines in NC files (e.g., checking the 4th line for material codes).
    """

    # Regex to match a valid (MA/number [optional name]) format.
    PATTERN: re.Pattern[str] = re.compile(
        r"\(MA/\d\.\d{4}(?: [0-9A-Za-zčěšřžýáíéůúťň-]+)*\)"
    )

    def __init__(self, material_repository: MaterialRepository | None = None) -> None:
        """Initialize NcFormatter with a console for logging."""
        self.pattern: re.Pattern[str] = self.PATTERN
        self.cons: Console = Console()
        self.material_repository = material_repository

    def access_line_4(self, nc_file: Path) -> str | None:
        """
        Retrieve the 4th line from a given NC file.

        Args:
            nc_file (Path): Path to the NC file.

        Returns:
            str | None: The 4th line without the newline character,
                        or None if the file has fewer than 4 lines.
        """
        with nc_file.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                if i == 4:
                    return line.rstrip("\n")
        return None

    def extract_material_value(self, text: str) -> str:
        """Return the material payload without wrapping ``(MA/...)`` syntax."""
        normalized = text.strip()
        if normalized.startswith("(") and normalized.endswith(")"):
            normalized = normalized[1:-1].strip()
        if normalized.upper().startswith("MA/"):
            normalized = normalized[3:].strip()
        return normalized

    def normalize_material_key(self, text: str) -> str:
        """Normalize a material value for CSV lookup."""
        return re.sub(r"\s+", "", self.extract_material_value(text)).upper()

    def lookup_material_mapping(self, text: str) -> str | None:
        """Return canonical material text from the repository when available."""
        if self.material_repository is None:
            return None

        normalized_input = self.normalize_material_key(text)
        for incorrect, correct, *_ in self.material_repository.load_materials():
            if self.normalize_material_key(incorrect) == normalized_input:
                return correct.strip()
        return None

    def infer_material_with_missing_space(self, text: str) -> str | None:
        """Infer canonical material when the only issue is a missing space."""
        material = self.extract_material_value(text)
        match = re.fullmatch(r"(\d\.\d{4})([A-Za-z][A-Za-z0-9]*)", material)
        if not match:
            return None

        number_part, suffix = match.groups()
        return f"{number_part} {suffix}"

    def fix_material_format(self, text: str) -> str:
        """
        Attempt to correct the material code format from a given string.

        Args:
            text (str): Line text potentially containing the material code.

        Returns:
            str | None: Corrected material code (e.g., '(MA/1.2345)') if found,
                        otherwise None.
        """
        mapped_material = self.lookup_material_mapping(text)
        if mapped_material:
            return f"(MA/{mapped_material})"

        inferred_material = self.infer_material_with_missing_space(text)
        if inferred_material:
            return f"(MA/{inferred_material})"

        # Match the number part only
        match = re.search(r"(\d\.\d{4})", text)
        if match:
            # Rebuild the whole correct format
            return f"(MA/{match.group(1)})"
        return text

    def write_line_4(self, file_path: Path, new_line: str) -> None:
        """
        Replace the 4th line of a file with a new line, if it exists.

        Args:
            file_path (Path): Path to the NC file.
            new_line (str): Text to write as the new 4th line.

        Logs:
            Warns if the file has fewer than 4 lines.
        """
        lines = file_path.read_text(encoding="utf-8").splitlines()
        if len(lines) >= 4:
            lines[3] = new_line
            file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            self.cons.log(
                f"{file_path.name}: File has fewer than 4 lines, cannot modify.",
                style="yellow",
            )

    def process_file(self, nc_file: Path) -> bool:
        """
        Validate and, if necessary, fix the 4th line of an NC file.

        Args:
            nc_file (Path): Path to the NC file.

        Returns:
            bool: True if the file was modified (line fixed),
                  False if no change was needed or possible.
        """
        line_4 = self.access_line_4(nc_file)
        if line_4 is None:
            self.cons.log(f"{nc_file.name}: 4th line not found", style="yellow")
            return False

        mapped_material = self.lookup_material_mapping(line_4)
        if mapped_material:
            expected_line = f"(MA/{mapped_material})"
            if line_4 == expected_line:
                self.cons.log(f"{nc_file.name}: {line_4} -> correct", style="green")
                return False

            self.cons.log(
                f"{nc_file.name}: {line_4} -> fixed to: {expected_line}", style="red"
            )
            self.write_line_4(nc_file, expected_line)
            return True

        if self.pattern.fullmatch(line_4):
            self.cons.log(f"{nc_file.name}: {line_4} -> correct", style="green")
            return False

        fixed_line = self.fix_material_format(line_4)
        if fixed_line != line_4:
            self.cons.log(
                f"{nc_file.name}: {line_4} -> fixed to: {fixed_line}", style="red"
            )
            self.write_line_4(nc_file, fixed_line)
            return True

        self.cons.log(
            f"{nc_file.name}: {line_4} -> invalid, cannot fix",
            style="bold red",
        )
        return False
    
