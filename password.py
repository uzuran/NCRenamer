
import customtkinter as ctk
from tkinter import messagebox
from settings import CORRECT_PASSWORD 

class PasswordManager:
    def __init__(self, main_frame_instance):
        
        self.main_frame_instance = main_frame_instance

    def prompt_for_password_and_reset(self) -> None:
        
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