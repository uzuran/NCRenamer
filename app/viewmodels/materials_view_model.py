from pathlib import Path
import csv

class MaterialsViewModel:  # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
    def __init__(self, formatter_model=None, main_frame_instance=None):
        self.materials_content = ""
        self.formatter = formatter_model
        self.main_frame_instance = main_frame_instance
        self.history = self.load_nc_files()

    def load_nc_files(self):
        """Načítá historii ze souboru CSV a vrací ji jako seznam."""
        path = Path("CNCs/materials_new.csv")
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    return list(reader)
            except Exception as e:
                print(f"Chyba při načítání souboru: {e}")
                return []
        return []
    

    def process_data(self, data):
        """Zpracuje data a přidá je do historie."""
        processed_data = self.formatter.format(data)
        self.history.append([processed_data])
        self.main_frame_instance.update_output(processed_data)
        return processed_data

    def get_processed_history(self):
        """Převede historii ze seznamu na formátovaný text."""
        if self.history:
            return "\n".join([", ".join(row) for row in self.history])
        return ""

    def set_content(
        self, content: str
    ):  # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        self.materials_content = content

    def search(
        self, query: str
    ) -> str:  # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        query = query.strip().lower()
        if not query:
            return self.materials_content

        filtered_lines = [
            line
            for line in self.materials_content.splitlines()
            if query in line.lower()
        ]
        return "\n".join(filtered_lines)
