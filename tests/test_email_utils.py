import pytest
from unittest.mock import patch, MagicMock
from smtplib import SMTPException

from werkzeug.exceptions import ServiceUnavailable

from accounts.email_utils import (
    send_mail,
    send_confirmation_mail,
    send_reset_password,
    send_reset_email,
)
from accounts.extensions import database as db
from accounts.models import User


class TestSendMail:
    def test_send_mail_success(self, app):
        with app.app_context():
            with patch("accounts.email_utils.mail") as mock_mail:
                mock_mail.connect = MagicMock()
                mock_mail.send = MagicMock()
                send_mail(
                    subject="Test",
                    recipients=["user@example.com"],
                    body="Hello!",
                )
                mock_mail.send.assert_called_once()

    def test_send_mail_smtp_failure(self, app):
        with app.app_context():
            with patch("accounts.email_utils.mail") as mock_mail:
                mock_mail.connect = MagicMock()
                mock_mail.send.side_effect = SMTPException("SMTP error")
                with pytest.raises(ServiceUnavailable):
                    send_mail(
                        subject="Test",
                        recipients=["user@example.com"],
                        body="Hello!",
                    )

    def test_send_mail_missing_sender(self, app):
        with app.app_context():
            import os

            old = os.environ.pop("MAIL_DEFAULT_SENDER", None)
            try:
                with pytest.raises(ValueError, match="MAIL_USERNAME"):
                    send_mail(
                        subject="Test",
                        recipients=["user@example.com"],
                        body="Hello!",
                    )
            finally:
                if old is not None:
                    os.environ["MAIL_DEFAULT_SENDER"] = old


class TestSendConfirmationMail:
    def test_sends_confirmation(self, app, sample_user):
        with app.test_request_context():
            user = User.get_user_by_id(sample_user.id)
            with patch("accounts.email_utils.send_mail") as mock_send:
                send_confirmation_mail(user)
                mock_send.assert_called_once()
                args = mock_send.call_args
                assert args[1]["subject"] == "Verify Your Account"
                assert user.email in args[1]["recipients"]


class TestSendResetPassword:
    def test_sends_reset_password(self, app, sample_user):
        with app.test_request_context():
            user = User.get_user_by_id(sample_user.id)
            with patch("accounts.email_utils.send_mail") as mock_send:
                send_reset_password(user)
                mock_send.assert_called_once()
                args = mock_send.call_args
                assert args[1]["subject"] == "Reset Your Password"


class TestSendResetEmail:
    def test_sends_reset_email(self, app, sample_user):
        with app.test_request_context():
            user = User.get_user_by_id(sample_user.id)
            user.change_email = "newemail@example.com"
            db.session.commit()
            with patch("accounts.email_utils.send_mail") as mock_send:
                send_reset_email(user)
                mock_send.assert_called_once()
                args = mock_send.call_args
                assert args[1]["subject"] == "Confirm Your Email Address"
                assert "newemail@example.com" in args[1]["recipients"]
