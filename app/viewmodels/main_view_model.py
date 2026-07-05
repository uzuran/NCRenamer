"""ViewModel for the main application screen."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.formatter_model import FormatterModel


class MainViewModel:
    """
    ViewModel for the main screen.

    Mediates between the UI and the domain models for file selection and
    NC-file processing.  Has no knowledge of any View class.
    """

    def __init__(self, formatter_model: FormatterModel) -> None:
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
