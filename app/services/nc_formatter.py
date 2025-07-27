"""Module for formatting and validating NC files."""

import re
import sys
from pathlib import Path
from rich.console import Console


class NcFormatter:
    """
    Provides functionality to validate, extract, and fix specific
    lines in NC files (e.g., checking the 4th line for material codes).
    """

    # Regex to match a valid (MA/number [optional name]) format.
    PATTERN: re.Pattern[str] = re.compile(
        r"\(MA/\d\.\d{4}(?: ?[a-zA-Zčěšřžýáíéůúťň]+)?\)?"
    )

    def __init__(self) -> None:
        """Initialize NcFormatter with a console for logging."""
        self.pattern: re.Pattern[str] = self.PATTERN
        self.cons: Console = Console()

    def get_nc_files(self, file_path: Path) -> list[Path]:
        """
        Return all `.NC` files in the given directory.

        Args:
            file_path (Path): Path to the directory containing NC files.

        Returns:
            list[Path]: List of `.NC` file paths.

        Raises:
            SystemExit: If the provided path is invalid or not a directory.
        """
        if not file_path.exists() or not file_path.is_dir():
            self.cons.log(
                f"Directory {file_path} does not exist or is not a directory.",
                style="red",
            )
            sys.exit(1)

        return [file for file in file_path.iterdir() if file.suffix.upper() == ".NC"]

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

    def fix_material_format(self, text: str) -> str | None:
        """
        Attempt to correct the material code format from a given string.

        Args:
            text (str): Line text potentially containing the material code.

        Returns:
            str | None: Corrected material code (e.g., '(MA/1.2345)') if found,
                        otherwise None.
        """
        # Match the number part only
        match = re.search(r"(\d\.\d{4})", text)
        if match:
            # Rebuild the whole correct format
            return f"(MA/{match.group(1)})"
        return None

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

        if self.pattern.fullmatch(line_4):
            self.cons.log(f"{nc_file.name}: {line_4} -> correct", style="green")
            return False

        fixed_line = self.fix_material_format(line_4)
        if fixed_line:
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
