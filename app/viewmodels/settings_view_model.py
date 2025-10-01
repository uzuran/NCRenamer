"""ViewModel for managing application settings and interactions."""

import customtkinter as ctk
from app.translations.translations import LANGUAGE_NAMES



class SettingsViewModel:
    """ViewModel for managing application settings and interactions."""
    def __init__(self, app_instance, app_settings):
        self.app = app_instance
        self.app_settings = app_settings

    def toggle_appearance_mode(self):
        """Toggle between Light and Dark appearance modes."""
        current_mode = ctk.get_appearance_mode()
        new_mode = "Light" if current_mode == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        if self.app:
            self.app_settings.model.settings["appearance_mode"] = new_mode
            self.app_settings.save_app_settings()
        return new_mode

    def get_current_language_name(self, language_names: dict) -> str:
        """Get the display name of the current language."""
        code = self.app.current_language_code
        for name, lang_code in language_names.items():
            if lang_code == code:
                return name
        return "Czech"

    def change_language(self, new_lang_display_name: str):
        """Change the application's language based on the display name."""
        new_lang_code = LANGUAGE_NAMES.get(new_lang_display_name)
        if new_lang_code:
            self.app.set_language(new_lang_code)
