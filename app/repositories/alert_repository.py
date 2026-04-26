from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository):
    def active_alerts(self, huilerie: str | None = None):
        params = []
        query = """
            SELECT a.date_alerte, a.type_alerte, a.priorite, a.message, h.nom AS huilerie
            FROM alertes a
            LEFT JOIN huilerie h ON h.id = a.huilerie_id
            WHERE 1=1
        """
        if huilerie:
            query += " AND lower(h.nom)=lower(?)"
            params.append(huilerie)
        query += " ORDER BY CASE a.priorite WHEN 'haute' THEN 1 WHEN 'moyenne' THEN 2 ELSE 3 END, a.date_alerte DESC"
        return self._fetchall(query, tuple(params))
