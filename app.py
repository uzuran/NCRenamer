from pathlib import Path
from tkinter import messagebox
import time
import webbrowser
import urllib.parse
from PIL import Image
from rich.console import Console
import customtkinter as ctk
from customtkinter import filedialog
import json 

from nc_formatter import NcFormatter
from email_bug_tracker import EmailBugTracker
from settings import Settings, CORRECT_PASSWORD 
from password import PasswordManager 
from translations import LANGUAGES, LANGUAGE_NAMES # Importujeme slovníky jazyků

cons: Console = Console()

HISTORY_FILE = "history.json"


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
        
        # Překlad aplikace do zvoleného jazyka - čeština je výchozí
        self.current_language_code = self.app_settings.settings.get("language", "cs")
        self.texts = LANGUAGES[self.current_language_code] 

        ctk.set_appearance_mode(self.app_settings.settings.get("appearance_mode", "System"))

        self.main_frame: MainFrame = MainFrame(
            master=self, formatter=self.formatter, email=self.email, app_instance=self, texts=self.texts
        )
        self.settings_frame: SettingsFrame = SettingsFrame(
            master=self, app_instance=self, main_frame_instance=self.main_frame, texts=self.texts
        )
        self.materials_frame: MaterialsFrame = MaterialsFrame(
            master=self, app_instance=self, main_frame_instance=self.main_frame, texts=self.texts
        )

        self.utils.configure_app(self.texts["app_title"], 400, 400) 
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.show_main_content()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """Metoda volaná při zavírání okna aplikace pro uložení historie."""
        if self.main_frame:
            self.main_frame.save_history()
        self.destroy()

    def set_language(self, lang_code: str):
        """Nastaví nový jazyk a aktualizuje všechny texty v aplikaci."""
        if self.current_language_code != lang_code:
            self.current_language_code = lang_code
            self.texts = LANGUAGES[lang_code]
            self.app_settings.settings["language"] = lang_code
            self.app_settings.save_app_settings()

          
            self.utils.configure_app(self.texts["app_title"], 400, 400)

            # Texty se aktualizují ve všech frames
            self.main_frame.update_texts(self.texts)
            self.settings_frame.update_texts(self.texts)
            self.materials_frame.update_texts(self.texts)


    def show_main_content(self) -> None:
        self.settings_frame.grid_forget()
        self.materials_frame.grid_forget()
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    def show_settings_content(self) -> None:
        self.main_frame.grid_forget()
        self.settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    def show_materials_content(self, content: str = "") -> None:
        self.main_frame.grid_forget()
        self.settings_frame.grid_forget() 
        self.materials_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.materials_frame.update_output_content(content) 

    


class MainFrame(ctk.CTkFrame):
    def __init__(self, master, formatter, app_instance, email, texts, **kwargs):
        super().__init__(master, **kwargs)

        self.formatter = formatter
        self.email = email
        self.app_instance = app_instance
        self.texts = texts 
        self.file_list = []
        self.processed_files_history = self.load_history() 

        self.settings_icon = ctk.CTkImage(Image.open("setting.png"), size=(24, 24))
        self.settings_btn = ctk.CTkButton(
            self, image=self.settings_icon, text="", command=self.open_settings_window, fg_color="white", width=30
        )
        self.settings_btn.pack(pady=(10, 10), padx=20, side="right", anchor="ne")

        self.history_icon = ctk.CTkImage(Image.open("box.png"), size=(24, 24))
        self.history_materials_btn = ctk.CTkButton(
            self,image=self.history_icon, text="", command=self.show_processed_materials_history, fg_color="white", width=30
        )
        self.history_materials_btn.pack(pady=(10, 10), padx=10, side="left", anchor="nw")
       
        self.email_counter_label = ctk.CTkLabel(self, text=self.texts["email_count"].format(self.email.email_counter))
        self.email_counter_label.pack(pady=(0, 10))

        self.count_label = ctk.CTkLabel(self, text=self.texts["selected_files"].format(0))
        self.count_label.pack(pady=(0, 10))

        self.select_btn = ctk.CTkButton(
            self, text=self.texts["select_nc_files"], command=self.select_files
        )
        self.select_btn.pack(pady=(10, 0))
        self.progressbar = ctk.CTkProgressBar(self)
        self.progressbar.pack(pady=(10, 10), fill="x", padx=20)
        self.progressbar.configure(corner_radius=5)
        self.progressbar.set(0)
        self.rename_btn = ctk.CTkButton(
            self, text=self.texts["rename_nc_files"], command=self.rename_files
        )
        self.rename_btn.pack(pady=(0, 10))
        self.reportbug_btn = ctk.CTkButton(
            self, text=self.texts["report_bug"], command=self.set_email
        )
        self.reportbug_btn.pack(pady=(0, 10))
        self.output_label = ctk.CTkLabel(self, text=self.texts["renamed_ncs"], anchor="w")
        self.output_label.pack(pady=0, padx=25, fill="x")

        self.output_box = ctk.CTkTextbox(self)
        self.output_box.pack(padx=20, pady=(0, 10), fill="both", expand=True)
        self.output_box.configure(state="disabled")

    def update_texts(self, new_texts: dict):
        """Aktualizuje texty všech widgetů v tomto rámci."""
        self.texts = new_texts
        self.email_counter_label.configure(text=self.texts["email_count"].format(self.email.email_counter))
        self.count_label.configure(text=self.texts["selected_files"].format(len(self.file_list)))
        self.select_btn.configure(text=self.texts["select_nc_files"])
        self.rename_btn.configure(text=self.texts["rename_nc_files"])
        self.reportbug_btn.configure(text=self.texts["report_bug"])
        self.output_label.configure(text=self.texts["renamed_ncs"])

    def load_history(self) -> list:
        """Načte historii z JSON souboru."""
        if Path(HISTORY_FILE).exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                cons.print(f"[yellow]Soubor historie '{HISTORY_FILE}' je poškozený, vytvářím nový.[/yellow]")
                return []
            except Exception as e:
                cons.print(f"[red]Chyba při načítání historie: {e}[/red]")
                return []
        return []

    def save_history(self) -> None:
        """Uloží historii do JSON souboru."""
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.processed_files_history, f, indent=4)
        except Exception as e:
            cons.print(f"[red]Chyba při ukládání historie: {e}[/red]")

    def _reset_email_counter(self) -> None:
        self.email.email_counter = 0
        self.email.save_counter()
        self.email_counter_label.configure(
            text=self.texts["email_count"].format(self.email.email_counter)
        )
        messagebox.showinfo(
            title=self.texts["reset_counter_title"],
            message=self.texts["reset_counter_message"],
        )

    def select_files(self):
        file_paths = filedialog.askopenfilenames(
            title=self.texts["select_nc_files"],
            filetypes=[("NC soubory", "*.NC"), ("Všechny soubory", "*.*")],
        )

        self.file_list = [Path(f) for f in file_paths]
        self.count_label.configure(text=self.texts["selected_files"].format(len(self.file_list)))

    def rename_files(self):
        total = len(self.file_list)
        if total == 0:
            messagebox.showinfo(title=self.texts["done_title"], message=self.texts["no_files_to_rename"])
            return

        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")

        for i, file in enumerate(self.file_list, start=1):
            time.sleep(0.25)
            changed = self.formatter.process_file(file)

            message = ""
            if changed:
                message = self.texts["file_modified"].format(file.name)
            else:
                message = self.texts["file_no_change"].format(file.name)
            
            self.output_box.insert("end", f"{message}\n")
            self.processed_files_history.append(message)

            self.progressbar.set(i / total)
            self.update_idletasks()
        
        self.save_history()

        self.output_box.configure(state="disabled")

        messagebox.showinfo(
            title=self.texts["done_title"],
            message=self.texts["done_message"].format(len(self.file_list)),
        )

    def show_processed_materials_history(self):
        history_content = "\n".join(self.processed_files_history)

        if self.app_instance:
            self.app_instance.show_materials_content(history_content)

    def set_email(self):
        self.email.email_counter += 1
        self.email.save_counter()
        self.email_counter_label.configure(
            text=self.texts["email_count"].format(self.email.email_counter)
        )

        recipient_email = "else.artem@gmail.com"
        subject = f"Report bug_{self.email.email_counter}"

        mailto_url = f"mailto:{recipient_email}?subject={urllib.parse.quote(subject)}"

        try:
            webbrowser.open(mailto_url)
        except webbrowser.Error as e:
            cons.print(f"[red]Nepodařilo se otevřít e-mailového klienta: {e}[/red]")
            messagebox.showerror(
                title=self.texts["email_error_title"],
                message=self.texts["email_error_message"],
            )
    
    def open_settings_window(self):
        self.app_instance.show_settings_content()

    def open_incorrect_materials_window(self): # Tato metoda je nyní duplicitní, ale ponechána pro kompatibilitu
        output_content = self.output_box.get("1.0", "end-1c") 
        if self.app_instance:
            self.app_instance.show_materials_content(output_content)

class MaterialsFrame(ctk.CTkFrame):
       def __init__(
        self, master=None, app_instance=None, main_frame_instance=None, texts=None, **kwargs
    ):
        super().__init__(master, **kwargs)

        self.app_instance = app_instance
        self.main_frame_instance = main_frame_instance
        self.texts = texts 
        self.full_history_content = ""

        self.materials_output_label = ctk.CTkLabel(self, text=self.texts["processed_history"], anchor="w")
        self.materials_output_label.pack(pady=(10, 0), padx=25, fill="x")

        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.pack(pady=(10, 5), padx=20, fill="x") 

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text=self.texts["search_placeholder"],
            width=250 
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.search_button = ctk.CTkButton(
            self.search_frame,
            text=self.texts["search_button"],
           command=self.search_function
        )
        self.search_button.pack(side="right", padx=(5, 0))

        self.materials_output_box = ctk.CTkTextbox(self)
        self.materials_output_box.pack(padx=20, pady=(0, 10), fill="both", expand=True)
        self.materials_output_box.configure(state="disabled")


        self.close_button = ctk.CTkButton(
            self,
            text=self.texts["back_button"],
            fg_color="white",
            text_color="black",
            command=self.return_to_main_content, 
        )
        self.close_button.pack(pady=10, padx=25, fill="x", side="bottom")
       
       def update_texts(self, new_texts: dict):
           """Aktualizuje texty všech widgetů v tomto rámci."""
           self.texts = new_texts
           self.materials_output_label.configure(text=self.texts["processed_history"])
           self.search_entry.configure(placeholder_text=self.texts["search_placeholder"])
           self.search_button.configure(text=self.texts["search_button"])
           self.close_button.configure(text=self.texts["back_button"])


       def search_function(self):
         query = self.search_entry.get().strip().lower()
         
         if not query:
             self.update_output_box_display(self.full_history_content)
             return

         filtered_lines = []
         for line in self.full_history_content.splitlines():
             if query in line.lower():
                 filtered_lines.append(line)
         
         self.update_output_box_display("\n".join(filtered_lines))


       def update_output_content(self, content: str) -> None:
        self.full_history_content = content
        self.update_output_box_display(content)


       def update_output_box_display(self, content_to_display: str) -> None:
        self.materials_output_box.configure(state="normal")
        self.materials_output_box.delete("1.0", "end")
        self.materials_output_box.insert("end", content_to_display)
        self.materials_output_box.configure(state="disabled")


       def return_to_main_content(self):
        if self.app_instance:
            self.app_instance.show_main_content()

        


class SettingsFrame(ctk.CTkFrame):
    def __init__(
        self, master=None, app_instance=None, main_frame_instance=None, texts=None, **kwargs
    ):
        super().__init__(master, **kwargs)

        self.app_instance = app_instance
        self.main_frame_instance = main_frame_instance
        self.texts = texts
        
        self.password_manager = PasswordManager(self.main_frame_instance)

        self.setting_label = ctk.CTkLabel(self, text=self.texts["appearance_mode_setting"], anchor="w")
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

       #Label a option menu pro výběř jazyka
        self.language_label = ctk.CTkLabel(self, text=self.texts["language_setting"], anchor="w")
        self.language_label.pack(pady=(20, 0), padx=25)

        self.language_optionmenu = ctk.CTkOptionMenu(
            self,
            values=list(LANGUAGE_NAMES.keys()), 
            command=self.change_language
        )
        
        current_lang_name = next(name for name, code in LANGUAGE_NAMES.items() if code == self.app_instance.current_language_code)
        self.language_optionmenu.set(current_lang_name)
        self.language_optionmenu.pack(pady=10, padx=25)


        self.reset_counter_btn = ctk.CTkButton(
            self,
            image=self.restart_icon,
            text="",
            fg_color="white",
            width=100,
            height=38,
            command=self.password_manager.prompt_for_password_and_reset, 
        )
        self.reset_counter_btn.pack(pady=(20, 10))

        self.close_button = ctk.CTkButton(
            self,
            text=self.texts["back_button"],
            fg_color="white",
            text_color="black",
            command=self.return_to_main_content, 
        )
        self.close_button.pack(pady=10, padx=25, fill="x", side="bottom")

    def update_texts(self, new_texts: dict):
        """Aktualizuje texty všech widgetů v tomto rámci."""
        self.texts = new_texts
        self.setting_label.configure(text=self.texts["appearance_mode_setting"])
        self.language_label.configure(text=self.texts["language_setting"])
        self.close_button.configure(text=self.texts["back_button"])

        current_lang_name = next(name for name, code in LANGUAGE_NAMES.items() if code == self.app_instance.current_language_code)
        self.language_optionmenu.set(current_lang_name)


    def _change_mode_and_save(self):
        current_mode = ctk.get_appearance_mode()
        new_mode = "Light" if current_mode == "Dark" else "Dark"

        ctk.set_appearance_mode(new_mode)

        if self.app_instance:
            self.app_instance.app_settings.settings["appearance_mode"] = new_mode
            self.app_instance.app_settings.save_settings()

        self._update_button_icon()

    def _update_button_icon(self):
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark":
            self.color_button.configure(image=self.light_icon, text="")
        else:
            self.color_button.configure(image=self.dark_icon, text="")

    def change_language(self, new_lang_display_name: str):
        """Voláno, když uživatel vybere nový jazyk z optionmenu."""
        new_lang_code = LANGUAGE_NAMES.get(new_lang_display_name)
        if new_lang_code:
            self.app_instance.set_language(new_lang_code)
    
    def return_to_main_content(self):
        if self.app_instance:
            self.app_instance.show_main_content()


if __name__ == "__main__":
    app: App = App()
    app.mainloop()