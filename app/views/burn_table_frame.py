"""burn_table_frame.py — CTkFrame for the burn-table tab inside NCRenamer."""

from __future__ import annotations

import dataclasses
from datetime import date as _date
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from app.burn_table.viewmodels.burn_view_model import BurnViewModel

_COLUMN_IDS = (
    "date",
    "program",
    "sheet_fmt",
    "count",
    "total_time",
    "burned",
    "product",
    "operator",
)
_COLUMN_WIDTHS = (120, 85, 160, 50, 90, 65, 95, 95)
_MIN_WIDTHS = (80, 60, 110, 35, 65, 45, 65, 65)

# Maps each treeview column to its BurnRecord attribute and edit entry width.
# (text_key, attr_name, entry_width, fallback_label)
_EDIT_FIELDS = (
    ("col_date", "date", 70, "Date"),
    ("col_program", "program_number", 80, "Program"),
    ("col_sheet_fmt", "sheet_format", 150, "Format"),
    ("col_count", "sheet_count", 45, "Count"),
    ("col_total_time", "total_time", 70, "Time"),
    ("col_burned", "burned", 55, "Burned"),
    ("col_product", "product_group", 90, "Product"),
    ("col_operator", "operator", 85, "Operator"),
)


class _BurnTabContent(ctk.CTkFrame):
    """Per-material tab: toolbar + edit panel + pending banner + tree + status bar."""

    def __init__(
        self,
        master,
        view_model: BurnViewModel,
        texts: dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.vm = view_model
        self.texts = texts or {}
        self._editing_index: int | None = None

        self._build_toolbar()
        self._build_pending_banner()
        self._build_edit_panel()
        self._build_tree()
        self._build_status_bar()
        self.vm.subscribe(self._on_vm_change)
        self.vm.set_confirm_duplicate(self._make_confirm_duplicate())

    # ─── Build ───────────────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(4, 0), padx=10)

        self.load_nc_btn = ctk.CTkButton(
            bar,
            text=self.texts.get("load_nc_sch", "Load NC/SCH"),
            width=105,
            command=self._cmd_load_nc_sch,
        )
        self.load_nc_btn.pack(side="left", padx=2)

        self.clear_table_btn = ctk.CTkButton(
            bar,
            text=self.texts.get("clear_table", "Clear table"),
            width=115,
            fg_color="#c0392b",
            hover_color="#922b21",
            command=self._cmd_clear_table,
        )
        self.clear_table_btn.pack(side="left", padx=2)

        self.delete_record_btn = ctk.CTkButton(
            bar,
            text=self.texts.get("delete_record", "Delete row"),
            width=100,
            fg_color="#922b21",
            hover_color="#6e1f18",
            command=self._cmd_delete_record,
        )
        self.delete_record_btn.pack(side="left", padx=2)

        self.print_btn = ctk.CTkButton(
            bar,
            text=self.texts.get("print_table", "Print"),
            width=65,
            command=self._cmd_print,
        )
        self.print_btn.pack(side="right", padx=2)

    def _build_pending_banner(self) -> None:
        self.pending_frame = ctk.CTkFrame(
            self,
            fg_color=("#d9f7d9", "#1a4d1a"),
            corner_radius=4,
        )
        self.pending_lbl = ctk.CTkLabel(
            self.pending_frame,
            text="",
            anchor="w",
            wraplength=950,
        )
        self.pending_lbl.pack(fill="x", padx=10, pady=4)
        # Hidden until a pending record exists

    def _build_edit_panel(self) -> None:
        """Build the inline edit panel (hidden until a row is selected)."""
        self.edit_frame = ctk.CTkFrame(
            self, fg_color=("#ddeeff", "#1a2d4a"), corner_radius=4
        )

        inner = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=4)

        self._edit_entries: dict[str, ctk.CTkEntry] = {}
        self._edit_labels: dict[str, ctk.CTkLabel] = {}

        small_font = ctk.CTkFont(size=10)

        for text_key, attr, width, fallback in _EDIT_FIELDS:
            col_f = ctk.CTkFrame(inner, fg_color="transparent")
            col_f.pack(side="left", padx=3)

            lbl = ctk.CTkLabel(
                col_f,
                text=self.texts.get(text_key, fallback),
                font=small_font,
                anchor="w",
            )
            lbl.pack(anchor="w")
            self._edit_labels[attr] = lbl

            entry = ctk.CTkEntry(col_f, width=width)
            entry.pack()
            self._edit_entries[attr] = entry

        # Action buttons stacked to the right
        btn_col = ctk.CTkFrame(inner, fg_color="transparent")
        btn_col.pack(side="left", padx=(10, 0))

        self.update_record_btn = ctk.CTkButton(
            btn_col,
            text=self.texts.get("update_record", "Save changes"),
            width=100,
            fg_color="#1a6b3c",
            hover_color="#145530",
            command=self._cmd_update_record,
        )
        self.update_record_btn.pack(pady=(14, 3))

        self.cancel_edit_btn = ctk.CTkButton(
            btn_col,
            text=self.texts.get("cancel_edit_record", "Unselect"),
            width=100,
            fg_color="gray40",
            hover_color="gray30",
            command=self._deselect,
        )
        self.cancel_edit_btn.pack()
        # Panel stays hidden until on_tree_select fires

    def _build_tree(self) -> None:
        self.tree_container = ctk.CTkFrame(self)
        self.tree_container.pack(fill="both", expand=True, padx=10, pady=(4, 0))

        scrollbar_y = ttk.Scrollbar(self.tree_container, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")

        scrollbar_x = ttk.Scrollbar(self.tree_container, orient="horizontal")
        scrollbar_x.pack(side="bottom", fill="x")

        self.tree = ttk.Treeview(
            self.tree_container,
            columns=_COLUMN_IDS,
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )
        self.tree.pack(fill="both", expand=True)

        scrollbar_y.configure(command=self.tree.yview)
        scrollbar_x.configure(command=self.tree.xview)

        self._configure_columns()

        # Non-interactive filler rows shown in muted gray
        self.tree.tag_configure("sep_row", foreground="gray55")  # blank batch separator
        self.tree.tag_configure("free_row", foreground="gray55")  # remaining free space

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Escape>", lambda e: self._deselect())

    def _configure_columns(self) -> None:
        for col_id, width, min_w in zip(
            _COLUMN_IDS, _COLUMN_WIDTHS, _MIN_WIDTHS, strict=False
        ):
            header = self.texts.get(f"col_{col_id}", col_id.replace("_", " ").title())
            self.tree.heading(col_id, text=header)
            self.tree.column(
                col_id, width=width, minwidth=min_w, stretch=True, anchor="center"
            )

    def _build_status_bar(self) -> None:
        self.status_lbl = ctk.CTkLabel(
            self,
            text="",
            anchor="w",
            text_color="gray50",
        )
        self.status_lbl.pack(fill="x", padx=12, pady=(2, 6))

    # ─── Tree selection / edit panel ─────────────────────────────────────────

    def on_tree_select(self, event=None) -> None:
        """Populate the edit panel when the user selects a row."""
        selected = self.tree.selection()
        if not selected:
            self._reset_edit_state()
            return

        iid = selected[0]
        if iid.startswith("sep_") or iid.startswith("free_"):
            self.tree.selection_remove(iid)
            return

        index = int(iid) - 1  # iid is 1-based
        records = self.vm.records
        if not (0 <= index < len(records)):
            self._reset_edit_state()
            return

        self._editing_index = index
        rec = records[index]

        values = {
            "date": rec.date,
            "program_number": rec.program_number,
            "sheet_format": rec.sheet_format,
            "sheet_count": str(rec.sheet_count) if rec.sheet_count else "",
            "total_time": rec.total_time,
            "burned": rec.burned,
            "product_group": rec.product_group,
            "operator": rec.operator,
        }
        for attr, entry in self._edit_entries.items():
            entry.delete(0, "end")
            entry.insert(0, values.get(attr, ""))

        self._show_edit_panel()

    def _reset_edit_state(self) -> None:
        """Clear all edit entries and hide the edit panel."""
        self._editing_index = None
        for entry in self._edit_entries.values():
            entry.delete(0, "end")
        self._hide_edit_panel()

    def _deselect(self, event=None) -> None:
        """Clear the treeview selection → triggers on_tree_select with empty selection."""
        for iid in self.tree.selection():
            self.tree.selection_remove(iid)

    def _on_tree_click(self, event) -> None:
        row = self.tree.identify_row(event.y)
        if row and (row.startswith("sep_") or row.startswith("free_")):
            self._deselect()
            return
        # Empty-area click (not row) or re-click on the selected row both deselect.
        if not row or row in self.tree.selection():
            self._deselect()

    def _show_edit_panel(self) -> None:
        if not self.edit_frame.winfo_ismapped():
            self.edit_frame.pack(
                fill="x",
                padx=10,
                pady=(2, 0),
                before=self.tree_container,
            )

    def _hide_edit_panel(self) -> None:
        self.edit_frame.pack_forget()

    # ─── Duplicate confirmation ───────────────────────────────────────────────

    def _make_confirm_duplicate(self):
        """Return a callable that shows an askyesno dialog for each duplicate.

        The callable is injected into the ViewModel via ``set_confirm_duplicate``
        so the ViewModel never imports tkinter directly.  Because it closes over
        *self* the message is automatically re-translated whenever
        ``update_texts`` swaps ``self.texts``.
        """
        def confirm(program_number: str, sheet_name: str) -> bool:
            msg = self.texts.get(
                "dup_confirm_override",
                "Program {} already exists in {}. Add anyway?",
            ).format(program_number, sheet_name)
            return messagebox.askyesno(
                title=self.texts.get("duplicate_warning_title", "Duplicitní program"),
                message=msg,
                parent=self,
            )
        return confirm

    # ─── Commands ────────────────────────────────────────────────────────────

    def _cmd_load_nc_sch(self) -> None:
        nc_strs = filedialog.askopenfilenames(
            title=self.texts.get("select_nc_file", "Select NC file(s)"),
            filetypes=[
                ("NC files", "*.NC"),
                ("NC files", "*.nc"),
                ("All files", "*.*"),
            ],
        )
        if not nc_strs:
            return

        today = _date.today().strftime("%d.%m.%Y")
        date_str = (
            simpledialog.askstring(
                title=self.texts.get("product_group_dialog_title", "Load NC/SCH"),
                prompt=self.texts.get("date_prompt", "Datum pálení:"),
                initialvalue=today,
                parent=self,
            )
            or ""
        )

        product_group = (
            simpledialog.askstring(
                title=self.texts.get("product_group_dialog_title", "Load NC/SCH"),
                prompt=self.texts.get("product_group_prompt", "Product type:"),
                parent=self,
            )
            or ""
        )

        nc_paths = [Path(p) for p in nc_strs]
        self.vm.load_and_append_batch(nc_paths, product_group, date=date_str)

    def _cmd_clear_table(self) -> None:
        if self.vm.table_path is None:
            return
        if messagebox.askyesno(
            title=self.texts.get("clear_table", "Clear table"),
            message=self.texts.get("clear_confirm", "Delete all records from table?"),
            parent=self,
        ):
            self.vm.clear_table()

    def _cmd_delete_record(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        if selected[0].startswith("sep_") or selected[0].startswith("free_"):
            return
        if not messagebox.askyesno(
            title=self.texts.get("delete_record_title", "Delete record"),
            message=self.texts.get("delete_confirm_row", "Delete selected record?"),
            parent=self,
        ):
            return
        index = int(selected[0]) - 1  # iid is 1-based string
        self._reset_edit_state()
        self.vm.delete_record(index)

    def _cmd_update_record(self) -> None:
        if self._editing_index is None:
            return

        records = self.vm.records
        if not (0 <= self._editing_index < len(records)):
            self._reset_edit_state()
            return

        original = records[self._editing_index]

        count_str = self._edit_entries["sheet_count"].get().strip()
        try:
            sheet_count = int(count_str) if count_str else 0
        except ValueError:
            sheet_count = 0

        updated = dataclasses.replace(
            original,
            date=self._edit_entries["date"].get().strip(),
            program_number=self._edit_entries["program_number"].get().strip(),
            sheet_format=self._edit_entries["sheet_format"].get().strip(),
            sheet_count=sheet_count,
            total_time=self._edit_entries["total_time"].get().strip(),
            burned=self._edit_entries["burned"].get().strip(),
            product_group=self._edit_entries["product_group"].get().strip(),
            operator=self._edit_entries["operator"].get().strip(),
        )

        index = self._editing_index
        self._reset_edit_state()
        self.vm.update_record(index, updated)

    def _cmd_print(self) -> None:
        self.vm.print_table()

    # ─── Observer ────────────────────────────────────────────────────────────

    def _on_vm_change(self) -> None:
        self._refresh_tree()
        self._refresh_pending_banner()
        self._refresh_status_bar()
        self._check_popup()
        # Tree was fully re-rendered; clear any lingering edit state.
        self._reset_edit_state()

    def _check_popup(self) -> None:
        msg = self.vm.popup_message
        if msg:
            self.vm.clear_popup()
            messagebox.showwarning(
                title=self.texts.get("duplicate_warning_title", "Duplicitní program"),
                message=msg,
                parent=self,
            )

    def _refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        empty = ("",) * len(_COLUMN_IDS)
        data_idx = 0
        sep_idx = 0
        for row in self.vm.display_rows:
            if row is None:
                sep_idx += 1
                self.tree.insert(
                    "", "end", iid=f"sep_{sep_idx}", values=empty, tags=("sep_row",)
                )
            else:
                data_idx += 1
                self.tree.insert("", "end", iid=str(data_idx), values=row.to_row())
        # Remaining physical slots (separator rows also occupy Excel rows)
        free_slots = max(0, self.vm.status.free_rows - sep_idx)
        for n in range(1, free_slots + 1):
            self.tree.insert(
                "", "end", iid=f"free_{n}", values=empty, tags=("free_row",)
            )

    def _refresh_pending_banner(self) -> None:
        if self.vm.has_pending_record:
            rec = self.vm.pending_record
            if rec is None:
                return
            has_table = self.vm.table_path is not None

            operator_part = (
                f"  |  {self.texts.get('col_product', 'Product type')}: {rec.product_group}"
                if rec.product_group
                else ""
            )
            text = (
                f"{self.texts.get('pending_record', 'Pending')}: "
                f"{rec.date}  |  {rec.program_number}  |  {rec.sheet_format}"
                f"{operator_part}"
            )
            if not has_table:
                text += f"  —  {self.texts.get('no_table_hint', 'Create or load a table first!')}"

            banner_color = (
                ("#d9f7d9", "#1a4d1a") if has_table else ("#fff3cd", "#5a4000")
            )
            self.pending_frame.configure(fg_color=banner_color)
            self.pending_lbl.configure(text=text)
            if not self.pending_frame.winfo_ismapped():
                self.pending_frame.pack(
                    fill="x",
                    padx=10,
                    pady=(0, 4),
                    before=self.tree_container,
                )
        else:
            self.pending_frame.pack_forget()

    def _refresh_status_bar(self) -> None:
        parts: list[str] = []

        if self.vm.table_path:
            parts.append(self.vm.table_path.name)
            st = self.vm.status
            parts.append(
                self.texts.get("free_rows", "Free rows: {}").format(st.free_rows)
            )
            if st.warning:
                parts.append(st.warning)

        if self.vm.message:
            color = "green" if self.vm.message_ok else "red"
            prefix = "  |  ".join(parts) + "   —   " if parts else ""
            self.status_lbl.configure(
                text=f"{prefix}{self.vm.message}",
                text_color=color,
            )
        elif parts:
            self.status_lbl.configure(text="  |  ".join(parts), text_color="gray50")
        else:
            self.status_lbl.configure(
                text=self.texts.get("status_no_table", "No table loaded"),
                text_color="gray50",
            )

    # ─── Language switch ─────────────────────────────────────────────────────

    def update_texts(self, new_texts: dict) -> None:
        self.texts = new_texts
        self.load_nc_btn.configure(text=new_texts.get("load_nc_sch", "Load NC/SCH"))
        self.clear_table_btn.configure(text=new_texts.get("clear_table", "Clear table"))
        self.delete_record_btn.configure(
            text=new_texts.get("delete_record", "Delete row")
        )
        self.print_btn.configure(text=new_texts.get("print_table", "Print"))
        self.update_record_btn.configure(
            text=new_texts.get("update_record", "Save changes")
        )
        self.cancel_edit_btn.configure(
            text=new_texts.get("cancel_edit_record", "Unselect")
        )
        for text_key, attr, _, fallback in _EDIT_FIELDS:
            self._edit_labels[attr].configure(text=new_texts.get(text_key, fallback))
        self._configure_columns()
        self._refresh_status_bar()


class BurnTableFrame(ctk.CTkFrame):
    """Container with Steel and Aluminium tabs, each backed by its own BurnViewModel."""

    def __init__(
        self,
        master,
        app_instance,
        vm_steel: BurnViewModel,
        vm_aluminium: BurnViewModel,
        texts: dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.app = app_instance
        self.texts = texts or {}
        self._build_top_bar()
        self._build_tabs(vm_steel, vm_aluminium)

    # ─── Build ───────────────────────────────────────────────────────────────

    def _build_top_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(10, 0), padx=10)

        self.back_btn = ctk.CTkButton(
            bar,
            text=self.texts.get("back_button", "Back"),
            width=70,
            command=self._go_back,
        )
        self.back_btn.pack(side="left")

        self.title_lbl = ctk.CTkLabel(
            bar,
            text=self.texts.get("burn_table", "Burn Table"),
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.title_lbl.pack(side="left", padx=12)

    def _go_back(self) -> None:
        self.app.show_main_content()

    def _build_tabs(self, vm_steel: BurnViewModel, vm_aluminium: BurnViewModel) -> None:
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=4, pady=(4, 4))

        steel_name = self.texts.get("tab_steel", "Ocel")
        alu_name = self.texts.get("tab_aluminium", "Hliník")

        tab_steel_frame = self.tabview.add(steel_name)
        tab_alu_frame = self.tabview.add(alu_name)

        self.steel_tab = _BurnTabContent(tab_steel_frame, vm_steel, self.texts)
        self.steel_tab.pack(fill="both", expand=True)

        self.alu_tab = _BurnTabContent(tab_alu_frame, vm_aluminium, self.texts)
        self.alu_tab.pack(fill="both", expand=True)

    # ─── Language switch ─────────────────────────────────────────────────────

    def update_texts(self, new_texts: dict) -> None:
        self.texts = new_texts
        self.back_btn.configure(text=new_texts.get("back_button", "Back"))
        self.title_lbl.configure(text=new_texts.get("burn_table", "Burn Table"))
        self.steel_tab.update_texts(new_texts)
        self.alu_tab.update_texts(new_texts)
