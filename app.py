import os
import customtkinter as ctk

from app.models.email_model import EmailModel
from app.models.formatter_model import FormatterModel
from app.viewmodels.main_view_model import MainViewModel
from app.views.main_frame import MainFrame
from app.views.settings_frame import SettingsFrame

from app.translations.translations import LANGUAGES
from app.views.materials_frame import MaterialsFrame
from app.viewmodels.materials_view_model import MaterialsViewModel

from app.models.settings_model import SettingsModel


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        model = SettingsModel()  
        self.settings_model = model

        self.email_model = EmailModel()
        self.formatter_model = FormatterModel()

        self.settings_model.load()

        self.current_language_code = self.settings_model.settings.get("language", "cs")
        self.texts = LANGUAGES[self.current_language_code]

        self.title(self.texts.get("app_title", "NC Renamer"))
        self.geometry("400x500")

        ctk.set_appearance_mode(self.settings_model.settings.get("appearance_mode", "System"))

        folder = os.path.dirname(self.settings_model.path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        
        self.main_frame = MainFrame(
            master=self,
            texts=self.texts,
            app_instance=self,
            viewmodel=None, 
        )

        self.main_viewmodel = MainViewModel(
            main_frame_instance=self.main_frame,
            email_model=self.email_model,
            formatter_model=self.formatter_model
        )
        
        self.main_frame.vm = self.main_viewmodel
        self.main_frame.post_init()
        self.main_frame.pack(fill="both", expand=True)

        self.settings_frame = SettingsFrame(
            master=self,
            app_instance=self,
            app_settings=self.settings_model,
            texts=self.texts,
        )

        # Musíte předat ViewModel, aby měl materials_frame přístup k datům
        self.materials_viewmodel = MaterialsViewModel()
        self.materials_frame = MaterialsFrame(
            master=self,
            app_instance=self,
            viewmodel=self.materials_viewmodel,
        )

        self.show_main_content()

    def set_language(self, lang_code: str):
        if self.current_language_code != lang_code:
            self.current_language_code = lang_code
            self.texts = LANGUAGES[lang_code]
            self.settings_model.set("language", lang_code)
            self.settings_model.save()

            self.title(self.texts.get("app_title", "NC Renamer"))
            self.main_frame.update_texts(self.texts)
            self.settings_frame.update_texts(self.texts)
            self.materials_frame.update_texts(self.texts)

    def show_main_content(self):
        
        self._hide_all_frames()
        self.main_frame.pack(fill="both", expand=True)

    def show_settings_content(self):
        self._hide_all_frames()
        self.settings_frame.pack(fill="both", expand=True)

    def show_materials_content(self):
        self._hide_all_frames()
        # Získání obsahu od MainViewModel
        # Předpokládejme, že MainViewModel má metodu get_processed_history()
        processed_content = self.main_viewmodel.get_processed_history() 

        # Aktualizace MaterialsFrame s daty z ViewModel
        self.materials_frame.update_output_content(processed_content)

        self.materials_frame.pack(fill="both", expand=True)
        
    def _hide_all_frames(self):
        for frame in (self.main_frame, self.settings_frame, self.materials_frame):
            frame.pack_forget()


if __name__ == "__main__":
    app = App()
    app.mainloop()