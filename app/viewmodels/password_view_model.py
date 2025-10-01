import customtkinter as ctk
from tkinter import messagebox
from app.models.password_model import PasswordModel
from app.viewmodels.main_view_model import MainViewModel


class PasswordViewModel:
    def __init__(self, main_view_model: MainViewModel, password_model: PasswordModel):
        self.main_view_model = main_view_model
        self.password_model = password_model

    def prompt_for_password_and_reset(self) -> None:
        entered_password = ctk.CTkInputDialog(
            text="Zadejte heslo pro resetování počítadla:", title="Vyžadováno heslo"
            
        ).get_input()

        if self.password_model.verify_password(entered_password):
            self.main_view_model.reset_email_counter()
            
    
            self.main_view_model.update_email_counter_label()
            
            messagebox.showinfo("Úspěch", "Počítadlo bylo resetováno.")
        else:
            messagebox.showerror("Chybné heslo", "Zadané heslo je nesprávné.")