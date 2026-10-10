"""Password hashing (Argon2id) and JWT access tokens."""
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .errors import ApiError

_hasher = PasswordHasher()  # Argon2id with the library's recommended parameters.
_bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"

# Used when the email doesn't exist, so a failed login takes the same time
# whether or not the account exists (makes guessing valid emails harder).
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(user_id: int, secret: str, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "type": "access", "iat": now, "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, secret: str) -> int:
    """Return the user id from a valid token, or raise ApiError(401)."""
    try:
        # algorithms is pinned, so a token signed with "none" or another algorithm is rejected.
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "unauthorized", "Your session has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise ApiError(401, "unauthorized", "Invalid access token. Please log in again.")
    if payload.get("type") != "access" or not str(payload.get("sub", "")).isdigit():
        raise ApiError(401, "unauthorized", "Invalid access token. Please log in again.")
    return int(payload["sub"])


def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    """FastAPI dependency for protected routes."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "unauthorized", "You need to log in to do this.")
    return decode_access_token(credentials.credentials, request.app.state.settings.jwt_secret)
