"""Password ViewModel Module"""

from tkinter import messagebox
import customtkinter as ctk
from app.models.password_model import PasswordModel  # import the model


class PasswordViewModel: # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
    def __init__(self, main_frame_instance, password_model: PasswordModel):
        self.main_frame_instance = main_frame_instance
        self.password_model = password_model

    def prompt_for_password_and_reset(self) -> None: # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        entered_password = ctk.CTkInputDialog(
            text="Zadejte heslo pro resetování počítadla:", title="Vyžadováno heslo"
        ).get_input()

        if entered_password is None:
            return

        if self.password_model.verify_password(entered_password):
            if self.main_frame_instance:
                self.main_frame_instance.reset_email_counter()
                messagebox.showinfo("Úspěch", "Počítadlo bylo resetováno.")
            else:
                messagebox.showerror(
                    "Chyba",
                    "Nelze resetovat počítadlo. Instance MainFrame není k dispozici.",
                )
        else:
            messagebox.showerror("Chybné heslo", "Zadané heslo je nesprávné.")
