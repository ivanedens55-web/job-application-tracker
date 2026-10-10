"""Unit tests: no database needed."""
from datetime import date, datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError

from app.applications_logic import is_follow_up_due
from app.errors import ApiError
from app.schemas import ApplicationCreate, ApplicationUpdate, Credentials
from app.security import create_access_token, decode_access_token, hash_password, verify_password

TODAY = date(2026, 10, 7)
SECRET = "unit-test-secret-that-is-at-least-32-chars"


# ---------- follow_up_due ----------

@pytest.mark.parametrize(
    "status, follow_up, expected",
    [
        ("Applied", TODAY, True),                        # due today
        ("Interview", TODAY - timedelta(days=3), True),  # overdue
        ("Applied", TODAY + timedelta(days=1), False),   # in the future
        ("Applied", None, False),                        # no date set
        ("Offer", TODAY - timedelta(days=1), False),     # finished: no follow-up needed
        ("Rejected", TODAY - timedelta(days=1), False),
    ],
)
def test_is_follow_up_due(status, follow_up, expected):
    assert is_follow_up_due(status, follow_up, TODAY) is expected


# ---------- validation ----------

def test_create_defaults_and_trimming():
    app = ApplicationCreate(company="  Acme  ", role="Engineer")
    assert app.company == "Acme"
    assert app.status.value == "Applied"
    assert app.url is None and app.notes is None


@pytest.mark.parametrize("bad_url", ["javascript:alert(1)", "ftp://x.com", "example.com", "https://"])
def test_create_rejects_non_http_urls(bad_url):
    with pytest.raises(ValidationError):
        ApplicationCreate(company="Acme", role="Engineer", url=bad_url)


def test_create_rejects_blank_company_and_long_fields():
    with pytest.raises(ValidationError):
        ApplicationCreate(company="   ", role="Engineer")
    with pytest.raises(ValidationError):
        ApplicationCreate(company="A" * 121, role="Engineer")
    with pytest.raises(ValidationError):
        ApplicationCreate(company="Acme", role="Engineer", notes="x" * 2001)


def test_create_rejects_unknown_status_and_extra_fields():
    with pytest.raises(ValidationError):
        ApplicationCreate(company="Acme", role="Engineer", status="Ghosted")
    with pytest.raises(ValidationError):
        ApplicationCreate(company="Acme", role="Engineer", user_id=99)


def test_update_needs_a_field_and_cannot_clear_required_ones():
    with pytest.raises(ValidationError):
        ApplicationUpdate()
    with pytest.raises(ValidationError):
        ApplicationUpdate(company=None)
    assert ApplicationUpdate(url=None).changes() == {"url": None}
    assert ApplicationUpdate(status="Offer").changes() == {"status": "Offer"}


def test_email_is_lowercased_and_password_length_checked():
    assert Credentials(email="Ivan@Example.COM", password="12345678").email == "ivan@example.com"
    with pytest.raises(ValidationError):
        Credentials(email="ivan@example.com", password="short")
    with pytest.raises(ValidationError):
        Credentials(email="not-an-email", password="12345678")


# ---------- passwords and tokens ----------

def test_password_hashing():
    hashed = hash_password("correct-horse-1")
    assert hashed.startswith("$argon2id$") and "correct-horse-1" not in hashed
    assert verify_password("correct-horse-1", hashed)
    assert not verify_password("wrong-password", hashed)
    assert not verify_password("anything", None)  # unknown user


def test_token_round_trip():
    token = create_access_token(42, SECRET, minutes=30)
    assert decode_access_token(token, SECRET) == 42


def test_expired_wrong_secret_and_unsigned_tokens_are_rejected():
    expired = create_access_token(42, SECRET, minutes=-1)
    wrong_secret = create_access_token(42, "another-secret-that-is-at-least-32-chars", minutes=30)
    unsigned = jwt.encode({"sub": "42", "type": "access",
                           "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, key=None, algorithm="none")
    for token in (expired, wrong_secret, unsigned, "not-a-token"):
        with pytest.raises(ApiError) as exc:
            decode_access_token(token, SECRET)
        assert exc.value.status_code == 401
