"""All SQL lives here. Every query is parameterised, and every application query
includes user_id, so a user can never read or change another user's rows."""
from psycopg import Connection, sql

APPLICATION_COLUMNS = "id, company, role, url, status, follow_up_date, notes, created_at, updated_at"

# Whitelist of columns PATCH may change. Column names come from this fixed set,
# never from the request, and values are always passed as parameters.
UPDATABLE_COLUMNS = {"company", "role", "url", "status", "follow_up_date", "notes"}


# ---------- Users ----------

def create_user(conn: Connection, email: str, password_hash: str) -> dict:
    return conn.execute(
        "INSERT INTO jobtracker_users (email, password_hash) VALUES (%s, %s) RETURNING id, email",
        (email, password_hash),
    ).fetchone()


def get_user_by_email(conn: Connection, email: str) -> dict | None:
    return conn.execute(
        "SELECT id, email, password_hash FROM jobtracker_users WHERE email = %s", (email,)
    ).fetchone()


def get_user_by_id(conn: Connection, user_id: int) -> dict | None:
    return conn.execute("SELECT id, email FROM jobtracker_users WHERE id = %s", (user_id,)).fetchone()


# ---------- Applications ----------

def list_applications(conn: Connection, user_id: int, status: str | None) -> list[dict]:
    query = f"SELECT {APPLICATION_COLUMNS} FROM jobtracker_applications WHERE user_id = %s"
    params: list = [user_id]
    if status is not None:
        query += " AND status = %s"
        params.append(status)
    query += " ORDER BY follow_up_date ASC NULLS LAST, created_at DESC, id DESC"
    return conn.execute(query, params).fetchall()


def get_application(conn: Connection, user_id: int, application_id: int) -> dict | None:
    return conn.execute(
        f"SELECT {APPLICATION_COLUMNS} FROM jobtracker_applications WHERE id = %s AND user_id = %s",
        (application_id, user_id),
    ).fetchone()


def create_application(conn: Connection, user_id: int, data: dict) -> dict:
    return conn.execute(
        f"""INSERT INTO jobtracker_applications
                (user_id, company, role, url, status, follow_up_date, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING {APPLICATION_COLUMNS}""",
        (user_id, data["company"], data["role"], data["url"], data["status"],
         data["follow_up_date"], data["notes"]),
    ).fetchone()


def update_application(conn: Connection, user_id: int, application_id: int, changes: dict) -> dict | None:
    columns = [c for c in changes if c in UPDATABLE_COLUMNS]
    assignments = [sql.SQL("{} = %s").format(sql.Identifier(c)) for c in columns]
    assignments.append(sql.SQL("updated_at = now()"))
    query = sql.SQL(
        "UPDATE jobtracker_applications SET {} WHERE id = %s AND user_id = %s RETURNING "
        + APPLICATION_COLUMNS
    ).format(sql.SQL(", ").join(assignments))
    params = [changes[c] for c in columns] + [application_id, user_id]
    return conn.execute(query, params).fetchone()


def delete_application(conn: Connection, user_id: int, application_id: int) -> bool:
    cur = conn.execute(
        "DELETE FROM jobtracker_applications WHERE id = %s AND user_id = %s", (application_id, user_id)
    )
    return cur.rowcount == 1
