from fastapi import APIRouter, Depends, Request, status
from psycopg import Connection
from psycopg.errors import UniqueViolation

from .. import repository
from ..db import get_conn
from ..errors import ApiError
from ..schemas import Credentials, TokenOut, UserOut
from ..security import create_access_token, get_current_user_id, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register(body: Credentials, conn: Connection = Depends(get_conn)):
    try:
        user = repository.create_user(conn, body.email, hash_password(body.password))
    except UniqueViolation:
        raise ApiError(409, "conflict", "An account with this email already exists. Try logging in.")
    return user


@router.post("/login", response_model=TokenOut)
def login(body: Credentials, request: Request, conn: Connection = Depends(get_conn)):
    user = repository.get_user_by_email(conn, body.email)
    # Same message whether the email or the password is wrong.
    if not verify_password(body.password, user["password_hash"] if user else None):
        raise ApiError(401, "unauthorized", "Email or password is incorrect.")
    settings = request.app.state.settings
    token = create_access_token(user["id"], settings.jwt_secret, settings.access_token_minutes)
    return TokenOut(access_token=token, expires_in=settings.access_token_minutes * 60)


@router.get("/me", response_model=UserOut)
def me(user_id: int = Depends(get_current_user_id), conn: Connection = Depends(get_conn)):
    user = repository.get_user_by_id(conn, user_id)
    if user is None:
        raise ApiError(401, "unauthorized", "Your account was not found. Please log in again.")
    return user
