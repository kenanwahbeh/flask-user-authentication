import pytest
from flask import url_for
from flask_login import login_user

from accounts.models import User


class TestAuthenticationRedirect:
    def test_redirects_authenticated_user(self, app, client, sample_user):
        with app.app_context():
            user = User.get_user_by_id(sample_user.id)
            with client.session_transaction():
                pass
            with client:
                with app.test_request_context():
                    login_user(user)

                # Simulate logged-in state via direct session cookie
                client.post(
                    "/login",
                    data={
                        "username": "testuser",
                        "password": "Test@1234",
                        "remember": True,
                    },
                    follow_redirects=False,
                )
                response = client.get("/login")
                assert response.status_code == 302

    def test_allows_unauthenticated(self, client):
        response = client.get("/login")
        assert response.status_code == 200


class TestGuestUserExempt:
    def test_guest_can_get(self, app, client, sample_user):
        with app.app_context():
            client.post(
                "/login",
                data={
                    "username": "testuser",
                    "password": "Test@1234",
                    "remember": True,
                },
            )
            response = client.get("/change/password")
            assert response.status_code == 200

    def test_guest_post_blocked(self, app, client, sample_user):
        with app.app_context():
            # testuser matches TEST_USER_USERNAME config, so POST is blocked
            client.post(
                "/login",
                data={
                    "username": "testuser",
                    "password": "Test@1234",
                    "remember": True,
                },
            )
            response = client.post(
                "/change/password",
                data={
                    "old_password": "Test@1234",
                    "new_password": "New@12345",
                    "confirm_password": "New@12345",
                    "remember": True,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302
