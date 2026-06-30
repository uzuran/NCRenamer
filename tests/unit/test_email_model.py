"""Unit tests for EmailModel — counter persistence and mutation."""

import json

import pytest

from app.models.email_model import EmailModel


@pytest.fixture
def counter_path(tmp_path):
    return tmp_path / "counter.json"


@pytest.fixture
def model(counter_path):
    return EmailModel(counter_file=str(counter_path))


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


def test_counter_starts_at_zero_when_file_is_missing(counter_path):
    assert not counter_path.exists()
    m = EmailModel(counter_file=str(counter_path))
    assert m.email_counter == 0


def test_counter_loaded_from_existing_file(counter_path):
    counter_path.write_text('{"counter": 7}', encoding="utf-8")
    m = EmailModel(counter_file=str(counter_path))
    assert m.email_counter == 7


def test_counter_defaults_to_zero_on_corrupt_json(counter_path):
    counter_path.write_text("not json at all", encoding="utf-8")
    m = EmailModel(counter_file=str(counter_path))
    assert m.email_counter == 0


def test_counter_defaults_to_zero_when_key_missing(counter_path):
    counter_path.write_text('{"other_key": 99}', encoding="utf-8")
    m = EmailModel(counter_file=str(counter_path))
    assert m.email_counter == 0


# --------------------------------------------------------------------------- #
# save_counter
# --------------------------------------------------------------------------- #


def test_save_counter_creates_file(model, counter_path):
    model.save_counter()
    assert counter_path.exists()


def test_save_counter_writes_correct_json(model, counter_path):
    model.email_counter = 3
    model.save_counter()
    data = json.loads(counter_path.read_text(encoding="utf-8"))
    assert data == {"counter": 3}


# --------------------------------------------------------------------------- #
# increment_counter
# --------------------------------------------------------------------------- #


def test_increment_increases_counter_by_one(model):
    model.increment_counter()
    assert model.email_counter == 1


def test_increment_twice_gives_two(model):
    model.increment_counter()
    model.increment_counter()
    assert model.email_counter == 2


def test_increment_persists_to_file(model, counter_path):
    model.increment_counter()
    data = json.loads(counter_path.read_text(encoding="utf-8"))
    assert data["counter"] == 1


# --------------------------------------------------------------------------- #
# reset_counter
# --------------------------------------------------------------------------- #


def test_reset_sets_counter_to_zero(model):
    model.email_counter = 5
    model.reset_counter()
    assert model.email_counter == 0


def test_reset_persists_to_file(model, counter_path):
    model.email_counter = 5
    model.reset_counter()
    data = json.loads(counter_path.read_text(encoding="utf-8"))
    assert data["counter"] == 0


def test_reset_after_increments_gives_zero(model):
    model.increment_counter()
    model.increment_counter()
    model.reset_counter()
    assert model.email_counter == 0
