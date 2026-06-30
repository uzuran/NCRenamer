"""ViewModel for the main application screen."""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.email_model import EmailModel
    from app.models.formatter_model import FormatterModel


class MainViewModel:
    """
    ViewModel for the main screen.

    Mediates between the UI and the domain models for file selection,
    NC-file processing, and bug reporting.  Has no knowledge of any View class.
    """

    BUG_REPORT_EMAIL: str = "else.artem@gmail.com"

    def __init__(
        self,
        email_model: EmailModel,
        formatter_model: FormatterModel,
    ) -> None:
        self._email_model = email_model
        self._formatter = formatter_model
        self._file_paths: list[Path] = []

    # ------------------------------------------------------------------ #
    # File selection
    # ------------------------------------------------------------------ #

    @property
    def file_paths(self) -> list[Path]:
        """Currently selected NC file paths."""
        return self._file_paths

    def select_files(self, file_paths: list[str] | tuple[str, ...]) -> None:
        """Replace the current selection with *file_paths*."""
        self._file_paths = [Path(f) for f in file_paths]

    def unselect_files(self) -> int:
        """Clear all selected files and return how many were removed."""
        count = len(self._file_paths)
        self._file_paths.clear()
        return count

    # ------------------------------------------------------------------ #
    # File processing
    # ------------------------------------------------------------------ #

    def process_single_file(self, file_path: Path) -> tuple[str, bool, str | None]:
        """
        Validate and fix the material code in *file_path*.

        Returns:
            A 3-tuple of (filename, was_changed, final_material_value).
            *final_material_value* is ``None`` when line 4 is absent.
        """
        changed = self._formatter.process_file(file_path)
        line_4 = self._formatter.access_line_4(file_path)
        final_material = (
            self._formatter.extract_material_value(line_4)
            if line_4 is not None
            else None
        )
        return file_path.name, changed, final_material

    # ------------------------------------------------------------------ #
    # Bug reporting
    # ------------------------------------------------------------------ #

    @property
    def email_counter(self) -> int:
        """Current number of submitted bug reports."""
        return self._email_model.email_counter

    def increment_email_counter(self) -> None:
        """Record one additional bug report."""
        self._email_model.increment_counter()

    def reset_email_counter(self) -> None:
        """Reset the bug-report counter to zero."""
        self._email_model.reset_counter()

    def get_mailto_url(self) -> str:
        """Return a ``mailto:`` URL pre-filled with the bug-report subject."""
        subject = f"Report bug_{self._email_model.email_counter}"
        return f"mailto:{self.BUG_REPORT_EMAIL}?subject={urllib.parse.quote(subject)}"
