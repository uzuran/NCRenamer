"""Unit tests for EmailService.open_email."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import EmailService

# ── helpers ──────────────────────────────────────────────────────────────────


def _capture_mailto(platform: str) -> str:
    """Call open_email and return the mailto URL that would reach the OS."""
    captured: list[str] = []
    svc = EmailService()
    method = "_open_windows" if platform == "win32" else "_open_unix"
    with (
        patch("sys.platform", platform),
        patch.object(
            EmailService, method, staticmethod(lambda url: captured.append(url))
        ),
    ):
        svc.open_email("user@example.com", "Test subject", "Test body")
    return captured[0]


# ── mailto URL format ─────────────────────────────────────────────────────────


class TestMailtoFormat:
    def test_starts_with_mailto_scheme(self):
        assert _capture_mailto("win32").startswith("mailto:")

    def test_starts_with_mailto_scheme_unix(self):
        assert _capture_mailto("linux").startswith("mailto:")

    def test_recipient_in_url(self):
        assert "user@example.com" in _capture_mailto("win32")

    def test_subject_param_present(self):
        assert "subject=" in _capture_mailto("win32")

    def test_body_param_present(self):
        assert "body=" in _capture_mailto("win32")

    def test_no_literal_spaces_in_url(self):
        url = _capture_mailto("win32")
        assert " " not in url

    def test_subject_is_percent_encoded(self):
        captured: list[str] = []
        svc = EmailService()
        with (
            patch("sys.platform", "win32"),
            patch.object(
                EmailService,
                "_open_windows",
                staticmethod(lambda u: captured.append(u)),
            ),
        ):
            svc.open_email("x@y.com", "Hello World", "")
        assert "Hello+World" in captured[0] or "Hello%20World" in captured[0]


# ── Windows opener ────────────────────────────────────────────────────────────


class TestWindowsOpener:
    def _windll_patch(self, shell32_mock):
        """Return a patcher that works on both Windows and Linux (creates windll if absent)."""
        return patch("ctypes.windll", MagicMock(shell32=shell32_mock), create=True)

    def test_calls_shell_execute_w(self):
        mock_shell32 = MagicMock()
        mock_shell32.ShellExecuteW.return_value = 42  # > 32 means success

        with self._windll_patch(mock_shell32):
            EmailService._open_windows("mailto:x@y.com")

        mock_shell32.ShellExecuteW.assert_called_once()
        args = mock_shell32.ShellExecuteW.call_args[0]
        assert args[1] == "open"
        assert args[2].startswith("mailto:")

    def test_raises_on_return_code_le_32(self):
        mock_shell32 = MagicMock()
        mock_shell32.ShellExecuteW.return_value = 2  # error

        with self._windll_patch(mock_shell32), pytest.raises(OSError):
            EmailService._open_windows("mailto:x@y.com")

    def test_does_not_raise_on_return_code_gt_32(self):
        mock_shell32 = MagicMock()
        mock_shell32.ShellExecuteW.return_value = 33

        with self._windll_patch(mock_shell32):
            EmailService._open_windows("mailto:x@y.com")  # no exception


# ── Unix opener ───────────────────────────────────────────────────────────────


class TestUnixOpener:
    def test_calls_xdg_open(self):
        with patch("subprocess.run") as mock_run:
            EmailService._open_unix("mailto:x@y.com")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "xdg-open"
        assert cmd[1].startswith("mailto:")

    def test_passes_full_mailto_url(self):
        with patch("subprocess.run") as mock_run:
            EmailService._open_unix("mailto:a@b.com?subject=Hi")

        url = mock_run.call_args[0][0][1]
        assert "a@b.com" in url
        assert "subject=Hi" in url
