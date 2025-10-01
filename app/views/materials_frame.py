"""MaterialsFrame class for displaying and managing materials in a custom tkinter application."""

import customtkinter as ctk


class MaterialsFrame(
    ctk.CTkFrame
):  # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
    def __init__(
        self, master=None, viewmodel=None, texts=None, app_instance=None, **kwargs
    ):
        super().__init__(master, **kwargs)

        self.viewmodel = viewmodel
        self.texts = texts or {}
        self.app_instance = app_instance

        self.materials_output_label = ctk.CTkLabel(
            self,
            text=self.texts.get(
                "incorrect_correct_materials", "Incorect and correct materials formats"
            ),
            anchor="w",
        )
        self.materials_output_label.pack(pady=(10, 0), padx=25, fill="x")

        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.pack(pady=(10, 5), padx=20, fill="x")

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text=self.texts.get("search_placeholder", "Search..."),
            width=250,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.search_button = ctk.CTkButton(
            self.search_frame,
            text=self.texts.get("search_button", "Search"),
            command=self.search_function,
        )
        self.search_button.pack(side="right", padx=(5, 0))

        self.materials_output_box = ctk.CTkTextbox(self)
        self.materials_output_box.pack(padx=20, pady=(0, 10), fill="both", expand=True)
        self.materials_output_box.configure(state="disabled")

        self.close_button = ctk.CTkButton(
            self,
            text=self.texts.get("back_button", "Back"),
            text_color="black",
            command=self.return_to_main_content,
        )
        self.close_button.pack(pady=10, padx=25, fill="x", side="bottom")

    def update_texts(self, new_texts: dict):
        """Update UI texts when language or content changes."""
        self.texts = new_texts
        self.materials_output_label.configure(
            text=self.texts.get(
                "incorrect_correct_materials",
                "Incorrect and correct materials formats:",
            )
        )  # TODO: Rename this label for correct and incorrect materials
        self.search_entry.configure(
            placeholder_text=self.texts.get("search_placeholder", "Search...")
        )
        self.search_button.configure(text=self.texts.get("search_button", "Search"))
        self.close_button.configure(text=self.texts.get("back_button", "Back"))

    def search_function(
        self,
    ):  # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        query = self.search_entry.get()
        filtered_content = self.viewmodel.search(query)
        self.update_output_box_display(filtered_content)

    def update_output_content(
        self, content: str
    ) -> None:  # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        self.viewmodel.set_content(content)
        self.update_output_box_display(content)

    def update_output_box_display(
        self, content_to_display: str
    ) -> None:  # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        self.materials_output_box.configure(state="normal")
        self.materials_output_box.delete("1.0", "end")
        self.materials_output_box.insert("end", content_to_display)
        self.materials_output_box.configure(state="disabled")

    def return_to_main_content(
        self,
    ):  # TODO: Missing function or method docstringPylintC0116:missing-function-docstring
        if self.app_instance:
            self.app_instance.show_main_content()
