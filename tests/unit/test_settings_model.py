"""Unit tests for SettingsModel — load, save, get, set."""

import json

import pytest

from app.models.settings_model import SettingsModel


@pytest.fixture
def settings_path(tmp_path):
    return tmp_path / "settings.json"


@pytest.fixture
def model(settings_path):
    return SettingsModel(path=str(settings_path))


# --------------------------------------------------------------------------- #
# load
# --------------------------------------------------------------------------- #


def test_load_gives_empty_dict_when_file_missing(model):
    model.load()
    assert model.settings == {}


def test_load_parses_existing_json(settings_path, model):
    settings_path.write_text(
        '{"language": "cs", "appearance_mode": "Dark"}', encoding="utf-8"
    )
    model.load()
    assert model.settings == {"language": "cs", "appearance_mode": "Dark"}


def test_load_gives_empty_dict_on_corrupt_json(settings_path, model):
    settings_path.write_text("not valid json {{", encoding="utf-8")
    model.load()
    assert model.settings == {}


def test_load_gives_empty_dict_on_empty_file(settings_path, model):
    settings_path.write_text("", encoding="utf-8")
    model.load()
    assert model.settings == {}


# --------------------------------------------------------------------------- #
# save
# --------------------------------------------------------------------------- #


def test_save_creates_file(model, settings_path):
    model.settings["key"] = "value"
    model.save()
    assert settings_path.exists()


def test_save_writes_valid_json(model, settings_path):
    model.settings = {"language": "en"}
    model.save()
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    assert data == {"language": "en"}


def test_save_creates_parent_directories(tmp_path):
    nested = tmp_path / "a" / "b" / "settings.json"
    m = SettingsModel(path=str(nested))
    m.settings["x"] = 1
    m.save()
    assert nested.exists()


# --------------------------------------------------------------------------- #
# get
# --------------------------------------------------------------------------- #


def test_get_returns_value_for_existing_key(model):
    model.settings["language"] = "en"
    assert model.get("language") == "en"


def test_get_returns_none_for_missing_key_by_default(model):
    assert model.get("nonexistent") is None


def test_get_returns_custom_default_for_missing_key(model):
    assert model.get("nonexistent", "fallback") == "fallback"


# --------------------------------------------------------------------------- #
# set
# --------------------------------------------------------------------------- #


def test_set_updates_in_memory_value(model):
    model.set("language", "en")
    assert model.settings["language"] == "en"


def test_set_persists_immediately(model, settings_path):
    model.set("language", "en")
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    assert data["language"] == "en"


# --------------------------------------------------------------------------- #
# round-trip
# --------------------------------------------------------------------------- #


def test_round_trip_save_then_load(settings_path):
    m1 = SettingsModel(path=str(settings_path))
    m1.settings = {"language": "cs", "appearance_mode": "Light"}
    m1.save()

    m2 = SettingsModel(path=str(settings_path))
    m2.load()
    assert m2.settings == {"language": "cs", "appearance_mode": "Light"}
