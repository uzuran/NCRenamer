import csv
import shutil
from pathlib import Path

from app.utils.resource_path import resource_path


class MaterialRepository:
    "Material repository for managing materials stored in a CSV file."

    def __init__(self, csv_path: Path | None = None):
        self.default_csv_path = Path(resource_path("CNCs/materials_new.csv"))

        if csv_path:
            self.csv_path = csv_path
        else:
            self.csv_path = self._resolve_writable_csv_path()

        self._ensure_csv_exists()

    def _resolve_writable_csv_path(self) -> Path:
        """Return a persistent writable path for the materials CSV."""

        user_dir = Path.home() / "AppData" / "Local" / "NCRenamer"
        user_dir.mkdir(parents=True, exist_ok=True)

        return user_dir / "materials_new.csv"

    def _ensure_csv_exists(self) -> None:
        if self.csv_path.exists():
            return

        if self.default_csv_path.exists():
            shutil.copyfile(self.default_csv_path, self.csv_path)
        else:
            self.csv_path.touch()

    def add_material(self, incorrect: str, correct: str) -> bool:
        "Add material to cvs file"
        materials = self.load_materials()

        for row in materials:
            if row[0] == incorrect:
                return False

        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([incorrect.strip(), correct.strip()])

        return True

    def delete_material(self, incorrect: str) -> bool:
        incorrect = incorrect.strip()

        materials = self.load_materials()

        new_materials = [row for row in materials if row[0].strip() != incorrect]

        if len(new_materials) == len(materials):
            return False

        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerows(new_materials)

        return True

    def load_materials(self) -> list[list[str]]:
        """Load tab-separated CSV as list of lists."""
        if not self.csv_path.exists():
            print(f"CSV file not found at {self.csv_path}")
            return []

        try:
            with open(self.csv_path, encoding="utf-8-sig") as f:
                reader = csv.reader(f, delimiter="\t")
                return [row for row in reader if len(row) >= 2]  # only valid rows
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return []
