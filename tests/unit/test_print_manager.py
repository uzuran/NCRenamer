"""Tests for PrintManager — preview_lines and print delegation."""

from pathlib import Path
from unittest.mock import MagicMock

from app.burn_table.models.burn_record import BurnRecord
from app.burn_table.viewmodels.print_manager import PrintManager


def _rec(**kwargs) -> BurnRecord:
    defaults = {
        "date": "30.06.2026",
        "program_number": "6670-18",
        "sheet_format": "1.0037-5X1700X1500",
        "total_time": "00:21:51",
    }
    defaults.update(kwargs)
    return BurnRecord(**defaults)  # type: ignore[arg-type]


class TestPreviewLines:
    def test_empty_records_returns_placeholder(self):
        pm = PrintManager()
        lines = pm.preview_lines([])
        assert lines == ["(žádná data)"]

    def test_non_empty_returns_header_separator_and_data(self):
        pm = PrintManager()
        lines = pm.preview_lines([_rec()])
        assert len(lines) == 3  # header + separator + 1 data row

    def test_header_row_contains_column_names(self):
        pm = PrintManager()
        header = pm.preview_lines([_rec()])[0]
        assert "Datum" in header
        assert "Číslo pr." in header

    def test_data_row_contains_record_values(self):
        pm = PrintManager()
        data_line = pm.preview_lines([_rec()])[2]
        assert "30.06.2026" in data_line
        assert "6670-18" in data_line

    def test_multiple_records_produce_correct_line_count(self):
        pm = PrintManager()
        records = [_rec(program_number=f"prog-{i:02d}") for i in range(5)]
        lines = pm.preview_lines(records)
        assert len(lines) == 7  # header + separator + 5 data rows


class TestPrintTable:
    def test_success_returns_true_and_empty_message(self):
        mock_svc = MagicMock()
        pm = PrintManager(print_service=mock_svc)
        ok, msg = pm.print_table(Path("/tmp/table.xls"))
        assert ok is True
        assert msg == ""

    def test_file_not_found_returns_false(self):
        mock_svc = MagicMock()
        mock_svc.print_table.side_effect = FileNotFoundError("no file")
        pm = PrintManager(print_service=mock_svc)
        ok, msg = pm.print_table(Path("/tmp/missing.xls"))
        assert ok is False
        assert "no file" in msg

    def test_generic_exception_returns_false(self):
        mock_svc = MagicMock()
        mock_svc.print_table.side_effect = RuntimeError("oops")
        pm = PrintManager(print_service=mock_svc)
        ok, msg = pm.print_table(Path("/tmp/table.xls"))
        assert ok is False
        assert "oops" in msg


class TestExportPdf:
    def test_defaults_to_pdf_extension(self):
        mock_svc = MagicMock()
        mock_svc.export_pdf.return_value = Path("/tmp/table.pdf")
        pm = PrintManager(print_service=mock_svc)
        ok, msg, path = pm.export_pdf(Path("/tmp/table.xlsx"))
        assert ok is True
        called_output = mock_svc.export_pdf.call_args[0][1]
        assert called_output.suffix == ".pdf"

    def test_failure_returns_false_and_message(self):
        mock_svc = MagicMock()
        mock_svc.export_pdf.side_effect = RuntimeError("libreoffice missing")
        pm = PrintManager(print_service=mock_svc)
        ok, msg, path = pm.export_pdf(Path("/tmp/table.xlsx"))
        assert ok is False
        assert path is None
        assert "libreoffice missing" in msg
