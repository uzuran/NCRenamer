"""Materials view model"""

from pathlib import Path
import csv

class MaterialsViewModel:
    """Simple ViewModel to load CSV data for materials."""

    def __init__(self, csv_path="CNCs/materials_new.csv"):
        self.csv_path = Path(csv_path)
        self.nc_files = self.load_nc_files()

    def load_nc_files(self):
        """Load tab-separated CSV as list of lists."""
        if not self.csv_path.exists():
            print(f"CSV file not found at {self.csv_path}")
            return []

        try:
            with open(self.csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f, delimiter="\t")
                return [row for row in reader if len(row) >= 2]  # only valid rows
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return []
