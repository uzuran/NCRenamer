"""Unit tests for shared_storage — exe_dir and file_lock."""

from pathlib import Path

from app.utils.shared_storage import exe_dir, file_lock


class TestExeDir:
    def test_returns_path_instance(self):
        result = exe_dir()
        assert isinstance(result, Path)

    def test_returns_existing_directory(self):
        result = exe_dir()
        assert result.exists()
        assert result.is_dir()

    def test_is_consistent_across_calls(self):
        assert exe_dir() == exe_dir()


class TestFileLock:
    def test_context_manager_does_not_raise(self, tmp_path):
        lock_path = tmp_path / "test.lock"
        with file_lock(lock_path):
            pass  # should not raise

    def test_creates_lock_file(self, tmp_path):
        lock_path = tmp_path / "sub" / "test.lock"
        with file_lock(lock_path):
            pass
        assert lock_path.exists()

    def test_creates_parent_directories(self, tmp_path):
        lock_path = tmp_path / "a" / "b" / "c" / "test.lock"
        with file_lock(lock_path):
            pass
        assert lock_path.parent.exists()

    def test_can_be_acquired_again_after_release(self, tmp_path):
        lock_path = tmp_path / "test.lock"
        with file_lock(lock_path):
            pass
        with file_lock(lock_path):
            pass  # second acquisition must succeed

    def test_yields_control_to_body(self, tmp_path):
        lock_path = tmp_path / "test.lock"
        executed = []
        with file_lock(lock_path):
            executed.append(True)
        assert executed == [True]
