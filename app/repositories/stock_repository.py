from app.repositories.base import BaseRepository


class StockRepository(BaseRepository):
    def current_stock(self, huilerie: str | None = None, type_huile: str | None = None):
        params = []
        query = """
            SELECT total_stock AS total
            FROM vue_stock_total
            WHERE 1=1
        """
        if type_huile:
            query += " AND LOWER(type_stock) = LOWER(%s)"
            params.append(type_huile)
        if huilerie:
            query += " AND LOWER(huilerie) = LOWER(%s)"
            params.append(huilerie)
        query += " LIMIT 1"
        return self._fetchone(query, tuple(params))
