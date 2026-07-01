"""PrintPreview — read-only table preview with print and PDF export."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.burn_table.viewmodels.burn_view_model import BurnViewModel

from app.burn_table.views.preview_table import PreviewTable


class PrintPreview(tk.Toplevel):
    """A separate window that shows the full table for review before printing.

    Contains:
        - A read-only PreviewTable (full A–J columns)
        - Print button
        - Export PDF button
        - Close button
    """

    def __init__(self, parent: tk.Widget, vm: BurnViewModel) -> None:
        super().__init__(parent)
        self._vm = vm

        self.title("Náhled tisku — Tabulka pálení")
        self.minsize(900, 480)
        self.resizable(True, True)

        self._build()
        self._load_data()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ── build ────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # ── Title bar ─────────────────────────────────────────────────
        header = ttk.Label(
            self,
            text="Náhled tabulky pálení",
            font=("Arial", 13, "bold"),
            anchor="center",
        )
        header.pack(fill="x", padx=10, pady=(10, 4))

        # ── File name label ───────────────────────────────────────────
        file_name = (
            self._vm.table_path.name if self._vm.table_path else "—"
        )
        self._file_label = ttk.Label(
            self, text=f"Soubor: {file_name}", anchor="center",
            foreground="#555555",
        )
        self._file_label.pack(fill="x", padx=10)

        # ── Preview table ─────────────────────────────────────────────
        self._preview = PreviewTable(self)
        self._preview.pack(fill="both", expand=True, padx=10, pady=8)

        # ── Button row ────────────────────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(
            btn_frame, text="🖨  Tisk", width=16, command=self._on_print
        ).pack(side="left", padx=4)

        ttk.Button(
            btn_frame, text="📄  Export PDF", width=16, command=self._on_export_pdf
        ).pack(side="left", padx=4)

        ttk.Button(
            btn_frame, text="Zavřít", width=12, command=self.destroy
        ).pack(side="right", padx=4)

    # ── data loading ─────────────────────────────────────────────────────

    def _load_data(self) -> None:
        self._preview.load(self._vm.records)

    # ── button handlers ──────────────────────────────────────────────────

    def _on_print(self) -> None:
        self._vm.print_table()
        if not self._vm.message_ok:
            messagebox.showerror("Chyba tisku", self._vm.message, parent=self)
        else:
            messagebox.showinfo("Tisk", "Tisková úloha odeslána.", parent=self)

    def _on_export_pdf(self) -> None:
        if not self._vm.table_path:
            messagebox.showinfo(
                "Info", "Není načtena žádná tabulka.", parent=self
            )
            return

        output_str = filedialog.asksaveasfilename(
            title="Uložit PDF jako…",
            defaultextension=".pdf",
            filetypes=[("PDF soubory", "*.pdf")],
            initialfile=self._vm.table_path.stem + ".pdf",
            parent=self,
        )
        if not output_str:
            return

        self._vm.export_pdf(Path(output_str))
        if self._vm.message_ok:
            messagebox.showinfo("Export", self._vm.message, parent=self)
        else:
            messagebox.showerror("Chyba exportu", self._vm.message, parent=self)
