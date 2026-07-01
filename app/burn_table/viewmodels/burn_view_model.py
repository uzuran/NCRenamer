"""BurnViewModel — central ViewModel for the burn-table application."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from app.burn_table.models.burn_record import BurnRecord
from app.burn_table.models.table_status import TableStatus
from app.burn_table.services.excel_reader import ExcelReader
from app.burn_table.services.excel_writer import ExcelWriter, TableFullError
from app.burn_table.services.file_service import FileService
from app.burn_table.services.free_slot_detector import FreeSlotDetector
from app.burn_table.viewmodels.performance_recorder import PerformanceRecorder
from app.burn_table.viewmodels.print_manager import PrintManager


_SETTINGS_FILE = Path(__file__).parent.parent / "_burn_table_settings.json"

_EMPTY_STATUS = TableStatus(
    used_rows=0,
    free_rows=34,
    is_full=False,
    warning="",
)


class BurnViewModel:
    """Holds all application state and exposes operations to the view layer.

    Views must never access services or models directly.  Instead they:
        1. Read properties on this ViewModel.
        2. Call methods on this ViewModel.
        3. Subscribe via ``subscribe(callback)`` to be notified of changes.

    No GUI code lives here.  Side effects (file I/O) happen only inside
    the service layer called from this ViewModel.
    """

    def __init__(
        self,
        reader: ExcelReader | None = None,
        writer: ExcelWriter | None = None,
        detector: FreeSlotDetector | None = None,
        file_service: FileService | None = None,
        recorder: PerformanceRecorder | None = None,
        print_manager: PrintManager | None = None,
    ) -> None:
        # Services (injectable for testing)
        self._reader = reader or ExcelReader()
        self._writer = writer or ExcelWriter()
        self._detector = detector or FreeSlotDetector()
        self._file_service = file_service or FileService()
        self._recorder = recorder or PerformanceRecorder()
        self._print_manager = print_manager or PrintManager()

        # State
        self._table_path: Path | None = None
        self._records: list[BurnRecord] = []
        self._status: TableStatus = _EMPTY_STATUS
        self._pending_record: BurnRecord | None = None
        self._last_nc_path: Path | None = None
        self._last_sch_path: Path | None = None
        self._message: str = ""
        self._message_ok: bool = True

        # Observer callbacks registered by views
        self._callbacks: list[Callable[[], None]] = []

        # Popup warning to show after next notify (cleared by view after display)
        self._popup_message: str | None = None

    # ══════════════════════════════════════════════════════════════════
    # Observable infrastructure
    # ══════════════════════════════════════════════════════════════════

    def subscribe(self, callback: Callable[[], None]) -> None:
        """Register a zero-argument callable to be called after any state change."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        """Remove a previously registered callback."""
        self._callbacks = [c for c in self._callbacks if c is not callback]

    # ══════════════════════════════════════════════════════════════════
    # Read-only properties for the view
    # ══════════════════════════════════════════════════════════════════

    @property
    def records(self) -> list[BurnRecord]:
        """Current table rows (immutable snapshot)."""
        return list(self._records)

    @property
    def status(self) -> TableStatus:
        """Current capacity status."""
        return self._status

    @property
    def table_path(self) -> Path | None:
        """Path of the currently loaded table file, or None."""
        return self._table_path

    @property
    def pending_record(self) -> BurnRecord | None:
        """Parsed record waiting to be appended, or None."""
        return self._pending_record

    @property
    def has_pending_record(self) -> bool:
        """True when a parsed record is ready to append."""
        return self._pending_record is not None

    @property
    def message(self) -> str:
        """Last user-facing message (info or error)."""
        return self._message

    @property
    def message_ok(self) -> bool:
        """True if *message* is informational; False if it represents an error."""
        return self._message_ok

    @property
    def last_nc_path(self) -> Path | None:
        return self._last_nc_path

    @property
    def last_sch_path(self) -> Path | None:
        return self._last_sch_path

    @property
    def popup_message(self) -> str | None:
        """Non-None when the view should show a modal warning popup."""
        return self._popup_message

    def clear_popup(self) -> None:
        """Called by the view after it has shown the popup."""
        self._popup_message = None

    # ══════════════════════════════════════════════════════════════════
    # Operations (called by views)
    # ══════════════════════════════════════════════════════════════════

    def load_table(self, path: Path) -> None:
        """Load the table at *path* and update state."""
        try:
            records = self._reader.read_all(path)
            self._records = records
            self._table_path = path
            self._status = self._detector.detect_from_records(len(records))
            self._set_message(f"Tabulka načtena: {path.name}")
            self._save_settings()
        except Exception as exc:  # noqa: BLE001
            self._set_message(f"Chyba při načítání: {exc}", ok=False)
        self._notify()

    def load_last_table(self) -> None:
        """Attempt to load the table saved in the settings file on startup."""
        settings = self._read_settings()
        last = settings.get("last_table_path")
        if last:
            path = Path(last)
            if path.is_file():
                self.load_table(path)

    def load_nc_sch(
        self,
        nc_path: Path,
        sch_path: Path | None = None,
        product_group: str = "",
    ) -> None:
        """Parse NC (and optionally SCH) files and store as pending record.

        The parsed record is *not* appended automatically — the user must
        confirm via ``append_pending_record()``.
        """
        try:
            record = self._recorder.record_from_paths(nc_path, sch_path, product_group)
            self._pending_record = record
            self._last_nc_path = nc_path
            self._last_sch_path = sch_path
            self._set_message(
                f"Soubory načteny: {nc_path.name}"
                + (f" + {sch_path.name}" if sch_path else "")
            )
        except Exception as exc:  # noqa: BLE001
            self._pending_record = None
            self._set_message(f"Chyba parsování: {exc}", ok=False)
        self._notify()

    def append_pending_record(self) -> None:
        """Append the pending record to the current table and save.

        Does nothing if there is no pending record or no table loaded.
        """
        if self._pending_record is None:
            self._set_message("Žádný záznam k uložení.", ok=False)
            self._notify()
            return

        if self._table_path is None:
            self._set_message("Nejprve načtěte tabulku.", ok=False)
            self._notify()
            return

        if self._status.is_full:
            self._set_message("Tabulka je plná — nelze přidat další záznam.", ok=False)
            self._notify()
            return

        try:
            row_num = self._writer.append_record(self._table_path, self._pending_record)
            self._records.append(self._pending_record)
            self._pending_record = None
            self._status = self._detector.detect_from_records(len(self._records))
            self._set_message(f"Záznam uložen do řádku {row_num}.")
        except TableFullError:
            self._set_message("Tabulka je plná.", ok=False)
        except Exception as exc:  # noqa: BLE001
            self._set_message(f"Chyba při ukládání: {exc}", ok=False)
        self._notify()

    def discard_pending_record(self) -> None:
        """Discard the parsed pending record without appending it."""
        self._pending_record = None
        self._set_message("Záznam zahozen.")
        self._notify()

    def validate_unique_program(self, program_number: str) -> bool:
        """Return True when *program_number* is not already in the loaded records."""
        if not program_number:
            return True
        return not any(r.program_number == program_number for r in self._records)

    def load_and_append_batch(
        self,
        nc_paths: list[Path],
        product_group: str = "",
    ) -> None:
        """Parse and immediately append multiple NC files (SCH auto-detected).

        Duplicate program numbers are rejected with a popup warning.
        """
        if self._table_path is None:
            self._set_message("Nejprve načtěte tabulku.", ok=False)
            self._notify()
            return

        added: int = 0
        failed: list[str] = []
        duplicates: list[str] = []

        for nc_path in nc_paths:
            if self._status.is_full:
                failed.append(f"{nc_path.name}: tabulka plná")
                break
            sch_path = self.find_sch_for_nc(nc_path)
            try:
                record = self._recorder.record_from_paths(nc_path, sch_path, product_group)
                if not self.validate_unique_program(record.program_number):
                    duplicates.append(record.program_number)
                    continue
                row_num = self._writer.append_record(self._table_path, record)
                self._records.append(record)
                self._status = self._detector.detect_from_records(len(self._records))
                added += 1
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{nc_path.name}: {exc}")

        if duplicates:
            self._popup_message = (
                "Program již existuje v tabulce.\n"
                "Duplicitní záznamy nejsou povoleny.\n\n"
                + ", ".join(duplicates)
            )

        if failed:
            self._set_message(
                f"Přidáno: {added}, chyb: {len(failed)} — {failed[0]}",
                ok=added > 0,
            )
        elif duplicates and added == 0:
            self._set_message(
                f"Přeskočeno — duplicitní program: {', '.join(duplicates)}", ok=False,
            )
        else:
            self._set_message(f"Přidáno {added} záznamů do tabulky.")
        self._notify()

    @staticmethod
    def find_sch_for_nc(nc_path: Path) -> Path | None:
        """Return the matching SCH/XML file next to *nc_path*, or None."""
        for ext in (".sch", ".SCH", ".xml", ".XML"):
            candidate = nc_path.with_suffix(ext)
            if candidate.exists():
                return candidate
        return None

    def refresh_status(self) -> None:
        """Re-read the table file and refresh the capacity status."""
        if self._table_path and self._table_path.is_file():
            try:
                self._status = self._detector.detect(self._table_path)
                records = self._reader.read_all(self._table_path)
                self._records = records
                self._set_message("Stav obnoven.")
            except Exception as exc:  # noqa: BLE001
                self._set_message(f"Chyba obnovení: {exc}", ok=False)
        else:
            self._set_message("Není načtena žádná tabulka.", ok=False)
        self._notify()

    def print_table(self) -> None:
        """Print the current table file."""
        if self._table_path is None:
            self._set_message("Nejprve načtěte tabulku.", ok=False)
            self._notify()
            return
        success, error = self._print_manager.print_table(self._table_path)
        if success:
            self._set_message("Tisk odeslán.")
        else:
            self._set_message(error, ok=False)
        self._notify()

    def export_pdf(self, output_path: Path | None = None) -> None:
        """Export the current table to PDF."""
        if self._table_path is None:
            self._set_message("Nejprve načtěte tabulku.", ok=False)
            self._notify()
            return
        success, msg, _ = self._print_manager.export_pdf(
            self._table_path, output_path
        )
        self._set_message(msg, ok=success)
        self._notify()

    def clear_table(self) -> None:
        """Remove all data records from the current table file."""
        if self._table_path is None:
            self._set_message("Nejprve načtěte tabulku.", ok=False)
            self._notify()
            return
        try:
            self._writer.clear_all_records(self._table_path)
            self._records = []
            self._status = _EMPTY_STATUS
            self._set_message("Tabulka byla vymazána.")
        except Exception as exc:  # noqa: BLE001
            self._set_message(f"Chyba při mazání: {exc}", ok=False)
        self._notify()

    def clear_message(self) -> None:
        """Clear the current status message."""
        self._message = ""
        self._notify()

    # ══════════════════════════════════════════════════════════════════
    # Private helpers
    # ══════════════════════════════════════════════════════════════════

    def _notify(self) -> None:
        """Invoke all registered observer callbacks."""
        for cb in list(self._callbacks):
            try:
                cb()
            except Exception:  # noqa: BLE001
                pass  # Never let a broken callback crash the ViewModel

    def _set_message(self, text: str, *, ok: bool = True) -> None:
        self._message = text
        self._message_ok = ok

    def _save_settings(self) -> None:
        """Persist the last table path to the settings file."""
        if self._table_path is None:
            return
        try:
            _SETTINGS_FILE.write_text(
                json.dumps({"last_table_path": str(self._table_path)}, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass  # Settings are a convenience — failure is non-fatal

    @staticmethod
    def _read_settings() -> dict:
        """Read the settings file; return empty dict if missing or invalid."""
        try:
            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
