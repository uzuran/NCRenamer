"app/utils/window_utils.py"

import customtkinter as ctk

class WindowUtils:
    """Provides helper functions for managing the app's main window."""

    def __init__(self, parent: ctk.CTk) -> None:
        """
        Initialize with a reference to the parent window.

        Args:
            parent (ctk.CTk): The root application window.
        """
        self.parent = parent

    @staticmethod
    def set_appearance(theme: str = "system") -> None:
        """
        Configure the global appearance mode and scaling.

        Args:
            theme (str): Appearance mode ('system', 'light', 'dark').
        """
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)

    def center_window(self, width: int, height: int) -> None:
        """
        Center the window on the screen.

        Args:
            width (int): Desired window width.
            height (int): Desired window height.
        """
        self.parent.update_idletasks()
        x = (self.parent.winfo_screenwidth() - width) // 2
        y = (self.parent.winfo_screenheight() - height) // 2
        self.parent.geometry(f"{width}x{height}+{x}+{y}")

    def configure_app(self, title: str, width: int, height: int) -> None:
        """
        Set the window title, size, and minimum constraints.

        Args:
            title (str): Window title.
            width (int): Window width.
            height (int): Window height.
        """
        self.parent.title(title)
        self.center_window(width, height)
        self.parent.minsize(width, height)
        self.parent.resizable(False, False)

    def shutdown_app(self) -> None:
        """Gracefully close the application window."""
        self.parent.destroy()
