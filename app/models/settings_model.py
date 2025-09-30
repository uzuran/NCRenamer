import json
import os

class AppSettings:
    def __init__(self, settings_file="json/app_settings.json"):
        self.settings_file = settings_file
        self.settings = {}
        self.load_app_settings()

    def load_app_settings(self) -> None:
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, KeyError):
                self.settings = {}
        else:
            self.settings = {}

    def save_app_settings(self) -> None:
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4)