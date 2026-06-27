import pytest
from unittest.mock import patch, MagicMock

from accounts.extensions import database as db
from accounts.models import User, UserSecurityToken


def _login(client, username="testuser", password="Test@1234"):
    return client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "remember": True,
        },
    )


class TestIndex:
    def test_requires_login(self, client):
        response = client.get("/")
        assert response.status_code == 302

    def test_home_alias(self, client):
        response = client.get("/home")
        assert response.status_code == 302

    def test_authenticated_access(self, app, client, sample_user):
        with app.app_context():
            _login(client)
            response = client.get("/")
            assert response.status_code == 200


class TestRegister:
    def test_get_register_page(self, client):
        response = client.get("/register")
        assert response.status_code == 200

    def test_register_success(self, app, client):
        with app.app_context():
            with patch("accounts.views.User.send_confirmation"):
                response = client.post(
                    "/register",
                    data={
                        "username": "newuser",
                        "first_name": "New",
                        "last_name": "User",
                        "email": "newuser@example.com",
                        "password": "Strong@123",
                        "remember": True,
                    },
                    follow_redirects=False,
                )
                assert response.status_code == 302


class TestLogin:
    def test_get_login_page(self, client):
        response = client.get("/login")
        assert response.status_code == 200

    def test_login_success(self, app, client, sample_user):
        with app.app_context():
            response = _login(client)
            assert response.status_code == 302

    def test_login_wrong_password(self, app, client, sample_user):
        with app.app_context():
            response = _login(client, password="Wrong@1234")
            assert response.status_code == 302

    def test_login_inactive_user(self, app, client, inactive_user):
        with app.app_context():
            with patch("accounts.views.User.send_confirmation"):
                response = _login(client, username="inactive")
                assert response.status_code == 302

    def test_login_redirect_when_authenticated(self, app, client, sample_user):
        with app.app_context():
            _login(client)
            response = client.get("/login")
            assert response.status_code == 302


class TestLogout:
    def test_logout(self, app, client, sample_user):
        with app.app_context():
            _login(client)
            response = client.get("/logout", follow_redirects=False)
            assert response.status_code == 302

    def test_logout_requires_login(self, client):
        response = client.get("/logout")
        assert response.status_code == 302


class TestForgotPassword:
    def test_get_page(self, client):
        response = client.get("/forgot/password")
        assert response.status_code == 200

    def test_submit_valid_email(self, app, client, sample_user):
        with app.app_context():
            with patch("accounts.views.send_reset_password"):
                response = client.post(
                    "/forgot/password",
                    data={
                        "email": "testuser@example.com",
                        "remember": True,
                    },
                    follow_redirects=False,
                )
                assert response.status_code == 302

    def test_submit_unknown_email(self, app, client):
        with app.app_context():
            response = client.post(
                "/forgot/password",
                data={
                    "email": "unknown@example.com",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302


class TestResetPassword:
    def _get_token(self, app, user_ref):
        with app.app_context():
            u = User.get_user_by_id(user_ref.id)
            return u.generate_token(salt=app.config["SALT_RESET_PASSWORD"])

    def test_get_page_valid_token(self, app, client, sample_user):
        with app.app_context():
            token = self._get_token(app, sample_user)
            response = client.get(f"/password/reset?token={token}")
            assert response.status_code == 200

    def test_get_page_invalid_token(self, client):
        response = client.get("/password/reset?token=invalid")
        assert response.status_code == 404

    def test_reset_success(self, app, client, sample_user):
        with app.app_context():
            token = self._get_token(app, sample_user)
            response = client.post(
                f"/password/reset?token={token}",
                data={
                    "password": "NewPass@123",
                    "confirm_password": "NewPass@123",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302

    def test_reset_mismatched_passwords(self, app, client, sample_user):
        with app.app_context():
            token = self._get_token(app, sample_user)
            response = client.post(
                f"/password/reset?token={token}",
                data={
                    "password": "NewPass@123",
                    "confirm_password": "DiffPass@123",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302

    def test_reset_same_as_old(self, app, client, sample_user):
        with app.app_context():
            token = self._get_token(app, sample_user)
            response = client.post(
                f"/password/reset?token={token}",
                data={
                    "password": "Test@1234",
                    "confirm_password": "Test@1234",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302


class TestChangePassword:
    def _create_regular_user(self, app):
        with app.app_context():
            user = User.create(
                username="regularuser",
                first_name="Regular",
                last_name="User",
                email="regular@example.com",
                password="Test@1234",
            )
            user.active = True
            db.session.commit()

    def test_get_page(self, app, client):
        with app.app_context():
            self._create_regular_user(app)
            _login(client, username="regularuser")
            response = client.get("/change/password")
            assert response.status_code == 200

    def test_change_success(self, app, client):
        with app.app_context():
            self._create_regular_user(app)
            _login(client, username="regularuser")
            response = client.post(
                "/change/password",
                data={
                    "old_password": "Test@1234",
                    "new_password": "NewPass@123",
                    "confirm_password": "NewPass@123",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302

    def test_wrong_old_password(self, app, client):
        with app.app_context():
            self._create_regular_user(app)
            _login(client, username="regularuser")
            response = client.post(
                "/change/password",
                data={
                    "old_password": "Wrong@1234",
                    "new_password": "NewPass@123",
                    "confirm_password": "NewPass@123",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302

    def test_mismatched_new_passwords(self, app, client):
        with app.app_context():
            self._create_regular_user(app)
            _login(client, username="regularuser")
            response = client.post(
                "/change/password",
                data={
                    "old_password": "Test@1234",
                    "new_password": "NewPass@123",
                    "confirm_password": "OtherPass@1",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302

    def test_weak_new_password(self, app, client):
        with app.app_context():
            self._create_regular_user(app)
            _login(client, username="regularuser")
            response = client.post(
                "/change/password",
                data={
                    "old_password": "Test@1234",
                    "new_password": "weakpass",
                    "confirm_password": "weakpass",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302


class TestChangeEmail:
    def _create_and_login(self, app, client):
        with app.app_context():
            user = User.create(
                username="emailuser",
                first_name="Email",
                last_name="User",
                email="emailuser@example.com",
                password="Test@1234",
            )
            user.active = True
            db.session.commit()
        _login(client, username="emailuser")

    def test_get_page(self, app, client):
        with app.app_context():
            self._create_and_login(app, client)
            response = client.get("/change/email")
            assert response.status_code == 200

    def test_change_email_success(self, app, client):
        with app.app_context():
            self._create_and_login(app, client)
            with patch("accounts.views.send_reset_email"):
                response = client.post(
                    "/change/email",
                    data={
                        "email": "newemail@example.com",
                        "remember": True,
                    },
                    follow_redirects=False,
                )
                assert response.status_code == 302

    def test_same_email(self, app, client):
        with app.app_context():
            self._create_and_login(app, client)
            response = client.post(
                "/change/email",
                data={
                    "email": "emailuser@example.com",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302

    def test_email_already_registered(self, app, client, sample_user):
        with app.app_context():
            self._create_and_login(app, client)
            response = client.post(
                "/change/email",
                data={
                    "email": "testuser@example.com",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302


class TestConfirmAccount:
    def test_valid_token_get(self, app, client, inactive_user):
        with app.app_context():
            user = User.get_user_by_id(inactive_user.id)
            token = user.generate_token(salt=app.config["SALT_ACCOUNT_CONFIRM"])
            response = client.get(f"/account/confirm?token={token}")
            assert response.status_code == 200

    def test_valid_token_post_activates(self, app, client, inactive_user):
        with app.app_context():
            user = User.get_user_by_id(inactive_user.id)
            token = user.generate_token(salt=app.config["SALT_ACCOUNT_CONFIRM"])
            response = client.post(
                f"/account/confirm?token={token}", follow_redirects=False
            )
            assert response.status_code == 302
            user = User.get_user_by_id(inactive_user.id)
            assert user.active is True

    def test_invalid_token(self, client):
        response = client.get("/account/confirm?token=badtoken")
        assert response.status_code == 404


class TestConfirmEmail:
    def test_invalid_token(self, client):
        response = client.get("/account/email/confirm?token=invalid")
        assert response.status_code == 404

    def test_valid_token_get(self, app, client, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            token = user.generate_token(salt=app.config["SALT_CHANGE_EMAIL"])
            response = client.get(f"/account/email/confirm?token={token}")
            assert response.status_code == 200

    def test_valid_token_post_updates_email(self, app, client, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            user.change_email = "updated@example.com"
            db.session.commit()
            token = user.generate_token(salt=app.config["SALT_CHANGE_EMAIL"])
            response = client.post(
                f"/account/email/confirm?token={token}", follow_redirects=False
            )
            assert response.status_code == 302
            user = User.get_user_by_id(sample_user.id)
            assert user.email == "updated@example.com"


class TestProfile:
    def _create_and_login(self, app, client):
        with app.app_context():
            user = User.create(
                username="profuser",
                first_name="Prof",
                last_name="User",
                email="profuser@example.com",
                password="Test@1234",
            )
            user.active = True
            db.session.commit()
        _login(client, username="profuser")

    def test_get_profile(self, app, client):
        with app.app_context():
            self._create_and_login(app, client)
            response = client.get("/profile")
            assert response.status_code == 200

    def test_update_profile(self, app, client):
        with app.app_context():
            self._create_and_login(app, client)
            response = client.post(
                "/profile",
                data={
                    "username": "profuser",
                    "first_name": "Updated",
                    "last_name": "Name",
                    "about": "My bio",
                },
                follow_redirects=False,
            )
            assert response.status_code == 302

    def test_duplicate_username(self, app, client, sample_user):
        with app.app_context():
            self._create_and_login(app, client)
            response = client.post(
                "/profile",
                data={
                    "username": "testuser",
                    "first_name": "Prof",
                    "last_name": "User",
                    "about": "",
                },
                follow_redirects=False,
            )
            assert response.status_code == 302


class TestSettings:
    def test_get_settings(self, app, client, sample_user):
        with app.app_context():
            _login(client)
            response = client.get("/account/settings")
            assert response.status_code == 200


class TestDeleteUser:
    def _create_and_login(self, app, client):
        with app.app_context():
            user = User.create(
                username="deleteuser",
                first_name="Delete",
                last_name="User",
                email="delete@example.com",
                password="Test@1234",
            )
            user.active = True
            db.session.commit()
        _login(client, username="deleteuser")

    def test_delete_success(self, app, client):
        with app.app_context():
            self._create_and_login(app, client)
            response = client.post(
                "/account/delete",
                data={"password": "Test@1234"},
                follow_redirects=False,
            )
            assert response.status_code == 302
            assert User.get_user_by_username("deleteuser") is None

    def test_delete_wrong_password(self, app, client):
        with app.app_context():
            self._create_and_login(app, client)
            response = client.post(
                "/account/delete",
                data={"password": "Wrong@1234"},
                follow_redirects=False,
            )
            assert response.status_code == 302
            assert User.get_user_by_username("deleteuser") is not None


class TestLoginGuestUser:
    def test_post_guest_login(self, app, client, sample_user):
        with app.app_context():
            response = client.post("/login_as_guest", follow_redirects=False)
            assert response.status_code == 302

    def test_get_returns_404(self, client):
        response = client.get("/login_as_guest")
        assert response.status_code == 404

    def test_guest_login_no_testuser(self, app, client):
        with app.app_context():
            response = client.post("/login_as_guest", follow_redirects=False)
            assert response.status_code == 302


class TestResetPasswordWhileAuthenticated:
    def test_reset_password_while_logged_in(self, app, client, sample_user):
        """When an authenticated user resets password, redirect to index."""
        with app.app_context():
            _login(client)
            user = User.get_user_by_id(sample_user.id)
            token = user.generate_token(salt=app.config["SALT_RESET_PASSWORD"])
            response = client.post(
                f"/password/reset?token={token}",
                data={
                    "password": "Brand@New1",
                    "confirm_password": "Brand@New1",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302
            assert "/" in response.headers.get("Location", "")


class TestGoogleOAuth:
    def test_google_login_post(self, app, client, sample_user):
        with app.app_context():
            with patch("accounts.views.oauth") as mock_oauth:
                mock_oauth.google.authorize_redirect.return_value = app.make_response(
                    ("redirect", 302)
                )
                response = client.post("/account/google-login", follow_redirects=False)
                assert response.status_code == 302

    def test_google_login_connection_error(self, app, client):
        from requests.exceptions import ConnectionError

        with app.app_context():
            with patch("accounts.views.oauth") as mock_oauth:
                mock_oauth.google.authorize_redirect.side_effect = ConnectionError()
                response = client.post(
                    "/account/google-login", follow_redirects=False
                )
                assert response.status_code == 302

    def test_google_callback_oauth_error(self, app, client):
        from authlib.integrations.flask_client import OAuthError

        with app.app_context():
            with patch("accounts.views.oauth") as mock_oauth:
                mock_oauth.google.authorize_access_token.side_effect = OAuthError(
                    "error"
                )
                response = client.get(
                    "/account/google-login/callback", follow_redirects=False
                )
                assert response.status_code == 302

    def test_google_callback_success_new_user(self, app, client):
        with app.app_context():
            token_data = {
                "userinfo": {
                    "email": "googleuser@example.com",
                    "email_verified": True,
                    "sub": "google-sub-new-user",
                    "given_name": "Google",
                    "family_name": "User",
                    "picture": "",
                }
            }
            with patch("accounts.views.oauth") as mock_oauth:
                mock_oauth.google.authorize_access_token.return_value = token_data
                with patch("accounts.views.download_and_save_image_from_url", return_value=None):
                    response = client.get(
                        "/account/google-login/callback", follow_redirects=False
                    )
                    assert response.status_code == 302

    def test_google_callback_no_token(self, app, client):
        with app.app_context():
            with patch("accounts.views.oauth") as mock_oauth:
                mock_oauth.google.authorize_access_token.return_value = None
                response = client.get(
                    "/account/google-login/callback", follow_redirects=False
                )
                assert response.status_code == 302


class TestErrorHandlers:
    def test_404(self, client):
        response = client.get("/nonexistent-page")
        assert response.status_code == 404


class TestRemoveOAuthProvider:
    def test_requires_login(self, client):
        response = client.post("/account/oauth/remove?provider=google")
        assert response.status_code == 302

    def test_invalid_provider(self, app, client, sample_user):
        with app.app_context():
            _login(client)
            response = client.post(
                "/account/oauth/remove?provider=invalid",
                follow_redirects=False,
            )
            assert response.status_code in (302, 400)

    def test_remove_nonexistent_provider(self, app, client, sample_user):
        with app.app_context():
            _login(client)
            response = client.post(
                "/account/oauth/remove?provider=google",
                follow_redirects=False,
            )
            assert response.status_code == 302
