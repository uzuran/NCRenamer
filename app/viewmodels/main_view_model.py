from pathlib import Path
import urllib.parse


class MainViewModel:
    def __init__(self, main_frame_instance, email_model, formatter_model):
        self.main_frame_instance = main_frame_instance
        self.email_model = email_model
        self.formatter = formatter_model
        self.file_list = []

    def reset_email_counter(self):
        self.email_model.reset_counter()

    def increment_email_counter(self):
        self.email_model.increment_counter()

    def select_files(self, file_paths):
        self.file_list = [Path(f) for f in file_paths]

    def list_of_nc_files(self): #TODO: rename this function in the 
        """Returns the file list for processing in the UI."""
        return self.file_list

    def process_single_file(self, file_path: Path) -> tuple[str, bool, str | None]:
        """Process a single file and return filename, change flag and final material."""
        changed = self.formatter.process_file(file_path)
        final_line = self.formatter.access_line_4(file_path)
        final_material = (
            self.formatter.extract_material_value(final_line)
            if final_line is not None
            else None
        )
        return (file_path.name, changed, final_material)

    def get_mailto_url(self):
        recipient_email = "else.artem@gmail.com"
        subject = f"Report bug_{self.email_model.email_counter}"
        return f"mailto:{recipient_email}?subject={urllib.parse.quote(subject)}"

    def update_email_counter_label(self):
        """Metoda, která říká View (MainFrame), aby se aktualizoval."""
        if self.main_frame_instance:
            self.main_frame_instance.update_email_counter_label()


    def unselect_files(self) -> int:
        """Clear selected NC files"""
        removed_count = len(self.file_list)
        self.file_list.clear()
        return removed_count
