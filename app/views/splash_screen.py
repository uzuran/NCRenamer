"""splash_screen.py — borderless loading screen shown during app startup.

Inherits from tk.Toplevel (NOT ctk.CTkToplevel).  On Windows, CTkToplevel
uses WinAPI to render a custom title bar; combining that with
overrideredirect(True) leaves the window in a broken state and prevents the
main window from appearing.  Plain tk.Toplevel + overrideredirect is
well-tested on both Windows and Linux and has no such conflict.
CTk widgets placed inside work normally — they read the global theme.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from app.version import APP_NAME, APP_VERSION, AUTHOR


class SplashScreen(tk.Toplevel):
    """Borderless splash shown while App.__init__ runs.

    Usage:
        splash = SplashScreen(root)        # root must be withdrawn first
        splash.set_status("Loading…")
        # … do heavy work …
        splash.destroy()
        root.deiconify()
    """

    _W = 320
    _H = 175

    def __init__(self, master) -> None:
        super().__init__(master)
        self.overrideredirect(True)   # remove title bar / window chrome
        self.resizable(False, False)
        self.lift()

        self._build()
        self._center()
        self.update()                 # force render before caller starts heavy work

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Thin border via the raw Toplevel background showing around the inner frame
        self.configure(bg="#2e2e2e")

        inner = ctk.CTkFrame(self, fg_color=("#ffffff", "#1e1e1e"), corner_radius=8)
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        # app name
        ctk.CTkLabel(
            inner,
            text=APP_NAME,
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(22, 2))

        # version
        ctk.CTkLabel(
            inner,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
        ).pack(pady=(0, 2))

        # author
        ctk.CTkLabel(
            inner,
            text=AUTHOR,
            font=ctk.CTkFont(size=10),
            text_color=("gray60", "gray50"),
        ).pack(pady=(0, 12))

        # status text
        self._status_var = ctk.StringVar(value="Starting…")
        ctk.CTkLabel(
            inner,
            textvariable=self._status_var,
            font=ctk.CTkFont(size=10),
            text_color=("gray55", "gray55"),
        ).pack(pady=(0, 6))

        # indeterminate progress bar
        self._bar = ctk.CTkProgressBar(inner, width=220, mode="indeterminate")
        self._bar.pack(pady=(0, 18))
        self._bar.start()

    # ── public ────────────────────────────────────────────────────────────────

    def set_status(self, text: str) -> None:
        """Update the status line and repaint immediately."""
        self._status_var.set(text)
        self.update_idletasks()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _center(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - self._W) // 2
        y = (sh - self._H) // 2
        self.geometry(f"{self._W}x{self._H}+{x}+{y}")
