"""bootstrap.py — extract embedded CNCs assets from the PyInstaller bundle.

When running as a frozen EXE, CNCs/laser.xls lives inside sys._MEIPASS
(the unpacked bundle directory).  On first launch this module copies it next
to the executable so the rest of the app can reach it at the normal filesystem
path <exe_dir>/CNCs/laser.xls.

Safe-overwrite rule: existing files are NEVER replaced.
  - A user who already has laser.xls with recorded data keeps their file.
  - A fresh install on any machine gets the blank template automatically.

No-op when running from source — the developer already has CNCs/ on disk.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Files to extract.  Listed explicitly — accidental extras in the bundle are
# never written to the user's machine.
_BUNDLE_FILES = (
    "laser.xls",
)


def bootstrap_cncs(exe_dir: Path) -> None:
    """Copy bundled CNCs files into <exe_dir>/CNCs on first launch.

    Parameters
    ----------
    exe_dir:
        Directory that contains the frozen executable
        (``Path(sys.executable).parent``).
    """
    if not getattr(sys, "frozen", False):
        return  # running from source; CNCs/ is already present on disk

    meipass: Path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    bundle_cncs = meipass / "CNCs"
    target_cncs = exe_dir / "CNCs"
    target_cncs.mkdir(parents=True, exist_ok=True)

    for name in _BUNDLE_FILES:
        src = bundle_cncs / name
        dst = target_cncs / name
        if dst.exists():
            continue  # never overwrite — user data is sacred
        if src.exists():
            shutil.copy2(src, dst)
