from pathlib import Path
import csv


class MaterialRepository:
    "Material repository for managing materials stored in a CSV file."
    def __init__(self):
        self.csv_path = Path("CNCs/materials_new.csv")

    
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

        new_materials = [
            row for row in materials
            if row[0].strip() != incorrect
        ]

        if len(new_materials) == len(materials):
            return False

        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerows(new_materials)

        return True

    def load_materials(self):
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
        