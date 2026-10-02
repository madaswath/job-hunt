from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from jobhunt_api.settings import settings


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn


def fetch_all(sql: str, params: tuple | dict | None = None) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def fetch_one(sql: str, params: tuple | dict | None = None) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute(sql: str, params: tuple | dict | None = None) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
