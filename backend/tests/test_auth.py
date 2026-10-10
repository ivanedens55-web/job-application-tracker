from .conftest import register_and_login

CREDS = {"email": "ivan@example.com", "password": "correct-horse-1"}


def test_register_returns_user_without_password(client):
    res = client.post("/auth/register", json=CREDS)
    assert res.status_code == 201
    assert res.json() == {"id": 1, "email": "ivan@example.com"}


def test_duplicate_email_is_rejected_case_insensitively(client):
    client.post("/auth/register", json=CREDS)
    res = client.post("/auth/register", json={**CREDS, "email": "IVAN@example.com"})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "conflict"


def test_register_validation_uses_error_format(client):
    res = client.post("/auth/register", json={"email": "ivan@example.com", "password": "short"})
    assert res.status_code == 422
    error = res.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"][0]["field"] == "password"
    assert "short" not in res.text  # the submitted value is never echoed back


def test_password_is_stored_hashed(client, admin_conn):
    client.post("/auth/register", json=CREDS)
    stored = admin_conn.execute("SELECT password_hash FROM jobtracker_users").fetchone()[0]
    assert stored.startswith("$argon2id$") and CREDS["password"] not in stored


def test_login_success(client):
    client.post("/auth/register", json=CREDS)
    res = client.post("/auth/login", json=CREDS)
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 1800 and body["access_token"]


def test_login_failures_give_the_same_message(client):
    client.post("/auth/register", json=CREDS)
    wrong_password = client.post("/auth/login", json={**CREDS, "password": "wrong-password"})
    unknown_email = client.post("/auth/login", json={**CREDS, "email": "nobody@example.com"})
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_requires_a_valid_token(client):
    headers = register_and_login(client)
    assert client.get("/auth/me", headers=headers).json()["email"] == "ivan@example.com"
    for bad in ({}, {"Authorization": "Bearer nonsense"}, {"Authorization": "Basic abc"}):
        res = client.get("/auth/me", headers=bad)
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "unauthorized"
