from app.repositories.base import BaseRepository


class HuilerieRepository(BaseRepository):
    def list_names(self):
        rows = self._fetchall("SELECT nom FROM huilerie ORDER BY nom")
        return [row["nom"] for row in rows]
