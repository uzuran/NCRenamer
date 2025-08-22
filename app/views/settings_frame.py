import customtkinter as ctk
from PIL import Image
from app.viewmodels.password_view_model import PasswordViewModel
from app.models.password_model import PasswordModel
from app.services.settings_service import CORRECT_PASSWORD

from translations import LANGUAGE_NAMES
from ..viewmodels.settings_view_model import SettingsViewModel


class SettingsFrame(ctk.CTkFrame):
    def __init__(
        self,
        master=None,
        app_instance=None,
        app_settings=None,
        main_frame_instance=None,
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
            command=self._change_mode_and_save,
            width=100,
            height=30,
            fg_color="white",
        )
        self.color_button.pack(pady=10, padx=25)
        self._update_button_icon()

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
            fg_color="white",
            width=100,
            height=38,
            command=self.password_vm.prompt_for_password_and_reset,
        )
        self.reset_counter_btn.pack(pady=(20, 10))
        
        self.close_button = ctk.CTkButton(
            self,
            text=self.texts.get("back_button", "Back"),
            fg_color="white",
            text_color="black",
            command=self.return_to_main_content,
        )
        self.close_button.pack(pady=10, padx=25, fill="x", side="bottom")

    def update_texts(self, new_texts: dict):
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

    def _change_mode_and_save(self):
        if self.viewmodel:
            new_mode = self.viewmodel.toggle_appearance_mode()
            self._update_button_icon()

    def _update_button_icon(self):
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark":
            self.color_button.configure(image=self.light_icon, text="")
        else:
            self.color_button.configure(image=self.dark_icon, text="")

    def change_language(self, new_lang_display_name: str):
        if self.viewmodel:
            self.viewmodel.change_language(new_lang_display_name)

    def return_to_main_content(self):
        if self.app_instance:
            self.app_instance.show_main_content()