from contextlib import contextmanager
from app.database import get_db_connection


def get_connection():
    return get_db_connection()


@contextmanager
def connection_scope():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
