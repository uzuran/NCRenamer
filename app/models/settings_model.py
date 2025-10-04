import json
import os

class SettingsModel:
    """
    Model for storing and managing application settings.

    Handles loading and saving settings from a JSON file, and provides
    access to appearance mode, language code, and other configuration values.

    Attributes:
        path (str): Path to the settings JSON file.
        settings (dict): Dictionary containing the loaded settings.
    """

    def __init__(self, path="resources/app_settings.json"):
        self.path = path
        self.settings = {}

    def load(self):
        """
        Load settings from the JSON file.

        If the file does not exist or is invalid, initializes with defaults.
        """
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.settings = {}
        else:
            self.settings = {}

    def save(self):
        """
        Save the current settings to the JSON file.

        Creates the directory if it does not exist.
        """
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4)

    def get(self, key: str, default=None):
        """
        Retrieve a setting value.

        Args:
            key (str): The setting key.
            default (Any): Default value if key is not found.

        Returns:
            Any: The value of the setting or the default.
        """
        return self.settings.get(key, default)

    def set(self, key: str, value):
        """
        Update a setting value and persist it.

        Args:
            key (str): The setting key.
            value (Any): The new value to set.
        """
        self.settings[key] = value
        self.save()