import customtkinter as ctk
from app.models.email_bug_tracker_model import EmailBugTrackerModel
from app.services.nc_formatter import NcFormatter
from app.viewmodels.main_view_model import MainViewModel
from app.views.main_frame import MainFrame
from app.views.settings_frame import SettingsFrame
from app.views.materials_frame import MaterialsFrame
from translations import LANGUAGES


class App(ctk.CTk): # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
    def __init__(self):
        super().__init__()
        self.title("NC Renamer")  # Optional title
        self.geometry("400x500")  # Optional size

        # Pick default language (must match keys in translations.py)
        self.current_language_code = "en"
        self.texts = LANGUAGES[self.current_language_code]

        # Models & services
        self.email_model = EmailBugTrackerModel()
        self.formatter_model = NcFormatter()

        # ViewModel (business logic handler)
        self.main_viewmodel = MainViewModel(self.email_model, self.formatter_model)

        # Views (UI frames)
        self.main_frame = MainFrame(
            master=self,
            viewmodel=self.main_viewmodel,
            texts=self.texts,
            app_instance=self,
        )
        self.main_frame.pack(fill="both", expand=True)

        # If needed later
        self.settings_frame = SettingsFrame(master=self, app_instance=self)
        self.materials_frame = MaterialsFrame(master=self, app_instance=self)

        # Show main frame by default
        self.show_main_content()

    def show_main_content(self):
        """Switch to main frame."""
        self._hide_all_frames()
        self.main_frame.pack(fill="both", expand=True)

    def show_settings_content(self):
        """Switch to settings frame."""
        self._hide_all_frames()
        self.settings_frame.pack(fill="both", expand=True)

    def show_materials_content(self):
        """Switch to settings frame."""
        self._hide_all_frames()
        self.materials_frame.pack(fill="both", expand=True)

    def _hide_all_frames(self):
        """Hide all frames before showing another one."""
        for frame in (self.main_frame, self.settings_frame, self.materials_frame):
            frame.pack_forget()


if __name__ == "__main__":
    app = App()  # Start your App class, not CTk directly
    app.mainloop()
