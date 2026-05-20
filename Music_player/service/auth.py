from datetime import datetime, timedelta
import secrets
import re

import bcrypt

import service.database as db

from service.settings import SESSION_LIFETIME_DAYS
from service.utils import parse_cookies


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(password):
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)
    return password_hash.decode("utf-8")


def check_password(password, password_hash):
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )


def validate_username(username):
    return bool(USERNAME_RE.fullmatch(username or ""))


def validate_email(email):
    return bool(EMAIL_RE.fullmatch(email or ""))


def validate_password(password):
    return isinstance(password, str) and 8 <= len(password) <= 72


def generate_session_token():
    return secrets.token_urlsafe(48)


def create_user_session(user_id):
    session_token = generate_session_token()
    expires_at = datetime.now() + timedelta(days=SESSION_LIFETIME_DAYS)

    db.create_session(user_id, session_token, expires_at)

    return session_token


def get_current_user(headers):
    cookies = parse_cookies(headers)
    session_token = cookies.get("session_token")

    if not session_token:
        return None

    row = db.get_user_by_session_token(session_token)

    if not row:
        return None

    (
        user_id,
        username,
        email,
        password_hash,
        role,
        created_at,
        expires_at,
    ) = row

    if expires_at < datetime.now():
        db.delete_session(session_token)
        return None

    return {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "created_at": created_at.isoformat() if created_at else None,
    }

def user_to_dict(user):
    if not user:
        return None

    (
        user_id,
        username,
        email,
        password_hash,
        role,
        created_at,
    ) = user

    return {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "created_at": created_at.isoformat() if created_at else None,
    }


def public_user_to_dict(user):
    if not user:
        return None

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


def is_admin(current_user):
    return bool(current_user and current_user.get("role") == "admin")


def is_authenticated(current_user):
    return current_user is not None