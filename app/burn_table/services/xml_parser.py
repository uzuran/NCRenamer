"""XmlParser — extracts production data from SCH XML schedule files."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from app.burn_table.models.parsed_info import SheetInfo


class XmlParser:
    """Parses a SCH (schedule/nesting) XML file into a SheetInfo object.

    The parser is deliberately lenient: it searches for quantity-related
    tags by name so it works with different software exports (TRUMPF
    TruTops, Lantek, etc.) without requiring a fixed schema.

    Quantity discovery order:
        1. Attributes named 'quantity', 'qty', 'Quantity', 'Menge'.
        2. Child elements named <Quantity>, <Qty>, <AnzahlTeile>.
        3. Falls back to 1 if nothing is found.
    """

    # Tag and attribute names searched for quantity data (case-sensitive list)
    QUANTITY_ATTRS = ("quantity", "qty", "Quantity", "Qty", "Menge", "count")
    QUANTITY_TAGS = (
        "Quantity", "qty", "AnzahlTeile", "PartQuantity",
        "PartCount", "Stueckzahl", "Count", "product_quantity",
    )
    # Tags that may contain the program / part name
    PARTS_NAME_TAGS = ("parts_name", "PartName", "ProgramName", "Name")

    def find_quantity_for_program(self, xml_text: str, program_number: str) -> int:
        """Return <product_quantity> from the <parts_info> whose <parts_name> matches.

        The SCH file may contain one block per NC program on the same sheet.
        This method finds the block for *program_number* specifically instead
        of summing all blocks.

        Returns 1 (safe default) when:
          - *program_number* is empty
          - *xml_text* is not valid XML
          - no <parts_info> block with a matching <parts_name> is found
        """
        if not program_number:
            return 1
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return 1

        for block in root.iter("parts_info"):
            name_elem = block.find("parts_name")
            if name_elem is not None and (name_elem.text or "").strip() == program_number:
                qty_elem = block.find("product_quantity")
                if qty_elem is not None and qty_elem.text:
                    return self._safe_int(qty_elem.text) or 1
                return 1  # block matched but no quantity element

        return 1  # no matching block found

    def parse(self, xml_text: str) -> SheetInfo:
        """Parse *xml_text* and return a SheetInfo.

        Raises:
            ValueError: if *xml_text* is not valid XML.
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid XML: {exc}") from exc

        quantity = self._find_total_quantity(root)
        parts_name = self._find_parts_name(root)
        raw_fields = self._collect_raw_fields(root)

        return SheetInfo(
            product_quantity=quantity,
            parts_name=parts_name,
            raw_fields=raw_fields,
        )

    # ── private ─────────────────────────────────────────────────────────

    def _find_total_quantity(self, root: ET.Element) -> int:
        """Walk the element tree and sum all discovered part quantities."""
        totals: list[int] = []

        for elem in root.iter():
            # Check attributes
            for attr_name in self.QUANTITY_ATTRS:
                val = elem.get(attr_name)
                if val is not None:
                    totals.append(self._safe_int(val))
                    break

            # Check element text of known quantity tags
            if elem.tag in self.QUANTITY_TAGS and elem.text:
                totals.append(self._safe_int(elem.text))

        return sum(totals) if totals else 1

    def _find_parts_name(self, root: ET.Element) -> str:
        """Return the program/part name found in the XML, or empty string."""
        for elem in root.iter():
            if elem.tag in self.PARTS_NAME_TAGS and elem.text and elem.text.strip():
                return elem.text.strip()
        return ""

    def _collect_raw_fields(self, root: ET.Element) -> dict:
        """Return a flat dict of tag → text for diagnostic purposes."""
        return {
            elem.tag: (elem.text or "").strip()
            for elem in root.iter()
            if elem.text and elem.text.strip()
        }

    @staticmethod
    def _safe_int(value: str) -> int:
        """Convert *value* to int, returning 0 on failure."""
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            return 0
