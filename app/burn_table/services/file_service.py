"""FileService — low-level file I/O without any GUI dependency."""

from __future__ import annotations

from pathlib import Path


class FileService:
    """Reads file contents from disk.

    Intentionally has no file-dialog logic — the view layer is responsible
    for asking the user which file to open and then passing the path here.
    """

    # ── NC files ─────────────────────────────────────────────────────────

    def read_nc(self, path: Path) -> str:
        """Read an NC program file and return its full text content.

        Tries UTF-8 first, then falls back to Windows-1250 (common in
        Czech CNC shops).

        Raises:
            FileNotFoundError: if *path* does not exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"NC file not found: {path}")

        for encoding in ("utf-8", "windows-1250", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue

        return path.read_text(encoding="latin-1", errors="replace")

    # ── SCH / XML files ──────────────────────────────────────────────────

    def read_sch(self, path: Path) -> str:
        """Read a SCH XML schedule file and return its raw XML text.

        Raises:
            FileNotFoundError: if *path* does not exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"SCH file not found: {path}")

        for encoding in ("utf-8", "windows-1250", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue

        return path.read_text(encoding="latin-1", errors="replace")

    # ── Excel files ──────────────────────────────────────────────────────

    def exists(self, path: Path) -> bool:
        """Return True when *path* points to an existing file."""
        return path.is_file()

    def ensure_parent(self, path: Path) -> None:
        """Create parent directories of *path* if they do not yet exist."""
        path.parent.mkdir(parents=True, exist_ok=True)
