"""BurnDashboard — main window of the burn-table application."""

from __future__ import annotations

import contextlib
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.burn_table.viewmodels.burn_view_model import BurnViewModel

from app.burn_table.views.counter_window import CounterWindow
from app.burn_table.views.preview_table import PreviewTable
from app.burn_table.views.print_preview import PrintPreview


class BurnDashboard(ttk.Frame):
    """Main application frame: toolbar → table preview → status bar.

    Subscribes to BurnViewModel changes and refreshes the UI
    automatically.  Contains no business logic — every action delegates
    to the ViewModel.

    Can be embedded inside an existing Tk root or used standalone via
    ``BurnDashboard.launch()``.
    """

    _WARN_BG = "#FFF3CD"
    _CRIT_BG = "#F8D7DA"
    _OK_BG = "#D1ECE1"

    def __init__(self, master: tk.Widget, vm: BurnViewModel) -> None:
        super().__init__(master)
        self._vm = vm
        self._counter_win: CounterWindow | None = None

        self._build()
        self._vm.subscribe(self._on_vm_change)
        self._vm.load_last_table()

    # ══════════════════════════════════════════════════════════════════
    # Build
    # ══════════════════════════════════════════════════════════════════

    def _build(self) -> None:
        self.pack(fill="both", expand=True)
        self._build_toolbar()
        self._build_preview()
        self._build_status_bar()

    def _build_toolbar(self) -> None:
        tb = ttk.Frame(self, relief="ridge", padding=4)
        tb.pack(fill="x", side="top")

        buttons: list[tuple[str, Callable[[], None]]] = [
            ("📂  Načíst tabulku", self._on_load_table),
            ("+  Nová tabulka", self._on_new_table),
            ("🗂  Načíst NC/SCH", self._on_load_nc_sch),
            ("🖨  Tisk", self._on_print),
            ("📄  Export PDF", self._on_export_pdf),
            ("📊  Otevřít počítadlo", self._on_open_counter),
        ]
        for text, cmd in buttons:
            ttk.Button(tb, text=text, command=cmd, width=18).pack(
                side="left", padx=3, pady=2
            )

        # Pending record indicator (right side of toolbar)
        self._pending_var = tk.StringVar(value="")
        self._pending_label = ttk.Label(
            tb, textvariable=self._pending_var, foreground="#005588"
        )
        self._pending_label.pack(side="right", padx=8)

    def _build_preview(self) -> None:
        self._preview = PreviewTable(self)
        self._preview.pack(fill="both", expand=True, padx=6, pady=4)

    def _build_status_bar(self) -> None:
        self._status_bar = tk.Label(
            self,
            text="Žádná tabulka není načtena",
            anchor="w",
            relief="sunken",
            padx=8,
            pady=3,
            font=("Arial", 9),
        )
        self._status_bar.pack(fill="x", side="bottom")

    # ══════════════════════════════════════════════════════════════════
    # ViewModel observer
    # ══════════════════════════════════════════════════════════════════

    def _on_vm_change(self) -> None:
        """Called by the ViewModel after every state change."""
        self._refresh_preview()
        self._refresh_status_bar()
        self._refresh_pending_label()
        self._maybe_show_warning_popup()

    def _refresh_preview(self) -> None:
        self._preview.load(self._vm.records)

    def _refresh_status_bar(self) -> None:
        status = self._vm.status
        msg = self._vm.message

        if msg:
            colour = self._OK_BG if self._vm.message_ok else self._CRIT_BG
            self._status_bar.configure(text=msg, background=colour)
        else:
            colour = {
                "critical": self._CRIT_BG,
                "warning": self._WARN_BG,
            }.get(status.warning, self._OK_BG)
            self._status_bar.configure(text=status.status_text, background=colour)

    def _refresh_pending_label(self) -> None:
        rec = self._vm.pending_record
        if rec:
            self._pending_var.set(
                f"⏳  Připraveno k uložení: {rec.program_number or '(bez čísla)'}"
            )
        else:
            self._pending_var.set("")

    # Tracks whether a warning popup is already visible to avoid duplicates.
    _popup_open: bool = False

    def _maybe_show_warning_popup(self) -> None:
        """Show a warning popup when the table is running low on free rows."""
        if self._popup_open:
            return
        status = self._vm.status
        if status.warning == "critical":
            self._show_warning_popup(
                "KRITICKÉ UPOZORNĚNÍ",
                f"V tabulce pálení zbývají pouze {status.free_rows} volné řádky!\n"
                "Brzy bude potřeba vytvořit novou tabulku.",
                level="critical",
            )
        elif status.warning == "warning":
            self._show_warning_popup(
                "Upozornění",
                f"V tabulce pálení zbývá {status.free_rows} volných řádků.",
                level="warning",
            )

    def _show_warning_popup(self, title: str, message: str, level: str) -> None:
        """Display a non-blocking popup warning."""

        popup = tk.Toplevel(self)
        popup.title(title)
        popup.resizable(False, False)
        popup.grab_set()
        BurnDashboard._popup_open = True

        bg = "#F8D7DA" if level == "critical" else "#FFF3CD"
        popup.configure(background=bg)

        icon = "🔴" if level == "critical" else "⚠️"
        tk.Label(
            popup,
            text=f"{icon}  {message}",
            background=bg,
            font=("Arial", 10),
            wraplength=340,
            justify="left",
            padx=16,
            pady=12,
        ).pack()

        tk.Label(
            popup,
            text="(Toto je pouze upozornění — žádná automatická akce neproběhla.)",
            background=bg,
            foreground="#666666",
            font=("Arial", 8),
            padx=16,
        ).pack()

        def _close() -> None:
            BurnDashboard._popup_open = False
            popup.destroy()

        ttk.Button(popup, text="Rozumím", command=_close, width=14).pack(pady=(4, 12))
        popup.protocol("WM_DELETE_WINDOW", _close)

    # ══════════════════════════════════════════════════════════════════
    # Toolbar button handlers
    # ══════════════════════════════════════════════════════════════════

    def _on_load_table(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Načíst tabulku pálení",
            filetypes=[
                ("Excel soubory", "*.xlsx *.xlsm"),
                ("Všechny soubory", "*.*"),
            ],
        )
        if path_str:
            self._vm.load_table(Path(path_str))

    def _on_new_table(self) -> None:
        path_str = filedialog.asksaveasfilename(
            title="Vytvořit novou tabulku",
            defaultextension=".xlsx",
            filetypes=[("Excel soubory", "*.xlsx")],
            initialfile="tabulka_paleni.xlsx",
        )
        if path_str:
            self._vm.create_new_table(Path(path_str))

    def _on_load_nc_sch(self) -> None:
        nc_str = filedialog.askopenfilename(
            title="Vyberte NC soubor",
            filetypes=[("NC soubory", "*.NC *.nc"), ("Všechny soubory", "*.*")],
        )
        if not nc_str:
            return

        sch_str = filedialog.askopenfilename(
            title="Vyberte SCH soubor (nepovinné — zrušit pro přeskočení)",
            filetypes=[
                ("SCH / XML soubory", "*.SCH *.sch *.xml *.XML"),
                ("Všechny soubory", "*.*"),
            ],
        )

        operator = self._ask_operator()
        self._vm.load_nc_sch(
            nc_path=Path(nc_str),
            sch_path=Path(sch_str) if sch_str else None,
            operator=operator,
        )

        if self._vm.has_pending_record:
            rec = self._vm.pending_record
            assert rec is not None
            answer = messagebox.askyesno(
                "Přidat záznam?",
                f"Načten program {rec.program_number}\n"
                f"Formát: {rec.sheet_format}\n"
                f"Datum: {rec.date}\n\n"
                "Přidat záznam do tabulky?",
            )
            if answer:
                self._vm.append_pending_record()

    def _on_print(self) -> None:
        if not self._vm.table_path:
            messagebox.showinfo("Info", "Nejprve načtěte tabulku.")
            return
        PrintPreview(self, self._vm)

    def _on_export_pdf(self) -> None:
        if not self._vm.table_path:
            messagebox.showinfo("Info", "Nejprve načtěte tabulku.")
            return
        out_str = filedialog.asksaveasfilename(
            title="Uložit PDF jako…",
            defaultextension=".pdf",
            filetypes=[("PDF soubory", "*.pdf")],
            initialfile=(
                self._vm.table_path.stem + ".pdf"
                if self._vm.table_path
                else "tabulka.pdf"
            ),
        )
        if out_str:
            self._vm.export_pdf(Path(out_str))

    def _on_open_counter(self) -> None:
        """Open (or focus) the CounterWindow."""
        if self._counter_win and self._counter_win.winfo_exists():
            self._counter_win.lift()
            self._counter_win.focus_set()
        else:
            self._counter_win = CounterWindow(self, self._vm)

    # ── helpers ──────────────────────────────────────────────────────────

    def _ask_operator(self) -> str:
        """Ask the operator for their name via a simple dialog."""
        dialog = tk.Toplevel(self)
        dialog.title("Operátor")
        dialog.resizable(False, False)
        dialog.grab_set()
        result: list[str] = [""]

        ttk.Label(dialog, text="Zadejte jméno operátora:").pack(padx=16, pady=(12, 4))
        entry = ttk.Entry(dialog, width=24)
        entry.pack(padx=16, pady=4)
        entry.focus_set()

        def _ok(event=None) -> None:
            result[0] = entry.get().strip()
            dialog.destroy()

        ttk.Button(dialog, text="OK", command=_ok, width=10).pack(pady=(4, 12))
        entry.bind("<Return>", _ok)
        dialog.wait_window()
        return result[0]

    # ══════════════════════════════════════════════════════════════════
    # Standalone launcher
    # ══════════════════════════════════════════════════════════════════

    @classmethod
    def launch(cls, vm: BurnViewModel) -> None:
        """Create a Tk root window and run the dashboard event loop.

        Call this from ``main.py`` to start the application.
        """
        root = tk.Tk()
        root.title("Tabulka pálení")
        root.minsize(960, 560)
        root.geometry("1100x640")

        with contextlib.suppress(tk.TclError):
            root.iconbitmap(default="")

        app = cls(root, vm)  # type: ignore[arg-type]  # noqa: F841

        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()
