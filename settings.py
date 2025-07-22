import os
import json
from rich.console import Console
CORRECT_PASSWORD = "aejkvhl68"
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

    def _prompt_for_password_and_reset(self) -> None:
        entered_password = ctk.CTkInputDialog(
            text="Zadejte heslo pro resetování počítadla:", title="Vyžadováno heslo"
        ).get_input()


        if entered_password is None:
            return

        if entered_password == CORRECT_PASSWORD:
            if self.main_frame_instance:
                self.main_frame_instance._reset_email_counter()
                messagebox.showinfo("Úspěch", "Počítadlo bylo resetováno.")
            else:
                messagebox.showerror(
                    "Chyba",
                    "Nelze resetovat počítadlo. Instance MainFrame není k dispozici.",
                )
        else:
            messagebox.showerror("Chybné heslo", "Zadané heslo je nesprávné.")