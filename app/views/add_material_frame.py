import customtkinter as ctk
from tkinter import ttk
from typing import Optional, List


class AddMaterialFrame(ctk.CTkFrame):
    "Add material frame class"
    def __init__(self, texts=None, master=None, view_model=None, app_instance=None, **kwargs):
        super().__init__(master, **kwargs)

        self.view_model = view_model
        self.app_instance = app_instance
        self.texts = texts or {}
        
        # TOP
        title = ctk.CTkLabel(self, text=self.texts.get("add_material", "Add material"), font=("Arial", 18))
        title.pack(pady=10)

        inputs_frame = ctk.CTkFrame(self)
        inputs_frame.pack(pady=10)

        self.incorrect_entry = ctk.CTkEntry(inputs_frame, placeholder_text="Incorrect material")
        self.incorrect_entry.pack(side="left", padx=10)

        self.correct_entry = ctk.CTkEntry(inputs_frame, placeholder_text="Correct material")
        self.correct_entry.pack(side="left")

        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(pady=10)
        
        add_btn = ctk.CTkButton(buttons_frame, text=self.texts.get("add_material", "Add material"), command=self.add_material)
        add_btn.pack(side="left", padx=10)

        add_btn = ctk.CTkButton(buttons_frame, text=self.texts.get("remove_material", "Remove material"), command=self.remove_selected_material)
        add_btn.pack(side="left")

        flash_message_frame = ctk.CTkFrame(self)
        flash_message_frame.pack()        
        self.flash_label = ctk.CTkLabel(flash_message_frame, text="")
        self.flash_label.pack(side="bottom")

        # MIDDLE (expand)
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("Incorrect Material", "Correct Material"),
            show="headings",
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

        # BOTTOM
        self.back_button = ctk.CTkButton(
            self,
            text=self.texts.get("back_button", "Back"),
            text_color="black",
            command=self.return_to_main_content,
        )
        self.back_button.pack(pady=10, padx=25, fill="x")

    def return_to_main_content(self):
        "Function to allow user return back to the main content"
        if self.app_instance:
            self.app_instance.show_materials_content()

    def update_treeview_display(self, content: Optional[List[List[str]]] = None):
        "Update treeview display"
        for row in self.tree.get_children():
            self.tree.delete(row)

        if content is None:
            content = self.view_model.get_materials()

        for row in content:
            self.tree.insert("", "end", values=(row[0], row[1]))

    def add_material(self):
        "Add material"
        incorrect = self.incorrect_entry.get()
        correct = self.correct_entry.get()

        success, message = self.view_model.add_material(incorrect, correct)

        if success:
            self.show_flash(message, "green")
            self.update_treeview_display()
            self.incorrect_entry.delete(0, "end")
            self.correct_entry.delete(0, "end")

        else:
            self.show_flash(message, "red")

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

    
    def show_flash(self, message, color="green"):
        "Show flash message"
        self.flash_label.configure(text=message, text_color=color)

        self.after(2500, lambda: self.flash_label.configure(text=""))