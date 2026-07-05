"""Open the system default email client via a mailto: URL.

On Windows: calls ShellExecuteW from shell32.dll directly — no child process,
no Python registry lookup, works inside a PyInstaller exe with console=False.
On other platforms: delegates to xdg-open.
"""

from __future__ import annotations

import subprocess
import sys
import urllib.parse


class EmailService:
    def open_email(self, to: str, subject: str, body: str) -> None:
        """Open the default email client pre-filled with *to*, *subject*, *body*."""
        params = urllib.parse.urlencode({"subject": subject, "body": body})
        mailto = f"mailto:{to}?{params}"
        if sys.platform == "win32":
            self._open_windows(mailto)
        else:
            self._open_unix(mailto)

    @staticmethod
    def _open_windows(mailto: str) -> None:
        import ctypes

        ret = ctypes.windll.shell32.ShellExecuteW(None, "open", mailto, None, None, 1)  # type: ignore[attr-defined]
        if ret <= 32:
            raise OSError(f"ShellExecuteW failed with code {ret}")

    @staticmethod
    def _open_unix(mailto: str) -> None:
        subprocess.run(["xdg-open", mailto], check=False)
