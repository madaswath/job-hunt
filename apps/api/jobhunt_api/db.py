from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

import psycopg
from psycopg.rows import dict_row

from jobhunt_api.settings import settings

_uow: ContextVar[psycopg.Connection | None] = ContextVar("jobhunt_uow", default=None)


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    existing = _uow.get()
    if existing is not None:
        yield existing
        return
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn


@contextmanager
def unit_of_work() -> Iterator[psycopg.Connection]:
    existing = _uow.get()
    if existing is not None:
        yield existing
        return
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        token = _uow.set(conn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _uow.reset(token)


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
        if _uow.get() is None:
            conn.commit()
