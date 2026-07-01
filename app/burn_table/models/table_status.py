"""TableStatus — read-only snapshot of the burn table's current capacity."""

from dataclasses import dataclass
from typing import Literal


WarningLevel = Literal["", "warning", "critical"]


@dataclass(frozen=True)
class TableStatus:
    """Immutable snapshot of how many rows are used and how many remain.

    Attributes:
        used_rows:  Number of rows with data (rows 3–36 where column A is filled).
        free_rows:  Number of remaining empty rows (max 34).
        is_full:    True when free_rows == 0.
        warning:    '' = OK, 'warning' = ≤5 free, 'critical' = ≤2 free.
    """

    used_rows: int
    free_rows: int
    is_full: bool
    warning: WarningLevel

    # ── convenience properties ──────────────────────────────────────────

    @property
    def status_text(self) -> str:
        """Human-readable status line for display in a UI label."""
        if self.is_full:
            return "Tabulka je plná!"
        if self.warning == "critical":
            return f"KRITICKÉ: zbývá {self.free_rows} řádků"
        if self.warning == "warning":
            return f"Varování: zbývá {self.free_rows} řádků"
        return f"Volné řádky: {self.free_rows}"

    @property
    def status_color(self) -> str:
        """Tkinter-compatible colour string for the status indicator."""
        if self.is_full or self.warning == "critical":
            return "#CC0000"  # red
        if self.warning == "warning":
            return "#CC7700"  # amber
        return "#007700"  # green
