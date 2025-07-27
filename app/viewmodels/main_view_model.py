from pathlib import Path
import csv
import time
import urllib.parse
import webbrowser

class MainViewModel:
    def __init__(self, email_model, formatter_model):
        self.email = email_model
        self.formatter = formatter_model
        self.file_list = []
        self.processed_files_history = self.load_history()

    def load_history(self):
        path = Path("CNCs/materials_new.csv")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                return list(reader)
        return []

    def reset_email_counter(self):
        self.email.email_counter = 0
        self.email.save_counter()

    def increment_email_counter(self):
        self.email.email_counter += 1
        self.email.save_counter()

    def select_files(self, file_paths):
        self.file_list = [Path(f) for f in file_paths]

    def rename_files(self):
        total = len(self.file_list)
        results = []
        for file in self.file_list:
            changed = self.formatter.process_file(file)
            results.append((file.name, changed))
            time.sleep(0.25)
        return results

    def get_mailto_url(self):
        recipient_email = "else.artem@gmail.com"
        subject = f"Report bug_{self.email.email_counter}"
        return f"mailto:{recipient_email}?subject={urllib.parse.quote(subject)}"

    def get_history_content(self):
        if self.processed_files_history:
            return "\n".join([", ".join(row) for row in self.processed_files_history])
        return ""
