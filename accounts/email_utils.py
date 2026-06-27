import os
import click
import typing as t

from smtplib import SMTPException
from werkzeug.exceptions import ServiceUnavailable

from flask import current_app
from flask_mail import Message

from accounts.extensions import mail
from accounts.models import User
from accounts.utils import send_token_email


def send_mail(subject: t.AnyStr, recipients: t.List[str], body: t.Text):
    """
    Sends an email using the Flask-Mail extension.

    :param subject: The subject of the email.
    :param recipients: A list of recipient email addresses.
    :param body: The body content of the email.

    :raises ServiceUnavailable: If the SMTP service is unavailable.
    """
    sender: str = os.environ.get("MAIL_DEFAULT_SENDER", None)

    if not sender:
        raise ValueError("`MAIL_USERNAME` environment variable is not set")

    message = Message(subject=subject, sender=sender, recipients=recipients)
    message.body = body

    click.echo(message.body)

    try:
        mail.connect()
        mail.send(message)
    except SMTPException as e:
        raise ServiceUnavailable(
            description=(
                "The SMTP mail service is currently not available. "
                "Please try later or contact the developers team."
            )
        )


def send_confirmation_mail(user: User = None):
    """
    Sends an account verification email to the specified user.

    :param user: The specified user for sending email.
    """
    send_token_email(
        user=user,
        salt=current_app.config["SALT_ACCOUNT_CONFIRM"],
        endpoint="accounts.confirm_account",
        template="emails/verify_account.txt",
        subject="Verify Your Account",
        link_param="verification_link",
    )


def send_reset_password(user: User = None):
    """
    Sends a reset-password email to the specified user.

    :param user: The specified user for sending email.
    """
    send_token_email(
        user=user,
        salt=current_app.config["SALT_RESET_PASSWORD"],
        endpoint="accounts.reset_password",
        template="emails/reset_password.txt",
        subject="Reset Your Password",
        link_param="reset_link",
    )


def send_reset_email(user: User = None):
    """
    Sends a reset new email-address email to the specified user.

    :param user: The specified user for sending email.
    """
    send_token_email(
        user=user,
        salt=current_app.config["SALT_CHANGE_EMAIL"],
        endpoint="accounts.confirm_email",
        template="emails/reset_email.txt",
        subject="Confirm Your Email Address",
        link_param="confirmation_link",
    )
