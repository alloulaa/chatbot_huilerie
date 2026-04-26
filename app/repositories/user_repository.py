from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def get_user(self, user_id: int):
        return self._fetchone(
            """
            SELECT u.id, u.nom, u.role, h.nom AS huilerie_nom, u.huilerie_id
            FROM user_account u
            LEFT JOIN huilerie h ON h.id = u.huilerie_id
            WHERE u.id = ?
            """,
            (user_id,),
        )
