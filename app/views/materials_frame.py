import customtkinter as ctk
from tkinter import ttk
from typing import Optional, List

class MaterialsFrame(ctk.CTkFrame):
    def __init__(self, master=None, view_model=None, app_instance=None, **kwargs):
        super().__init__(master, **kwargs)  # only pass kwargs valid for CTkFrame
        self.view_model = view_model
        self.app_instance = app_instance  # store separately


        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(anchor="n", pady=10, padx=10)  # top-left

        self.remove_material_button = ctk.CTkButton(
            buttons_frame,
            text="Remove material",
            width=100,
            height=30,
        )
        self.remove_material_button.pack(side="left", padx=5)

        self.add_material_button = ctk.CTkButton(
            buttons_frame,
            text="Add material",
            width=100,
            height=30,
        )
        self.add_material_button.pack(side="left", padx=5)

        # Treeview
        self.tree = ttk.Treeview(
            self,
            columns=("Incorrect Material", "Correct Material"),
            show="headings",
            height=15
        )
        self.tree.heading("Incorrect Material", text="Incorrect Material")
        self.tree.heading("Correct Material", text="Correct Material")
        self.tree.column("Incorrect Material", width=150)
        self.tree.column("Correct Material", width=150)

        # Scrollbar
        y_scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")

        # Load data immediately
        self.update_treeview_display()

    def update_treeview_display(self, content: Optional[List[List[str]]] = None):
        """Clear the tree and insert rows from the ViewModel."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        if content is None:
            content = self.view_model.nc_files

        for row in content:
            self.tree.insert("", "end", values=(row[0], row[1]))
