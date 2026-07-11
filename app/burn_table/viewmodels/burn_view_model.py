"""BurnViewModel — central ViewModel for the burn-table application."""

from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.burn_table.models.burn_record import BurnRecord

from app.burn_table.models.table_status import TableStatus
from app.burn_table.services.excel_reader import ExcelReader
from app.burn_table.services.excel_writer import ExcelWriter, TableFullError
from app.burn_table.services.file_service import FileService
from app.burn_table.services.free_slot_detector import FreeSlotDetector
from app.burn_table.viewmodels.performance_recorder import PerformanceRecorder
from app.burn_table.viewmodels.print_manager import PrintManager


def _burn_settings_file() -> Path:
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or str(Path.home())
        d = Path(base) / "NCRenamer"
        d.mkdir(parents=True, exist_ok=True)
        return d / "_burn_table_settings.json"
    return Path(__file__).parent.parent / "_burn_table_settings.json"


_SETTINGS_FILE = _burn_settings_file()

_EMPTY_STATUS = TableStatus(
    used_rows=0,
    free_rows=38,
    is_full=False,
    warning="",
)


def _program_sort_key(program_number: str) -> int:
    """Return the numeric suffix of a 'PREFIX-SUFFIX' program number for sorting.

    '6678-79' → 79.  Falls back to 0 for non-standard formats so they sort first.
    """
    try:
        return int(program_number.rsplit("-", 1)[-1])
    except (ValueError, IndexError):
        return 0


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
        texts: dict | None = None,
        sheet_name: str = "Pálení",
        settings_key: str = "last_table_path",
    ) -> None:
        # Services (injectable for testing)
        self._reader = reader or ExcelReader()
        self._writer = writer or ExcelWriter()
        self._detector = detector or FreeSlotDetector()
        self._sheet_name = sheet_name
        self._settings_key = settings_key
        self._file_service = file_service or FileService()
        self._recorder = recorder or PerformanceRecorder()
        self._print_manager = print_manager or PrintManager()
        self._texts: dict = texts or {}

        # State
        self._table_path: Path | None = None
        self._records: list[BurnRecord] = []
        # Display order including None entries for blank batch-separator rows.
        # Mirrors the physical Excel layout so the treeview can show separators.
        self._display_rows: list[BurnRecord | None] = []
        self._status: TableStatus = _EMPTY_STATUS
        self._pending_record: BurnRecord | None = None
        self._last_nc_path: Path | None = None
        self._last_sch_path: Path | None = None
        self._message: str = ""
        self._message_ok: bool = True
        # True once the first record with a date has been written in this
        # session; all subsequent records are written with date = "".
        self._date_written: bool = False
        # Tracks the last sheet_format value actually written to Excel.
        # Consecutive rows with the same format are written as "-----".
        # Resets on load (to last format found) and on clear (to "").
        self._last_sheet_format: str = ""

        # Observer callbacks registered by views
        self._callbacks: list[Callable[[], None]] = []

        # Popup warning to show after next notify (cleared by view after display)
        self._popup_message: str | None = None

        # Optional reference to the other sheet's VM for cross-sheet duplicate checks.
        # Set by the app after both VMs are constructed.
        self._peer_vm: BurnViewModel | None = None

        # Tracks the next Excel row to write into, managed explicitly so that
        # batch uploads pack records consecutively with ONE separator per batch.
        self._next_write_row: int = ExcelWriter.DATA_START_ROW

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

    def update_texts(self, texts: dict) -> None:
        """Update the UI language; call after ``set_language()`` in the app."""
        self._texts = texts

    # ══════════════════════════════════════════════════════════════════
    # Read-only properties for the view
    # ══════════════════════════════════════════════════════════════════

    @property
    def records(self) -> list[BurnRecord]:
        """Current table rows (immutable snapshot)."""
        return list(self._records)

    @property
    def display_rows(self) -> list[BurnRecord | None]:
        """Data rows and batch-separator rows in physical order.

        None entries represent the blank separator rows that the writer inserts
        between batches in the Excel file.  Use this for treeview rendering;
        use ``records`` for business logic that indexes into data.
        """
        return list(self._display_rows)

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
            self._writer.ensure_sheet_exists(path, self._sheet_name)
            display = self._reader.read_all_with_separators(path)
            self._display_rows = display
            records = [r for r in display if r is not None]
            self._records = records
            self._table_path = path.resolve()
            self._status = self._detector.detect_from_records(len(display))
            self._next_write_row = self._compute_next_write_row(path, records)
            # If the table already has rows the date was already written;
            # new appends must leave the date cell empty.
            self._date_written = len(records) > 0
            # Resume the format chain: find the last real (non-placeholder) format
            # in the loaded records so new appends continue the dedup correctly.
            self._last_sheet_format = ""
            for rec in reversed(records):
                if rec.sheet_format and rec.sheet_format != "-----":
                    self._last_sheet_format = rec.sheet_format
                    break
            with contextlib.suppress(Exception):
                self._writer.update_header(
                    path
                )  # non-fatal — header formatting is cosmetic
            self._set_message(
                self._texts.get("table_loaded", "Table loaded: {}").format(path.name)
            )
            self._save_settings()
        except Exception as exc:
            self._set_message(
                self._texts.get("table_load_error", "Error loading: {}").format(exc),
                ok=False,
            )
        self._notify()

    def load_last_table(self) -> None:
        """Attempt to load the table saved in the settings file on startup."""
        settings = self._read_settings()
        last = settings.get(self._settings_key) or settings.get("last_table_path")
        if last:
            path = Path(last)
            if path.is_file():
                self.load_table(path)
                return

        # Frozen exe fallback: look for laser.xls next to the executable
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            fallback = exe_dir / "CNCs" / "laser.xls"
            if fallback.is_file():
                self.load_table(fallback)
                return

        # Development fallback: CNCs/laser.xls next to the project root
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        dev_fallback = project_root / "CNCs" / "laser.xls"
        if dev_fallback.is_file():
            self.load_table(dev_fallback)

    def create_new_table(self, path: Path) -> None:
        """Create a new blank table file at *path* then load it."""
        from app.burn_table.services.table_factory import TableFactory

        TableFactory().create(path)
        self.load_table(path)

    def load_nc_sch(
        self,
        nc_path: Path,
        sch_path: Path | None = None,
        product_group: str = "",
        operator: str = "",
    ) -> None:
        """Parse NC (and optionally SCH) files and store as pending record.

        The parsed record is *not* appended automatically — the user must
        confirm via ``append_pending_record()``.
        """
        try:
            record = self._recorder.record_from_paths(
                nc_path, sch_path, product_group, operator
            )
            self._pending_record = record
            self._last_nc_path = nc_path
            self._last_sch_path = sch_path
            msg = self._texts.get("files_loaded", "Files loaded: {}").format(
                nc_path.name
            )
            if sch_path:
                msg += f" + {sch_path.name}"
            self._set_message(msg)
        except Exception as exc:
            self._pending_record = None
            self._set_message(
                self._texts.get("parse_error", "Parse error: {}").format(exc), ok=False
            )
        self._notify()

    def append_pending_record(self) -> None:
        """Append the pending record to the current table and save.

        Does nothing if there is no pending record or no table loaded.
        """
        if self._pending_record is None:
            self._set_message(
                self._texts.get("no_record_to_save", "No record to save."), ok=False
            )
            self._notify()
            return

        if self._table_path is None:
            self._set_message(
                self._texts.get("load_table_first", "Load a table first."), ok=False
            )
            self._notify()
            return

        if self._status.is_full:
            self._set_message(
                self._texts.get(
                    "table_full_add", "Table is full — cannot add more records."
                ),
                ok=False,
            )
            self._notify()
            return

        if self._next_write_row > ExcelWriter.MAX_ROW:
            self._set_message(
                self._texts.get(
                    "table_full_add", "Table is full — cannot add more records."
                ),
                ok=False,
            )
            self._notify()
            return

        try:
            record_to_write = self._prepare_record_for_writing(self._pending_record)
            row_num = self._next_write_row
            self._writer.write_record_at_row(self._table_path, row_num, record_to_write)
            self._next_write_row += 1
            # Insert a styled empty separator row after the single-record batch.
            with contextlib.suppress(Exception):
                self._writer.write_empty_row(self._table_path, self._next_write_row)
            self._next_write_row += 1
            self._records.append(record_to_write)
            self._display_rows.append(record_to_write)
            self._display_rows.append(None)  # separator
            self._pending_record = None
            self._status = self._detector.detect_from_records(len(self._display_rows))
            self._set_message(
                self._texts.get("record_saved", "Record saved to row {}.").format(
                    row_num
                )
            )
        except TableFullError:
            self._set_message(self._texts.get("table_full", "Table is full."), ok=False)
        except Exception as exc:
            self._set_message(
                self._texts.get("save_error", "Save error: {}").format(exc), ok=False
            )
        self._notify()

    def discard_pending_record(self) -> None:
        """Discard the parsed pending record without appending it."""
        self._pending_record = None
        self._set_message(self._texts.get("record_discarded", "Record discarded."))
        self._notify()

    def set_peer_vm(self, peer: BurnViewModel) -> None:
        """Wire the other sheet's VM so cross-sheet duplicate checks are possible."""
        self._peer_vm = peer

    def validate_unique_program(self, program_number: str) -> bool:
        """Return True when *program_number* is not already in the loaded records (case-insensitive)."""
        if not program_number:
            return True
        pn_lower = program_number.strip().lower()
        return not any(
            r.program_number.strip().lower() == pn_lower for r in self._records
        )

    def load_and_append_batch(
        self,
        nc_paths: list[Path],
        product_group: str = "",
        date: str = "",
    ) -> None:
        """Parse and immediately append multiple NC files (SCH auto-detected).

        Duplicate program numbers are rejected with a popup warning.

        The *product_group* value is written only into the **first successfully
        appended record** of this call; all subsequent records in the same batch
        get an empty product_group cell.  Each new call resets this flag, so
        loading a second batch always writes the product_group in its first row.
        """
        if self._table_path is None:
            self._set_message(
                self._texts.get("load_table_first", "Load a table first."), ok=False
            )
            self._notify()
            return

        added: int = 0
        failed: list[str] = []
        duplicates: list[str] = []
        cross_duplicates: list[str] = []
        product_group_written = False  # reset every batch call
        batch_written: list[BurnRecord] = []  # for _display_rows update

        # Phase 1: parse all records first so we can sort them before writing.
        parsed: list[tuple[Path, BurnRecord]] = []
        for nc_path in nc_paths:
            resolved_sch = self.find_sch_for_nc(nc_path)
            try:
                record = self._recorder.record_from_paths(
                    nc_path, resolved_sch, product_group
                )
                parsed.append((nc_path, record))
            except Exception as exc:
                failed.append(f"{nc_path.name}: {exc}")

        # Sort by the numeric suffix of the program number (e.g. '6678-79' → 79).
        parsed.sort(key=lambda pair: _program_sort_key(pair[1].program_number))

        # Phase 2: validate, prepare, and write in sorted order.
        for nc_path, record in parsed:
            if self._status.is_full or self._next_write_row > ExcelWriter.MAX_ROW:
                failed.append(
                    f"{nc_path.name}: {self._texts.get('table_full_label', 'table full')}"
                )
                break
            if not self.validate_unique_program(record.program_number):
                duplicates.append(record.program_number)
                continue
            if self._peer_vm is not None and record.program_number:
                pn_lower = record.program_number.strip().lower()
                if any(
                    r.program_number.strip().lower() == pn_lower
                    for r in self._peer_vm._records
                ):
                    cross_duplicates.append(record.program_number)
                    continue
            record_to_write = self._prepare_record_for_writing(record)
            # For the first written record: apply user date and product_group.
            if product_group_written:
                record_to_write = dataclasses.replace(record_to_write, product_group="")
            else:
                product_group_written = True
                if date:
                    record_to_write = dataclasses.replace(record_to_write, date=date)
            self._writer.write_record_at_row(
                self._table_path, self._next_write_row, record_to_write
            )
            self._next_write_row += 1
            self._records.append(record_to_write)
            batch_written.append(record_to_write)
            self._status = self._detector.detect_from_records(len(self._records))
            added += 1

        # Insert ONE styled separator row after the entire batch.
        if added > 0:
            with contextlib.suppress(Exception):
                self._writer.write_empty_row(self._table_path, self._next_write_row)
            self._next_write_row += 1
            self._display_rows.extend(batch_written)
            self._display_rows.append(None)  # separator after batch
            self._status = self._detector.detect_from_records(len(self._display_rows))

        popup_parts: list[str] = []
        if duplicates:
            popup_parts.append(
                self._texts.get(
                    "dup_program_warning",
                    "Program already exists in table.\nDuplicate records are not allowed.",
                )
                + "\n\n"
                + ", ".join(duplicates)
            )
        if cross_duplicates:
            peer_name = self._peer_vm._sheet_name if self._peer_vm else ""
            popup_parts.append(
                self._texts.get(
                    "dup_cross_sheet_warning",
                    "Program already exists in the other table ({}).",
                ).format(peer_name)
                + "\n\n"
                + ", ".join(cross_duplicates)
            )
        if popup_parts:
            self._popup_message = "\n\n".join(popup_parts)

        all_skipped = duplicates + cross_duplicates
        if failed:
            self._set_message(
                self._texts.get(
                    "added_with_errors", "Added: {0}, errors: {1} — {2}"
                ).format(added, len(failed), failed[0]),
                ok=added > 0,
            )
        elif all_skipped and added == 0:
            self._set_message(
                self._texts.get(
                    "skipped_duplicate", "Skipped — duplicate program: {}"
                ).format(", ".join(all_skipped)),
                ok=False,
            )
        else:
            self._set_message(
                self._texts.get("added_records", "Added {} records to table.").format(
                    added
                )
            )
        self._notify()

    @staticmethod
    def find_sch_for_nc(nc_path: Path) -> Path | None:
        """Return the matching SCH/XML file next to *nc_path*, or None.

        Search order:
        1. Exact stem match  — 6670-18.NC  → 6670-18.SCH
        2. Job-prefix glob   — 6684-97.NC  → 6684-*.SCH → 6684-32.SCH
           (one SCH file often covers all programs cut from the same sheet)
        """
        # 1. Exact match
        for ext in (".sch", ".SCH", ".xml", ".XML"):
            candidate = nc_path.with_suffix(ext)
            if candidate.exists():
                return candidate

        # 2. Job prefix: strip last '-NN' segment (e.g. '6684' from '6684-97')
        stem = nc_path.stem
        if "-" in stem:
            prefix = stem.rsplit("-", 1)[0]
            for ext in (".SCH", ".sch"):
                matches = sorted(nc_path.parent.glob(f"{prefix}-*{ext}"))
                if matches:
                    return matches[0]

        return None

    def refresh_status(self) -> None:
        """Re-read the table file and refresh the capacity status."""
        if self._table_path and self._table_path.is_file():
            try:
                display = self._reader.read_all_with_separators(self._table_path)
                self._display_rows = display
                self._records = [r for r in display if r is not None]
                self._status = self._detector.detect_from_records(len(display))
                self._set_message(
                    self._texts.get("status_refreshed", "Status refreshed.")
                )
            except Exception as exc:
                self._set_message(
                    self._texts.get("refresh_error", "Refresh error: {}").format(exc),
                    ok=False,
                )
        else:
            self._set_message(
                self._texts.get("status_no_table", "No table loaded."), ok=False
            )
        self._notify()

    def print_table(self) -> None:
        """Print the current table file."""
        if self._table_path is None:
            self._set_message(
                self._texts.get("load_table_first", "Load a table first."), ok=False
            )
            self._notify()
            return
        success, exc_msg = self._print_manager.print_table(self._table_path)
        if success:
            self._set_message(self._texts.get("print_sent", "Print sent."))
        else:
            self._set_message(
                self._texts.get("print_error", "Print error: {}").format(exc_msg),
                ok=False,
            )
        self._notify()

    def export_pdf(self, output_path: Path | None = None) -> None:
        """Export the current table to PDF."""
        if self._table_path is None:
            self._set_message(
                self._texts.get("load_table_first", "Load a table first."), ok=False
            )
            self._notify()
            return
        success, msg, _ = self._print_manager.export_pdf(self._table_path, output_path)
        self._set_message(msg, ok=success)
        self._notify()

    def clear_table(self) -> None:
        """Remove all data records from the current table file."""
        if self._table_path is None:
            self._set_message(
                self._texts.get("load_table_first", "Load a table first."), ok=False
            )
            self._notify()
            return
        try:
            self._writer.clear_all_records(self._table_path)
            self._records = []
            self._display_rows = []
            self._status = _EMPTY_STATUS
            self._date_written = False
            self._last_sheet_format = ""
            self._next_write_row = ExcelWriter.DATA_START_ROW
            self._set_message(self._texts.get("table_cleared", "Table cleared."))
        except Exception as exc:
            self._set_message(
                self._texts.get("clear_error", "Clear error: {}").format(exc), ok=False
            )
        self._notify()

    def update_record(self, index: int, record: BurnRecord) -> None:
        """Replace the record at *index* (0-based) with *record* and save."""
        if self._table_path is None:
            self._set_message(
                self._texts.get("load_table_first", "Load a table first."), ok=False
            )
            self._notify()
            return
        if not (0 <= index < len(self._records)):
            return
        self._records[index] = record
        # Update _display_rows in-place BEFORE the rewrite so separator rows (None
        # entries) are preserved in both the treeview and the written Excel file.
        data_count = 0
        for i, disp_row in enumerate(self._display_rows):
            if disp_row is not None:
                if data_count == index:
                    self._display_rows[i] = record
                    break
                data_count += 1
        else:
            self._display_rows = list(self._records)
        try:
            # Pass _display_rows (with None separators) so blank rows are preserved
            # in the physical Excel layout, not just in the treeview.
            self._writer.rewrite_all_records(self._table_path, self._display_rows)
        except Exception as exc:
            self._set_message(
                self._texts.get("save_error", "Save error: {}").format(exc), ok=False
            )
            self._notify()
            return
        # Each entry in _display_rows (data or separator) occupies one physical row.
        self._next_write_row = ExcelWriter.DATA_START_ROW + len(self._display_rows)
        self._set_message(self._texts.get("record_updated", "Record updated."))
        self._notify()

    def delete_record(self, index: int) -> None:
        """Remove the record at *index* (0-based) from the table and save."""
        if self._table_path is None:
            self._set_message(
                self._texts.get("load_table_first", "Load a table first."), ok=False
            )
            self._notify()
            return
        if not (0 <= index < len(self._records)):
            return
        self._records.pop(index)
        try:
            self._writer.rewrite_all_records(self._table_path, self._records)
        except Exception as exc:
            self._set_message(
                self._texts.get("save_error", "Save error: {}").format(exc), ok=False
            )
            self._notify()
            return
        self._next_write_row = ExcelWriter.DATA_START_ROW + len(self._records)
        self._display_rows = list(self._records)  # rewrite packs records; no separators
        self._status = self._detector.detect_from_records(len(self._records))
        self._date_written = len(self._records) > 0
        self._last_sheet_format = ""
        for rec in reversed(self._records):
            if rec.sheet_format and rec.sheet_format != "-----":
                self._last_sheet_format = rec.sheet_format
                break
        self._set_message(self._texts.get("record_deleted", "Record deleted."))
        self._notify()

    def clear_message(self) -> None:
        """Clear the current status message."""
        self._message = ""
        self._notify()

    # ══════════════════════════════════════════════════════════════════
    # Private helpers
    # ══════════════════════════════════════════════════════════════════

    def _compute_next_write_row(self, path: Path, records: list) -> int:
        """Return the row where the next write should start after loading *records*.

        Scans the file for the last occupied column-B row and adds 2 to leave
        room for a batch separator.  Falls back to DATA_START_ROW + len(records)
        for old files or when the reader is mocked (returns a non-int).
        """
        if not records:
            return ExcelWriter.DATA_START_ROW
        try:
            last_row = self._reader.find_last_data_row(path)
        except Exception:
            last_row = None
        if isinstance(last_row, int) and last_row >= ExcelWriter.DATA_START_ROW:
            return last_row + 2
        # Fallback for files without separator rows or mocked readers
        return ExcelWriter.DATA_START_ROW + len(records)

    def _prepare_record_for_writing(self, record: BurnRecord) -> BurnRecord:
        """Return *record* ready for Excel, applying two appearance rules.

        **Date rule** — the date is written only in the very first row.
        All subsequent rows receive ``date=""``.  The flag ``_date_written``
        is reset when the table is cleared or a fresh (empty) table is loaded.

        **Sheet-format dedup rule** — the first occurrence of a given format
        is written in full (e.g. ``"1.0037-4X3000X1500"``).  Every consecutive
        row that carries the *same* format is replaced with ``"-----"``.
        When the format changes the new value is written in full and becomes
        the new baseline.  ``_last_sheet_format`` is reset on clear and
        re-populated from the last real format when a table is loaded.

        Both rules operate on a shallow copy so the original *record* (shown
        in the pending banner) is never mutated.
        """
        # ── date rule ────────────────────────────────────────────────────────
        if self._date_written:
            new_date = ""
        else:
            new_date = record.date
            self._date_written = True

        # ── sheet-format dedup rule ───────────────────────────────────────────
        fmt = record.sheet_format
        if fmt and fmt == self._last_sheet_format:
            new_fmt = "-----"
        else:
            new_fmt = fmt
            if fmt:  # only update tracker for non-empty real formats
                self._last_sheet_format = fmt

        # Return the original object when nothing changed (avoids allocation)
        if new_date == record.date and new_fmt == record.sheet_format:
            return record
        return dataclasses.replace(record, date=new_date, sheet_format=new_fmt)

    def _notify(self) -> None:
        """Invoke all registered observer callbacks."""
        for cb in list(self._callbacks):
            with contextlib.suppress(Exception):
                cb()  # Never let a broken callback crash the ViewModel

    def _set_message(self, text: str, *, ok: bool = True) -> None:
        self._message = text
        self._message_ok = ok

    def _save_settings(self) -> None:
        """Persist the last table path to the settings file."""
        if self._table_path is None:
            return
        try:
            existing = self._read_settings()
            existing[self._settings_key] = str(self._table_path)
            _SETTINGS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        except OSError:
            pass  # Settings are a convenience — failure is non-fatal

    @staticmethod
    def _read_settings() -> dict[str, str]:
        """Read the settings file; return empty dict if missing or invalid."""
        try:
            data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
            return {}
        except (OSError, json.JSONDecodeError):
            return {}
