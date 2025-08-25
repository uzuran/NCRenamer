"File service for handling CSV-based of processed materials."

import csv
from pathlib import Path


class FileService:
    """Handles reading and writing CSV-based history of processed materials."""

    def __init__(self, materials_file):
        """
        Initialize the service with a path to the materials CSV file.

        Args:
            materials_file (str or Path): Path to the CSV file containing materials history.
        """
        self.materials_file = Path(materials_file)

    def load_nc_materials(self):
        """
        Load the processed materials history from the CSV file.

        Returns:
            list[list[str]]: A list of rows (each row is a list of strings).
                             Returns an empty list if the file does not exist.
        """
        if self.materials_file.exists():
            with self.materials_file.open("r", encoding="utf-8") as f:
                return list(csv.reader(f))
        return []
