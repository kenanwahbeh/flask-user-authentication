import os
import pytest

os.environ.setdefault("MAIL_PORT", "587")
os.environ.setdefault("MAIL_DEFAULT_SENDER", "test@example.com")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("CSRF_SECRET_KEY", "test-csrf-key")

from accounts import create_app
from accounts.extensions import database as db
from accounts.models import User


@pytest.fixture(scope="session")
def app():
    """Create the Flask application for the test session."""
    application = create_app("testing")
    application.config["RATELIMIT_ENABLED"] = False
    application.config["RATELIMIT_STORAGE_URI"] = "memory://"

    from accounts.extensions import limiter
    limiter.enabled = False
    application.config["SECRET_KEY"] = "test-secret-key"
    application.config["WTF_CSRF_SECRET_KEY"] = "test-csrf-key"
    application.config["SITE_URL"] = "http://localhost:5000"
    yield application


@pytest.fixture(autouse=True)
def _setup_db(app):
    """Create tables before each test and drop them after."""
    from accounts.extensions import limiter

    with app.app_context():
        db.create_all()
        limiter.reset()
        yield
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """A Flask test client."""
    return app.test_client()


@pytest.fixture()
def runner(app):
    """A Flask CLI test runner."""
    return app.test_cli_runner(mix_stderr=False)


@pytest.fixture()
def sample_user(app):
    """Create and return a sample active user."""
    with app.app_context():
        user = User.create(
            username="testuser",
            first_name="Test",
            last_name="User",
            email="testuser@example.com",
            password="Test@1234",
        )
        user.active = True
        db.session.commit()
        # Return a plain object to avoid DetachedInstanceError
        return type("UserRef", (), {"id": user.id, "username": user.username, "email": user.email})()


@pytest.fixture()
def inactive_user(app):
    """Create and return a sample inactive user."""
    with app.app_context():
        user = User.create(
            username="inactive",
            first_name="Inactive",
            last_name="User",
            email="inactive@example.com",
            password="Test@1234",
        )
        return type("UserRef", (), {"id": user.id, "username": user.username, "email": user.email})()
