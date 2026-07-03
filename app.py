import os
import threading
import webbrowser

import customtkinter as ctk

from app.burn_table.main import create_view_model as create_burn_view_model
from app.models.email_model import EmailModel
from app.models.formatter_model import FormatterModel
from app.models.material_repository import MaterialRepository
from app.models.settings_model import SettingsModel
from app.services.update_checker import check_for_updates
from app.translations.translations import LANGUAGES
from app.version import APP_NAME, APP_VERSION
from app.viewmodels.main_view_model import MainViewModel
from app.viewmodels.materials_view_model import MaterialsViewModel
from app.views.add_material_frame import AddMaterialFrame
from app.views.burn_table_frame import BurnTableFrame
from app.views.main_frame import MainFrame
from app.views.materials_frame import MaterialsFrame
from app.views.settings_frame import SettingsFrame


class App(ctk.CTk):
    "Main application class for NCRenamer"

    def __init__(self):
        super().__init__()
        self.settings_model = SettingsModel()
        self.email_model = EmailModel()
        self.material_repo = MaterialRepository()
        self.formatter_model = FormatterModel(self.material_repo)

        self.settings_model.load()

        self.current_language_code = self.settings_model.settings.get("language", "cs")
        self.texts = LANGUAGES[self.current_language_code]
        self.materials_view_model = MaterialsViewModel(
            app_instance=self,
            repo=self.material_repo,
            texts=self.texts,
        )

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("350x600")

        ctk.set_appearance_mode(
            self.settings_model.settings.get("appearance_mode", "System")
        )

        folder = os.path.dirname(self.settings_model.path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        self.main_frame = MainFrame(
            master=self,
            texts=self.texts,
            app_instance=self,
            viewmodel=None,
        )

        self.main_view_model = MainViewModel(
            email_model=self.email_model,
            formatter_model=self.formatter_model,
        )

        self.main_frame.vm = self.main_view_model
        self.main_frame.post_init()
        self.main_frame.pack(fill="both", expand=True)

        self.settings_frame = SettingsFrame(
            master=self,
            app_instance=self,
            app_settings=self.settings_model,
            texts=self.texts,
        )

        self.materials_frame = MaterialsFrame(
            master=self,
            app_instance=self,
            view_model=self.materials_view_model,
            texts=self.texts,
        )

        self.add_material_frame = AddMaterialFrame(
            master=self,
            view_model=self.materials_view_model,
            app_instance=self,
            texts=self.texts,
        )

        self.vm_steel = create_burn_view_model(
            texts=self.texts, sheet_index=0,
            sheet_name="Ocel", settings_key="last_table_path",
        )
        self.vm_aluminium = create_burn_view_model(
            texts=self.texts, sheet_index=1,
            sheet_name="Hliník", settings_key="last_table_path_alu",
        )
        self.burn_table_frame = BurnTableFrame(
            master=self,
            app_instance=self,
            vm_steel=self.vm_steel,
            vm_aluminium=self.vm_aluminium,
            texts=self.texts,
        )

        self.show_main_content()
        self.vm_steel.load_last_table()
        self.vm_aluminium.load_last_table()

        self._update_check_in_progress = False

        # update check po startu aplikace
        self.after(2000, self.start_update_check)

    def set_language(self, lang_code: str):
        if self.current_language_code != lang_code:
            self.current_language_code = lang_code
            self.texts = LANGUAGES[lang_code]
            self.settings_model.set("language", lang_code)
            self.settings_model.save()

            self.title(self.texts.get("app_title", "NC Renamer"))
            self.materials_view_model.update_texts(self.texts)
            self.vm_steel.update_texts(self.texts)
            self.vm_aluminium.update_texts(self.texts)
            self.main_frame.update_texts(self.texts)
            self.settings_frame.update_texts(self.texts)
            self.materials_frame.update_texts(self.texts)
            self.add_material_frame.update_texts(self.texts)
            self.burn_table_frame.update_texts(self.texts)

    def show_main_content(self):
        self._hide_all_frames()
        self.geometry("350x600")
        self.main_frame.pack(fill="both", expand=True)

    def show_burn_table_content(self):
        self._hide_all_frames()
        self.geometry("1100x650")
        self.burn_table_frame.pack(fill="both", expand=True)

    def show_settings_content(self):
        self._hide_all_frames()
        self.settings_frame.pack(fill="both", expand=True)

    def show_materials_content(self):
        self._hide_all_frames()
        # get loaded CSV directly
        processed_content = self.materials_view_model.get_materials()
        self.materials_frame.update_treeview_display(processed_content)
        self.materials_frame.pack(fill="both", expand=True)

    def show_add_materials_content(self):
        self._hide_all_frames()
        self.add_material_frame.pack(fill="both", expand=True)

    def _hide_all_frames(self):
        for frame in (
            self.main_frame,
            self.settings_frame,
            self.materials_frame,
            self.add_material_frame,
            self.burn_table_frame,
        ):
            frame.pack_forget()

    def start_update_check(self):
        if self._update_check_in_progress:
            return

        self._update_check_in_progress = True
        threading.Thread(target=self.check_updates, daemon=True).start()

    def check_updates(self):
        try:
            update_available, url = check_for_updates()
        except Exception:
            update_available, url = False, None
        finally:
            self.after(0, self._finish_update_check, update_available, url)

    def _finish_update_check(self, update_available, url):
        self._update_check_in_progress = False
        if update_available:
            webbrowser.open(url)


if __name__ == "__main__":
    app = App()
    app.mainloop()
