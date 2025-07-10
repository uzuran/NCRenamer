from pathlib import Path
from tkinter import messagebox
import time
import webbrowser
import urllib.parse
from PIL import Image
from rich.console import Console
import customtkinter as ctk
from customtkinter import filedialog
from nc_formatter import NcFormatter
from email_bug_tracker import EmailBugTracker
from settings import Settings


cons: Console = Console()


class Utils:
    def __init__(self, parent: ctk.CTk) -> None:
        self.parent = parent

    @staticmethod
    def set_appearance(theme: str = "system") -> None:
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)

    def center_window(self, width: int, height: int) -> None:
        self.parent.update_idletasks()
        x = (self.parent.winfo_screenwidth() - width) // 2
        y = (self.parent.winfo_screenheight() - height) // 2
        self.parent.geometry(f"{width}x{height}+{x}+{y}")

    def configure_app(self, title: str, width: int, height: int) -> None:
        self.parent.title(title)
        self.center_window(width, height)
        self.parent.minsize(width, height)
        self.parent.resizable(False, False)

    def shutdown_app(self) -> None:
        self.parent.destroy()


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.utils: Utils = Utils(self)
        self.formatter: NcFormatter = NcFormatter()
        self.email: EmailBugTracker = EmailBugTracker()

        self.app_settings: Settings = Settings()

        ctk.set_appearance_mode(
            self.app_settings.settings.get("appearance_mode", "System")
        )

        self.main_frame: MainFrame = MainFrame(
            master=self,
            formatter=self.formatter,
            email=self.email,
            app_instance=self,
        )
        # Instance SettingsFrame, která bude přepínána
        self.settings_frame: SettingsFrame = SettingsFrame(
            master=self, app_instance=self, main_frame_instance=self.main_frame
        )

        self.utils.configure_app("NCRenamer", 400, 400)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Na začátku zobrazíme hlavní rámec
        self.show_main_content()

    def show_main_content(self) -> None:
        self.settings_frame.grid_forget()
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    def show_settings_content(self) -> None:
        self.main_frame.grid_forget()
        self.settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")


class MainFrame(ctk.CTkFrame):
    def __init__(self, master, formatter, app_instance, email, **kwargs):
        super().__init__(master, **kwargs)

        self.formatter = formatter
        self.email = email
        self.app_instance = app_instance
        self.file_list = []
        # self.settings_window = None # Tuto proměnnou už nepotřebujeme
        self.settings_icon = ctk.CTkImage(Image.open("setting.png"), size=(24, 24))
        self.settings_btn = ctk.CTkButton(
            self,
            image=self.settings_icon,
            text="",
            command=self.open_settings_window,
            fg_color="white",
            width=30,
        )
        self.settings_btn.pack(pady=(10, 10), padx=20, side="top", anchor="ne")

        self.email_counter_label = ctk.CTkLabel(
            self, text=f"Počet hlášení chyb: {self.email.email_counter}"
        )
        self.email_counter_label.pack(pady=(0, 10))

        self.count_label = ctk.CTkLabel(self, text="Vybráno: 0 souborů")
        self.count_label.pack(pady=(0, 10))

        self.select_btn = ctk.CTkButton(
            self, text="Select NC files", command=self.select_files
        )
        self.select_btn.pack(pady=(10, 0))
        self.progressbar = ctk.CTkProgressBar(self)
        self.progressbar.pack(pady=(10, 10), fill="x", padx=20)
        self.progressbar.configure(corner_radius=5)
        self.progressbar.set(0)
        self.rename_btn = ctk.CTkButton(
            self, text="Rename NC files", command=self.rename_files
        )
        self.rename_btn.pack(pady=(0, 10))
        self.reportbug_btn = ctk.CTkButton(
            self, text="Report Bug", command=self.set_email
        )
        self.reportbug_btn.pack(pady=(0, 10))
        self.output_label = ctk.CTkLabel(self, text="Renamed NCs", anchor="w")
        self.output_label.pack(pady=0, padx=25, fill="x")

        self.output_box = ctk.CTkTextbox(self)
        self.output_box.pack(padx=20, pady=(0, 10), fill="both", expand=True)
        self.output_box.configure(state="disabled")

    def reset_email_counter(self) -> None:
        self.email.email_counter = 0
        self.email.save_counter()
        self.email_counter_label.configure(
            text=f"Počet hlášení chyb: {self.email.email_counter}"
        )
        messagebox.showinfo(
            title="Počítadlo resetováno",
            message="Počítadlo hlášení chyb bylo resetováno na 0.",
        )

    def select_files(self):
        file_paths = filedialog.askopenfilenames(
            title="Vyberte NC soubory",
            filetypes=[("NC soubory", "*.NC"), ("Všechny soubory", "*.*")],
        )

        self.file_list = [Path(f) for f in file_paths]
        self.count_label.configure(text=f"Vybráno: {len(self.file_list)} souborů")

    def rename_files(self):
        total = len(self.file_list)
        if total == 0:
            print("Žádné soubory k přejmenování.")
            return

        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")

        for i, file in enumerate(self.file_list, start=1):
            time.sleep(0.25)
            changed = self.formatter.process_file(file)

            if changed:
                self.output_box.insert("end", f"✅ Upraveno: {file.name}\n")
            else:
                self.output_box.insert("end", f"✔️ Bez změny: {file.name}\n")

            self.progressbar.set(i / total)
            self.update_idletasks()

        self.output_box.configure(state="disabled")

        messagebox.showinfo(
            title="Hotovo",
            message=f"Zpracování dokončeno.\nCelkem souborů: {len(self.file_list)}",
        )

    def set_email(self):
        self.email.email_counter += 1
        self.email.save_counter()
        self.email_counter_label.configure(
            text=f"Počet hlášení chyb: {self.email.email_counter}"
        )

        recipient_email = "else.artem@gmail.com"
        subject = f"Report bug_{self.email.email_counter}"

        mailto_url = f"mailto:{recipient_email}?subject={urllib.parse.quote(subject)}"

        try:
            webbrowser.open(mailto_url)
        except webbrowser.Error as e:
            cons.print(f"[red]Nepodařilo se otevřít e-mailového klienta: {e}[/red]")
            messagebox.showerror(
                title="Chyba",
                message="Nepodařilo se otevřít výchozí e-mailový klient. Ujistěte se, že máte nějaký nastavený.",
            )

    def open_settings_window(self):
        self.app_instance.show_settings_content()


class SettingsFrame(ctk.CTkFrame):  # Změna z CTkToplevel na CTkFrame
    def __init__(
        self, master=None, app_instance=None, main_frame_instance=None, **kwargs
    ):
        super().__init__(master, **kwargs)
        # Odstraněny Toplevel-specifické řádky: title, geometry, transient, protocol

        self.app_instance = app_instance
        self.main_frame_instance = main_frame_instance

        self.setting_label = ctk.CTkLabel(self, text="Změnit režim vzhledu", anchor="w")
        self.setting_label.pack(pady=0, padx=25)

        self.light_icon = ctk.CTkImage(Image.open("light-mode.png"), size=(34, 34))
        self.dark_icon = ctk.CTkImage(Image.open("night-mode.png"), size=(34, 34))

        self.restart_icon = ctk.CTkImage(Image.open("restart.png"), size=(24, 24))

        self.color_button = ctk.CTkButton(
            self,
            text="",
            image=self.light_icon,
            command=self._change_mode_and_save,
            width=100,
            height=30,
            fg_color="white",
        )
        self.color_button.pack(pady=10, padx=25)
        self._update_button_icon()

        self.reset_counter_btn = ctk.CTkButton(
            self,
            image=self.restart_icon,
            text="",
            fg_color="white",
            width=100,
            height=38,
            command=self._prompt_for_password_and_reset,
        )
        self.reset_counter_btn.pack(pady=(20, 10))

        self.close_button = ctk.CTkButton(
            self,
            text="Zavřít",
            fg_color="white",
            text_color="black",
            command=self.return_to_main_content,  # Změna na metodu pro návrat
        )
        self.close_button.pack(pady=10, padx=25, fill="x", side="bottom")

    def _change_mode_and_save(self):
        current_mode = ctk.get_appearance_mode()
        new_mode = "Light" if current_mode == "Dark" else "Dark"

        ctk.set_appearance_mode(new_mode)

        if self.app_instance:
            self.app_instance.app_settings.settings["appearance_mode"] = new_mode
            self.app_instance.app_settings.save_app_settings()

        self._update_button_icon()

    def _update_button_icon(self):
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark":
            self.color_button.configure(image=self.light_icon, text="")
        else:
            self.color_button.configure(image=self.dark_icon, text="")

    def _prompt_for_password_and_reset(self) -> None:
        entered_password = ctk.CTkInputDialog(
            text="Zadejte heslo pro resetování počítadla:", title="Vyžadováno heslo"
        ).get_input()

        CORRECT_PASSWORD = "aejkvhl68"

        if entered_password is None:
            return

        if entered_password == CORRECT_PASSWORD:
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

    def return_to_main_content(self):  # Nová metoda pro návrat do hlavního obsahu
        if self.app_instance:
            self.app_instance.show_main_content()


if __name__ == "__main__":
    # Zajištění existence souborů ikon pro testování
    # Vytvoří zástupné šedé obrázky, pokud soubory neexistují.
    for icon_name in ["light-mode.png", "night-mode.png", "restart.png"]:
        if not Path(icon_name).exists():
            try:
                Image.new("RGB", (34, 34), color="gray").save(icon_name)
            except ImportError:
                print(
                    f"Chyba: Pillow není nainstalován. Nelze vytvořit zástupný soubor '{icon_name}'."
                )

    app: App = App()
    app.mainloop()
