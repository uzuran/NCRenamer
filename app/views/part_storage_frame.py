"""part_storage_frame.py — Leftover parts storage UI."""

from __future__ import annotations

from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from app.viewmodels.part_storage_view_model import PartStorageViewModel


class PartStorageFrame(ctk.CTkFrame):
    """Add, edit, delete, and search leftover parts from laser cutting."""

    def __init__(
        self,
        master=None,
        view_model: PartStorageViewModel | None = None,
        app_instance=None,
        texts: dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.vm = view_model
        self.app_instance = app_instance
        self.texts = texts or {}
        self._editing_id: str | None = None
        self._build()
        if self.vm is not None:
            self.vm.set_confirm_duplicate(self._make_confirm_duplicate())

    # ─── Build ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.title_lbl = ctk.CTkLabel(
            self,
            text=self.texts.get("part_storage", "Leftovers"),
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.title_lbl.pack(pady=(6, 2))

        # All input rows share one grid so labels align in column 0 and entries in column 1
        fields_frame = ctk.CTkFrame(self, fg_color="transparent")
        fields_frame.pack(pady=(0, 2))

        self.search_lbl = ctk.CTkLabel(
            fields_frame,
            text=self.texts.get("part_search_label", "Hledat:"),
            width=110,
            anchor="e",
        )
        self.search_lbl.grid(row=0, column=0, padx=(0, 6), pady=1, sticky="e")
        self.search_entry = ctk.CTkEntry(
            fields_frame,
            placeholder_text=self.texts.get(
                "part_search_placeholder", "Search part number…"
            ),
            width=230,
        )
        self.search_entry.grid(row=0, column=1, pady=1, sticky="w")
        self.search_entry.bind("<KeyRelease>", lambda e: self.update_treeview())

        self.number_lbl = ctk.CTkLabel(
            fields_frame,
            text=self.texts.get("part_number_prompt", "Part number:"),
            width=110,
            anchor="e",
        )
        self.number_lbl.grid(row=1, column=0, padx=(0, 6), pady=1, sticky="e")
        self.number_entry = ctk.CTkEntry(fields_frame, width=230)
        self.number_entry.grid(row=1, column=1, pady=1, sticky="w")

        self.location_lbl = ctk.CTkLabel(
            fields_frame,
            text=self.texts.get("part_location_prompt", "Location:"),
            width=110,
            anchor="e",
        )
        self.location_lbl.grid(row=2, column=0, padx=(0, 6), pady=1, sticky="e")
        self.location_entry = ctk.CTkEntry(fields_frame, width=230)
        self.location_entry.grid(row=2, column=1, pady=1, sticky="w")

        self.notes_lbl = ctk.CTkLabel(
            fields_frame,
            text=self.texts.get("part_notes_prompt", "Notes:"),
            width=110,
            anchor="e",
        )
        self.notes_lbl.grid(row=3, column=0, padx=(0, 6), pady=1, sticky="e")
        self.notes_entry = ctk.CTkEntry(fields_frame, width=230)
        self.notes_entry.grid(row=3, column=1, pady=1, sticky="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 2))

        self.add_btn = ctk.CTkButton(
            btn_frame,
            text=self.texts.get("part_add", "Add"),
            width=100,
            command=self._cmd_add,
        )
        self.add_btn.pack(side="left", padx=5)

        self.update_btn = ctk.CTkButton(
            btn_frame,
            text=self.texts.get("part_update", "Update"),
            width=100,
            state="disabled",
            command=self._cmd_update,
        )
        self.update_btn.pack(side="left", padx=5)

        self.delete_btn = ctk.CTkButton(
            btn_frame,
            text=self.texts.get("part_delete", "Delete"),
            width=100,
            fg_color="#922b21",
            hover_color="#6e1f18",
            command=self._cmd_delete,
        )
        self.delete_btn.pack(side="left", padx=5)

        # Flash label
        flash_frame = ctk.CTkFrame(self, fg_color="transparent")
        flash_frame.pack(pady=(0, 2))
        self.flash_lbl = ctk.CTkLabel(flash_frame, text="")
        self.flash_lbl.pack()

        # TreeView
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("part_number", "location", "date_added", "notes"),
            show="headings",
        )
        self.tree.heading(
            "part_number", text=self.texts.get("part_col_number", "Part Number")
        )
        self.tree.heading(
            "location", text=self.texts.get("part_col_location", "Location")
        )
        self.tree.heading(
            "date_added", text=self.texts.get("part_col_date", "Date Added")
        )
        self.tree.heading(
            "notes", text=self.texts.get("part_col_notes", "Notes")
        )
        self.tree.column(
            "part_number", width=130, minwidth=80, anchor="w", stretch=False
        )
        self.tree.column(
            "location", width=130, minwidth=80, anchor="w", stretch=False
        )
        self.tree.column(
            "date_added", width=120, minwidth=80, anchor="center", stretch=False
        )
        self.tree.column(
            "notes", width=220, minwidth=80, anchor="w", stretch=True
        )

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Escape>", lambda e: self._deselect())

        # Back button
        self.back_btn = ctk.CTkButton(
            self,
            text=self.texts.get("back_button", "Back"),
            command=self._go_back,
        )
        self.back_btn.pack(pady=10, padx=25, fill="x")

        self.update_treeview()
        if self.vm is not None:
            self.vm.subscribe(self.reload_treeview)

    # ─── Treeview helpers ─────────────────────────────────────────────────────

    def reload_treeview(self) -> None:
        self.update_treeview()

    def update_treeview(self) -> None:
        """Reload the treeview, filtered by the current search entry text."""
        query = (
            self.search_entry.get() if hasattr(self, "search_entry") else ""
        )
        self.tree.delete(*self.tree.get_children())
        if self.vm is None:
            return
        for item in self.vm.get_all_parts(query):
            raw_date = item.get("date_added", "")
            try:
                y, m, d = raw_date.split("-")
                date_str = f"{d}.{m}.{y}"
            except Exception:
                date_str = raw_date or "—"
            self.tree.insert(
                "",
                "end",
                iid=item["id"],
                values=(
                    item.get("part_number", ""),
                    item.get("location", ""),
                    date_str,
                    item.get("notes", ""),
                ),
            )

    # ─── Selection handling ───────────────────────────────────────────────────

    def _on_tree_select(self, event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            self._reset_edit_state()
            return
        self._editing_id = selected[0]
        values = self.tree.item(self._editing_id, "values")
        self.number_entry.delete(0, "end")
        self.number_entry.insert(0, values[0] if len(values) > 0 else "")
        self.location_entry.delete(0, "end")
        self.location_entry.insert(0, values[1] if len(values) > 1 else "")
        self.notes_entry.delete(0, "end")
        self.notes_entry.insert(0, values[3] if len(values) > 3 else "")
        self.update_btn.configure(state="normal")
        self.add_btn.configure(state="disabled")

    def _reset_edit_state(self) -> None:
        self._editing_id = None
        self.number_entry.delete(0, "end")
        self.location_entry.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self.update_btn.configure(state="disabled")
        self.add_btn.configure(state="normal")

    def _deselect(self) -> None:
        for iid in self.tree.selection():
            self.tree.selection_remove(iid)

    def _on_tree_click(self, event) -> None:
        row = self.tree.identify_row(event.y)
        if not row or row in self.tree.selection():
            self._deselect()

    # ─── Commands ─────────────────────────────────────────────────────────────

    def _cmd_add(self) -> None:
        if self.vm is None:
            return
        success, msg = self.vm.add_part(
            self.number_entry.get(),
            self.location_entry.get(),
            self.notes_entry.get(),
        )
        if success:
            self._reset_edit_state()
            self.update_treeview()
        self._show_flash(msg, "green" if success else "red")

    def _cmd_update(self) -> None:
        if not self._editing_id or self.vm is None:
            return
        success, msg = self.vm.update_part(
            self._editing_id,
            self.number_entry.get(),
            self.location_entry.get(),
            self.notes_entry.get(),
        )
        if success:
            self._deselect()
            self.update_treeview()
        self._show_flash(msg, "green" if success else "red")

    def _cmd_delete(self) -> None:
        selected = self.tree.selection()
        if not selected or self.vm is None:
            self._show_flash(
                self.texts.get("part_no_selected", "No part selected."), "red"
            )
            return
        success, msg = self.vm.delete_part(selected[0])
        if success:
            self._deselect()
            self.update_treeview()
        self._show_flash(msg, "green" if success else "red")

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _make_confirm_duplicate(self):
        def confirm(part_number: str) -> bool:
            msg = self.texts.get(
                "part_exists_confirm",
                "Part number {} already exists. Add anyway?",
            ).format(part_number)
            return messagebox.askyesno(
                title=self.texts.get("part_exists_title", "Duplicate part"),
                message=msg,
                parent=self,
            )

        return confirm

    def _show_flash(self, message: str, color: str = "green") -> None:
        self.flash_lbl.configure(text=message, text_color=color)
        self.after(2500, lambda: self.flash_lbl.configure(text=""))

    def _go_back(self) -> None:
        if self.app_instance:
            self.app_instance.show_main_content()

    # ─── Language switch ──────────────────────────────────────────────────────

    def update_texts(self, new_texts: dict) -> None:
        self.texts = new_texts
        self.title_lbl.configure(text=new_texts.get("part_storage", "Leftovers"))
        self.search_lbl.configure(text=new_texts.get("part_search_label", "Hledat:"))
        self.search_entry.configure(
            placeholder_text=new_texts.get(
                "part_search_placeholder", "Search part number…"
            )
        )
        self.number_lbl.configure(
            text=new_texts.get("part_number_prompt", "Part number:")
        )
        self.location_lbl.configure(
            text=new_texts.get("part_location_prompt", "Location:")
        )
        self.notes_lbl.configure(text=new_texts.get("part_notes_prompt", "Notes:"))
        self.add_btn.configure(text=new_texts.get("part_add", "Add"))
        self.update_btn.configure(text=new_texts.get("part_update", "Update"))
        self.delete_btn.configure(text=new_texts.get("part_delete", "Delete"))
        self.back_btn.configure(text=new_texts.get("back_button", "Back"))
        self.tree.heading(
            "part_number", text=new_texts.get("part_col_number", "Part Number")
        )
        self.tree.heading(
            "location", text=new_texts.get("part_col_location", "Location")
        )
        self.tree.heading(
            "date_added", text=new_texts.get("part_col_date", "Date Added")
        )
        self.tree.heading(
            "notes", text=new_texts.get("part_col_notes", "Notes")
        )
