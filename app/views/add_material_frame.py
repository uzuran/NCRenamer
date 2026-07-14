from tkinter import ttk

import customtkinter as ctk


class AddMaterialFrame(ctk.CTkFrame):
    "Add / edit material frame."

    def __init__(
        self, texts=None, master=None, view_model=None, app_instance=None, **kwargs
    ):
        super().__init__(master, **kwargs)

        self.view_model = view_model
        self.app_instance = app_instance
        self.texts = texts or {}

        # Key of the row currently being edited; None means "add mode".
        self._editing_incorrect: str | None = None

        # ─── TITLE ────────────────────────────────────────────────────
        self.title = ctk.CTkLabel(
            self,
            text=self.texts.get("add_material", "Add material"),
            font=("Arial", 18),
        )
        self.title.pack(pady=10)

        # ─── ENTRY FIELDS ─────────────────────────────────────────────
        inputs_frame = ctk.CTkFrame(self)
        inputs_frame.pack(pady=10)

        self.incorrect_entry = ctk.CTkEntry(
            inputs_frame,
            placeholder_text=self.texts.get("incorrect_material", "Incorrect material"),
        )
        self.incorrect_entry.pack(side="left", padx=10)

        self.correct_entry = ctk.CTkEntry(
            inputs_frame,
            placeholder_text=self.texts.get("correct_material", "Correct material"),
        )
        self.correct_entry.pack(side="left")

        # ─── ACTION BUTTONS ───────────────────────────────────────────
        buttons_row1 = ctk.CTkFrame(self)
        buttons_row1.pack(pady=(10, 4))

        self.add_button = ctk.CTkButton(
            buttons_row1,
            text=self.texts.get("add_material", "Add material"),
            command=self.add_material,
        )
        self.add_button.pack(side="left", padx=10)

        self.remove_button = ctk.CTkButton(
            buttons_row1,
            text=self.texts.get("remove_material", "Remove material"),
            command=self.remove_selected_material,
        )
        self.remove_button.pack(side="left", padx=10)

        buttons_row2 = ctk.CTkFrame(self)
        buttons_row2.pack(pady=(0, 10))

        self.update_button = ctk.CTkButton(
            buttons_row2,
            text=self.texts.get("update_material", "Update material"),
            command=self.update_selected_material,
            state="disabled",
        )
        self.update_button.pack(side="left", padx=10)

        # ─── FLASH MESSAGE ────────────────────────────────────────────
        flash_message_frame = ctk.CTkFrame(self)
        flash_message_frame.pack()
        self.flash_label = ctk.CTkLabel(flash_message_frame, text="")
        self.flash_label.pack(side="bottom")

        # ─── TREEVIEW ─────────────────────────────────────────────────
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("Incorrect Material", "Correct Material"),
            show="headings",
        )

        self.tree.heading(
            "Incorrect Material",
            text=self.texts.get("incorrect_material", "Incorrect material"),
        )
        self.tree.heading(
            "Correct Material",
            text=self.texts.get("correct_material", "Correct material"),
        )

        self.tree.column("Incorrect Material", width=150)
        self.tree.column("Correct Material", width=150)

        y_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        # Click on already-selected row or empty area → deselect
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Escape>", lambda e: self._deselect())

        self.update_treeview_display()

        # ─── BACK BUTTON ──────────────────────────────────────────────
        self.back_button = ctk.CTkButton(
            self,
            text=self.texts.get("back_button", "Back"),
            text_color="black",
            command=self.return_to_main_content,
        )
        self.back_button.pack(pady=10, padx=25, fill="x")

        if self.view_model is not None:
            self.view_model.subscribe(self.reload_treeview)

    # ── Treeview selection ─────────────────────────────────────────────

    def on_tree_select(self, event=None):
        """Fill entries from the selected row and switch to edit mode."""
        selected = self.tree.selection()
        if not selected:
            self._reset_edit_state()
            return

        item = self.tree.item(selected[0])
        self._editing_incorrect = str(item["values"][0])

        self.incorrect_entry.delete(0, "end")
        self.incorrect_entry.insert(0, self._editing_incorrect)

        self.correct_entry.delete(0, "end")
        self.correct_entry.insert(0, str(item["values"][1]))

        self.update_button.configure(state="normal")
        self.add_button.configure(state="disabled")

    def _reset_edit_state(self):
        """Return UI to add mode. Does NOT change treeview selection."""
        self._editing_incorrect = None
        self.incorrect_entry.configure(state="normal")
        self.incorrect_entry.delete(0, "end")
        self.correct_entry.delete(0, "end")
        self.update_button.configure(state="disabled")
        self.add_button.configure(state="normal")

    def _deselect(self, event=None):
        """Clear treeview selection and return to add mode.

        Calling selection_remove triggers <<TreeviewSelect>> with an empty
        selection, which calls on_tree_select → _reset_edit_state.
        """
        for iid in self.tree.selection():
            self.tree.selection_remove(iid)

    def _on_tree_click(self, event):
        row = self.tree.identify_row(event.y)
        # Empty-area click (not row) or re-click on the selected row both deselect.
        if not row or row in self.tree.selection():
            self._deselect()

    # ── CRUD actions ───────────────────────────────────────────────────

    def add_material(self):
        "Add a new material mapping."
        # Read entries FIRST — _reset_edit_state would clear them if called here.
        incorrect = self.incorrect_entry.get()
        correct = self.correct_entry.get()

        success, message = self.view_model.add_material(incorrect, correct)

        if success:
            self.show_flash(message, "green")
            self.incorrect_entry.delete(0, "end")
            self.correct_entry.delete(0, "end")
            self.update_treeview_display()
        else:
            self.show_flash(message, "red")

    def update_selected_material(self):
        "Save the edited correct value for the selected row."
        if not self._editing_incorrect:
            return

        new_incorrect = self.incorrect_entry.get()
        new_correct = self.correct_entry.get()
        success, message = self.view_model.update_material(
            self._editing_incorrect, new_incorrect, new_correct
        )

        if success:
            self.show_flash(message, "green")
            self._deselect()
            self.update_treeview_display()
        else:
            self.show_flash(message, "red")

    def remove_selected_material(self):
        "Remove the selected row."
        selected = self.tree.selection()

        if not selected:
            self.show_flash(
                self.texts.get("no_material_selected", "No material selected"), "red"
            )
            return

        item = self.tree.item(selected[0])
        incorrect_material = item["values"][0]

        success, message = self.view_model.remove_material(incorrect_material)

        if success:
            self.show_flash(message, "green")
            self._deselect()
            self.update_treeview_display()

    # ── Display helpers ────────────────────────────────────────────────

    def reload_treeview(self) -> None:
        self.update_treeview_display()

    def return_to_main_content(self):
        "Navigate back to the materials list."
        if self.app_instance:
            self.app_instance.show_materials_content()

    def update_treeview_display(self, content: list[list[str]] | None = None):
        "Reload the treeview from the ViewModel (or from *content* directly)."
        for child in self.tree.get_children():
            self.tree.delete(child)

        if content is None:
            content = self.view_model.get_materials()

        for row in content:
            self.tree.insert("", "end", values=(row[0], row[1]))

    def show_flash(self, message, color="green"):
        "Display a short-lived status message."
        self.flash_label.configure(text=message, text_color=color)
        self.after(2500, lambda: self.flash_label.configure(text=""))

    def update_texts(self, new_texts: dict):
        "Update all widget labels after a language change."
        self.texts = new_texts
        self.title.configure(text=self.texts.get("add_material", "Add material"))
        self.incorrect_entry.configure(
            placeholder_text=self.texts.get("incorrect_material", "Incorrect material")
        )
        self.correct_entry.configure(
            placeholder_text=self.texts.get("correct_material", "Correct material")
        )
        self.add_button.configure(text=self.texts.get("add_material", "Add material"))
        self.update_button.configure(
            text=self.texts.get("update_material", "Update material")
        )
        self.remove_button.configure(
            text=self.texts.get("remove_material", "Remove material")
        )
        self.tree.heading(
            "Incorrect Material",
            text=self.texts.get("incorrect_material", "Incorrect material"),
        )
        self.tree.heading(
            "Correct Material",
            text=self.texts.get("correct_material", "Correct material"),
        )
        self.back_button.configure(text=self.texts.get("back_button", "Back"))
