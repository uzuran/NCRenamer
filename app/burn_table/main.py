"""main.py — assembles all BurnViewModel dependencies."""

from __future__ import annotations

from app.burn_table.services.excel_reader import ExcelReader
from app.burn_table.services.excel_writer import ExcelWriter
from app.burn_table.services.file_service import FileService
from app.burn_table.services.free_slot_detector import FreeSlotDetector
from app.burn_table.services.print_service import PrintService
from app.burn_table.services.xml_parser import XmlParser
from app.burn_table.viewmodels.burn_view_model import BurnViewModel
from app.burn_table.viewmodels.performance_recorder import PerformanceRecorder
from app.burn_table.viewmodels.print_manager import PrintManager


def main() -> None:
    """Entry point for the standalone burn-table application."""
    from app.burn_table.views.burn_dashboard import BurnDashboard

    vm = create_view_model()
    BurnDashboard.launch(vm)


def create_view_model(
    texts: dict | None = None,
    sheet_index: int = 0,
    sheet_name: str = "Pálení",
    settings_key: str = "last_table_path",
    settings_file=None,
) -> BurnViewModel:
    """Assemble and return a fully wired BurnViewModel."""
    file_service = FileService()
    xml_parser = XmlParser()

    return BurnViewModel(
        reader=ExcelReader(sheet_index=sheet_index),
        writer=ExcelWriter(sheet_index=sheet_index),
        detector=FreeSlotDetector(sheet_index=sheet_index),
        file_service=file_service,
        recorder=PerformanceRecorder(
            file_service=file_service,
            xml_parser=xml_parser,
        ),
        print_manager=PrintManager(
            print_service=PrintService(),
        ),
        texts=texts,
        sheet_name=sheet_name,
        settings_key=settings_key,
        settings_file=settings_file,
    )
