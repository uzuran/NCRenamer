"""about_dialog.py — modal About / License dialog for NC/SCH Renamer."""

from __future__ import annotations

import webbrowser

import customtkinter as ctk

from app.version import APP_NAME, APP_VERSION, AUTHOR

_LICENSE_URL = "https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode"

_SECTIONS = [
    (
        "YOU ARE FREE TO",
        [
            (
                "Share",
                "Copy and redistribute this software in its original, unmodified "
                "form on any medium or format, for non-commercial purposes only.",
            ),
        ],
    ),
    (
        "YOU MUST",
        [
            (
                "Give credit",
                f"Clearly state the author's name ({AUTHOR}), the project name "
                f"({APP_NAME}), the year (2026), and include a link to this license "
                "whenever you share the software.",
            ),
            (
                "Keep it intact",
                "You may not remove or alter any copyright notices, license "
                "statements, or attribution information.",
            ),
        ],
    ),
    (
        "YOU MAY NOT",
        [
            (
                "Use commercially",
                "You may not use this software, or any part of it, for commercial "
                "purposes, paid services, or any activity intended for commercial "
                "advantage or monetary compensation.",
            ),
            (
                "Modify",
                "You may not alter, transform, translate, or build upon this "
                "software in any way.",
            ),
            (
                "Distribute derivatives",
                "You may not create or share modified or adapted versions of this "
                "software.",
            ),
        ],
    ),
    (
        "NO WARRANTIES",
        [
            (
                "",
                'This software is provided "as is", without any warranty of any '
                "kind. The author is not liable for any damages arising from its use.",
            ),
        ],
    ),
]


class AboutDialog(ctk.CTkToplevel):
    """Modal popup that shows app info and the CC BY-NC-ND 4.0 license summary."""

    def __init__(self, master, texts: dict | None = None) -> None:
        super().__init__(master)
        self._texts = texts or {}
        self.title(self._texts.get("about_title", f"About {APP_NAME}"))
        self.resizable(False, False)
        self.after(100, self.grab_set)  # defer until window is viewable

        self._build()
        self._center(master)

    def _build(self) -> None:
        pad = {"padx": 20, "pady": (0, 0)}

        # ── App header ────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text=f"{APP_NAME}  v{APP_VERSION}",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="center",
        ).pack(fill="x", padx=20, pady=(18, 2))

        ctk.CTkLabel(
            self,
            text=f"Copyright © 2026  {AUTHOR}",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            anchor="center",
        ).pack(fill="x", **pad)

        ctk.CTkLabel(
            self,
            text="Creative Commons BY-NC-ND 4.0",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#1a6b3c", "#4caf7d"),
            anchor="center",
        ).pack(fill="x", padx=20, pady=(4, 12))

        # ── Divider ───────────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color="gray40").pack(
            fill="x", padx=20, pady=(0, 12)
        )

        # ── Scrollable license content ────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(self, width=420, height=300)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        for section_title, items in _SECTIONS:
            # Section heading
            ctk.CTkLabel(
                scroll,
                text=section_title,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#1a3a6b", "#7aadff"),
                anchor="w",
            ).pack(fill="x", pady=(10, 2))

            for term, description in items:
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", pady=2)

                if term:
                    ctk.CTkLabel(
                        row,
                        text=f"{term}  —",
                        font=ctk.CTkFont(size=11, weight="bold"),
                        anchor="nw",
                        width=130,
                    ).pack(side="left", anchor="nw", padx=(6, 0))

                ctk.CTkLabel(
                    row,
                    text=description,
                    font=ctk.CTkFont(size=11),
                    anchor="nw",
                    wraplength=270,
                    justify="left",
                ).pack(side="left", anchor="nw", padx=(0, 6))

        # ── Full legal text link ──────────────────────────────────────────────
        ctk.CTkFrame(scroll, height=1, fg_color="gray40").pack(
            fill="x", pady=(12, 6)
        )

        ctk.CTkLabel(
            scroll,
            text="Full legal text:",
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=6)

        link_btn = ctk.CTkButton(
            scroll,
            text=_LICENSE_URL,
            font=ctk.CTkFont(size=10, underline=True),
            fg_color="transparent",
            text_color=("#0066cc", "#5aacff"),
            hover_color=("#e8f0fe", "#1a2d4a"),
            anchor="w",
            command=lambda: webbrowser.open(_LICENSE_URL),
        )
        link_btn.pack(fill="x", padx=2, pady=(0, 6))

        # ── Close button ──────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color="gray40").pack(
            fill="x", padx=20, pady=(0, 10)
        )

        ctk.CTkButton(
            self,
            text=self._texts.get("about_close", "Close"),
            width=100,
            command=self.destroy,
        ).pack(pady=(0, 16))

    def _center(self, master) -> None:
        """Position the dialog centered over the master window."""
        self.update_idletasks()
        mw = master.winfo_width()
        mh = master.winfo_height()
        mx = master.winfo_rootx()
        my = master.winfo_rooty()
        dw = self.winfo_width()
        dh = self.winfo_height()
        x = mx + (mw - dw) // 2
        y = my + (mh - dh) // 2
        self.geometry(f"+{x}+{y}")
