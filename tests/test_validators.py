import pytest
from unittest.mock import MagicMock
from wtforms import ValidationError

from accounts.validators import Unique, StrongNames, StrongUsername, StrongPassword


def _make_field(data):
    field = MagicMock()
    field.data = data
    field.name = "test_field"
    return field


class TestStrongNames:
    def test_valid_alpha(self):
        validator = StrongNames()
        validator(MagicMock(), _make_field("Alice"))

    def test_rejects_digits(self):
        validator = StrongNames()
        with pytest.raises(ValidationError):
            validator(MagicMock(), _make_field("Alice1"))

    def test_rejects_special_chars(self):
        validator = StrongNames()
        with pytest.raises(ValidationError):
            validator(MagicMock(), _make_field("Al!ce"))

    def test_rejects_spaces(self):
        validator = StrongNames()
        with pytest.raises(ValidationError):
            validator(MagicMock(), _make_field("Al ice"))

    def test_custom_message(self):
        validator = StrongNames(message="Custom msg")
        with pytest.raises(ValidationError, match="Custom msg"):
            validator(MagicMock(), _make_field("bad1"))


class TestStrongUsername:
    def test_valid_username(self):
        validator = StrongUsername()
        validator(MagicMock(), _make_field("user_name-123.test"))

    def test_rejects_spaces(self):
        validator = StrongUsername()
        with pytest.raises(ValidationError):
            validator(MagicMock(), _make_field("user name"))

    def test_rejects_special_chars(self):
        validator = StrongUsername()
        with pytest.raises(ValidationError):
            validator(MagicMock(), _make_field("user@name"))

    def test_custom_message(self):
        validator = StrongUsername(message="Bad username")
        with pytest.raises(ValidationError, match="Bad username"):
            validator(MagicMock(), _make_field("user!"))


class TestStrongPassword:
    def test_valid_strong_password(self):
        validator = StrongPassword()
        validator(MagicMock(), _make_field("Test@1234"))

    def test_rejects_no_uppercase(self):
        validator = StrongPassword()
        with pytest.raises(ValidationError):
            validator(MagicMock(), _make_field("test@1234"))

    def test_rejects_no_lowercase(self):
        validator = StrongPassword()
        with pytest.raises(ValidationError):
            validator(MagicMock(), _make_field("TEST@1234"))

    def test_rejects_no_digit(self):
        validator = StrongPassword()
        with pytest.raises(ValidationError):
            validator(MagicMock(), _make_field("Test@abcd"))

    def test_rejects_no_special_char(self):
        validator = StrongPassword()
        with pytest.raises(ValidationError):
            validator(MagicMock(), _make_field("Test12345"))

    def test_rejects_too_short(self):
        validator = StrongPassword()
        with pytest.raises(ValidationError):
            validator(MagicMock(), _make_field("T@1a"))

    def test_custom_message(self):
        validator = StrongPassword(message="Weak!")
        with pytest.raises(ValidationError, match="Weak!"):
            validator(MagicMock(), _make_field("weak"))


class TestUnique:
    def test_passes_when_not_found(self, app):
        with app.app_context():
            from accounts.models import User

            validator = Unique(User, User.username, message="Exists!")
            validator(MagicMock(), _make_field("nonexistent_user_xyz"))

    def test_raises_when_duplicate(self, app, sample_user):
        with app.app_context():
            from accounts.models import User

            validator = Unique(User, User.username, message="Exists!")
            with pytest.raises(ValidationError, match="Exists!"):
                validator(MagicMock(), _make_field("testuser"))

    def test_default_message(self, app, sample_user):
        with app.app_context():
            from accounts.models import User

            validator = Unique(User, User.username)
            with pytest.raises(ValidationError, match="already exists"):
                validator(MagicMock(), _make_field("testuser"))
