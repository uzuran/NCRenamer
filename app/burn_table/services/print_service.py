"""PrintService — delegates print and PDF-export to OS/external tools."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


class PrintService:
    """Opens a table file for printing or exports it to PDF.

    Strategy:
        print_table  → opens the .xlsx in the OS default app with 'print' verb
                        (Windows) or sends to lpr (Linux/macOS).
        export_pdf   → tries LibreOffice headless first; falls back to opening
                        the file so the user can print-to-PDF manually.

    All methods are side-effect-free until called.
    """

    def print_table(self, path: Path) -> None:
        """Send *path* to the operating system for printing.

        Raises:
            FileNotFoundError: if *path* does not exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"Cannot print — file not found: {path}")

        if sys.platform == "win32":
            os.startfile(str(path), "print")
        elif sys.platform == "darwin":
            subprocess.run(["lpr", str(path)], check=False)
        else:
            try:
                subprocess.run(["lpr", str(path)], check=False)
            except FileNotFoundError:
                raise RuntimeError(
                    "Tisk není dostupný — příkaz 'lpr' nebyl nalezen."
                ) from None

    def export_pdf(self, path: Path, output_path: Path) -> Path:
        """Convert *path* (.xlsx) to PDF at *output_path*.

        Tries LibreOffice first; if unavailable opens the source file in
        the default application so the user can print-to-PDF manually.

        Returns:
            The path of the created PDF, or *output_path* if LibreOffice
            was invoked (file may not exist yet if conversion is async).

        Raises:
            FileNotFoundError: if *path* does not exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"Cannot export — file not found: {path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self._libreoffice_available():
            try:
                subprocess.run(
                    [
                        "soffice",
                        "--headless",
                        "--convert-to", "pdf",
                        "--outdir", str(output_path.parent),
                        str(path),
                    ],
                    check=True,
                    timeout=60,
                    capture_output=True,
                )
                # LibreOffice names the output after the source stem
                candidate = output_path.parent / (path.stem + ".pdf")
                if candidate.exists() and candidate != output_path:
                    candidate.rename(output_path)
                return output_path
            except (subprocess.SubprocessError, OSError):
                pass  # Fall through to manual fallback

        # Fallback: open the file so the user can print-to-PDF manually
        if sys.platform == "win32":
            os.startfile(str(path))
        else:
            try:
                subprocess.run(["xdg-open", str(path)], check=False)
            except FileNotFoundError:
                raise RuntimeError(
                    "Export PDF není dostupný — LibreOffice ani 'xdg-open' nebyly nalezeny."
                ) from None

        return output_path

    # ── private ─────────────────────────────────────────────────────────

    @staticmethod
    def _libreoffice_available() -> bool:
        """Return True when the 'soffice' binary is on PATH."""
        import shutil
        return shutil.which("soffice") is not None
