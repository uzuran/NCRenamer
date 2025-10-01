"""Service for managing application settings."""

from tkinter import messagebox
import customtkinter as ctk
from app.models.settings_model import AppSettingsModel

CORRECT_PASSWORD = "amada"


class SettingsService:
    """Service for managing application settings."""    
    def __init__(self, model: AppSettingsModel, main_frame_instance=None):
        self.model = model
        self.main_frame_instance = main_frame_instance
        self.model.load()

    def load_app_settings(self):
        """Load application settings from the model."""
        try:
            self.model.load()
        except Exception as e:
            messagebox.showerror(
                title="Chyba při načítání",
                message=f"Nastala chyba při načítání nastavení: {e}"
            )

    def save_app_settings(self) -> None:
        """Save application settings using the model."""
        try:
            self.model.save()
        except IOError as e:
            messagebox.showerror(
                title="Chyba při ukládání",
                message=f"Došlo k chybě při ukládání nastavení: {e}"
            )
