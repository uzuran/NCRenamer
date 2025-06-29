"""CTK app"""

import time
from rich.console import Console
import customtkinter as ctk
from customtkinter import filedialog

# ---
cons: Console = Console()


class Utils:
    """Utility pro CTk okno."""

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
    """Hlavní aplikace."""

    def __init__(self) -> None:
        super().__init__()
        self.utils = Utils(self)
        self.utils.set_appearance("system")
        self.utils.configure_app("NCRenamer", 400, 400)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.main_frame = MainFrame(master=self)
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")


class MainFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.file_list = []
        # --- select_btn
        self.select_btn = ctk.CTkButton(
            self, text="Select NC files", command=self.select_files
        )
        self.select_btn.pack(pady=(10, 0))
        # --- progress bar
        self.progressbar = ctk.CTkProgressBar(self)
        self.progressbar.pack(pady=(10, 10), fill="x", padx=20)
        self.progressbar.configure(corner_radius=5)
        self.progressbar.set(0)
        # --- rename btn
        self.rename_btn = ctk.CTkButton(
            self, text="Rename NC files", command=self.rename_files
        )
        self.rename_btn.pack(pady=(0, 10))
        # --- report Bug btn
        self.reportbug_btn = ctk.CTkButton(
            self, text="Report Bug", command=self.rename_files
        )
        self.reportbug_btn.pack(pady=(0, 10))
        # --- Label
        self.output_label = ctk.CTkLabel(self, text="Renamed NCs", anchor="w")
        self.output_label.pack(pady=0, padx=25, fill="x")
        # --- Textbox
        self.output_box = ctk.CTkTextbox(self)
        self.output_box.pack(padx=20, pady=(0, 10), fill="both", expand=True)
        self.output_box.configure(state="disabled")

    def select_files(self):
        self.file_list = [f"file_{i}.nc" for i in range(1, 11)]

    def rename_files(self):
        total = len(self.file_list)
        if total == 0:
            print("Žádné soubory k přejmenování.")
            return

        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")

        for i, file in enumerate(self.file_list, start=1):
            time.sleep(0.2)  # Simulace
            new_name = f"{' ' * 25}{file}"
            self.output_box.insert("end", new_name + "\n")

            self.progressbar.set(i / total)
            self.update_idletasks()

        self.output_box.configure(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
