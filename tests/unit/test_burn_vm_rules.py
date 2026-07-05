"""Tests for BurnViewModel business rules:
- Date write-once (first record only)
- Sheet-format consecutive-dedup (→ '-----')
- Product-group per-batch (first record of each batch)
- Observer notification
- Settings key isolation (two VMs, same file)
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.burn_table.models.burn_record import BurnRecord
from app.burn_table.models.table_status import TableStatus
from app.burn_table.viewmodels.burn_view_model import BurnViewModel, _program_sort_key

# ── helpers ─────────────────────────────────────────────────────────────────


def _empty_vm(**kwargs) -> BurnViewModel:
    """BurnViewModel with mocked services and an empty loaded table."""
    vm = BurnViewModel(**kwargs)
    vm._table_path = Path("/fake/table.xls")
    vm._records = []
    vm._status = TableStatus(used_rows=0, free_rows=38, is_full=False, warning="")
    vm._date_written = False
    vm._last_sheet_format = ""
    vm._writer = MagicMock()
    return vm


def _rec(**kwargs) -> BurnRecord:
    defaults = {
        "date": "30.06.2026",
        "program_number": "6670-18",
        "sheet_format": "1.0037-5X1700X1500",
        "total_time": "00:21:51",
    }
    defaults.update(kwargs)
    return BurnRecord(**defaults)  # type: ignore[arg-type]


# ── Date write-once rule ─────────────────────────────────────────────────────


class TestDateRule:
    def test_first_record_keeps_date(self):
        vm = _empty_vm()
        result = vm._prepare_record_for_writing(_rec(date="30.06.2026"))
        assert result.date == "30.06.2026"

    def test_second_record_has_empty_date(self):
        vm = _empty_vm()
        vm._prepare_record_for_writing(_rec(date="30.06.2026"))  # first
        result = vm._prepare_record_for_writing(
            _rec(date="30.06.2026", program_number="AAA")
        )
        assert result.date == ""

    def test_date_written_flag_set_after_first(self):
        vm = _empty_vm()
        assert vm._date_written is False
        vm._prepare_record_for_writing(_rec())
        assert vm._date_written is True

    def test_clear_table_resets_date_flag(self):
        vm = _empty_vm()
        vm._date_written = True
        vm.clear_table()
        assert vm._date_written is False

    def test_load_empty_table_leaves_date_flag_false(self):
        vm = BurnViewModel()
        vm._reader = MagicMock()
        vm._reader.read_all.return_value = []
        vm._writer = MagicMock()
        vm._detector = MagicMock()
        vm._detector.detect_from_records.return_value = TableStatus(0, 38, False, "")
        vm.load_table(Path("/fake/table.xls"))
        assert vm._date_written is False

    def test_load_nonempty_table_sets_date_flag_true(self):
        vm = BurnViewModel()
        vm._reader = MagicMock()
        vm._reader.read_all.return_value = [_rec()]
        vm._writer = MagicMock()
        vm._detector = MagicMock()
        vm._detector.detect_from_records.return_value = TableStatus(1, 37, False, "")
        vm.load_table(Path("/fake/table.xls"))
        assert vm._date_written is True


# ── Sheet-format dedup rule ─────────────────────────────────────────────────


class TestSheetFormatDedupRule:
    def test_first_occurrence_written_in_full(self):
        vm = _empty_vm()
        result = vm._prepare_record_for_writing(_rec(sheet_format="1.0037-5X1700X1500"))
        assert result.sheet_format == "1.0037-5X1700X1500"

    def test_consecutive_same_format_becomes_dashes(self):
        vm = _empty_vm()
        fmt = "1.0037-5X1700X1500"
        vm._prepare_record_for_writing(_rec(sheet_format=fmt))  # first
        result = vm._prepare_record_for_writing(
            _rec(sheet_format=fmt, program_number="B")
        )
        assert result.sheet_format == "-----"

    def test_third_consecutive_also_becomes_dashes(self):
        vm = _empty_vm()
        fmt = "1.0037-5X1700X1500"
        for pn in ["A", "B"]:
            vm._prepare_record_for_writing(_rec(sheet_format=fmt, program_number=pn))
        result = vm._prepare_record_for_writing(
            _rec(sheet_format=fmt, program_number="C")
        )
        assert result.sheet_format == "-----"

    def test_different_format_resets_tracker(self):
        vm = _empty_vm()
        vm._prepare_record_for_writing(_rec(sheet_format="1.0037-5X1700X1500"))
        result = vm._prepare_record_for_writing(
            _rec(sheet_format="1.4301-3X2000X1000", program_number="B")
        )
        assert result.sheet_format == "1.4301-3X2000X1000"

    def test_format_after_different_written_in_full(self):
        vm = _empty_vm()
        vm._prepare_record_for_writing(_rec(sheet_format="1.0037-5X1700X1500"))
        vm._prepare_record_for_writing(
            _rec(sheet_format="1.4301-3X2000X1000", program_number="B")
        )
        result = vm._prepare_record_for_writing(
            _rec(sheet_format="1.0037-5X1700X1500", program_number="C")
        )
        # Different from last ("1.4301-...") → written in full
        assert result.sheet_format == "1.0037-5X1700X1500"

    def test_empty_format_not_tracked(self):
        vm = _empty_vm()
        vm._prepare_record_for_writing(_rec(sheet_format=""))
        # Tracker still empty, next record with real format written in full
        result = vm._prepare_record_for_writing(
            _rec(sheet_format="1.0037-5X1700X1500", program_number="B")
        )
        assert result.sheet_format == "1.0037-5X1700X1500"

    def test_clear_resets_format_tracker(self):
        vm = _empty_vm()
        fmt = "1.0037-5X1700X1500"
        vm._prepare_record_for_writing(_rec(sheet_format=fmt))
        vm.clear_table()
        assert vm._last_sheet_format == ""

    def test_load_resumes_format_from_last_real_record(self):
        vm = BurnViewModel()
        records = [
            _rec(sheet_format="1.0037-5X1700X1500"),
            _rec(sheet_format="-----", program_number="B"),
            _rec(sheet_format="1.4301-3X2000X1000", program_number="C"),
            _rec(sheet_format="-----", program_number="D"),
        ]
        vm._reader = MagicMock()
        vm._reader.read_all.return_value = records
        vm._writer = MagicMock()
        vm._detector = MagicMock()
        vm._detector.detect_from_records.return_value = TableStatus(4, 34, False, "")
        vm.load_table(Path("/fake/table.xls"))
        # Last real format was "1.4301-3X2000X1000" (the "-----" entries are skipped)
        assert vm._last_sheet_format == "1.4301-3X2000X1000"

    def test_original_record_not_mutated(self):
        vm = _empty_vm()
        fmt = "1.0037-5X1700X1500"
        original = _rec(sheet_format=fmt)
        vm._prepare_record_for_writing(original)  # first → no mutation
        # second with same format
        second = _rec(sheet_format=fmt, program_number="B")
        result = vm._prepare_record_for_writing(second)
        # result is modified but second is unchanged
        assert second.sheet_format == fmt
        assert result.sheet_format == "-----"


# ── Product-group per-batch rule ─────────────────────────────────────────────


class TestProductGroupPerBatchRule:
    def _vm_with_records_in_table(self) -> BurnViewModel:
        vm = _empty_vm()
        return vm

    def _fake_records(self, programs: list[str], format_: str = "1.0037-5X1700X1500"):
        """Return a side_effect callable that mirrors the real recorder's product_group passthrough."""
        it = iter([_rec(program_number=p, sheet_format=format_) for p in programs])

        def side_effect(nc_path, sch_path=None, product_group=""):
            return dataclasses.replace(next(it), product_group=product_group)

        return side_effect

    def test_first_record_has_product_group(self):
        vm = _empty_vm()
        written: list[BurnRecord] = []
        vm._writer.write_record_at_row.side_effect = (
            lambda path, row, rec: written.append(rec)
        )

        with patch.object(
            vm._recorder,
            "record_from_paths",
            side_effect=self._fake_records(["A", "B", "C"]),
        ):
            vm.load_and_append_batch(
                [Path("/nc/A.NC"), Path("/nc/B.NC"), Path("/nc/C.NC")],
                product_group="pwa",
            )

        assert written[0].product_group == "pwa"

    def test_subsequent_records_have_empty_product_group(self):
        vm = _empty_vm()
        written: list[BurnRecord] = []
        vm._writer.write_record_at_row.side_effect = (
            lambda path, row, rec: written.append(rec)
        )

        with patch.object(
            vm._recorder,
            "record_from_paths",
            side_effect=self._fake_records(["A", "B", "C"]),
        ):
            vm.load_and_append_batch(
                [Path("/nc/A.NC"), Path("/nc/B.NC"), Path("/nc/C.NC")],
                product_group="pwa",
            )

        assert written[1].product_group == ""
        assert written[2].product_group == ""

    def test_new_batch_resets_flag(self):
        vm = _empty_vm()
        written: list[BurnRecord] = []
        vm._writer.write_record_at_row.side_effect = (
            lambda path, row, rec: written.append(rec)
        )

        with patch.object(
            vm._recorder, "record_from_paths", side_effect=self._fake_records(["A"])
        ):
            vm.load_and_append_batch([Path("/nc/A.NC")], product_group="pwa")

        with patch.object(
            vm._recorder, "record_from_paths", side_effect=self._fake_records(["B"])
        ):
            vm.load_and_append_batch([Path("/nc/B.NC")], product_group="steel")

        assert written[0].product_group == "pwa"
        assert written[1].product_group == "steel"


# ── Observer notifications ────────────────────────────────────────────────────


class TestObserverNotification:
    def test_subscribe_registers_callback(self):
        vm = BurnViewModel()
        called = []
        vm.subscribe(lambda: called.append(1))
        vm._notify()
        assert len(called) == 1

    def test_unsubscribe_stops_notifications(self):
        vm = BurnViewModel()
        called = []

        def cb():
            called.append(1)

        vm.subscribe(cb)
        vm.unsubscribe(cb)
        vm._notify()
        assert called == []

    def test_broken_callback_does_not_crash_vm(self):
        vm = BurnViewModel()
        vm.subscribe(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        vm._notify()  # must not raise

    def test_load_and_append_notifies(self):
        vm = _empty_vm()
        notified = []
        vm.subscribe(lambda: notified.append(1))

        with patch.object(vm._recorder, "record_from_paths", return_value=_rec()):
            vm.load_and_append_batch([Path("/nc/X.NC")])

        assert len(notified) >= 1


# ── Settings key isolation ───────────────────────────────────────────────────


class TestSettingsKeyIsolation:
    def test_two_vms_save_separate_keys(self, tmp_path):
        from app.burn_table.viewmodels import burn_view_model as bvm_module

        settings_file = tmp_path / "settings.json"

        # Patch _SETTINGS_FILE to a temp path
        original = bvm_module._SETTINGS_FILE
        bvm_module._SETTINGS_FILE = settings_file
        try:
            vm_steel = BurnViewModel(settings_key="last_table_path")
            vm_alu = BurnViewModel(settings_key="last_table_path_alu")

            vm_steel._table_path = Path("/data/laser.xls")
            vm_alu._table_path = Path("/data/laser.xls")

            vm_steel._save_settings()
            vm_alu._save_settings()

            import json

            data = json.loads(settings_file.read_text())
            assert "last_table_path" in data
            assert "last_table_path_alu" in data
            assert data["last_table_path"] == str(Path("/data/laser.xls"))
            assert data["last_table_path_alu"] == str(Path("/data/laser.xls"))
        finally:
            bvm_module._SETTINGS_FILE = original

    def test_second_vm_does_not_overwrite_first_key(self, tmp_path):
        from app.burn_table.viewmodels import burn_view_model as bvm_module

        settings_file = tmp_path / "settings.json"
        original = bvm_module._SETTINGS_FILE
        bvm_module._SETTINGS_FILE = settings_file
        try:
            vm_steel = BurnViewModel(settings_key="last_table_path")
            vm_alu = BurnViewModel(settings_key="last_table_path_alu")

            vm_steel._table_path = Path("/steel.xls")
            vm_steel._save_settings()

            vm_alu._table_path = Path("/alu.xls")
            vm_alu._save_settings()

            import json

            data = json.loads(settings_file.read_text())
            # Steel key must still be there
            assert data["last_table_path"] == str(Path("/steel.xls"))
            assert data["last_table_path_alu"] == str(Path("/alu.xls"))
        finally:
            bvm_module._SETTINGS_FILE = original


# ── Message and status helpers ────────────────────────────────────────────────


class TestMessageAndStatus:
    def test_no_table_message_uses_texts(self):
        vm = _empty_vm(texts={"load_table_first": "Nejprve načtěte!"})
        vm._table_path = None
        vm.load_and_append_batch([Path("/nc/X.NC")])
        assert vm.message == "Nejprve načtěte!"
        assert vm.message_ok is False

    def test_full_table_prevents_append(self):
        from app.burn_table.models.table_status import TableStatus

        vm = _empty_vm()
        vm._status = TableStatus(
            used_rows=38, free_rows=0, is_full=True, warning="critical"
        )
        with patch.object(vm._recorder, "record_from_paths", return_value=_rec()):
            vm.load_and_append_batch([Path("/nc/X.NC")])
        assert vm._writer.write_record_at_row.call_count == 0

    def test_clear_popup(self):
        vm = BurnViewModel()
        vm._popup_message = "warning text"
        vm.clear_popup()
        assert vm.popup_message is None

    def test_update_texts_changes_message_language(self):
        vm = _empty_vm(texts={"load_table_first": "EN: load first"})
        vm._table_path = None
        vm.load_and_append_batch([Path("/nc/X.NC")])
        assert "EN: load first" in vm.message

        vm.update_texts({"load_table_first": "CS: načtěte"})
        vm.load_and_append_batch([Path("/nc/X.NC")])
        assert "CS: načtěte" in vm.message


# ── Batch sort by program-number suffix ──────────────────────────────────────


class TestProgramSortKey:
    def test_standard_format_returns_suffix_int(self):
        assert _program_sort_key("6678-79") == 79

    def test_larger_suffix(self):
        assert _program_sort_key("6678-120") == 120

    def test_no_dash_returns_zero(self):
        assert _program_sort_key("NODASH") == 0

    def test_non_numeric_suffix_returns_zero(self):
        assert _program_sort_key("6678-X") == 0

    def test_empty_string_returns_zero(self):
        assert _program_sort_key("") == 0


class TestBatchSortByProgramNumber:
    def _fake_by_stem(self, mapping: dict[str, str]):
        """side_effect that resolves program_number from the NC path stem."""

        def side_effect(nc_path, sch_path=None, product_group=""):
            return _rec(program_number=mapping[nc_path.stem])

        return side_effect

    def test_uploaded_out_of_order_written_in_suffix_order(self):
        vm = _empty_vm()
        written: list[BurnRecord] = []
        vm._writer.write_record_at_row.side_effect = (
            lambda path, row, rec: written.append(rec)
        )

        mapping = {"6678-80": "6678-80", "6678-78": "6678-78", "6678-79": "6678-79"}
        with patch.object(
            vm._recorder, "record_from_paths", side_effect=self._fake_by_stem(mapping)
        ):
            vm.load_and_append_batch(
                [
                    Path("/nc/6678-80.NC"),
                    Path("/nc/6678-78.NC"),
                    Path("/nc/6678-79.NC"),
                ]
            )

        assert [r.program_number for r in written] == ["6678-78", "6678-79", "6678-80"]

    def test_already_sorted_batch_unchanged(self):
        vm = _empty_vm()
        written: list[BurnRecord] = []
        vm._writer.write_record_at_row.side_effect = (
            lambda path, row, rec: written.append(rec)
        )

        mapping = {"6678-78": "6678-78", "6678-79": "6678-79", "6678-80": "6678-80"}
        with patch.object(
            vm._recorder, "record_from_paths", side_effect=self._fake_by_stem(mapping)
        ):
            vm.load_and_append_batch(
                [
                    Path("/nc/6678-78.NC"),
                    Path("/nc/6678-79.NC"),
                    Path("/nc/6678-80.NC"),
                ]
            )

        assert [r.program_number for r in written] == ["6678-78", "6678-79", "6678-80"]

    def test_non_standard_program_sorts_before_numeric(self):
        vm = _empty_vm()
        written: list[BurnRecord] = []
        vm._writer.write_record_at_row.side_effect = (
            lambda path, row, rec: written.append(rec)
        )

        mapping = {"6678-80": "6678-80", "NOFORMAT": "NOFORMAT"}
        with patch.object(
            vm._recorder, "record_from_paths", side_effect=self._fake_by_stem(mapping)
        ):
            vm.load_and_append_batch(
                [
                    Path("/nc/6678-80.NC"),
                    Path("/nc/NOFORMAT.NC"),
                ]
            )

        assert written[0].program_number == "NOFORMAT"
        assert written[1].program_number == "6678-80"

    def test_sort_applies_before_date_dedup(self):
        """First written record (by suffix order) gets the date, not the first uploaded."""
        vm = _empty_vm()
        written: list[BurnRecord] = []
        vm._writer.write_record_at_row.side_effect = (
            lambda path, row, rec: written.append(rec)
        )

        mapping = {"6678-80": "6678-80", "6678-78": "6678-78"}
        with patch.object(
            vm._recorder, "record_from_paths", side_effect=self._fake_by_stem(mapping)
        ):
            vm.load_and_append_batch(
                [
                    Path("/nc/6678-80.NC"),
                    Path("/nc/6678-78.NC"),
                ]
            )

        # 6678-78 sorts first, so it gets the date; 6678-80 gets an empty date
        assert written[0].program_number == "6678-78"
        assert written[0].date != ""
        assert written[1].program_number == "6678-80"
        assert written[1].date == ""
