import customtkinter as ctk

class SettingsViewModel: # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
    def __init__(self, app_instance):
        self.app = app_instance

    def toggle_appearance_mode(self): # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        current_mode = ctk.get_appearance_mode()
        new_mode = "Light" if current_mode == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        # Save in app settings
        if self.app:
            self.app.app_settings.settings["appearance_mode"] = new_mode
            self.app.app_settings.save_settings()
        return new_mode

    def get_current_language_name(self, language_names: dict) -> str: # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        # Find display name by current language code
        code = getattr(self.app, "current_language_code", "cs")
        for name, lang_code in language_names.items():
            if lang_code == code:
                return name
        return "Czech"  # default fallback

    def change_language(self, lang_display_name: str, language_names: dict): # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        new_lang_code = language_names.get(lang_display_name)
        if new_lang_code and self.app:
            self.app.set_language(new_lang_code)
