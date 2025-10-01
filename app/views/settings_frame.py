"""A frame for application settings, including appearance mode and language selection."""

import customtkinter as ctk
from PIL import Image
from app.viewmodels.password_view_model import PasswordViewModel
from app.models.password_model import PasswordModel
from app.services.settings_service import CORRECT_PASSWORD

from app.translations.translations import LANGUAGE_NAMES
from ..viewmodels.settings_view_model import SettingsViewModel


class SettingsFrame(ctk.CTkFrame):
    """A frame for application settings, including appearance mode and language selection."""
    def __init__(
        self,
        master=None,
        app_instance=None,
        app_settings=None,
        texts=None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.app_instance = app_instance
        self.texts = texts or {}
        self.viewmodel = None
        if app_instance:
            self.viewmodel = SettingsViewModel(app_instance, app_settings)

        self.password_vm = PasswordViewModel(
        main_view_model=self.app_instance.main_viewmodel if self.app_instance else None,
        password_model=PasswordModel(CORRECT_PASSWORD),
)

        self.setting_label = ctk.CTkLabel(
            self, text=self.texts.get("appearance_mode_setting", "Appearance Mode"), anchor="w"
        )
        self.setting_label.pack(pady=0, padx=25)

        self.light_icon = ctk.CTkImage(Image.open("img/light-mode.png"), size=(34, 34))
        self.dark_icon = ctk.CTkImage(Image.open("img/night-mode.png"), size=(34, 34))
        self.restart_icon = ctk.CTkImage(Image.open("img/restart.png"), size=(24, 24))

        self.color_button = ctk.CTkButton(
            self,
            text="",
            image=self.light_icon,
            command=self.change_mode_and_save,
            width=100,
            height=30,
        )
        self.color_button.pack(pady=10, padx=25)
        self.update_button_icon()

        self.language_label = ctk.CTkLabel(
            self, text=self.texts.get("language_setting", "Language"), anchor="w"
        )
        self.language_label.pack(pady=(20, 0), padx=25)

        self.language_optionmenu = ctk.CTkOptionMenu(
            self, values=list(LANGUAGE_NAMES.keys()), command=self.change_language
        )
        current_lang_name = (
            self.viewmodel.get_current_language_name(LANGUAGE_NAMES)
            if self.viewmodel
            else "Czech"
        )
        self.language_optionmenu.set(current_lang_name)
        self.language_optionmenu.pack(pady=10, padx=25)

        self.reset_counter_btn = ctk.CTkButton(
            self,
            image=self.restart_icon,
            text="",
            width=100,
            height=38,
            command=self.password_vm.prompt_for_password_and_reset,
        )
        self.reset_counter_btn.pack(pady=(20, 10))
        
        self.close_button = ctk.CTkButton(
            self,
            text=self.texts.get("back_button", "Back"),
            text_color="black",
            command=self.return_to_main_content,
        )
        self.close_button.pack(pady=10, padx=25, fill="x", side="bottom")

    def update_texts(self, new_texts: dict):
        """Update the texts in the settings frame."""
        self.texts = new_texts
        self.setting_label.configure(
            text=self.texts.get("appearance_mode_setting", "Appearance Mode")
        )
        self.language_label.configure(
            text=self.texts.get("language_setting", "Language")
        )
        self.close_button.configure(text=self.texts.get("back_button", "Back"))
        current_lang_name = (
            self.viewmodel.get_current_language_name(LANGUAGE_NAMES)
            if self.viewmodel
            else "Czech"
        )
        self.language_optionmenu.set(current_lang_name)

    def change_mode_and_save(self):
        """Toggle between light and dark mode and save the preference."""
        if self.viewmodel:
            self.viewmodel.toggle_appearance_mode()
            self.update_button_icon()

    def update_button_icon(self):
        """Update the icon of the appearance mode button based on the current mode."""
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark":
            self.color_button.configure(image=self.light_icon, text="")
        else:
            self.color_button.configure(image=self.dark_icon, text="")

    def change_language(self, new_lang_display_name: str):
        """Change the application language."""
        if self.viewmodel:
            self.viewmodel.change_language(new_lang_display_name)

    def return_to_main_content(self):
        """Return to the main content frame."""
        if self.app_instance:
            self.app_instance.show_main_content()