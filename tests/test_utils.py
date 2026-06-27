import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from accounts.utils import (
    get_unique_id,
    get_unique_filename,
    get_full_url,
    remove_existing_file,
    get_username_from_email,
    generate_unique_username,
    download_and_save_image_from_url,
)


class TestGetUniqueId:
    def test_returns_string(self):
        uid = get_unique_id()
        assert isinstance(uid, str)

    def test_returns_uuid_format(self):
        uid = get_unique_id()
        parts = uid.split("-")
        assert len(parts) == 5

    def test_unique_across_calls(self):
        ids = {get_unique_id() for _ in range(50)}
        assert len(ids) == 50


class TestGetUniqueFilename:
    def test_returns_none_for_empty(self):
        assert get_unique_filename(None) is None
        assert get_unique_filename("") is None

    def test_preserves_extension(self):
        result = get_unique_filename("photo.jpg")
        assert result.endswith(".jpg")

    def test_returns_unique_names(self):
        names = {get_unique_filename("a.png") for _ in range(20)}
        assert len(names) == 20

    def test_handles_multiple_dots(self):
        result = get_unique_filename("my.photo.file.png")
        assert result.endswith(".png")


class TestGetFullUrl:
    def test_combines_domain_and_endpoint(self, app):
        with app.app_context():
            app.config["SITE_URL"] = "http://localhost:5000"
            result = get_full_url("/some/path")
            assert result == "http://localhost:5000/some/path"


class TestRemoveExistingFile:
    def test_removes_existing_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        assert os.path.isfile(path)
        remove_existing_file(path)
        assert not os.path.isfile(path)

    def test_no_error_for_nonexistent(self):
        remove_existing_file("/tmp/no_such_file_xyz_12345")


class TestGetUsernameFromEmail:
    def test_extracts_username(self):
        assert get_username_from_email("john@example.com") == "john"

    def test_returns_none_for_invalid(self):
        assert get_username_from_email(None) is None
        assert get_username_from_email("") is None
        assert get_username_from_email("noemail") is None


class TestGenerateUniqueUsername:
    def test_uses_email_prefix(self):
        result = generate_unique_username("alice@example.com")
        assert result.startswith("alice_")
        assert len(result) == len("alice_") + 4

    def test_falls_back_to_user(self):
        result = generate_unique_username(None)
        assert result.startswith("user_")

    def test_lowercase(self):
        result = generate_unique_username("ALICE@EXAMPLE.COM")
        assert result.startswith("alice_")


class TestDownloadAndSaveImage:
    def test_successful_download(self, app):
        with app.app_context():
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"\x89PNG fake image data"
            mock_response.raise_for_status = MagicMock()

            with tempfile.TemporaryDirectory() as tmpdir:
                with patch("requests.get", return_value=mock_response):
                    result = download_and_save_image_from_url(
                        url="http://example.com/avatar.jpg",
                        save_path=tmpdir,
                        filename="test_img.jpg",
                    )
                    assert result == "test_img.jpg"
                    assert os.path.isfile(os.path.join(tmpdir, "test_img.jpg"))

    def test_request_failure(self, app):
        with app.app_context():
            import requests as req

            with patch(
                "requests.get",
                side_effect=req.RequestException("fail"),
            ):
                result = download_and_save_image_from_url(
                    url="http://example.com/bad.jpg",
                    save_path="/tmp",
                    filename="fail.jpg",
                )
                assert result is None
