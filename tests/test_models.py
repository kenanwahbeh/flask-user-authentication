import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from accounts.extensions import database as db
from accounts.models import User, Profile, UserSecurityToken, OAuthProvider


class TestUserCreate:
    def test_create_user(self, app):
        with app.app_context():
            user = User.create(
                username="alice",
                first_name="Alice",
                last_name="Smith",
                email="alice@example.com",
                password="Pass@1234",
            )
            assert user.id is not None
            assert user.username == "alice"
            assert user.email == "alice@example.com"
            assert not user.active

    def test_password_is_hashed(self, app):
        with app.app_context():
            user = User.create(
                username="bob",
                first_name="Bob",
                last_name="Jones",
                email="bob@example.com",
                password="Pass@1234",
            )
            assert user.password != "Pass@1234"
            assert user.check_password("Pass@1234")

    def test_profile_created_on_insert(self, app):
        with app.app_context():
            user = User.create(
                username="carol",
                first_name="Carol",
                last_name="White",
                email="carol@example.com",
                password="Pass@1234",
            )
            profile = Profile.query.filter_by(user_id=user.id).first()
            assert profile is not None


class TestUserAuthenticate:
    def test_authenticate_by_username(self, app, sample_user):
        with app.app_context():
            user = User.authenticate(username="testuser", password="Test@1234")
            assert user is not None
            assert user.username == "testuser"

    def test_authenticate_by_email(self, app, sample_user):
        with app.app_context():
            user = User.authenticate(
                username="testuser@example.com", password="Test@1234"
            )
            assert user is not None

    def test_wrong_password(self, app, sample_user):
        with app.app_context():
            user = User.authenticate(username="testuser", password="WrongPass@1")
            assert user is None

    def test_nonexistent_user(self, app):
        with app.app_context():
            user = User.authenticate(username="nobody", password="Pass@1234")
            assert user is None


class TestUserGetters:
    def test_get_by_id(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            assert user is not None
            assert user.username == "testuser"

    def test_get_by_id_not_found(self, app):
        with app.app_context():
            user = User.get_user_by_id("nonexistent-id")
            assert user is None

    def test_get_by_username(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_username("testuser")
            assert user is not None

    def test_get_by_email(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_email("testuser@example.com")
            assert user is not None


class TestUserPassword:
    def test_set_and_check_password(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            user.set_password("NewPass@123")
            assert user.check_password("NewPass@123")
            assert not user.check_password("Test@1234")

    def test_check_wrong_password(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            assert not user.check_password("WrongPassword1!")


class TestUserIsActive:
    def test_active_user(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            assert user.is_active is True

    def test_inactive_user(self, app, inactive_user):
        with app.app_context():
            user = User.get_user_by_id(inactive_user.id)
            assert user.is_active is False


class TestUserRepr:
    def test_repr(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            assert repr(user) == "<User 'testuser'>"


class TestGetOrCreate:
    def test_creates_new_user(self, app):
        with app.app_context():
            user = User.get_or_create(
                username="newuser",
                first_name="New",
                last_name="User",
                email="new@example.com",
                password="Pass@1234",
            )
            assert user.email == "new@example.com"

    def test_returns_existing_user(self, app, sample_user):
        with app.app_context():
            user = User.get_or_create(
                username="testuser",
                first_name="Test",
                last_name="User",
                email="testuser@example.com",
                password="Pass@1234",
            )
            assert user.id == sample_user.id

    def test_generates_unique_username_on_collision(self, app, sample_user):
        with app.app_context():
            user = User.get_or_create(
                username="testuser",
                first_name="Other",
                last_name="Person",
                email="other@example.com",
                password="Pass@1234",
            )
            assert user.username != "testuser"
            assert user.email == "other@example.com"


class TestUserDelete:
    def test_delete_user(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            uid = user.id
            user.delete()
            assert User.get_user_by_id(uid) is None


class TestUserSecurityToken:
    def test_generate_and_verify_token(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            token_str = user.generate_token(salt="test_salt")
            assert token_str is not None

            token_obj = User.verify_token(
                token=token_str, salt="test_salt", raise_exception=False
            )
            assert token_obj is not None
            assert token_obj.user_id == user.id

    def test_verify_nonexistent_token(self, app):
        with app.app_context():
            result = User.verify_token(
                token="nonexistent", salt="test_salt", raise_exception=False
            )
            assert result is None

    def test_expired_token(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            token_str = user.generate_token(salt="test_salt")
            token_obj = UserSecurityToken.query.filter_by(token=token_str).first()

            # Force expiration by backdating created_at
            token_obj.created_at = datetime.now() - timedelta(minutes=20)
            db.session.commit()

            result = User.verify_token(
                token=token_str, salt="test_salt", raise_exception=False
            )
            assert result is None

    def test_token_is_exists(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            token_str = user.generate_token(salt="test_salt")
            assert UserSecurityToken.is_exists(token_str) is not None
            assert UserSecurityToken.is_exists("no_such_token") is None


class TestOAuthProvider:
    def test_create_oauth_provider(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            provider = user.create_oauth_provider(
                provider="google", provider_id="google-sub-123"
            )
            assert provider.provider == "google"
            assert provider.provider_id == "google-sub-123"

    def test_is_social_user(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            assert user.is_social_user() is False

            user.create_oauth_provider(
                provider="google", provider_id="google-sub-456"
            )
            assert user.is_social_user() is True

    def test_repr(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            provider = user.create_oauth_provider(
                provider="google", provider_id="google-sub-789"
            )
            assert "google" in repr(provider)

    def test_remove_oauth_provider(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            user.create_oauth_provider(
                provider="google", provider_id="google-sub-remove"
            )
            assert user.is_social_user() is True
            user.remove_oauth_provider("google")
            assert user.is_social_user() is False


class TestProfile:
    def test_user_has_profile(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            assert user.profile is not None

    def test_get_avatar_default(self, app, sample_user):
        with app.test_request_context():
            user = User.get_user_by_id(sample_user.id)
            avatar = user.profile.get_avatar
            assert "default_avatar" in avatar

    def test_profile_bio_default(self, app, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            assert user.profile.bio == ""
