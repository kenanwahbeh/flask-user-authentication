import os
import pytest

os.environ.setdefault("MAIL_PORT", "587")
os.environ.setdefault("MAIL_DEFAULT_SENDER", "test@example.com")
os.environ.setdefault("POSTGRES_PORT", "5432")

from accounts import (
    create_app,
    config_application,
    config_errorhandler,
)


class TestCreateApp:
    def test_creates_testing_app(self):
        app = create_app("testing")
        assert app is not None
        assert app.config["TESTING"] is True

    def test_creates_development_app(self):
        app = create_app("development")
        assert app.config["DEBUG"] is True

    def test_invalid_config_raises(self):
        with pytest.raises(RuntimeError, match="Invalid configuration type"):
            create_app("invalid_config")

    def test_none_config_raises(self):
        with pytest.raises(RuntimeError, match="Configuration type must be provided"):
            create_app(None)


class TestChangeTheme:
    def test_change_theme(self):
        app = create_app("testing")
        client = app.test_client()
        with app.app_context():
            response = client.get("/change-theme?theme=flatly", follow_redirects=False)
            assert response.status_code == 302
            cookies = response.headers.getlist("Set-Cookie")
            cookie_str = "; ".join(cookies)
            assert "theme=flatly" in cookie_str

    def test_change_theme_invalid(self):
        app = create_app("testing")
        client = app.test_client()
        with app.app_context():
            response = client.get(
                "/change-theme?theme=nonexistent", follow_redirects=False
            )
            assert response.status_code == 302


class TestChangeLang:
    def test_change_lang_valid(self):
        app = create_app("testing")
        client = app.test_client()
        with app.app_context():
            response = client.get("/change-lang?lang=es", follow_redirects=False)
            assert response.status_code == 302
            cookies = response.headers.getlist("Set-Cookie")
            cookie_str = "; ".join(cookies)
            assert "lang=es" in cookie_str

    def test_change_lang_invalid(self):
        app = create_app("testing")
        client = app.test_client()
        with app.app_context():
            response = client.get(
                "/change-lang?lang=zz", follow_redirects=False
            )
            assert response.status_code == 302
            cookies = response.headers.getlist("Set-Cookie")
            cookie_str = "; ".join(cookies)
            assert "lang=en" in cookie_str


class TestConfig:
    def test_testing_config(self):
        app = create_app("testing")
        assert app.config["TESTING"] is True
        assert app.config["WTF_CSRF_ENABLED"] is False
        assert "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]
