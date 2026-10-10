from datetime import date, timedelta

from .conftest import register_and_login

NEW = {"company": "Acme", "role": "AI Engineer", "url": "https://acme.example/jobs/1",
       "follow_up_date": "2026-10-20", "notes": "Referred by a friend"}


def create(client, headers, **overrides):
    res = client.post("/applications", json={**NEW, **overrides}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def test_create_and_get(client, auth_headers):
    app = create(client, auth_headers)
    assert app["status"] == "Applied" and app["company"] == "Acme"
    assert client.get(f"/applications/{app['id']}", headers=auth_headers).json() == app


def test_routes_require_login(client):
    assert client.get("/applications").status_code == 401
    assert client.post("/applications", json=NEW).status_code == 401


def test_list_is_ordered_and_filterable(client, auth_headers):
    create(client, auth_headers, company="Later", follow_up_date="2026-12-01")
    create(client, auth_headers, company="NoDate", follow_up_date=None)
    create(client, auth_headers, company="Sooner", follow_up_date="2026-11-01", status="Interview")
    items = client.get("/applications", headers=auth_headers).json()["items"]
    assert [i["company"] for i in items] == ["Sooner", "Later", "NoDate"]

    interviews = client.get("/applications?status=Interview", headers=auth_headers).json()["items"]
    assert [i["company"] for i in interviews] == ["Sooner"]


def test_invalid_status_filter_is_422(client, auth_headers):
    res = client.get("/applications?status=Ghosted", headers=auth_headers)
    assert res.status_code == 422 and res.json()["error"]["details"][0]["field"] == "status"


def test_follow_up_due_is_computed_by_backend(client, auth_headers):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    due = create(client, auth_headers, follow_up_date=yesterday)
    finished = create(client, auth_headers, follow_up_date=yesterday, status="Rejected")
    assert due["follow_up_due"] is True
    assert finished["follow_up_due"] is False


def test_patch_changes_only_sent_fields_and_can_clear(client, auth_headers):
    app = create(client, auth_headers)
    res = client.patch(f"/applications/{app['id']}", json={"status": "Interview", "url": None},
                       headers=auth_headers)
    assert res.status_code == 200
    updated = res.json()
    assert updated["status"] == "Interview" and updated["url"] is None
    assert updated["company"] == "Acme" and updated["notes"] == NEW["notes"]
    assert updated["updated_at"] >= app["updated_at"]


def test_patch_validation(client, auth_headers):
    app = create(client, auth_headers)
    for body in ({}, {"company": None}, {"status": "Ghosted"}, {"user_id": 2}, {"url": "javascript:alert(1)"}):
        res = client.patch(f"/applications/{app['id']}", json=body, headers=auth_headers)
        assert res.status_code == 422, body


def test_delete(client, auth_headers):
    app = create(client, auth_headers)
    assert client.delete(f"/applications/{app['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/applications/{app['id']}", headers=auth_headers).status_code == 404


def test_users_cannot_see_or_change_each_others_applications(client):
    alice = register_and_login(client, "alice@example.com")
    bob = register_and_login(client, "bob@example.com")
    alices_app = create(client, alice)
    url = f"/applications/{alices_app['id']}"

    # Bob gets 404 (not 403), so he can't even learn that the id exists.
    assert client.get(url, headers=bob).status_code == 404
    assert client.patch(url, json={"status": "Rejected"}, headers=bob).status_code == 404
    assert client.delete(url, headers=bob).status_code == 404
    assert client.get("/applications", headers=bob).json()["items"] == []

    # Alice's application is untouched.
    assert client.get(url, headers=alice).json()["status"] == "Applied"


def test_bad_ids_are_validated(client, auth_headers):
    for bad in ("0", "-1", "abc", str(2**63)):
        assert client.get(f"/applications/{bad}", headers=auth_headers).status_code == 422, bad
    assert client.get("/applications/999999", headers=auth_headers).status_code == 404


def test_database_errors_are_not_leaked(client, auth_headers, admin_conn):
    # Break the table on purpose so the next query fails inside Postgres.
    admin_conn.execute("ALTER TABLE jobtracker_applications RENAME COLUMN notes TO notes_tmp")
    try:
        res = client.get("/applications", headers=auth_headers)
    finally:
        admin_conn.execute("ALTER TABLE jobtracker_applications RENAME COLUMN notes_tmp TO notes")
    assert res.status_code == 500
    assert res.json() == {"error": {"code": "internal_error",
                                    "message": "Something went wrong on our side. Please try again."}}
    for leak in ("psycopg", "notes", "Traceback", "SELECT", "/home"):
        assert leak not in res.text
