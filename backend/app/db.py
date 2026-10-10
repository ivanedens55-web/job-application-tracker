"""Database connection pool. All queries use parameters (%s), never string-built SQL."""
from collections.abc import Iterator

from fastapi import Request
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def create_pool(database_url: str) -> ConnectionPool:
    # Small pool: Supabase's Session pooler has a low connection limit on the free plan.
    return ConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=5,
        # autocommit: every operation here is a single SQL statement, so each one
        # commits immediately, before the response is sent.
        kwargs={"row_factory": dict_row, "autocommit": True},
        open=False,
    )


def get_conn(request: Request) -> Iterator[Connection]:
    """FastAPI dependency: borrow one connection from the pool for this request."""
    pool: ConnectionPool = request.app.state.pool
    with pool.connection() as conn:
        yield conn
