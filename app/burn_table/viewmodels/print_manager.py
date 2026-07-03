"""PrintManager — prepares table data for printing and PDF export."""

from __future__ import annotations

from pathlib import Path

from app.burn_table.models.burn_record import BurnRecord
from app.burn_table.services.print_service import PrintService


class PrintManager:
    """Coordinates the print/export workflow.

    The ViewModel layer is responsible for deciding *what* to print;
    PrintService handles the OS-level mechanics of *how* to print it.
    """

    def __init__(self, print_service: PrintService | None = None) -> None:
        self._print_service = print_service or PrintService()

    # ── public API ───────────────────────────────────────────────────────

    def print_table(self, table_path: Path) -> tuple[bool, str]:
        """Send the burn table at *table_path* to the OS printer.

        Returns:
            (True, "") on success.
            (False, error_message) on failure.
        """
        try:
            self._print_service.print_table(table_path)
            return True, ""
        except FileNotFoundError as exc:
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def export_pdf(
        self,
        table_path: Path,
        output_path: Path | None = None,
    ) -> tuple[bool, str, Path | None]:
        """Export the table to PDF.

        Args:
            table_path:  Source .xlsx workbook.
            output_path: Desired output path.  Defaults to same directory
                         with .pdf extension.

        Returns:
            (success, message, pdf_path_or_None)
        """
        if output_path is None:
            output_path = table_path.with_suffix(".pdf")

        try:
            result_path = self._print_service.export_pdf(table_path, output_path)
            return True, f"PDF uloženo: {result_path.name}", result_path
        except FileNotFoundError as exc:
            return False, str(exc), None
        except Exception as exc:  # noqa: BLE001
            return False, f"Chyba exportu: {exc}", None

    def preview_lines(self, records: list[BurnRecord]) -> list[str]:
        """Return the table as a list of formatted text lines for a text preview.

        Each line represents one data row with fixed-width columns.
        """
        if not records:
            return ["(žádná data)"]

        col_widths = [14, 10, 6, 34, 6, 12, 10, 16, 10]
        headers = ["Datum", "Číslo pr.", "Note", "Formát tabule",
                   "Ks", "Celk. čas", "Vypáleno", "Výrobek", "Pálil"]

        def fmt_row(values: list[str]) -> str:
            return "  ".join(
                str(v)[:w].ljust(w) for v, w in zip(values, col_widths)
            )

        lines: list[str] = [
            fmt_row(headers),
            "-" * sum(col_widths + [2] * (len(col_widths) - 1)),
        ]
        for rec in records:
            lines.append(fmt_row([
                rec.date, rec.program_number, rec.note,
                rec.sheet_format, str(rec.sheet_count),
                rec.total_time, rec.burned, rec.product_group, rec.operator,
            ]))
        return lines
