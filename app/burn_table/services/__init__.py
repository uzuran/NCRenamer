"""Burn-table service layer — all I/O and external-system adapters."""

from .excel_reader import ExcelReader
from .excel_writer import ExcelWriter, TableFullError
from .file_service import FileService
from .free_slot_detector import FreeSlotDetector
from .print_service import PrintService
from .table_factory import TableFactory
from .xml_parser import XmlParser

__all__ = [
    "ExcelReader",
    "ExcelWriter",
    "TableFullError",
    "FileService",
    "FreeSlotDetector",
    "PrintService",
    "TableFactory",
    "XmlParser",
]
