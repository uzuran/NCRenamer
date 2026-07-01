"""CounterWindow — floating status panel with operator controls."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.burn_table.viewmodels.burn_view_model import BurnViewModel


class CounterWindow(tk.Toplevel):
    """Separate popup window showing full table status and operator actions.

    Shows:
        - Used / free rows
        - Warning text
        - Last saved table file
        - Last loaded NC program number
        - Last loaded sheet count

    Buttons:
        - Load NC/SCH files
        - Convert and append to table
        - Refresh status
        - Close
    """

    def __init__(self, parent: tk.Widget, vm: BurnViewModel) -> None:
        super().__init__(parent)
        self._vm = vm

        self.title("Stav tabulky pálení")
        self.resizable(False, False)
        self.grab_set()  # Modal-like focus (doesn't block parent updates)

        self._build()
        self._vm.subscribe(self._on_vm_change)
        self._refresh_labels()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── build ────────────────────────────────────────────────────────────

    def _build(self) -> None:
        pad = {"padx": 12, "pady": 4}

        # ── Status section ────────────────────────────────────────────
        status_frame = ttk.LabelFrame(self, text="Stav tabulky", padding=8)
        status_frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))

        rows = [
            ("Použitých řádků:",  "_lbl_used"),
            ("Volných řádků:",    "_lbl_free"),
            ("Upozornění:",       "_lbl_warning"),
            ("Soubor tabulky:",   "_lbl_file"),
        ]
        for row_idx, (label_text, attr) in enumerate(rows):
            ttk.Label(status_frame, text=label_text, anchor="e", width=20).grid(
                row=row_idx, column=0, sticky="e", **pad
            )
            lbl = ttk.Label(status_frame, text="—", anchor="w", width=36)
            lbl.grid(row=row_idx, column=1, sticky="w", **pad)
            setattr(self, attr, lbl)

        # ── Pending record section ────────────────────────────────────
        pending_frame = ttk.LabelFrame(self, text="Načtený NC program", padding=8)
        pending_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=6)

        pending_rows = [
            ("Číslo programu:", "_lbl_prog_num"),
            ("Formát tabule:",  "_lbl_format"),
            ("Počet kusů:",     "_lbl_qty"),
            ("Datum:",          "_lbl_prog_date"),
        ]
        for row_idx, (label_text, attr) in enumerate(pending_rows):
            ttk.Label(pending_frame, text=label_text, anchor="e", width=20).grid(
                row=row_idx, column=0, sticky="e", **pad
            )
            lbl = ttk.Label(pending_frame, text="—", anchor="w", width=36)
            lbl.grid(row=row_idx, column=1, sticky="w", **pad)
            setattr(self, attr, lbl)

        # ── Operator field ────────────────────────────────────────────
        op_frame = ttk.LabelFrame(self, text="Operátor", padding=8)
        op_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=6)

        ttk.Label(op_frame, text="Jméno:").grid(row=0, column=0, sticky="e", **pad)
        self._operator_var = tk.StringVar()
        ttk.Entry(op_frame, textvariable=self._operator_var, width=30).grid(
            row=0, column=1, sticky="w", **pad
        )

        # ── Buttons ───────────────────────────────────────────────────
        btn_frame = ttk.Frame(self, padding=8)
        btn_frame.grid(row=3, column=0, sticky="ew", padx=14, pady=(6, 14))

        buttons = [
            ("📂  Načíst NC/SCH",       self._on_load_nc_sch),
            ("💾  Převést a přidat",    self._on_append),
            ("🔄  Obnovit stav",        self._on_refresh),
            ("✕  Zavřít",              self._on_close),
        ]
        for col_idx, (text, cmd) in enumerate(buttons):
            btn = ttk.Button(btn_frame, text=text, command=cmd, width=20)
            btn.grid(row=0, column=col_idx, padx=4)

        self.grid_columnconfigure(0, weight=1)

    # ── callbacks ────────────────────────────────────────────────────────

    def _on_load_nc_sch(self) -> None:
        """Open file dialogs for NC and optional SCH, then parse."""
        nc_path = filedialog.askopenfilename(
            title="Vyberte NC soubor",
            filetypes=[("NC soubory", "*.NC *.nc"), ("Všechny soubory", "*.*")],
            parent=self,
        )
        if not nc_path:
            return

        sch_path_str = filedialog.askopenfilename(
            title="Vyberte SCH soubor (nebo zrušit pro přeskočení)",
            filetypes=[
                ("SCH / XML soubory", "*.SCH *.sch *.xml *.XML"),
                ("Všechny soubory", "*.*"),
            ],
            parent=self,
        )

        operator = self._operator_var.get().strip()
        self._vm.load_nc_sch(
            nc_path=Path(nc_path),
            sch_path=Path(sch_path_str) if sch_path_str else None,
            operator=operator,
        )
        self._refresh_labels()

    def _on_append(self) -> None:
        """Append the pending record to the table."""
        if not self._vm.has_pending_record:
            messagebox.showinfo("Info", "Nejprve načtěte NC soubor.", parent=self)
            return
        if not self._vm.table_path:
            messagebox.showinfo("Info", "Nejprve načtěte tabulku.", parent=self)
            return
        self._vm.append_pending_record()
        self._refresh_labels()
        if self._vm.message_ok:
            messagebox.showinfo("Uloženo", self._vm.message, parent=self)
        else:
            messagebox.showerror("Chyba", self._vm.message, parent=self)

    def _on_refresh(self) -> None:
        self._vm.refresh_status()
        self._refresh_labels()

    def _on_close(self) -> None:
        self._vm.unsubscribe(self._on_vm_change)
        self.destroy()

    def _on_vm_change(self) -> None:
        self._refresh_labels()

    # ── label refresh ────────────────────────────────────────────────────

    def _refresh_labels(self) -> None:
        """Pull state from ViewModel and update all labels."""
        status = self._vm.status
        self._lbl_used.configure(text=str(status.used_rows))

        free_text = str(status.free_rows)
        self._lbl_free.configure(
            text=free_text,
            foreground=status.status_color,
        )
        self._lbl_warning.configure(
            text=status.status_text,
            foreground=status.status_color,
        )
        file_name = self._vm.table_path.name if self._vm.table_path else "—"
        self._lbl_file.configure(text=file_name)

        rec = self._vm.pending_record
        if rec:
            self._lbl_prog_num.configure(text=rec.program_number or "—")
            self._lbl_format.configure(text=rec.sheet_format or "—")
            self._lbl_qty.configure(text=str(rec.sheet_count) if rec.sheet_count else "—")
            self._lbl_prog_date.configure(text=rec.date or "—")
        else:
            for attr in ("_lbl_prog_num", "_lbl_format", "_lbl_qty", "_lbl_prog_date"):
                getattr(self, attr).configure(text="—")
