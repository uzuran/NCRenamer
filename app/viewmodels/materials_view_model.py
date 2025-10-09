from pathlib import Path
import csv

class MaterialsViewModel:
    """ViewModel pro MaterialsFrame."""
    def __init__(self, formatter_model=None, main_frame_instance=None):
        self.materials_content = ""
        self.formatter = formatter_model
        self.main_frame_instance = main_frame_instance
        self.nc_files = self.load_nc_files()

    def load_nc_files(self):
        """Load NC files from a CSV file."""
        path = Path("CNCs/materials_new.csv")
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    return list(reader)
            except Exception as e:
                print(f"Error while loading file: {e}")
                return []
        return []
    

    def process_data(self, data):
        """Process data using the formatter model."""
        processed_data = self.formatter.format(data)
        self.nc_files.append([processed_data])
        self.main_frame_instance.update_output(processed_data)
        return processed_data

    def get_processed_nc_files(self):
        """Převede historii ze seznamu na formátovaný text."""
        if self.nc_files:
            return "\n".join([", ".join(row) for row in self.nc_files])
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
