"""PrintService — delegates print to OS/external tools."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class PrintService:
    """Opens a table file for printing.

    Strategy:
        print_table  → opens the .xlsx in the OS default app with 'print' verb
                        (Windows) or opens in default app (Linux/macOS/WSL).

    All methods are side-effect-free until called.
    """

    def print_table(self, path: Path) -> None:
        """Send *path* to the operating system for printing.

        On WSL the file is opened in the Windows default application so the
        user can print using the familiar Excel print dialog.

        Raises:
            FileNotFoundError: if *path* does not exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"Cannot print — file not found: {path}")

        if sys.platform == "win32":
            os.startfile(str(path))
        elif self._is_wsl():
            self._open_in_windows(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            try:
                subprocess.run(["xdg-open", str(path)], check=False)
            except FileNotFoundError:
                raise RuntimeError("Cannot open file — 'xdg-open' not found.") from None

    # ── private ─────────────────────────────────────────────────────────

    @staticmethod
    def _is_wsl() -> bool:
        """Return True when running inside Windows Subsystem for Linux."""
        try:
            return "microsoft" in Path("/proc/version").read_text().lower()
        except OSError:
            return False

    @staticmethod
    def _open_in_windows(path: Path) -> None:
        """Open *path* in the default Windows application via cmd.exe.

        Uses wslpath to convert the Linux path to its Windows UNC equivalent
        (e.g. \\\\wsl.localhost\\Ubuntu\\home\\...) so Windows can locate it.
        """
        try:
            win_path = (
                subprocess.check_output(["wslpath", "-w", str(path)]).decode().strip()
            )
            # The empty-string title argument is required by 'start' when the
            # path is quoted — otherwise 'start' treats the path as the title.
            subprocess.run(["cmd.exe", "/c", "start", "", win_path], check=False)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(f"Nelze otevřít soubor ve Windows: {exc}") from exc
