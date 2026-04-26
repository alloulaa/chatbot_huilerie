from app.repositories.base import BaseRepository
from app.core.db import get_connection


class ChatRepository(BaseRepository):
    def ensure_session(self, session_id: str, user_id: int):
        row = self._fetchone("SELECT * FROM chat_session WHERE session_id=?", (session_id,))
        if row:
            return row
        self._execute("INSERT INTO chat_session (session_id, user_id) VALUES (?, ?)", (session_id, user_id))
        return self._fetchone("SELECT * FROM chat_session WHERE session_id=?", (session_id,))

    def update_context(self, session_id: str, huilerie: str | None, period_label: str | None, intent: str | None):
        self._execute(
            "UPDATE chat_session SET last_huilerie=?, last_period_label=?, last_intent=? WHERE session_id=?",
            (huilerie, period_label, intent, session_id),
        )

    def get_context(self, session_id: str):
        return self._fetchone("SELECT * FROM chat_session WHERE session_id=?", (session_id,))

    def add_message(self, session_id: str, sender: str, content: str):
        self._execute(
            "INSERT INTO chat_message (session_id, sender, content) VALUES (?, ?, ?)",
            (session_id, sender, content),
        )

    def history(self, session_id: str):
        return self._fetchall(
            "SELECT sender, content, created_at FROM chat_message WHERE session_id=? ORDER BY id ASC",
            (session_id,),
        )
