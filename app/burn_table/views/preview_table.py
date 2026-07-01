"""PreviewTable — scrollable Treeview widget for the A–J burn table."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.burn_table.models.burn_record import BurnRecord

# Column definitions: (id, heading, width_px, anchor)
_COLUMNS: list[tuple[str, str, int, str]] = [
    ("date",          "Datum",        100, "center"),
    ("program",       "Číslo pr.",     90, "center"),
    ("note",          "Poznámka",      70, "w"),
    ("sheet_format",  "Formát tabule",210, "w"),
    ("sheet_count",   "Ks",            40, "center"),
    ("prog_time",     "Čas pr.",        60, "center"),
    ("total_time",    "Celk. čas",     80, "center"),
    ("burned",        "Vypáleno",      70, "center"),
    ("product_group", "Výrobek",      100, "w"),
    ("operator",      "Pálil",         70, "center"),
]


class PreviewTable(ttk.Frame):
    """A ttk.Treeview wrapped in a Frame with horizontal and vertical scrollbars.

    Displays all BurnRecord rows (columns A–J).  The widget is purely
    presentational — it receives data by calling ``load(records)``; it
    never writes to any file or ViewModel.
    """

    def __init__(self, master: tk.Widget, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._build()

    # ── public API ───────────────────────────────────────────────────────

    def load(self, records: list[BurnRecord]) -> None:
        """Replace the current treeview content with *records*."""
        self._tree.delete(*self._tree.get_children())
        for idx, rec in enumerate(records):
            tag = "even" if idx % 2 == 0 else "odd"
            self._tree.insert(
                "",
                "end",
                values=(
                    rec.date,
                    rec.program_number,
                    rec.note,
                    rec.sheet_format,
                    rec.sheet_count or "",
                    rec.program_time,
                    rec.total_time,
                    rec.burned,
                    rec.product_group,
                    rec.operator,
                ),
                tags=(tag,),
            )

    def clear(self) -> None:
        """Remove all rows from the treeview."""
        self._tree.delete(*self._tree.get_children())

    # ── private ─────────────────────────────────────────────────────────

    def _build(self) -> None:
        col_ids = [c[0] for c in _COLUMNS]
        self._tree = ttk.Treeview(
            self,
            columns=col_ids,
            show="headings",
            selectmode="browse",
        )

        for col_id, heading, width, anchor in _COLUMNS:
            self._tree.heading(col_id, text=heading, anchor="center")
            self._tree.column(col_id, width=width, anchor=anchor, minwidth=30)

        # Alternating row colours
        self._tree.tag_configure("even", background="#FFFFFF")
        self._tree.tag_configure("odd",  background="#EEF2F8")

        # Scrollbars
        vsb = ttk.Scrollbar(self, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Layout
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
