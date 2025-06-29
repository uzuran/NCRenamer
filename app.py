import os
import customtkinter as ctk
from customtkinter import filedialog


def appearance(theme: str) -> None:
    # nastaveni Theme a scalingu
    ctk.set_appearance_mode(theme)
    ctk.set_default_color_theme("blue")
    # --
    ctk.set_widget_scaling(1.0)
    ctk.set_window_scaling(1.0)


class App(ctk.CTk):
    """hlavni apka"""

    def __init__(self) -> None:
        # --
        super().__init__()
        self.app_init("NCRenamer", 400, 600)
        appearance("system")
        # --
        self.update_idletasks()

    def center_window(self, app_width: int, app_height: int) -> None:
        self.update_idletasks()
        width: int = app_width
        height: int = app_height
        screen_width: int = self.winfo_screenwidth()
        screen_height: int = self.winfo_screenheight()
        x: int = screen_width // 2 - width // 2
        y: int = screen_height // 2 - height // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def app_init(self, name, width, height) -> None:
        """Nastavy zakladni rozmer appky"""
        self.title(name)
        self.center_window(width, height)
        self.minsize(width, height)
        self.resizable(True, True)

    def shutdown(self):
        self.destroy()
        os._exit(0)


if __name__ == "__main__":
    app: App = App()
    app.mainloop()
