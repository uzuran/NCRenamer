"""todo_frame.py — Todo list frame, mirrors the materials add/edit UI."""

from __future__ import annotations

from tkinter import ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from app.viewmodels.todo_view_model import TodoViewModel


class TodoFrame(ctk.CTkFrame):
    """Full todo list: add, edit, toggle done, delete — same UX as materials."""

    def __init__(
        self,
        master=None,
        view_model: TodoViewModel | None = None,
        app_instance=None,
        texts: dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.vm = view_model
        self.app_instance = app_instance
        self.texts = texts or {}

        # ID of the currently selected item; None = add mode.
        self._editing_id: str | None = None

        self._build()

    # ─── Build ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Title
        self.title_lbl = ctk.CTkLabel(
            self,
            text=self.texts.get("todo_list", "Todo List"),
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.title_lbl.pack(pady=(12, 6))

        # Entry field
        self.text_entry = ctk.CTkEntry(
            self,
            placeholder_text=self.texts.get("todo_add_placeholder", "New task…"),
            width=320,
        )
        self.text_entry.pack(pady=(0, 6))

        # Button row 1: Add + Delete (always visible)
        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(pady=(0, 4))

        self.add_btn = ctk.CTkButton(
            row1,
            text=self.texts.get("todo_add", "Add"),
            width=120,
            command=self._cmd_add,
        )
        self.add_btn.pack(side="left", padx=6)

        self.delete_btn = ctk.CTkButton(
            row1,
            text=self.texts.get("todo_remove", "Delete"),
            width=120,
            fg_color="#922b21",
            hover_color="#6e1f18",
            command=self._cmd_delete,
        )
        self.delete_btn.pack(side="left", padx=6)

        # Button row 2: Update + Toggle Done (enabled only on selection)
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(pady=(0, 4))

        self.update_btn = ctk.CTkButton(
            row2,
            text=self.texts.get("todo_update", "Update"),
            width=120,
            state="disabled",
            command=self._cmd_update,
        )
        self.update_btn.pack(side="left", padx=6)

        self.done_btn = ctk.CTkButton(
            row2,
            text=self.texts.get("todo_mark_done", "Mark done"),
            width=120,
            state="disabled",
            fg_color="#1a6b3c",
            hover_color="#145530",
            command=self._cmd_toggle_done,
        )
        self.done_btn.pack(side="left", padx=6)

        # Flash label
        flash_frame = ctk.CTkFrame(self, fg_color="transparent")
        flash_frame.pack()
        self.flash_lbl = ctk.CTkLabel(flash_frame, text="")
        self.flash_lbl.pack()

        # Treeview
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=6)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("status", "text", "date"),
            show="headings",
        )
        self.tree.heading("status", text=self.texts.get("todo_col_status", "✓"))
        self.tree.heading("text", text=self.texts.get("todo_col_text", "Task"))
        self.tree.heading("date", text=self.texts.get("todo_col_date", "Date"))
        self.tree.column(
            "status", width=40, minwidth=30, anchor="center", stretch=False
        )
        self.tree.column("text", width=220, minwidth=80, anchor="w", stretch=True)
        self.tree.column(
            "date", width=155, minwidth=155, anchor="center", stretch=False
        )

        # Done items shown in gray
        self.tree.tag_configure("done", foreground="gray60")
        self.tree.tag_configure("pending", foreground="")

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
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
        """Reload the treeview from the ViewModel."""
        self.tree.delete(*self.tree.get_children())
        if self.vm is None:
            return
        for item in self.vm.get_items():
            done = item.get("done", False)
            status = "✓" if done else "○"
            tag = "done" if done else "pending"
            raw_date = item.get("created_at", "")
            try:
                parts = raw_date.split()
                y, m, d = parts[0].split("-")
                time_part = f" {parts[1]}" if len(parts) == 2 else ""
                date_str = f"{d}.{m}.{y}{time_part}"
            except Exception:
                date_str = raw_date or "—"
            self.tree.insert(
                "",
                "end",
                iid=item["id"],
                values=(status, item["text"], date_str),
                tags=(tag,),
            )

    # ─── Selection handling (mirrors add_material_frame.py) ──────────────────

    def _on_tree_select(self, event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            self._reset_edit_state()
            return

        self._editing_id = selected[0]  # iid == item UUID

        values = self.tree.item(self._editing_id, "values")
        text = values[1] if len(values) > 1 else ""
        is_done = values[0] == "✓"

        self.text_entry.delete(0, "end")
        self.text_entry.insert(0, text)

        self.update_btn.configure(state="normal")
        self.done_btn.configure(
            state="normal",
            text=self.texts.get("todo_mark_pending", "Mark pending")
            if is_done
            else self.texts.get("todo_mark_done", "Mark done"),
        )
        self.add_btn.configure(state="disabled")

    def _reset_edit_state(self) -> None:
        self._editing_id = None
        self.text_entry.delete(0, "end")
        self.update_btn.configure(state="disabled")
        self.done_btn.configure(
            state="disabled",
            text=self.texts.get("todo_mark_done", "Mark done"),
        )
        self.add_btn.configure(state="normal")

    def _deselect(self, event=None) -> None:
        for iid in self.tree.selection():
            self.tree.selection_remove(iid)

    def _on_tree_click(self, event) -> None:
        row = self.tree.identify_row(event.y)
        # Empty-area click (not row) or re-click on the selected row both deselect.
        if not row or row in self.tree.selection():
            self._deselect()

    def _on_tree_double_click(self, event) -> None:
        row = self.tree.identify_row(event.y)
        if not row:
            return
        values = self.tree.item(row, "values")
        text = values[1] if len(values) > 1 else ""
        if not text:
            return
        popup = ctk.CTkToplevel(self)
        popup.title(self.texts.get("todo_detail_title", "Task detail"))
        popup.geometry("420x280")
        popup.after(100, popup.grab_set)
        textbox = ctk.CTkTextbox(popup, wrap="word")
        textbox.pack(fill="both", expand=True, padx=12, pady=(12, 6))
        textbox.insert("1.0", text)
        textbox.configure(state="disabled")
        ctk.CTkButton(
            popup,
            text=self.texts.get("about_close", "Close"),
            command=popup.destroy,
        ).pack(pady=(0, 12))

    # ─── Commands ─────────────────────────────────────────────────────────────

    def _cmd_add(self) -> None:
        text = self.text_entry.get()
        if self.vm is None:
            return
        success, msg = self.vm.add_item(text)
        if success:
            self.text_entry.delete(0, "end")
            self.update_treeview()
        self._show_flash(msg, "green" if success else "red")

    def _cmd_update(self) -> None:
        if not self._editing_id or self.vm is None:
            return
        text = self.text_entry.get()
        success, msg = self.vm.update_item(self._editing_id, text)
        if success:
            self._deselect()
            self.update_treeview()
        self._show_flash(msg, "green" if success else "red")

    def _cmd_toggle_done(self) -> None:
        if not self._editing_id or self.vm is None:
            return
        success, msg = self.vm.toggle_done(self._editing_id)
        if success:
            self._deselect()
            self.update_treeview()
        self._show_flash(msg, "green" if success else "red")

    def _cmd_delete(self) -> None:
        selected = self.tree.selection()
        if not selected or self.vm is None:
            self._show_flash(
                self.texts.get("todo_no_selected", "No task selected."), "red"
            )
            return
        item_id = selected[0]
        success, msg = self.vm.delete_item(item_id)
        if success:
            self._deselect()
            self.update_treeview()
        self._show_flash(msg, "green" if success else "red")

    # ─── Utilities ────────────────────────────────────────────────────────────

    def _show_flash(self, message: str, color: str = "green") -> None:
        self.flash_lbl.configure(text=message, text_color=color)
        self.after(2500, lambda: self.flash_lbl.configure(text=""))

    def _go_back(self) -> None:
        if self.app_instance:
            self.app_instance.show_main_content()

    # ─── Language switch ──────────────────────────────────────────────────────

    def update_texts(self, new_texts: dict) -> None:
        self.texts = new_texts
        self.title_lbl.configure(text=new_texts.get("todo_list", "Todo List"))
        self.text_entry.configure(
            placeholder_text=new_texts.get("todo_add_placeholder", "New task…")
        )
        self.add_btn.configure(text=new_texts.get("todo_add", "Add"))
        self.delete_btn.configure(text=new_texts.get("todo_remove", "Delete"))
        self.update_btn.configure(text=new_texts.get("todo_update", "Update"))
        self.back_btn.configure(text=new_texts.get("back_button", "Back"))
        self.tree.heading("status", text=new_texts.get("todo_col_status", "✓"))
        self.tree.heading("text", text=new_texts.get("todo_col_text", "Task"))
        self.tree.heading("date", text=new_texts.get("todo_col_date", "Date"))
        # Done button label depends on current selection state
        if self._editing_id:
            values = (
                self.tree.item(self._editing_id, "values")
                if self.tree.exists(self._editing_id)
                else ()
            )
            is_done = len(values) > 0 and values[0] == "✓"
            self.done_btn.configure(
                text=new_texts.get("todo_mark_pending", "Mark pending")
                if is_done
                else new_texts.get("todo_mark_done", "Mark done")
            )
        else:
            self.done_btn.configure(text=new_texts.get("todo_mark_done", "Mark done"))
