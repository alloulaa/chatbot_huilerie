from app.repositories.base import BaseRepository


class ReceptionRepository(BaseRepository):
    def total_reception(self, start_date: str, end_date: str, huilerie: str | None = None):
        params = [start_date, end_date]
        query = """
            SELECT COALESCE(SUM(r.quantite_kg),0) AS total
            FROM reception_olive r
            JOIN huilerie h ON h.id = r.huilerie_id
            WHERE r.date_reception BETWEEN ? AND ?
        """
        if huilerie:
            query += " AND lower(h.nom)=lower(?)"
            params.append(huilerie)
        return self._fetchone(query, tuple(params))
