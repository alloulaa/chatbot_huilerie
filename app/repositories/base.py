from app.core.db import get_connection


class BaseRepository:
    def _fetchone(self, query: str, params: tuple = ()):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    def _fetchall(self, query: str, params: tuple = ()):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def _execute(self, query: str, params: tuple = ()):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
        finally:
            cursor.close()
            conn.close()
