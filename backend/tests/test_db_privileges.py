"""Checks the database itself: the app role's limits, RLS, and constraints."""
import psycopg
import pytest


@pytest.fixture
def app_conn(app_database_url, admin_conn):
    admin_conn.execute("TRUNCATE jobtracker_applications, jobtracker_users RESTART IDENTITY CASCADE")
    with psycopg.connect(app_database_url, autocommit=True) as conn:
        yield conn


@pytest.mark.parametrize("statement", [
    "CREATE TABLE jobtracker_hack (id int)",
    "DROP TABLE jobtracker_applications",
    "TRUNCATE jobtracker_applications",
    "ALTER TABLE jobtracker_applications ADD COLUMN x int",
    "UPDATE jobtracker_users SET email = 'x@y.z'",
    "DELETE FROM jobtracker_users",
])
def test_app_role_cannot_change_structure_or_users(app_conn, statement):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_conn.execute(statement)


def test_rls_hides_rows_from_roles_without_a_policy(app_conn, admin_conn):
    # Simulates Supabase's Data API roles: table access granted, but no RLS policy.
    app_conn.execute("INSERT INTO jobtracker_users (email, password_hash) VALUES ('a@b.co', 'h')")
    admin_conn.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'jobtracker_probe') THEN
                CREATE ROLE jobtracker_probe NOLOGIN;
            END IF;
        END $$;
        GRANT USAGE ON SCHEMA public TO jobtracker_probe;
        GRANT SELECT ON jobtracker_users TO jobtracker_probe;
    """)
    with admin_conn.transaction():
        admin_conn.execute("SET LOCAL ROLE jobtracker_probe")
        assert admin_conn.execute("SELECT count(*) FROM jobtracker_users").fetchone()[0] == 0
    assert app_conn.execute("SELECT count(*) FROM jobtracker_users").fetchone()[0] == 1


@pytest.mark.parametrize("column, value", [
    ("status", "Ghosted"),
    ("url", "javascript:alert(1)"),
    ("company", "   "),
])
def test_check_constraints_back_up_the_api(app_conn, column, value):
    user_id = app_conn.execute(
        "INSERT INTO jobtracker_users (email, password_hash) VALUES ('c@d.co', 'h') RETURNING id"
    ).fetchone()[0]
    row = {"company": "Acme", "role": "Dev", "status": "Applied", "url": None, column: value}
    with pytest.raises(psycopg.errors.CheckViolation):
        app_conn.execute(
            "INSERT INTO jobtracker_applications (user_id, company, role, status, url) VALUES (%s,%s,%s,%s,%s)",
            (user_id, row["company"], row["role"], row["status"], row["url"]),
        )


def test_uppercase_email_rejected_by_database(app_conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        app_conn.execute("INSERT INTO jobtracker_users (email, password_hash) VALUES ('A@B.co', 'h')")
