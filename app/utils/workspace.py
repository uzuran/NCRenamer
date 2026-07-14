"""Hybrid workspace manager — resolves shared and per-user data paths.

Layout on disk::

    <root>/
      shared/
        materials.json   ← shared across every user
        todo.json        ← shared across every user
      users/
        <username>/
          settings.json  ← user-specific appearance / language prefs
          burn_table.xlsx ← user-specific burn log

In a frozen build *root* is the directory that contains the executable, which
may be a local install or a network share.  In development *root* is the
directory of ``sys.argv[0]`` (project root when running ``python app.py``).

All directory creation is explicit — callers must call the ``ensure_*``
helpers before expecting paths to exist.  This makes the lifecycle testable
without filesystem side-effects.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

from app.utils.shared_storage import exe_dir as _exe_dir


def _workspace_root() -> Path:
    """Return the root directory for workspace layout resolution."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return _exe_dir()


class WorkspaceManager:
    """Path resolver and directory initializer for the hybrid workspace.

    Path resolution is deterministic and has no side-effects; directory
    creation is explicit via the ``ensure_*`` helpers.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    # ── path properties ───────────────────────────────────────────────────────

    @property
    def root(self) -> Path:
        return self._root

    @property
    def shared_dir(self) -> Path:
        return self._root / "shared"

    def user_dir(self, username: str) -> Path:
        return self._root / "users" / username

    # ── shared paths ──────────────────────────────────────────────────────────

    def materials_path(self) -> Path:
        """Path to the shared materials JSON (shared across all users)."""
        return self.shared_dir / "materials.json"

    def todo_path(self) -> Path:
        """Path to the shared todo JSON (shared across all users)."""
        return self.shared_dir / "todo.json"

    # ── per-user paths ────────────────────────────────────────────────────────

    def user_settings_path(self, username: str) -> Path:
        """Path to the user-specific settings JSON."""
        return self.user_dir(username) / "settings.json"

    def user_burn_table_path(self, username: str) -> Path:
        """Path to the user-specific burn-table workbook."""
        return self.user_dir(username) / "burn_table.xlsx"

    # ── initialization ────────────────────────────────────────────────────────

    def ensure_shared_workspace_exists(self) -> None:
        """Create the shared directory (idempotent)."""
        self.shared_dir.mkdir(parents=True, exist_ok=True)

    def ensure_user_workspace_exists(self, username: str) -> None:
        """Create the per-user directory (idempotent)."""
        self.user_dir(username).mkdir(parents=True, exist_ok=True)


def create_workspace(username: str | None = None) -> tuple[WorkspaceManager, str]:
    """Bootstrap the workspace for *username* (defaults to the OS login name).

    Creates the shared and per-user directories if they do not exist.

    Returns:
        ``(workspace_manager, resolved_username)``
    """
    resolved = username or getpass.getuser()
    wm = WorkspaceManager(_workspace_root())
    wm.ensure_shared_workspace_exists()
    wm.ensure_user_workspace_exists(resolved)
    return wm, resolved
