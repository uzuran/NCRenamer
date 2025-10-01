import json
import os

class AppSettingsModel:
    """Model for managing application settings stored in a JSON file."""
    def __init__(self, settings_file="json/app_settings.json"):
        self.settings_file = settings_file
        self.settings = {}

    def load(self):
        """Load settings from the JSON file."""
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r", encoding="utf-8") as f:
                self.settings = json.load(f)
        else:
            self.settings = {}

    def save(self):
        """Save settings to the JSON file."""
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4)

    def reset_email_counter(self):
        """Reset the email counter in settings to zero."""
        if "email_counter" in self.settings:
            self.settings["email_counter"] = 0
        else:
            raise KeyError("email_counter not found in settings")