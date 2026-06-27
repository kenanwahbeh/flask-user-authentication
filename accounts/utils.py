import os
import secrets
import random
import string
import uuid
import typing as t

from datetime import timedelta

from werkzeug.exceptions import InternalServerError
from werkzeug.utils import secure_filename

from flask import current_app
from flask_login import login_user


# Regex pattern for strong password validation.
# Requires: 8+ chars, at least one uppercase, one lowercase, one digit, one special char (!@#$%^&*).
PASSWORD_STRENGTH_REGEX = (
    r"(?=^.{8,}$)(?=.*\d)(?=.*[!@#$%^&*]+)(?![.\n])(?=.*[A-Z])(?=.*[a-z]).*$"
)

# Standard session duration for remembered logins.
DEFAULT_LOGIN_DURATION = timedelta(days=15)


def get_unique_id() -> t.AnyStr:
    """
    Generate a unique identifier using `uuid4()`.

    Returns:
        str: A unique identifier string.
    """
    return str(uuid.uuid4())


def unique_security_token() -> t.AnyStr:
    """
    Generate a unique security token that does not already
    exist in the `UserSecurityToken` model.

    Recursively generates a new token if a collision is found.

    Returns:
        str: A unique security token.
    """
    from .models import UserSecurityToken

    generated_token = secrets.token_hex()

    token_exist = UserSecurityToken.is_exists(generated_token)

    if not token_exist:
        return generated_token

    return unique_security_token()


def get_unique_filename(filename: t.Text = None) -> t.Text:
    """
    Generate a unique filename by appending a `uuid4()` to the original file extension.

    Returns:
        str: A new filename with a unique `uuid4()` or None if no filename is provided.
    """
    if not filename:
        return None

    filename = secure_filename(filename).split(".")
    return "{}.{}".format(str(uuid.uuid4()), filename[len(filename) - 1])


def get_full_url(endpoint: str) -> str:
    """
    Construct a full url by combining the site `URL` from
    configuration with a given endpoint.

    Returns:
        str: The full `URL`.
    """
    domain = current_app.config["SITE_URL"]
    return "".join([domain, endpoint])


def remove_existing_file(path=None):
    """
    Remove an existing file from the filesystem.
    """
    if os.path.isfile(path=path):
        os.remove(path)


def get_username_from_email(email: str) -> str:
    """
    Create a username from the email address by taking the part before the '@'.

    Args:
        email (str): The email address.

    Returns:
        str: The username derived from the email.
    """
    if not email or "@" not in email:
        return None

    return email.split("@")[0]


def generate_unique_username(email: str = None) -> str:
    """
    Generates a random username.
    If email is provided, uses the prefix of the email as a base.

    Example output: john_doe_3f9x or user_7gkx

    :param email: Optional email to derive base username from.
    :return: A random unique-looking username string.
    """
    if email:
        base = email.split("@")[0].lower()
    else:
        base = "user"

    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{base}_{suffix}"


def safe_db_commit():
    """
    Commit the current database session, raising InternalServerError on failure.

    Wraps the common pattern of committing with exception handling
    that is repeated across multiple views.

    :raises InternalServerError: If the database commit fails.
    """
    from accounts.extensions import database as db

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise InternalServerError


def login_and_remember_user(user, duration: timedelta = None):
    """
    Log in a user with the standard "remember me" configuration.

    :param user: The user instance to log in.
    :param duration: Session duration. Defaults to DEFAULT_LOGIN_DURATION (15 days).
    """
    if duration is None:
        duration = DEFAULT_LOGIN_DURATION

    login_user(user, remember=True, duration=duration)


def verify_token_or_abort(salt: str):
    """
    Verify a security token from the request query string.

    Retrieves the 'token' query parameter, verifies it against the given salt,
    and returns both the token record and the associated user if valid.

    :param salt: The salt used when the token was generated.
    :return: A tuple of (auth_token, user) if valid, or (None, None) if invalid.
    """
    from flask import request
    from accounts.models import User

    token = request.args.get("token", None)

    auth_token = User.verify_token(token=token, salt=salt)

    if auth_token:
        user = User.get_user_by_id(auth_token.user_id, raise_exception=True)
        return auth_token, user

    return None, None


def send_token_email(
    user, salt: str, endpoint: str, template: str, subject: str, link_param: str
):
    """
    Generate a token and send a templated email to the user.

    Consolidates the common pattern of: generate token → build URL → render
    template → send mail.

    :param user: The User instance to send the email to.
    :param salt: The salt for token generation.
    :param endpoint: The Flask endpoint name for the verification URL.
    :param template: The email template path to render.
    :param subject: The email subject line.
    :param link_param: The template variable name for the URL link.
    """
    from flask import render_template, url_for

    token = user.generate_token(salt=salt)
    link = get_full_url(url_for(endpoint, token=token))

    context = render_template(
        template,
        username=user.username,
        **{link_param: link},
    )

    from accounts.email_utils import send_mail

    # Use change_email if set (for email change flow), otherwise primary email.
    recipient = user.change_email or user.email
    send_mail(subject=subject, recipients=[recipient], body=context)


def download_and_save_image_from_url(
    url: str, save_path: str = None, filename: str = None
) -> str:
    """
    Downloads image from the url and saves to specific path.

    :params url: The URL of the image to download.
    :params save_path: Optional directory where the image will be saved.
    :params filename: Optional custom filename for the saved image.

    Returns:
        str: The filename of the saved image.
    """
    import requests

    from config import UPLOAD_FOLDER

    if not save_path:
        save_path = os.path.join(UPLOAD_FOLDER, "profile")

    os.makedirs(save_path, exist_ok=True)

    if not filename:
        filename = get_unique_filename(os.path.basename(url))

    file_path = os.path.join(save_path, filename)

    try:
        response = requests.get(url, stream=True, timeout=5)
        response.raise_for_status()

        if response.status_code == 200:
            with open(file_path, "wb") as file:
                file.write(response.content)
            return filename
        else:
            return None
    except requests.RequestException as e:
        current_app.logger.error(f"Error downloading image: {e}")
        return None
