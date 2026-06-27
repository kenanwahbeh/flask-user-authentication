import os
import tempfile
import pytest
from unittest.mock import patch

from accounts.models import User


class TestCreateTestUser:
    def test_creates_user(self, app, runner):
        with app.app_context():
            result = runner.invoke(args=["createtestuser"])
            assert result.exit_code == 0
            assert "Test user created successfully" in result.output

            user = User.get_user_by_email("testuser@example.com")
            assert user is not None
            assert user.username == "testuser"

    def test_already_exists(self, app, runner, sample_user):
        with app.app_context():
            result = runner.invoke(args=["createtestuser"])
            assert result.exit_code == 0
            assert "already created" in result.output


class TestClearMigrations:
    def test_no_migrations_dir(self, app, runner):
        with app.app_context():
            result = runner.invoke(args=["clear-migrations"])
            assert result.exit_code == 0
            assert (
                "No migrations/versions directory found" in result.output
                or "No migration files" in result.output
            )

    def test_clears_files(self, app, runner):
        with app.app_context():
            migrations_dir = os.path.join(app.root_path, "..", "migrations", "versions")
            os.makedirs(migrations_dir, exist_ok=True)
            # Create dummy migration files
            for name in ["001_init.py", "002_add_col.py"]:
                with open(os.path.join(migrations_dir, name), "w") as f:
                    f.write("# migration")
            try:
                result = runner.invoke(args=["clear-migrations"])
                assert result.exit_code == 0
                assert "Cleared 2 migration file(s)" in result.output
                # Verify files were removed
                assert len(os.listdir(migrations_dir)) == 0
            finally:
                # Cleanup
                import shutil
                shutil.rmtree(os.path.join(app.root_path, "..", "migrations"), ignore_errors=True)

    def test_empty_versions_dir(self, app, runner):
        with app.app_context():
            migrations_dir = os.path.join(app.root_path, "..", "migrations", "versions")
            os.makedirs(migrations_dir, exist_ok=True)
            try:
                result = runner.invoke(args=["clear-migrations"])
                assert result.exit_code == 0
                assert "No migration files to delete" in result.output
            finally:
                import shutil
                shutil.rmtree(os.path.join(app.root_path, "..", "migrations"), ignore_errors=True)
