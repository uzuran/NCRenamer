import os
import json
from rich.console import Console
import customtkinter as ctk
from tkinter import messagebox 


CORRECT_PASSWORD = "amada"
cons: Console = Console()


class SettingsService:
    """This is settings for the application."""

    def __init__(self, main_frame_instance=None):
        """Initialize the settings."""
        self.settings_file = "app_settings.json"
        self.settings: dict[str, object] = {}
        self.main_frame_instance = main_frame_instance  
        self.load_app_settings()

    def load_app_settings(self) -> None:
        """Load the application settings from a JSON file."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, KeyError) as e:
             messagebox.showerror(
                title="Settings Error",
                message=f"Error loading settings from file: {e}. Using default settings."
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
         messagebox.showerror(
            title="Chyba při ukládání",
            message=f"Došlo k chybě při ukládání nastavení: {e}"
        )

    def _prompt_for_password_and_reset(self) -> None:
        """Prompt for password and reset the email counter if correct."""
        entered_password = ctk.CTkInputDialog(
            text="Zadejte heslo pro resetování počítadla:", title="Vyžadováno heslo"
        ).get_input()

        if entered_password is None:
            return

        if entered_password == CORRECT_PASSWORD:
            if self.main_frame_instance and hasattr(
                self.main_frame_instance, "reset_email_counter"
            ):
                self.main_frame_instance.reset_email_counter()
                messagebox.showinfo("Úspěch", "Počítadlo bylo resetováno.")
            else:
                messagebox.showerror(
                    "Chyba",
                    "Nelze resetovat počítadlo. Instance MainFrame není k dispozici nebo chybí metoda.",
                )
        else:
            messagebox.showerror("Chybné heslo", "Zadané heslo je nesprávné.")
