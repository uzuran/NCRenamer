import customtkinter as ctk
from tkinter import ttk
from typing import Optional, List
from app.translations.translations import LANGUAGE_NAMES

class MaterialsFrame(ctk.CTkFrame):
    def __init__(self, texts=None, master=None, view_model=None, app_instance=None, **kwargs):
        super().__init__(master, **kwargs)
        self.view_model = view_model
        self.app_instance = app_instance
        self.texts = texts or {}

        # ─── OPTION MENU ──────────────────────────────────────────────
        self.language_optionmenu = ctk.CTkOptionMenu(
            self, values=list(LANGUAGE_NAMES.keys()), command=self.change_language
        )

        # ─── TOP BUTTONS ──────────────────────────────────────────────
        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(anchor="n", pady=10)

        self.remove_material_button = ctk.CTkButton(
            buttons_frame, text="Remove material", width=100, height=30
        )
        self.remove_material_button.pack(side="left", padx=5)

        self.add_material_button = ctk.CTkButton(
            buttons_frame, text="Add material", width=100, height=30
        )
        self.add_material_button.pack(side="left", padx=5)

        # ─── MIDDLE: TREEVIEW IN ITS OWN FRAME ─────────────────────────
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("Incorrect Material", "Correct Material"),
            show="headings",
            height=15
        )
        self.tree.heading("Incorrect Material", text="Incorrect Material")
        self.tree.heading("Correct Material", text="Correct Material")
        self.tree.column("Incorrect Material", width=150)
        self.tree.column("Correct Material", width=150)

        y_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")

        self.update_treeview_display()

        # ─── BOTTOM: BACK BUTTON ───────────────────────────────────────
        self.back_button = ctk.CTkButton(
            self,
            text=self.texts.get("back_button", "Back"),
            text_color="black",
            command=self.return_to_main_content,
        )
        self.back_button.pack(pady=10, padx=25, fill="x", side="bottom")

    def return_to_main_content(self):
        if self.app_instance:
            self.app_instance.show_main_content()

    def update_treeview_display(self, content: Optional[List[List[str]]] = None):
        for row in self.tree.get_children():
            self.tree.delete(row)

        if content is None:
            content = self.view_model.nc_files

        for row in content:
            self.tree.insert("", "end", values=(row[0], row[1]))


    def update_texts(self, new_texts: dict):
        """Update the texts in the settings frame."""
        self.texts = new_texts
        self.back_button.configure(text=self.texts.get("back_button", "Back"))
        current_lang_name = (
            self.view_model.get_current_language_name(LANGUAGE_NAMES)
            if self.view_model
            else "Czech"
        )
        self.language_optionmenu.set(current_lang_name)

    def change_language(self, new_lang_display_name: str):
        """Change the application language."""
        if self.view_model:
            self.view_model.change_language(new_lang_display_name)