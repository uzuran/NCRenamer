"""Tests that all Czech translation keys also exist in English (and vice-versa)."""

from app.translations.translations import LANGUAGES, cs, en


class TestTranslationCompleteness:
    def test_all_cs_keys_exist_in_en(self):
        missing = [k for k in cs if k not in en]
        assert not missing, f"Keys in cs but missing from en: {missing}"

    def test_all_en_keys_exist_in_cs(self):
        missing = [k for k in en if k not in cs]
        assert not missing, f"Keys in en but missing from cs: {missing}"

    def test_all_values_are_strings(self):
        for lang, d in [("cs", cs), ("en", en)]:
            for key, val in d.items():
                assert isinstance(val, str), f"[{lang}][{key}] is not a str: {type(val)}"

    def test_no_empty_values(self):
        for lang, d in [("cs", cs), ("en", en)]:
            for key, val in d.items():
                assert val, f"[{lang}][{key}] is an empty string"

    def test_format_placeholders_match_between_languages(self):
        """Keys with {} placeholders must have the same number in both languages."""
        for key in cs:
            if key not in en:
                continue
            cs_count = cs[key].count("{")
            en_count = en[key].count("{")
            assert cs_count == en_count, (
                f"Placeholder mismatch for key '{key}': "
                f"cs has {cs_count}, en has {en_count}"
            )

    def test_languages_dict_contains_cs_and_en(self):
        assert "cs" in LANGUAGES
        assert "en" in LANGUAGES

    def test_languages_dict_points_to_correct_dicts(self):
        assert LANGUAGES["cs"] is cs
        assert LANGUAGES["en"] is en

    def test_burn_table_tab_keys_present(self):
        for key in ("tab_steel", "tab_aluminium"):
            assert key in cs, f"Missing '{key}' in cs"
            assert key in en, f"Missing '{key}' in en"
