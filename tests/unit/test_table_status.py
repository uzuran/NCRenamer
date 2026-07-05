"""Tests for TableStatus model — status_text, status_color, immutability."""

import pytest

from app.burn_table.models.table_status import TableStatus


def _status(free=34, used=0, is_full=False, warning=""):
    return TableStatus(used_rows=used, free_rows=free, is_full=is_full, warning=warning)


class TestStatusText:
    def test_full_table(self):
        st = TableStatus(used_rows=34, free_rows=0, is_full=True, warning="critical")
        assert "plná" in st.status_text.lower()

    def test_critical_warning(self):
        st = _status(free=2, used=32, warning="critical")
        assert "2" in st.status_text
        assert "KRITICKÉ" in st.status_text

    def test_warning_level(self):
        st = _status(free=5, used=29, warning="warning")
        assert "5" in st.status_text
        assert "Varování" in st.status_text

    def test_ok_state(self):
        st = _status(free=34)
        assert "34" in st.status_text
        assert "Volné" in st.status_text


class TestStatusColor:
    def test_full_is_red(self):
        st = TableStatus(used_rows=34, free_rows=0, is_full=True, warning="critical")
        assert st.status_color == "#CC0000"

    def test_critical_is_red(self):
        st = _status(free=1, warning="critical")
        assert st.status_color == "#CC0000"

    def test_warning_is_amber(self):
        st = _status(free=4, warning="warning")
        assert st.status_color == "#CC7700"

    def test_ok_is_green(self):
        st = _status(free=34)
        assert st.status_color == "#007700"


class TestImmutability:
    def test_frozen_dataclass_raises_on_set(self):
        st = _status()
        with pytest.raises((AttributeError, TypeError)):
            st.free_rows = 10  # frozen dataclass — raises at runtime
