import customtkinter as ctk
from tkinter import messagebox
from app.models.password_model import PasswordModel
from app.viewmodels.main_view_model import MainViewModel


class PasswordViewModel:
    def __init__(self, main_view_model: MainViewModel, password_model: PasswordModel, texts=None):
        self.main_view_model = main_view_model
        self.password_model = password_model
        self.texts = texts or {}

    def update_texts(self, texts: dict):
        """Store current UI texts for translated dialogs."""
        self.texts = texts or {}

    def prompt_for_password_and_reset(self) -> None:
        entered_password = ctk.CTkInputDialog(
            text=self.texts.get("password_prompt", "Enter password to reset counter."),
            title=self.texts.get("password_required_title", "Password required"),
        ).get_input()

        if self.password_model.verify_password(entered_password):
            self.main_view_model.reset_email_counter()
            self.main_view_model.update_email_counter_label()

            messagebox.showinfo(
                self.texts.get("password_success_title", "Success"),
                self.texts.get("password_success_message", "Counter has been reset."),
            )
        else:
            messagebox.showerror(
                self.texts.get("password_incorrect_title", "Wrong password"),
                self.texts.get("password_incorrect", "Incorrect password!"),
            )
