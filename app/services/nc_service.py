# app/services/nc_service.py
from pathlib import Path
from app.services.nc_formatter import NcFormatter

class NcService:
    """Service for handling NC file operations."""

    def __init__(self):
        self.formatter = NcFormatter()

    def process_nc_file(self, file_path: Path) -> bool:
        """
        Process a single NC file via the formatter.

        Args:
            file_path (Path): Path to the NC file.

        Returns:
            bool: True if the file was changed, False otherwise.
        """
        return self.formatter.process_file(file_path)
