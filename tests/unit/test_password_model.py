"""Unit tests for PasswordModel.verify_password."""

import pytest

from app.models.password_model import PasswordModel


@pytest.fixture
def model():
    return PasswordModel(correct_password="secret")


def test_correct_password_returns_true(model):
    assert model.verify_password("secret") is True


def test_wrong_password_returns_false(model):
    assert model.verify_password("wrong") is False


def test_empty_password_returns_false(model):
    assert model.verify_password("") is False


def test_none_password_returns_false(model):
    # CTkInputDialog returns None when the user cancels the dialog
    assert model.verify_password(None) is False


def test_case_sensitive(model):
    assert model.verify_password("Secret") is False
    assert model.verify_password("SECRET") is False


def test_password_with_leading_trailing_spaces_fails(model):
    assert model.verify_password(" secret ") is False
