import os
import json
from rich.console import Console

cons: Console = Console()

class Settings:
    """This is settings for the application."""

    def __init__(self):
        """Initialize the settings."""
        self.settings_file = "app_settings.json"
        self.settings: dict[str, object] = {}
        self.load_app_settings()

    def load_app_settings(self) -> None:
        """Load the application settings from a JSON file."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, KeyError) as e:
                cons.print(
                    f"[red]Chyba při načítání nastavení ze souboru: {e}. Používám výchozí nastavení.[/red]"
                )
                self.settings = {}
        else:
            self.settings = {}

    def save_app_settings(self) -> None:
        """Save the application settings to a JSON file."""
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            cons.print(f"[red]Chyba při ukládání nastavení do souboru: {e}[/red]")

