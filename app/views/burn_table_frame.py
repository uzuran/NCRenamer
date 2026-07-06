"""burn_table_frame.py — CTkFrame for the burn-table tab inside NCRenamer."""

from __future__ import annotations

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
    "note",
    "sheet_fmt",
    "count",
    "total_time",
    "burned",
    "product",
    "operator",
)
_COLUMN_WIDTHS = (120, 85, 75, 160, 50, 90, 65, 95, 95)
_MIN_WIDTHS = (80, 60, 55, 110, 35, 65, 45, 65, 65)


class _BurnTabContent(ctk.CTkFrame):
    """Per-material tab: toolbar + pending banner + tree + status bar."""

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
        self._build_toolbar()
        self._build_pending_banner()
        self._build_tree()
        self._build_status_bar()
        self.vm.subscribe(self._on_vm_change)

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
        if not messagebox.askyesno(
            title=self.texts.get("delete_record_title", "Delete record"),
            message=self.texts.get("delete_confirm_row", "Delete selected record?"),
            parent=self,
        ):
            return
        index = int(selected[0]) - 1  # iid is 1-based string
        self.vm.delete_record(index)

    def _cmd_print(self) -> None:
        self.vm.print_table()

    # ─── Observer ────────────────────────────────────────────────────────────

    def _on_vm_change(self) -> None:
        self._refresh_tree()
        self._refresh_pending_banner()
        self._refresh_status_bar()
        self._check_popup()

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
        for i, record in enumerate(self.vm.records, start=1):
            self.tree.insert("", "end", iid=str(i), values=record.to_row())

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
        self.delete_record_btn.configure(text=new_texts.get("delete_record", "Delete row"))
        self.print_btn.configure(text=new_texts.get("print_table", "Print"))
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
