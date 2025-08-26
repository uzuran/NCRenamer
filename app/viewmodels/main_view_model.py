from pathlib import Path
import csv
import time
import urllib.parse


class MainViewModel:
    def __init__(self, main_frame_instance, email_model, formatter_model):
        self.main_frame_instance = main_frame_instance
        self.email_model = email_model
        self.formatter = formatter_model
        self.file_list = []
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

    def reset_email_counter(self):
        self.email_model.reset_counter()

    def increment_email_counter(self):
        self.email_model.increment_counter()

    def select_files(self, file_paths):
        self.file_list = [Path(f) for f in file_paths]

    def rename_files(self):
        total = len(self.file_list)
        results = []
        for file in self.file_list:
            changed = self.formatter.process_file(file)
            results.append((file.name, changed))
            time.sleep(0.10)
        return results

    def get_mailto_url(self):
        recipient_email = "else.artem@gmail.com"
        subject = f"Report bug_{self.email_model.email_counter}"
        return f"mailto:{recipient_email}?subject={urllib.parse.quote(subject)}"

    def update_email_counter_label(self):
        """Metoda, která říká View (MainFrame), aby se aktualizoval."""
        if self.main_frame_instance:
            self.main_frame_instance.update_email_counter_label()
