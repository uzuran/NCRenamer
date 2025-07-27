import customtkinter as ctk
from tkinter import messagebox, filedialog
from rich.console import Console
import webbrowser
from PIL import Image

cons = Console()


class MainFrame(ctk.CTkFrame): # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
    def __init__(self, master, viewmodel, texts, app_instance, **kwargs):
        super().__init__(master, **kwargs)

        self.vm = viewmodel  # ViewModel
        self.texts = texts
        self.app_instance = app_instance

        # --- Build UI as before ---
        # (buttons, labels, etc. unchanged, just no logic inside)

        # Create a top bar for the two buttons
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.pack(fill="x", pady=(10, 0), padx=10)

        # History / Materials Button (left corner)
        try:
            self.history_icon = ctk.CTkImage(Image.open("box.png"), size=(24, 24))
        except FileNotFoundError:
            self.history_icon = None  # Fallback if missing

        self.history_materials_btn = ctk.CTkButton(
            self.top_bar,
            image=self.history_icon,
            text="",
            fg_color="white",
            width=30,
            command=self.open_materials_frame,
        )
        self.history_materials_btn.pack(side="left", anchor="w")

        # Settings Button (right corner)
        try:
            self.settings_icon = ctk.CTkImage(Image.open("setting.png"), size=(24, 24))
        except FileNotFoundError:
            self.settings_icon = None  # Avoid crash if image missing

        self.settings_btn = ctk.CTkButton(
            self.top_bar,
            image=self.settings_icon,
            text="",
            command=self.open_settings_window,
            fg_color="white",
            width=30,
        )
        self.settings_btn.pack(side="right", anchor="e")

        # Rest of your UI (centered below top bar)
        self.count_label = ctk.CTkLabel(
            self, text=self.texts["selected_files"].format(0)
        )
        self.count_label.pack(pady=5)

        # File selection button.
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

        # Rename button.
        self.rename_btn = ctk.CTkButton(
            self, text=self.texts["rename_nc_files"], command=self.rename_files
        )
        self.rename_btn.pack(pady=(0, 10))
        self.reportbug_btn = ctk.CTkButton(
            self, text=self.texts["report_bug"], command=self.set_email
        )

        self.output_box = ctk.CTkTextbox(self, height=150, width=400, state="disabled")
        self.output_box.pack(pady=5)

        self.email_counter_label = ctk.CTkLabel(
            self, text=self.texts["email_count"].format(0)
        )
        self.email_counter_label.pack(pady=5)

    def select_files(self): # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        files = filedialog.askopenfilenames(
            title=self.texts["select_nc_files"],
            filetypes=[("NC soubory", "*.NC"), ("Všechny soubory", "*.*")],
        )
        self.vm.select_files(files)
        self.count_label.configure(
            text=self.texts["selected_files"].format(len(self.vm.file_list))
        )

    def rename_files(self): # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        results = self.vm.rename_files()
        total = len(results)
        if total == 0:
            messagebox.showinfo(
                title=self.texts["done_title"], message=self.texts["no_files_to_rename"]
            )
            return

        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")

        for i, (name, changed) in enumerate(results, start=1):
            text = (
                self.texts["file_modified"].format(name)
                if changed
                else self.texts["file_no_change"].format(name)
            )
            self.output_box.insert("end", f"{text}\n")
            self.progressbar.set(i / total)
            self.update_idletasks()

        self.output_box.configure(state="disabled")
        messagebox.showinfo(
            title=self.texts["done_title"],
            message=self.texts["done_message"].format(total),
        )

    def set_email(self): # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        self.vm.increment_email_counter()
        self.email_counter_label.configure(
            text=self.texts["email_count"].format(self.vm.email.email_counter)
        )
        try:
            webbrowser.open(self.vm.get_mailto_url())
        except webbrowser.Error as e:
            cons.print(f"[red]Failed to open mail client: {e}[/red]")
            messagebox.showerror(
                title=self.texts["email_error_title"],
                message=self.texts["email_error_message"],
            )

    def open_settings_window(self):
        """Opens the SettingsFrame (or switches view)."""
        if self.app_instance:
            self.app_instance.show_settings_content()

    def open_materials_frame(self):
        """Opens the MaterialsFrame (or switches view)."""
        if self.app_instance:
            self.app_instance.show_materials_content()
