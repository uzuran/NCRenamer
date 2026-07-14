"""Unit tests for WorkspaceManager — path resolution and directory creation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.utils.workspace import WorkspaceManager, create_workspace


# ── path resolution ───────────────────────────────────────────────────────────


class TestPathResolution:
    def test_shared_dir_is_under_root(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        assert wm.shared_dir == tmp_path / "shared"

    def test_user_dir_is_under_users(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        assert wm.user_dir("alice") == tmp_path / "users" / "alice"

    def test_materials_path_is_inside_shared(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        assert wm.materials_path() == tmp_path / "shared" / "materials.json"

    def test_todo_path_is_inside_shared(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        assert wm.todo_path() == tmp_path / "shared" / "todo.json"

    def test_user_settings_path_is_inside_user_dir(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        assert wm.user_settings_path("alice") == tmp_path / "users" / "alice" / "settings.json"

    def test_user_burn_table_path_is_inside_user_dir(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        assert wm.user_burn_table_path("alice") == tmp_path / "users" / "alice" / "burn_table.xlsx"

    def test_root_property_returns_constructor_value(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        assert wm.root == tmp_path

    def test_different_users_have_different_dirs(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        assert wm.user_dir("alice") != wm.user_dir("bob")

    def test_different_users_have_different_settings_paths(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        assert wm.user_settings_path("alice") != wm.user_settings_path("bob")

    def test_different_users_have_different_burn_table_paths(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        assert wm.user_burn_table_path("alice") != wm.user_burn_table_path("bob")

    def test_shared_paths_are_the_same_for_every_user(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        assert wm.materials_path() == wm.materials_path()
        assert wm.todo_path() == wm.todo_path()


# ── directory creation ────────────────────────────────────────────────────────


class TestDirectoryCreation:
    def test_ensure_shared_workspace_creates_shared_dir(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        wm.ensure_shared_workspace_exists()
        assert (tmp_path / "shared").is_dir()

    def test_ensure_user_workspace_creates_user_dir(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        wm.ensure_user_workspace_exists("alice")
        assert (tmp_path / "users" / "alice").is_dir()

    def test_ensure_user_workspace_different_users_different_dirs(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        wm.ensure_user_workspace_exists("alice")
        wm.ensure_user_workspace_exists("bob")
        assert (tmp_path / "users" / "alice").is_dir()
        assert (tmp_path / "users" / "bob").is_dir()

    def test_ensure_shared_is_idempotent(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        wm.ensure_shared_workspace_exists()
        wm.ensure_shared_workspace_exists()
        assert (tmp_path / "shared").is_dir()

    def test_ensure_user_is_idempotent(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        wm.ensure_user_workspace_exists("alice")
        wm.ensure_user_workspace_exists("alice")
        assert (tmp_path / "users" / "alice").is_dir()

    def test_ensure_shared_does_not_create_user_dirs(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        wm.ensure_shared_workspace_exists()
        assert not (tmp_path / "users").exists()

    def test_ensure_user_does_not_create_shared_dir(self, tmp_path):
        wm = WorkspaceManager(tmp_path)
        wm.ensure_user_workspace_exists("alice")
        assert not (tmp_path / "shared").exists()

    def test_ensure_shared_creates_nested_dirs_if_root_missing(self, tmp_path):
        deep_root = tmp_path / "a" / "b" / "c"
        wm = WorkspaceManager(deep_root)
        wm.ensure_shared_workspace_exists()
        assert (deep_root / "shared").is_dir()


# ── create_workspace factory ──────────────────────────────────────────────────


class TestCreateWorkspace:
    def test_returns_workspace_manager_and_username(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.utils.workspace._workspace_root", lambda: tmp_path)
        wm, username = create_workspace("alice")
        assert isinstance(wm, WorkspaceManager)
        assert username == "alice"

    def test_creates_shared_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.utils.workspace._workspace_root", lambda: tmp_path)
        create_workspace("alice")
        assert (tmp_path / "shared").is_dir()

    def test_creates_user_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.utils.workspace._workspace_root", lambda: tmp_path)
        create_workspace("alice")
        assert (tmp_path / "users" / "alice").is_dir()

    def test_defaults_to_os_username(self, tmp_path, monkeypatch):
        import getpass
        monkeypatch.setattr("app.utils.workspace._workspace_root", lambda: tmp_path)
        monkeypatch.setattr(getpass, "getuser", lambda: "system_user")
        wm, username = create_workspace()
        assert username == "system_user"
        assert (tmp_path / "users" / "system_user").is_dir()

    def test_is_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.utils.workspace._workspace_root", lambda: tmp_path)
        create_workspace("alice")
        create_workspace("alice")
        assert (tmp_path / "users" / "alice").is_dir()

    def test_workspace_root_matches_returned_manager(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.utils.workspace._workspace_root", lambda: tmp_path)
        wm, _ = create_workspace("alice")
        assert wm.root == tmp_path
