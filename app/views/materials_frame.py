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
            buttons_frame, text=self.texts.get("remove_material", "Remove material"), width=100, height=30, command=self.remove_selected_material
        )
        self.remove_material_button.pack(side="left", padx=10)

        self.add_material_button = ctk.CTkButton(
            buttons_frame, text=self.texts.get("add_material", "Add material"), width=100, height=30, command=self.open_add_materials_window
        )
        self.add_material_button.pack(side="left")

        flash_message_frame = ctk.CTkFrame(self)
        flash_message_frame.pack()        
        self.flash_label = ctk.CTkLabel(flash_message_frame, text="")
        self.flash_label.pack(side="bottom")
        
        #Search input
        self.search_entry = ctk.CTkEntry(
        self,
        placeholder_text="Search material..."
        )
        self.search_entry.pack(padx=10, pady=5, fill="x")
        self.search_entry.bind("<KeyRelease>", self.search_material)

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
        self.back_button.pack(pady=10, padx=25, fill="x")

    def return_to_main_content(self):
        if self.app_instance:
            self.app_instance.show_main_content()

    def update_treeview_display(self, content: Optional[List[List[str]]] = None):
        "Update the treeview with the provided content or reload from the view model."
        for row in self.tree.get_children():
            self.tree.delete(row)

        if content is None:
            content = self.view_model.get_materials()

        for row in content:
            self.tree.insert("", "end", values=(row[0], row[1]))


    def update_texts(self, new_texts: dict):
        """Update the texts in the settings frame."""
        self.texts = new_texts
        self.remove_material_button.configure(
            text=self.texts.get("remove_material", "Remove material")
        )
        self.add_material_button.configure(
            text=self.texts.get("add_material", "Add material")
        )
        self.back_button.configure(text=self.texts.get("back_button", "Back"))
        current_lang_name = (
            self.view_model.get_current_language_name(LANGUAGE_NAMES)
            if self.view_model
            else "Czech"
        )
        self.language_optionmenu.set(current_lang_name)
    
    def remove_selected_material(self):
        "Remove selected material"
        selected = self.tree.selection()

        if not selected:
            self.show_flash("No material selected", "red")
            return

        item = self.tree.item(selected[0])
        incorrect_material = item["values"][0]

        success, message = self.view_model.remove_material(incorrect_material)

        if success:
            self.show_flash(message, "green")
            self.update_treeview_display()

    def search_material(self, event=None):
        "Function for search materials in treeview"
        query = self.search_entry.get().lower()

        materials = self.view_model.get_materials()

        filtered = [
            row for row in materials
            if row[0].lower().startswith(query)
        ]

        self.update_treeview_display(filtered)

    def show_flash(self, message, color="green"):
        "Show flash message"
        self.flash_label.configure(text=message, text_color=color)

        self.after(2500, lambda: self.flash_label.configure(text=""))

    def change_language(self, new_lang_display_name: str):
        """Change the application language."""
        if self.view_model:
            self.view_model.change_language(new_lang_display_name)

    def open_add_materials_window(self):
        """Opens the SettingsFrame (or switches view)."""
        if self.app_instance:
            self.app_instance.show_add_materials_content()
